#!/usr/bin/env python3
import argparse, base64, hashlib, json, os, re, shlex, subprocess, sys, time, fcntl, tempfile, shutil, signal, sqlite3, atexit
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error
from urllib.parse import urlparse

ROOT = Path('/opt/ai-loop')
STATE_ROOT = Path('/var/lib/ai-loop/state')
RUNS_ROOT = Path('/var/lib/ai-loop/runs')
UPLOAD_ROOT = Path(os.environ.get('AI_LOOP_PLAYWRIGHT_UPLOAD_ROOT', str(Path.home()/'.playwright-mcp/uploads')))
PROMPTS = ROOT / 'prompts'
REPO_DIR_DEFAULT = Path('/mnt/d/works/bot_trad/bot_trading')
VPS_WRAPPER = ROOT / 'bin/vps-ssh'
CI_STATUS = ROOT / 'bin/ci-status'
PROJECT_YAML = ROOT / 'project.yaml'
ENV_FILE = ROOT / 'ai-loop.env'

POLL_GENERATING_BASE = int(os.environ.get('AI_LOOP_GENERATING_POLL_BASE_SECONDS','60'))
POLL_GENERATING_MAX = int(os.environ.get('AI_LOOP_GENERATING_POLL_MAX_SECONDS','300'))
POLL_CI = 45
OPENCODE_TURN_TIMEOUT = int(os.environ.get('AI_LOOP_OPENCODE_TURN_TIMEOUT_SECONDS','2700'))
DEFAULT_ACTION_TIMEOUT = 180
MAX_NO_ACTION_FOLLOWUPS = 1
PLAN_ARTIFACT_MAX_ATTEMPTS = int(os.environ.get('AI_LOOP_PLAN_ARTIFACT_MAX_ATTEMPTS','3'))
PLAN_ARTIFACT_BLOCKED_RECHECK_SECONDS = int(os.environ.get('AI_LOOP_PLAN_ARTIFACT_BLOCKED_RECHECK_SECONDS','900'))
PLAN_ARTIFACT_MAX_REQUESTS = int(os.environ.get('AI_LOOP_PLAN_ARTIFACT_MAX_REQUESTS','1'))
SEMANTIC_MIN_CONFIDENCE = float(os.environ.get('AI_LOOP_SEMANTIC_MIN_CONFIDENCE','0.55'))
SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS = int(os.environ.get('AI_LOOP_SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS','300'))
NEW_MESSAGE_POLL_BASE_SECONDS = int(os.environ.get('AI_LOOP_NEW_MESSAGE_POLL_BASE_SECONDS','30'))
NEW_MESSAGE_POLL_MAX_SECONDS = int(os.environ.get('AI_LOOP_NEW_MESSAGE_POLL_MAX_SECONDS','300'))
INLINE_EVIDENCE_LIMIT = 10000
MIN_SEND_INTERVAL = int(os.environ.get('AI_LOOP_MIN_SEND_INTERVAL_SECONDS','300'))
RATE_LIMIT_BASE = int(os.environ.get('AI_LOOP_RATE_LIMIT_BASE_SECONDS','300'))
RATE_LIMIT_STEP = int(os.environ.get('AI_LOOP_RATE_LIMIT_STEP_SECONDS','120'))
STARTUP_QUIET_SECONDS = int(os.environ.get('AI_LOOP_STARTUP_QUIET_SECONDS','300'))
RESPONSE_SETTLE_SECONDS = int(os.environ.get('AI_LOOP_RESPONSE_SETTLE_SECONDS','12'))
DOM_HANDOFF_ROOT = Path(os.environ.get('AI_LOOP_DOM_HANDOFF_ROOT', str(Path.home()/'.playwright-mcp/handoff')))
VERSION = '4.2.0'
CHATGPT_REQUIRED_SURFACE = 'chat'
CHATGPT_REQUIRED_MODEL = 'GPT-5.6 Sol'
CHATGPT_REQUIRED_REASONING = 'High'
CHATGPT_FORBIDDEN_SURFACES = {'work','codex'}
BROWSER_PROFILE = Path(os.environ.get('AI_LOOP_BROWSER_PROFILE', str(Path.home()/'.cache/ai-loop-chatgpt-profile')))
OPENCODE_CLI_DIR = Path(os.environ.get('AI_LOOP_OPENCODE_CLI_DIR','/mnt/d/works/ai-control-plane'))
OPENCODE_CLI_LOCK = STATE_ROOT/'.opencode-cli-browser.lock'
ARTIFACT_WORKER = Path(os.environ.get('AI_LOOP_ARTIFACT_WORKER', str(ROOT/'playwright-artifact-worker.cjs')))
BOOTSTRAP_OBSERVER_WORKER = Path(os.environ.get('AI_LOOP_BOOTSTRAP_OBSERVER_WORKER', str(ROOT/'playwright-bootstrap-observer.cjs')))
BOOTSTRAP_WORKER = Path(os.environ.get('AI_LOOP_BOOTSTRAP_WORKER', str(ROOT/'playwright-bootstrap-worker.cjs')))
BROWSER_BROKER = Path(os.environ.get('AI_LOOP_BROWSER_BROKER', str(ROOT/'browser-broker-v1.cjs')))
BROWSER_ACTION_TIMEOUT_MS = int(os.environ.get('AI_LOOP_BROWSER_ACTION_TIMEOUT_MS','8000'))
BROWSER_NAVIGATION_TIMEOUT_MS = int(os.environ.get('AI_LOOP_BROWSER_NAVIGATION_TIMEOUT_MS','30000'))
BROWSER_SETTLE_TIMEOUT_MS = int(os.environ.get('AI_LOOP_BROWSER_SETTLE_TIMEOUT_MS','12000'))
ASSISTANT_RESPONSE_TIMEOUT_MS = int(os.environ.get('AI_LOOP_ASSISTANT_RESPONSE_TIMEOUT_MS','900000'))
_BROWSER_BROKER_PROC = None
_BROWSER_BROKER_RUN_ID = ''
_BROWSER_BROKER_EPOCH = ''
_BROWSER_BROKER_STDERR = None
CHROME_EXECUTABLE = os.environ.get('AI_LOOP_CHROME_EXECUTABLE','/opt/google/chrome/chrome')
_BROWSER_OWNER_SID = ''
_BROWSER_OWNER_STATE = None
_BROWSER_OWNER_STATE_PATH = None

DISABLED_TOOLS = {
    'bash': False, 'read': False, 'write': False, 'edit': False,
    'glob': False, 'grep': False, 'task': False, 'todowrite': False,
    'webfetch': False, 'websearch': False, 'patch': False,
}

EVENT_SCHEMA = {
  'type': 'object',
  'additionalProperties': False,
  'properties': {
    'state': {'type':'string','enum':['GENERATING','RATE_LIMIT','ACTIONS','CONTINUE','NO_ACTIONS','GO','PLAN_READY','ERROR','BLOCKED','WAITING','SETTLED']},
    'chat_url': {'type':'string'},
    'sol_text': {'type':'string'},
    'needs_operator_capabilities': {'type':'boolean'},
    'actions': {
      'type':'array',
      'items': {
        'type':'object','additionalProperties':False,
        'properties': {
          'id': {'type':'string'},
          'target': {'type':'string','enum':['local','vps','github-readonly']},
          'payload_transport': {'type':'string','enum':['dom_file','chunked_file']},
          'command_sha256': {'type':'string'},
          'command_len': {'type':'integer','minimum':1},
          'timeout_seconds': {'type':'integer','minimum':1,'maximum':3600},
        },
        'required':['id','target','payload_transport','command_sha256','command_len','timeout_seconds']
      }
    },
    'plan_filename': {'type':'string'},
    'plan_markdown': {'type':'string'},
    'error': {'type':'string'},
    'delivery_status': {'type':'string','enum':['NONE','SENT','ALREADY_SENT','NOT_SENT_GENERATING','NOT_SENT_RATE_LIMIT']},
    'ui_surface': {'type':'string'},
    'ui_model': {'type':'string'},
    'ui_reasoning': {'type':'string'},
    'chat_policy_status': {'type':'string','enum':['PASS','FAIL','NOT_CHECKED']},
  },
  'required':['state','chat_url','sol_text','needs_operator_capabilities','actions','plan_filename','plan_markdown','error','delivery_status','ui_surface','ui_model','ui_reasoning','chat_policy_status']
}


def now(): return datetime.now(timezone.utc).isoformat()

atexit.register(lambda: _browser_broker_stop() if '_browser_broker_stop' in globals() else None)

def log(msg):
    print(f'[{now()}] {msg}', flush=True)

def load_env(path=ENV_FILE):
    if not path.exists(): return
    for raw in path.read_text(errors='replace').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1)
        v=v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)

def read_text(path, default=''):
    try: return Path(path).read_text()
    except Exception: return default

def load_project():
    txt = read_text(PROJECT_YAML)
    out = {'repo':'Trochez/bot_trading','branch':'feature/GRU',
           'project_url':'https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading',
           'repo_dir':str(REPO_DIR_DEFAULT)}
    for key in ('repo','branch'):
        m=re.search(rf'^\s*{key}:\s*(.+?)\s*$',txt,re.M)
        if m: out[key]=m.group(1).strip().strip('"\'')
    m=re.search(r'^\s*project_url:\s*(.+?)\s*$',txt,re.M)
    if m: out['project_url']=m.group(1).strip().strip('"\'')
    return out

def api_auth_header():
    u=os.environ.get('OPENCODE_SERVER_USERNAME','opencode')
    p=os.environ.get('OPENCODE_SERVER_PASSWORD','')
    token=base64.b64encode(f'{u}:{p}'.encode()).decode()
    return 'Basic '+token

def api_json(method, path, body=None, timeout=30):
    base=os.environ.get('OPENCODE_SERVER_URL','http://127.0.0.1:4096').rstrip('/')
    data=None if body is None else json.dumps(body).encode()
    req=request.Request(base+path, data=data, method=method,
                        headers={'Authorization':api_auth_header(),'Content-Type':'application/json'})
    try:
        with request.urlopen(req, timeout=timeout) as r:
            raw=r.read()
            if not raw: return None
            return json.loads(raw)
    except error.HTTPError as e:
        raw=e.read().decode(errors='replace')
        raise RuntimeError(f'OpenCode HTTP {e.code} {path}: {raw[:1200]}')

def opencode_health(timeout=5):
    obj=api_json('GET','/global/health',None,timeout=timeout)
    return bool((obj or {}).get('healthy'))

def ensure_opencode_server():
    try:
        if opencode_health(): return
    except Exception:
        pass
    base=os.environ.get('OPENCODE_SERVER_URL','http://127.0.0.1:4096')
    u=urlparse(base)
    if u.hostname not in ('127.0.0.1','localhost'):
        raise RuntimeError(f'OpenCode server unavailable and auto-start is only allowed for localhost: {base}')
    port=str(u.port or 4096)
    log_path=Path('/var/lib/ai-loop/logs/opencode-v3.log')
    log_path.parent.mkdir(parents=True,exist_ok=True)
    log(f'OpenCode health failed; starting local server on {u.hostname}:{port}')
    fp=open(log_path,'ab',buffering=0)
    env=os.environ.copy()
    subprocess.Popen(['opencode','serve','--hostname',u.hostname or '127.0.0.1','--port',port],
                     stdin=subprocess.DEVNULL,stdout=fp,stderr=fp,env=env,start_new_session=True)
    deadline=time.time()+30
    last=''
    while time.time()<deadline:
        time.sleep(1)
        try:
            if opencode_health():
                log('OpenCode server healthy after auto-start')
                return
        except Exception as e:
            last=str(e)
    raise RuntimeError('OpenCode server did not become healthy after auto-start: '+last)

def _local_opencode_host_port():
    base=os.environ.get('OPENCODE_SERVER_URL','http://127.0.0.1:4096')
    u=urlparse(base)
    if u.hostname not in ('127.0.0.1','localhost'):
        raise RuntimeError(f'OpenCode lifecycle management is only allowed for localhost: {base}')
    return (u.hostname or '127.0.0.1', int(u.port or 4096))

def _terminate_local_opencode_server():
    """Terminate only the localhost OpenCode `serve` process bound to this ai-loop port."""
    host,port=_local_opencode_host_port()
    killed=[]
    try:
        cp=subprocess.run(['ps','-eo','pid=,args='],capture_output=True,text=True,timeout=10)
        for line in cp.stdout.splitlines():
            line=line.strip()
            if not line: continue
            try: pid_s,args=line.split(None,1); pid=int(pid_s)
            except Exception: continue
            if pid==os.getpid(): continue
            low=args.lower()
            if 'opencode' not in low or 'serve' not in low: continue
            if not re.search(rf'(?:--port(?:=|\s+)){port}(?:\s|$)',args):
                continue
            try:
                os.kill(pid,signal.SIGTERM); killed.append(pid)
            except (ProcessLookupError,PermissionError):
                pass
        deadline=time.time()+5
        while killed and time.time()<deadline:
            alive=[]
            for pid in killed:
                try: os.kill(pid,0); alive.append(pid)
                except ProcessLookupError: pass
                except PermissionError: alive.append(pid)
            if not alive: break
            time.sleep(.25)
        for pid in killed:
            try: os.kill(pid,signal.SIGKILL)
            except (ProcessLookupError,PermissionError): pass
    except Exception as e:
        log(f'WARN local OpenCode termination inspection failed: {e}')
    return killed


def _strip_ansi(text):
    return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(text or ''))


def _mark_browser_profile_clean_exit():
    """Mark Chrome's dedicated profile as cleanly exited without touching cookies/history.

    This suppresses the native "Restore pages?" crash bubble after controller-owned
    forced cleanup. The function runs only while no dedicated-profile browser process
    is expected to be alive. Failure is non-fatal because browser profile formats may
    vary across Chrome releases.
    """
    pref=BROWSER_PROFILE/'Default'/'Preferences'
    if not pref.exists() or not pref.is_file():
        return False
    try:
        raw=pref.read_text(encoding='utf-8')
        obj=json.loads(raw)
        if not isinstance(obj,dict):
            return False
        profile=obj.setdefault('profile',{})
        if not isinstance(profile,dict):
            profile={}; obj['profile']=profile
        changed=(profile.get('exit_type')!='Normal' or profile.get('exited_cleanly') is not True)
        profile['exit_type']='Normal'
        profile['exited_cleanly']=True
        if changed:
            mode=pref.stat().st_mode & 0o777
            tmp=pref.with_name('Preferences.ai-loop-clean.tmp')
            tmp.write_text(json.dumps(obj,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
            os.chmod(tmp,mode or 0o600)
            os.replace(tmp,pref)
        return changed
    except Exception as e:
        log(f'WARN could not mark dedicated browser profile clean exit: {e}')
        return False


def _cleanup_dedicated_browser_profile():
    """Kill only residual processes bound to the dedicated ai-loop browser profile."""
    killed=_terminate_dedicated_browser_profile_processes()
    for name in ('SingletonLock','SingletonSocket','SingletonCookie'):
        try: (BROWSER_PROFILE/name).unlink(missing_ok=True)
        except TypeError:
            q=BROWSER_PROFILE/name
            if q.exists(): q.unlink()
        except Exception:
            pass
    # Chrome's native restore bubble is state in Preferences, not page DOM. Mark only
    # the dedicated profile as clean after residual processes are gone; sessions/cookies
    # remain intact.
    _mark_browser_profile_clean_exit()
    return killed


def _run_opencode_cli(prompt, purpose, timeout=None):
    """Run one serialized text-only OpenCode reasoning turn. Browser ownership remains with the persistent broker."""
    timeout=int(timeout or OPENCODE_TURN_TIMEOUT)
    agent=os.environ.get('OPENCODE_TRANSPORT_AGENT','operator').strip() or 'operator'
    model=os.environ.get('OPENCODE_OPERATOR_MODEL','omniroute/codex/gpt-5.6-luna').strip()
    cli_dir=Path(os.environ.get('AI_LOOP_OPENCODE_CLI_DIR',str(OPENCODE_CLI_DIR)))
    cli_dir.mkdir(parents=True,exist_ok=True)
    OPENCODE_CLI_LOCK.parent.mkdir(parents=True,exist_ok=True)
    lock_fp=open(OPENCODE_CLI_LOCK,'w'); fcntl.flock(lock_fp,fcntl.LOCK_EX)
    try:
        cmd=['opencode','run','--agent',agent,'--model',model,'--dir',str(cli_dir),str(prompt)]
        env=os.environ.copy(); env['AI_LOOP_TEXT_ONLY_OPENCODE']='1'
        try:
            cp=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,env=env)
        except subprocess.TimeoutExpired as e:
            out=((e.stdout or '') if isinstance(e.stdout,str) else ((e.stdout or b'').decode(errors='replace')))
            err=((e.stderr or '') if isinstance(e.stderr,str) else ((e.stderr or b'').decode(errors='replace')))
            raise RuntimeError(f'OPENCODE_CLI_TIMEOUT purpose={purpose} timeout={timeout}s tail={_strip_ansi(out+chr(10)+err)[-2500:]}')
        text=_strip_ansi((cp.stdout or '')+'\n'+(cp.stderr or ''))
        if cp.returncode != 0:
            raise RuntimeError(f'OPENCODE_CLI_FAILED purpose={purpose} rc={cp.returncode} tail={text[-3000:]}')
        return text
    finally:
        try: fcntl.flock(lock_fp,fcntl.LOCK_UN)
        except Exception: pass
        lock_fp.close()


def _playwright_cli_probe_result(text):
    """Require evidence of the real tool call; model-written PASS alone is never sufficient."""
    plain=_strip_ansi(text)
    low=plain.lower()
    called='playwright_browser_tabs' in low
    # The observed failure transcript includes the tool name plus `failed` and an Error line.
    failed=bool(re.search(r'(?im)^.*playwright_browser_tabs.*\bfailed\b',plain))
    if 'browser is already in use' in low and 'user-data-dir' in low:
        failed=True
    if 'no playwright browser tool is available' in low or 'playwright tool is unavailable' in low:
        failed=True
    model_pass=bool(re.search(r'(?im)^\s*(?:playwright_cli_run=)?pass\s*$',plain))
    if called and not failed and model_pass:
        return True,'playwright_browser_tabs called successfully via opencode run'
    if not called:
        return False,'PLAYWRIGHT_BROWSER_TABS_NOT_CALLED'
    if failed:
        return False,'PLAYWRIGHT_BROWSER_TABS_TOOL_FAILED'
    return False,'PLAYWRIGHT_CLI_PASS_NOT_PROVEN'


def probe_playwright_cli_capability(timeout=120):
    prompt=('CAPABILITY PROBE ONLY. Use Playwright MCP. Call playwright_browser_tabs exactly once. '
            'Do not navigate, click, type, or modify anything. Report PASS only if the '
            'playwright_browser_tabs tool call itself succeeds. Otherwise report FAIL with the exact tool error.')
    text=_run_opencode_cli(prompt,'playwright-cli-capability',timeout=max(30,min(int(timeout),180)))
    return _playwright_cli_probe_result(text)


def ensure_cli_playwright_capability(st, state_path):
    ok,detail=probe_playwright_cli_capability(120)
    st['opencode_transport_mode']='cli-run-in-process'
    st['opencode_cli_playwright_probe_at']=now()
    st['opencode_cli_playwright_capability']='PASS' if ok else 'FAIL'
    st['opencode_cli_playwright_probe_error']='' if ok else detail
    save_state(Path(state_path),st)
    if not ok:
        raise RuntimeError('PLAYWRIGHT_CLI_CAPABILITY_UNAVAILABLE:'+detail)
    log('PLAYWRIGHT_CLI_CAPABILITY=PASS transport=opencode-run-in-process tool=playwright_browser_tabs')
    return True



def _playwright_node_module_root(allow_bootstrap=True):
    """Resolve a cached Playwright Node module without involving the AI model."""
    configured=os.environ.get('AI_LOOP_PLAYWRIGHT_NODE_MODULE_ROOT','').strip()
    roots=[]
    if configured:
        roots.append(Path(configured))
    roots += [OPENCODE_CLI_DIR/'node_modules', Path.cwd()/'node_modules']
    npx_root=Path.home()/'.npm'/'_npx'
    if npx_root.exists():
        try:
            roots += sorted((x/'node_modules' for x in npx_root.iterdir() if (x/'node_modules').is_dir()), key=lambda q:q.stat().st_mtime, reverse=True)
        except Exception:
            pass
    try:
        cp=subprocess.run(['npm','root','-g'],capture_output=True,text=True,timeout=15)
        if cp.returncode==0 and cp.stdout.strip(): roots.append(Path(cp.stdout.strip()))
    except Exception:
        pass
    seen=set()
    for root in roots:
        try: rr=root.resolve()
        except Exception: rr=root
        if str(rr) in seen: continue
        seen.add(str(rr))
        if (rr/'playwright'/'package.json').exists() or (rr/'playwright-core'/'package.json').exists():
            return rr
    if allow_bootstrap:
        # The machine already uses npm for @playwright/mcp. If its cache lacks a reusable
        # Playwright package, ask npx to populate the cache once; no browser download is
        # requested here because the worker launches the already-installed Google Chrome.
        try:
            subprocess.run(['npx','-y','playwright','--version'],capture_output=True,text=True,timeout=120)
        except Exception:
            pass
        return _playwright_node_module_root(False)
    raise RuntimeError('PLAYWRIGHT_NODE_MODULE_NOT_FOUND')


def _parse_artifact_worker_json(text):
    last=None
    for line in str(text or '').splitlines():
        line=line.strip()
        if not line.startswith('{'): continue
        try:
            obj=json.loads(line)
            if isinstance(obj,dict) and 'status' in obj: last=obj
        except Exception:
            continue
    if not last:
        raise RuntimeError('ARTIFACT_WORKER_JSON_MISSING tail='+_strip_ansi(str(text or ''))[-1600:])
    return last


def run_deterministic_plan_artifact_worker(st, destination, source_message_id='', source_locator=None, timeout=180):
    """Acquire downloadable .md bytes through the single persistent browser broker."""
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    try: destination.unlink(missing_ok=True)
    except TypeError:
        if destination.exists(): destination.unlink()
    args={'chatUrl':str(st.get('chat_url') or ''),'destination':str(destination),'sourceMessageId':str(source_message_id or '')}
    if not args['chatUrl']: raise RuntimeError('ARTIFACT_WORKER_CHAT_URL_MISSING')
    obj=browser_broker_call(str(st.get('run_id') or 'artifact'),'DOWNLOAD_ARTIFACT',args,timeout=timeout)
    ev=obj.get('evidence') if isinstance(obj.get('evidence'),dict) else {}
    if not destination.exists(): raise RuntimeError('PLAN_ARTIFACT_BROKER_PASS_WITHOUT_FILE')
    raw=destination.read_bytes(); observed=hashlib.sha256(raw).hexdigest()
    if int(ev.get('bytes') or -1)!=len(raw) or str(ev.get('sha256') or '')!=observed:
        raise RuntimeError(f'PLAN_ARTIFACT_BROKER_INTEGRITY_MISMATCH bytes={len(raw)} sha={observed}')
    ev.update({'status':'PASS','path':str(destination),'sha256':observed,'bytes':len(raw),'sourceMessageId':str(source_message_id or ''),'locatorMethod':'browser-broker'})
    log(f"PLAN_ARTIFACT_BROKER=PASS source_message={source_message_id or 'latest'} method={ev.get('method','unknown')} bytes={len(raw)} sha={observed}")
    return ev


def _project_name_from_url(project_url):
    m=re.search(r'/g/g-p-[^/]+-([^/]+)',str(project_url or ''))
    if not m: return 'bot_trading'
    return m.group(1).replace('-','_')


def _browser_broker_stop():
    global _BROWSER_BROKER_PROC,_BROWSER_BROKER_RUN_ID,_BROWSER_BROKER_EPOCH,_BROWSER_BROKER_STDERR
    proc=_BROWSER_BROKER_PROC
    if proc is None: return
    try:
        if proc.poll() is None:
            req={'request_id':'close-'+hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:12],'run_id':_BROWSER_BROKER_RUN_ID,'operation':'CLOSE','arguments':{},'deadline_epoch_ms':int((time.time()+5)*1000)}
            proc.stdin.write(json.dumps(req)+'\n'); proc.stdin.flush()
            proc.stdout.readline()
    except Exception:
        pass
    try:
        if proc.poll() is None: proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try: proc.kill()
        except Exception: pass
    try:
        if _BROWSER_BROKER_STDERR: _BROWSER_BROKER_STDERR.close()
    except Exception: pass
    _BROWSER_BROKER_PROC=None; _BROWSER_BROKER_RUN_ID=''; _BROWSER_BROKER_EPOCH=''; _BROWSER_BROKER_STDERR=None


def _browser_broker_start(run_id):
    global _BROWSER_BROKER_PROC,_BROWSER_BROKER_RUN_ID,_BROWSER_BROKER_EPOCH,_BROWSER_BROKER_STDERR
    run_id=str(run_id or 'broker')
    if _BROWSER_BROKER_PROC is not None and _BROWSER_BROKER_PROC.poll() is None and _BROWSER_BROKER_RUN_ID==run_id:
        return _BROWSER_BROKER_PROC
    _browser_broker_stop()
    if not BROWSER_BROKER.exists(): raise RuntimeError('BROWSER_BROKER_MISSING:'+str(BROWSER_BROKER))
    node=shutil.which('node')
    if not node: raise RuntimeError('NODE_RUNTIME_MISSING')
    module_root=_playwright_node_module_root()
    run_dir=RUNS_ROOT/run_id
    run_dir.mkdir(parents=True,exist_ok=True)
    cfg={'browserProfile':str(BROWSER_PROFILE),'moduleRoot':str(module_root),'chromeExecutable':str(CHROME_EXECUTABLE),'runDir':str(run_dir),'projectName':'bot_trading','actionTimeoutMs':BROWSER_ACTION_TIMEOUT_MS,'navigationTimeoutMs':BROWSER_NAVIGATION_TIMEOUT_MS,'settleTimeoutMs':BROWSER_SETTLE_TIMEOUT_MS,'responseTimeoutMs':ASSISTANT_RESPONSE_TIMEOUT_MS}
    cfg_path=run_dir/'browser-broker-config.json'; cfg_path.write_text(json.dumps(cfg),encoding='utf-8'); os.chmod(cfg_path,0o600)
    err_path=run_dir/'browser'/'broker.stderr.log'; err_path.parent.mkdir(parents=True,exist_ok=True)
    _BROWSER_BROKER_STDERR=open(err_path,'a',encoding='utf-8',buffering=1)
    proc=subprocess.Popen([node,str(BROWSER_BROKER),str(cfg_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=_BROWSER_BROKER_STDERR,text=True,bufsize=1,env=os.environ.copy())
    deadline=time.time()+30; first=''
    while time.time()<deadline:
        if proc.poll() is not None: break
        import select
        r,_,_=select.select([proc.stdout],[],[],0.5)
        if not r: continue
        first=proc.stdout.readline().strip()
        if first: break
    try: ready=json.loads(first)
    except Exception: ready={}
    if not ready.get('broker_ready'):
        rc=proc.poll(); _browser_broker_stop(); raise RuntimeError(f'BROWSER_BROKER_START_FAILED rc={rc} first={first[:800]}')
    _BROWSER_BROKER_PROC=proc; _BROWSER_BROKER_RUN_ID=run_id; _BROWSER_BROKER_EPOCH=str(ready.get('epoch') or '')
    log(f'BROWSER_BROKER=PASS epoch={_BROWSER_BROKER_EPOCH} run={run_id}')
    return proc


def browser_broker_call(run_id, operation, arguments=None, timeout=120):
    global _BROWSER_BROKER_PROC
    proc=_browser_broker_start(run_id)
    req_id=hashlib.sha256(f'{run_id}|{operation}|{time.time_ns()}'.encode()).hexdigest()[:20]
    req={'request_id':req_id,'run_id':str(run_id),'operation':str(operation),'arguments':arguments or {},'deadline_epoch_ms':int((time.time()+float(timeout))*1000)}
    try:
        proc.stdin.write(json.dumps(req,ensure_ascii=False)+'\n'); proc.stdin.flush()
        import select
        end=time.time()+float(timeout)
        while time.time()<end:
            r,_,_=select.select([proc.stdout],[],[],min(0.5,max(0,end-time.time())))
            if not r:
                if proc.poll() is not None: break
                continue
            line=proc.stdout.readline()
            if not line: break
            try: obj=json.loads(line)
            except Exception: continue
            if str(obj.get('request_id') or '')!=req_id: continue
            if str(obj.get('status') or '').upper()=='ERROR':
                raise RuntimeError('BROWSER_BROKER_'+operation+'_FAILED:'+str(obj.get('error') or 'UNKNOWN')+' evidence='+json.dumps(obj.get('evidence') or {})[:1000])
            return obj
        raise RuntimeError('BROWSER_BROKER_TIMEOUT:'+operation)
    except Exception:
        if proc.poll() is not None: _browser_broker_stop()
        raise


def broker_project_args(project_url):
    return {'projectUrl':str(project_url),'projectId':_adaptive_project_id(project_url),'projectName':_project_name_from_url(project_url)}

def _parse_worker_status_json(text):
    last=None
    for line in str(text or '').splitlines():
        line=line.strip()
        if not line.startswith('{'): continue
        try:
            obj=json.loads(line)
            if isinstance(obj,dict) and 'status' in obj: last=obj
        except Exception:
            continue
    if not last:
        raise RuntimeError('WORKER_JSON_MISSING tail='+_strip_ansi(str(text or ''))[-1600:])
    return last



def _extract_project_chat_urls(text, project_url):
    """Extract canonical project-chat URLs from controller state/diagnostics without trusting model semantics."""
    pid=_adaptive_project_id(project_url)
    if not pid: return []
    txt=str(text or '').replace('\\/','/')
    vals=[]; seen=set()
    # Absolute and relative links are both common in Playwright transcripts.
    pats=[
      rf'https://chatgpt\.com/g/{re.escape(pid)}/c/[A-Za-z0-9-]+',
      rf'/g/{re.escape(pid)}/c/[A-Za-z0-9-]+'
    ]
    for pat in pats:
        for m in re.finditer(pat,txt):
            u=m.group(0)
            if u.startswith('/'): u='https://chatgpt.com'+u
            u=_norm_chat_url(u)
            if u and u not in seen:
                seen.add(u); vals.append(u)
    return vals


def _prior_state_candidate_urls(rec, project_url):
    """Recover every project chat URL already mentioned by the failed run/state/diagnostics."""
    vals=[]; seen=set()
    def add(v):
        for u in _extract_project_chat_urls(v,project_url):
            if u not in seen: seen.add(u); vals.append(u)
    sp=Path(str(rec.get('state_path') or ''))
    if sp.is_file():
        try: add(sp.read_text(encoding='utf-8',errors='replace'))
        except Exception: pass
    for q in rec.get('diag_paths') or ([rec.get('diag')] if rec.get('diag') else []):
        qp=Path(str(q or ''))
        if qp.is_file():
            try: add(qp.read_text(encoding='utf-8',errors='replace'))
            except Exception: pass
    for u in rec.get('candidate_urls') or []:
        add(u)
    return vals


def _chrome_history_project_chat_urls(project_url, limit=120):
    """Read Chrome history from a copied SQLite DB after browser cleanup; returns exhaustive recent project chat candidates."""
    pid=_adaptive_project_id(project_url)
    meta={'ok':False,'profiles':0,'rows':0,'error':'','urls':[]}
    if not pid:
        meta['error']='PROJECT_ID_MISSING'; return meta
    history_files=[]
    for q in [BROWSER_PROFILE/'History', BROWSER_PROFILE/'Default'/'History']:
        if q.is_file() and q not in history_files: history_files.append(q)
    try:
        for q in sorted(BROWSER_PROFILE.glob('Profile */History')):
            if q.is_file() and q not in history_files: history_files.append(q)
    except Exception:
        pass
    urls=[]; seen=set(); errors=[]
    for hf in history_files:
        tmp=None
        try:
            fd,tmpname=tempfile.mkstemp(prefix='ai-loop-history-',suffix='.sqlite'); os.close(fd); tmp=Path(tmpname)
            shutil.copy2(hf,tmp)
            # Preserve uncheckpointed recent SPA navigation when Chrome left a WAL beside History.
            for suffix in ('-wal','-shm'):
                src=Path(str(hf)+suffix); dst=Path(str(tmp)+suffix)
                if src.is_file():
                    try: shutil.copy2(src,dst)
                    except Exception: pass
            con=sqlite3.connect(str(tmp));
            cur=con.execute("SELECT url,last_visit_time,title FROM urls WHERE url LIKE ? AND url LIKE '%/c/%' ORDER BY last_visit_time DESC LIMIT ?",(f'%/g/{pid}/c/%',int(limit)))
            rows=cur.fetchall(); con.close()
            meta['profiles']+=1; meta['rows']+=len(rows)
            for url,ts,title in rows:
                u=_norm_chat_url(url)
                if u and u not in seen:
                    seen.add(u); urls.append(u)
        except Exception as e:
            errors.append(f'{hf}:{e}')
        finally:
            try:
                if tmp:
                    tmp.unlink(missing_ok=True)
                    Path(str(tmp)+'-wal').unlink(missing_ok=True)
                    Path(str(tmp)+'-shm').unlink(missing_ok=True)
            except Exception: pass
    meta['urls']=urls[:int(limit)]
    meta['ok']=meta['profiles']>0
    if not history_files: meta['error']='CHROME_HISTORY_FILE_MISSING'
    elif errors: meta['error']='; '.join(errors)[:1000]
    return meta


def _merge_chat_candidates(*groups, limit=160):
    out=[]; seen=set()
    for group in groups:
        for u in (group or []):
            q=_norm_chat_url(u)
            if '/c/' not in q: continue
            if q not in seen:
                seen.add(q); out.append(q)
            if len(out)>=int(limit): return out
    return out


def _mark_prior_ambiguity_resolved_not_sent(rec, evidence):
    """Make negative reconciliation durable so a stale diagnostic can never deadlock future runs again."""
    sp=Path(str(rec.get('state_path') or ''))
    if not sp.is_file(): return False
    try:
        obj=json.loads(sp.read_text(encoding='utf-8'))
        ab=obj.get('adaptive_bootstrap') if isinstance(obj.get('adaptive_bootstrap'),dict) else {}
        ab.update({'status':'AMBIGUITY_RESOLVED_NOT_SENT','ambiguity_resolution':evidence,'resolved_at':now()})
        obj['adaptive_bootstrap']=ab
        save_state(sp,obj)
        return True
    except Exception:
        return False


def _negative_delivery_reconciliation(direct, history_meta, explicit_candidates):
    """Conservative negative proof: exhaustive history-backed scan + no sent ledger + no matching user marker."""
    if not isinstance(direct,dict) or str(direct.get('status') or '')!='PASS' or bool(direct.get('found')):
        return False
    if not bool(direct.get('scanComplete')):
        return False
    ledger=direct.get('ledger') if isinstance(direct.get('ledger'),dict) else {}
    if bool(ledger.get('sent')) or str(ledger.get('send_status') or '').upper() in {'SENT','ALREADY_SENT'}:
        return False
    if not bool((history_meta or {}).get('ok')):
        return False
    expected=set(_merge_chat_candidates(explicit_candidates,(history_meta or {}).get('urls') or []))
    visited=set(_norm_chat_url(x) for x in (direct.get('visited') or []) if '/c/' in _norm_chat_url(x))
    # If history exposes candidates, every one must have been inspected. If history has none,
    # an intact history DB plus no persisted project chat after the suspected click is itself negative evidence.
    if expected and not expected.issubset(visited):
        return False
    return True

def run_deterministic_bootstrap_observer(project_url, delivery_id, run_id='', max_chats=16, timeout=150, candidate_urls=None):
    """Read-only delivery scan through the single persistent broker."""
    args=broker_project_args(project_url)
    args.update({'deliveryId':str(delivery_id),'candidateUrls':list(candidate_urls or []),'maxChats':int(max_chats)})
    obj=browser_broker_call(run_id or 'observer','OBSERVE_DELIVERY',args,timeout=timeout)
    ev=obj.get('evidence') if isinstance(obj.get('evidence'),dict) else obj.get('state_after') if isinstance(obj.get('state_after'),dict) else obj
    if not isinstance(ev,dict): ev={}
    log(f"BOOTSTRAP_OBSERVER PASS delivery_id={delivery_id} found={bool(ev.get('found'))} chat={ev.get('url','')} visited={len(ev.get('visited') or [])} candidates={int(ev.get('candidateCount') or 0)} scan_complete={bool(ev.get('scanComplete'))}")
    return ev

def run_deterministic_browser_bootstrap(project_url, plan_path, plan_filename, implement_text, run_id, delivery_id, timeout=180):
    """v4.1 broker bootstrap: one persistent browser owner, semantic project proof, one send authority."""
    args=broker_project_args(project_url)
    fresh=browser_broker_call(run_id,'ENSURE_FRESH_PROJECT_DRAFT',args,timeout=min(timeout,90))
    st=fresh.get('state_after') or {}
    if st.get('projectContext')!='TARGET' or int((st.get('turns') or {}).get('total',-1))!=0:
        raise RuntimeError('BROKER_FRESH_PROJECT_DRAFT_NOT_PROVEN:'+json.dumps(st)[:1200])
    log(f"PROJECT_CONTEXT PASS project={args['projectName']} evidence={json.dumps((st.get('projectEvidence') or {}),ensure_ascii=False)[:900]}")
    log('FRESH_PROJECT_DRAFT PASS turns=0')
    pol=browser_broker_call(run_id,'ENSURE_CHAT_POLICY',args,timeout=min(timeout,90))
    pev=pol.get('evidence') or {}
    if not (pev.get('chat') and pev.get('model') and pev.get('high')):
        raise RuntimeError('BROKER_POLICY_NOT_PROVEN:'+json.dumps(pev)[:1000])
    log('CHAT_SURFACE PASS surface=chat')
    log('MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high')
    browser_broker_call(run_id,'ATTACH_FILE',{'path':str(plan_path),'name':str(plan_filename)},timeout=min(timeout,90))
    log(f'ATTACHMENT_GUARD PASS filename={plan_filename}')
    full=f'[AI_LOOP_DELIVERY id={delivery_id}]\n'+str(implement_text)
    browser_broker_call(run_id,'FILL_COMPOSER',{'message':full},timeout=min(timeout,90))
    log(f'DELIVERY_READY id={delivery_id}')
    send_args=dict(args); send_args.update({'deliveryId':str(delivery_id)})
    out=browser_broker_call(run_id,'SEND_ATOMIC',send_args,timeout=timeout)
    status=str(out.get('status') or '').upper()
    if status=='PASS':
        log(f"DELIVERY_SENT id={delivery_id} chat={out.get('url','')}")
        log(f"DELIVERY_PROOF PASS id={delivery_id}")
        return {'status':'PASS','clicked':bool(out.get('clicked')),'safeToRetry':False,'url':str(out.get('url') or ''),'ledger':out.get('ledger') or {},'project':bool(out.get('project',True))}
    if status=='ALREADY_SENT':
        return {'status':'PASS','clicked':False,'safeToRetry':False,'url':str(out.get('url') or ''),'ledger':{'delivery_id':delivery_id,'send_status':'SENT','sent':True},'project':True}
    if status=='AMBIGUOUS_SEND': return out
    return {'status':'ERROR','clicked':bool(out.get('clicked')),'safeToRetry':not bool(out.get('clicked')),'url':str(out.get('url') or ''),'error':str(out.get('error') or status or 'UNKNOWN')}

def run_deterministic_chat_policy(target_url, run_id='', purpose='policy', timeout=120):
    """Persistent-broker Chat+Sol+High guard with positive selected-state proof."""
    project_url=str(target_url).split('/c/',1)[0]
    args=broker_project_args(project_url); args['targetUrl']=str(target_url)
    obj=browser_broker_call(run_id or 'policy','ENSURE_CHAT_POLICY',args,timeout=timeout)
    ev=obj.get('evidence') or {}
    if not (ev.get('chat') and ev.get('model') and ev.get('high')):
        raise RuntimeError('DETERMINISTIC_POLICY_FAILED:MODEL_POLICY_NOT_PROVEN_SELECTED_STATE')
    return {'status':'PASS','url':str(target_url),'surface':'CHAT','model':'GPT-5.6 Sol','reasoning':'High','evidence':ev}

def run_deterministic_chat_send(target_url, message, delivery_id, run_id='', attachment='', timeout=180):
    """Broker-owned send for existing chat; no OpenCode/browser ownership handoff."""
    project_url=str(target_url).split('/c/',1)[0]
    args=broker_project_args(project_url); args['targetUrl']=str(target_url)
    # Keep the browser on the exact chat when a conversation URL is available.
    browser_broker_call(run_id or 'send','NAVIGATE_URL',{'url':str(target_url)},timeout=min(timeout,60))
    pol=browser_broker_call(run_id or 'send','ENSURE_CHAT_POLICY',args,timeout=min(timeout,60)).get('evidence') or {}
    if not (pol.get('chat') and pol.get('model') and pol.get('high')):
        return {'status':'ERROR','clicked':False,'safeToRetry':True,'url':str(target_url),'error':'MODEL_POLICY_NOT_PROVEN_SELECTED_STATE'}
    if attachment:
        browser_broker_call(run_id or 'send','ATTACH_FILE',{'path':str(attachment),'name':Path(attachment).name},timeout=min(timeout,90))
    browser_broker_call(run_id or 'send','FILL_COMPOSER',{'message':str(message)},timeout=min(timeout,90))
    send_args=dict(args); send_args.update({'deliveryId':str(delivery_id)})
    out=browser_broker_call(run_id or 'send','SEND_ATOMIC',send_args,timeout=timeout)
    status=str(out.get('status') or '').upper()
    if status=='PASS':
        out['status']='SENT'
    return out

def create_oc_session(title):
    obj=api_json('POST','/session',{'title':title},timeout=30)
    sid=(obj or {}).get('id')
    if not sid: raise RuntimeError(f'No session id: {obj}')
    return sid

def abort_oc_session(sid):
    try: api_json('POST',f'/session/{sid}/abort',{},timeout=20)
    except Exception as e: log(f'WARN abort {sid}: {e}')

def split_model():
    full=os.environ.get('OPENCODE_OPERATOR_MODEL','omniroute/codex/gpt-5.6-luna')
    if '/' not in full: return 'omniroute', full
    return full.split('/',1)

def list_agents():
    try:
        obj=api_json('GET','/agent',None,timeout=15)
        return obj if isinstance(obj,list) else []
    except Exception as e:
        log(f'WARN cannot list OpenCode agents: {e}')
        return []

def resolve_transport_agent():
    wanted=os.environ.get('OPENCODE_TRANSPORT_AGENT','operator')
    agents=list_agents()
    names=[]
    for a in agents:
        if isinstance(a,dict):
            n=a.get('name') or a.get('id')
            if n: names.append(str(n))
    if wanted in names:
        return wanted
    for fallback in ('operator','build'):
        if fallback in names:
            log(f"WARN transport agent {wanted!r} not loaded by server; using {fallback!r} for this turn with tools restricted by request")
            return fallback
    if names:
        log(f"WARN transport agent {wanted!r} not loaded; using first available agent {names[0]!r}")
        return names[0]
    return ''

def event_contract_text():
    return """
OUTPUT CONTRACT (mandatory):
After all Playwright work is complete, output exactly one JSON object between these two literal markers and no prose outside them:
AI_LOOP_EVENT_BEGIN
{"state":"GENERATING|RATE_LIMIT|ACTIONS|CONTINUE|NO_ACTIONS|GO|PLAN_READY|ERROR","chat_url":"...","sol_text":"...","needs_operator_capabilities":false,"actions":[{"id":"B01","target":"local|vps","payload_transport":"dom_file","command_sha256":"64_lowercase_hex","command_len":123,"timeout_seconds":180}],"plan_filename":"","plan_markdown":"","error":"","delivery_status":"NONE|SENT|ALREADY_SENT|NOT_SENT_GENERATING|NOT_SENT_RATE_LIMIT","ui_surface":"CHAT|WORK|CODEX|UNKNOWN","ui_model":"visible model label or empty","ui_reasoning":"visible reasoning label or empty","chat_policy_status":"PASS|FAIL|NOT_CHECKED"}
AI_LOOP_EVENT_END
state must be exactly one of GENERATING, RATE_LIMIT, ACTIONS, CONTINUE, NO_ACTIONS, GO, PLAN_READY, ERROR. NEVER output BLOCKED, WAITING or SETTLED as the state. Browser words such as WAITING/SETTLED describe observation status only; translate them into the canonical semantic state.

ACTION METADATA TRANSPORT — MANDATORY FOR EVERY ACTION:
- NEVER put the operator command itself or its Base64 in AI_LOOP_EVENT JSON.
- Locate the exact fenced code block belonging to the action in the settled Sol assistant message.
- Use Playwright DOM/evaluate on that code element's literal textContent. Do NOT use snapshot text for command metadata.
- In browser JavaScript, UTF-8 encode that exact textContent and compute SHA-256 over those exact bytes.
- Return ONLY payload_transport="dom_file", command_sha256, and command_len for the payload, plus action id/target/timeout.
- command_len is the UTF-8 byte length, not character count. command_sha256 must be lowercase 64-hex.
- The controller will ask Playwright to save the exact DOM code block directly to a local handoff file. Do NOT emit command text, Base64, chunks, or reconstructed payload bytes here.
- If the exact code block cannot be unambiguously matched, DOM evaluate is unavailable, or SHA/length cannot be proven, return ERROR with error=INCOMPLETE_OR_UNVERIFIED_ACTION_METADATA and actions=[]. NEVER guess or reconstruct it.

If Sol has issued any operator action, ACTIONS takes precedence over CONTINUE. Never return an action summary without verified metadata. If Sol says the external operator is not exposed/available in its own ChatGPT tool runtime, return NO_ACTIONS with needs_operator_capabilities=true instead. All thirteen top-level keys are required. For ordinary read-only inspection turns that do not perform a Chat/model guard, set ui_surface/ui_model/ui_reasoning to empty strings and chat_policy_status="NOT_CHECKED". For every turn that can send a ChatGPT message, chat_policy_status MUST be PASS before submission and the visible UI must prove surface=CHAT, model=GPT-5.6 Sol, reasoning=High. delivery_status is NONE for inspection, SENT when this turn actually submitted the message, ALREADY_SENT when its exact marker was already present, NOT_SENT_GENERATING when no message was sent because ChatGPT was still working, and NOT_SENT_RATE_LIMIT when no message was sent because the UI was rate limited. Use [] for no actions and empty strings for unused text fields. Do not put Markdown fences around the JSON.
"""

def _decode_legacy_base64_action(a, index=0):
    if not isinstance(a,dict):
        raise RuntimeError(f'Invalid action #{index}: not an object')
    target=str(a.get('target',''))
    if target not in ('local','vps','github-readonly'):
        raise RuntimeError(f'Invalid action target #{index}: {target!r}')
    b64=a.get('command_b64')
    sha=str(a.get('command_sha256') or '').lower()
    clen=a.get('command_len')
    if not isinstance(b64,str) or not b64.strip() or not re.fullmatch(r'[0-9a-f]{64}',sha):
        raise ValueError('INCOMPLETE_OR_UNVERIFIED_ACTION_PAYLOAD')
    try:
        raw=base64.b64decode(b64.encode('ascii'), validate=True)
    except Exception as e:
        raise ValueError('ACTION_PAYLOAD_BASE64_INVALID') from e
    try:
        command=raw.decode('utf-8','strict')
    except UnicodeDecodeError as e:
        raise ValueError('ACTION_PAYLOAD_UTF8_INVALID') from e
    calc=hashlib.sha256(raw).hexdigest()
    if calc != sha:
        raise ValueError(f'ACTION_PAYLOAD_SHA256_MISMATCH expected={sha} observed={calc}')
    try:
        expected_len=int(clen)
    except Exception as e:
        raise ValueError('ACTION_PAYLOAD_LENGTH_INVALID') from e
    if expected_len != len(raw):
        raise ValueError(f'ACTION_PAYLOAD_LENGTH_MISMATCH expected={expected_len} observed={len(raw)}')
    if not command.strip():
        raise ValueError('ACTION_PAYLOAD_EMPTY')
    try: tout=int(a.get('timeout_seconds') or DEFAULT_ACTION_TIMEOUT)
    except Exception: tout=DEFAULT_ACTION_TIMEOUT
    tout=max(1,min(3600,tout))
    return {
      'id':str(a.get('id') or f'A{index+1:02d}'),
      'target':target,
      'command':command,
      'command_b64':b64,
      'command_sha256':sha,
      'command_len':expected_len,
      'timeout_seconds':tout,
      'transport_integrity_verified':True,
    }


def _decode_action_descriptor(a, index=0):
    """Decode small action metadata. Large payload bytes are materialized separately."""
    if not isinstance(a,dict):
        raise RuntimeError(f'Invalid action #{index}: not an object')
    if a.get('command_b64'):
        return _decode_legacy_base64_action(a,index)
    target=str(a.get('target',''))
    if target not in ('local','vps','github-readonly'):
        raise ValueError(f'INVALID_ACTION_TARGET:{target}')
    sha=str(a.get('command_sha256') or '').lower()
    if not re.fullmatch(r'[0-9a-f]{64}',sha):
        raise ValueError('INCOMPLETE_OR_UNVERIFIED_ACTION_METADATA')
    try: expected_len=int(a.get('command_len'))
    except Exception as e: raise ValueError('ACTION_METADATA_LENGTH_INVALID') from e
    if expected_len <= 0:
        raise ValueError('ACTION_METADATA_LENGTH_INVALID')
    try: tout=int(a.get('timeout_seconds') or DEFAULT_ACTION_TIMEOUT)
    except Exception: tout=DEFAULT_ACTION_TIMEOUT
    tout=max(1,min(3600,tout))
    transport=str(a.get('payload_transport') or 'dom_file')
    if transport not in ('dom_file','chunked_file'):
        raise ValueError('ACTION_METADATA_TRANSPORT_UNSUPPORTED')
    return {
      'id':str(a.get('id') or f'A{index+1:02d}'),
      'target':target,
      'payload_transport':'dom_file',
      'command':'',
      'command_sha256':sha,
      'command_len':expected_len,
      'timeout_seconds':tout,
      'transport_integrity_verified':False,
    }


def _safe_action_id(value):
    v=re.sub(r'[^A-Za-z0-9_.-]+','-',str(value or 'action')).strip('-._')
    return (v or 'action')[:120]


def action_handoff_dir(run_id):
    d=RUNS_ROOT/str(run_id)/'action-handoff'
    d.mkdir(parents=True,exist_ok=True)
    return d


def dom_handoff_dir(run_id):
    d=DOM_HANDOFF_ROOT/str(run_id)
    d.mkdir(parents=True,exist_ok=True)
    try: os.chmod(d,0o700)
    except Exception: pass
    return d


def plan_handoff_dir(run_id):
    d=RUNS_ROOT/str(run_id)/'plan-handoff'
    d.mkdir(parents=True,exist_ok=True)
    return d


def plan_dom_file_prompt(chat_url, dest_path, candidate_sha=''):
    dest=str(dest_path)
    filename=Path(dest).name
    anchor=str(candidate_sha or '')[:12]
    return f"""ROLE: IMPLEMENTATION_PLAN_DOM_FILE_TRANSPORT_V1.
Use Playwright browser tools only. Do NOT send any ChatGPT message. Do NOT execute commands. Do NOT summarize or rewrite the plan.
Open/stay in exactly this ChatGPT conversation:
{chat_url}

The controller is in FAILURE_ANALYSIS after a remediation/replan request. A complete implementation plan is already expected in the latest settled GPT-5.6 Sol assistant response.
Failed candidate anchor (context only): {anchor}
Destination file (exact): {dest}
Download filename: {filename}

MANDATORY PLAN MATERIALIZATION METHOD:
1. Inspect the LIVE conversation. If ChatGPT is still generating, stop with PLAN_DOM_FILE_HANDOFF=GENERATING and do not create a file.
2. Identify the COMPLETE latest SETTLED assistant message. It must be the remediation implementation/release plan produced after the latest diagnosis/replan request. Do not select an older diagnosis, evidence message, or user prompt.
3. Inside that assistant message select the answer body itself (prefer the rendered markdown/article body under the latest element with data-message-author-role=\"assistant\"). Exclude composer text, navigation/sidebar, reaction/copy buttons, and other UI chrome.
4. Use Playwright browser_run_code with the page object. Inside the browser call read that selected plan body's `innerText` directly from the DOM, create a Blob/download from that exact string, wait for the download, and call download.saveAs({dest!r}).
5. Do NOT emit the plan text, Base64, chunks, escaped content, or a reconstructed plan through model output. The plan bytes must move DOM -> browser download -> local file.
6. The selected body must visibly be a substantial implementation PLAN (not a short status reply). If it is ambiguous, missing, or still generating, do not save a substitute.
7. Never use OpenCode bash/read/write/edit/task tools.

After the browser save attempt output exactly one small line and nothing else:
PLAN_DOM_FILE_HANDOFF=PASS
or
PLAN_DOM_FILE_HANDOFF=GENERATING
or
PLAN_DOM_FILE_HANDOFF=ERROR:<SHORT_UPPERCASE_REASON>

The controller independently validates the produced file and ignores model-written PASS if the file is absent/invalid."""


def plan_artifact_download_prompt(chat_url, dest_path, candidate_sha='', source_message_id=''):
    dest=str(dest_path)
    anchor=str(candidate_sha or '')[:12]
    source_id=str(source_message_id or '').strip()
    return f"""ROLE: DOWNLOADABLE_PLAN_ARTIFACT_ACQUISITION_V2.
Use Playwright browser tools only. Do NOT send any ChatGPT message. Do NOT execute shell commands. Do NOT use OpenCode bash/read/write/edit/task. Do NOT transcribe, summarize, reconstruct, Base64-encode, or print the plan bytes.
Open/stay in exactly this ChatGPT conversation:
{chat_url}

Failed candidate anchor (context only): {anchor}
Authoritative assistant message id when available: {source_id or 'LATEST_SETTLED_ASSISTANT'}
Destination file (exact): {dest}

SOURCE / SCOPE CONTRACT:
- The authoritative implementation plan MUST be the actual downloadable Markdown (.md) attachment/link/file card produced by GPT-5.6 Sol in the authoritative assistant response above.
- Work ONLY inside that assistant turn. Prefer an exact DOM message-id/data-message-id match for {source_id!r}. If that id is not exposed directly, use the newest SETTLED assistant turn only; never select an older plan/diagnosis/file elsewhere in the conversation.
- Inline rendered plan text is NOT an acceptable source and MUST NOT be scraped as a fallback.
- The controller validates the resulting bytes independently. Never claim PASS merely because a visible filename or preview exists.

ACQUISITION STRATEGY — perform in this order, stopping as soon as `{dest}` is saved:
A) DIRECT DOWNLOAD EVENT
1. Inside the scoped assistant turn find the unambiguous implementation-plan `.md` control. Prefer a control whose visible text/filename contains PLAN / COMPLETE_GO / REMEDIATION / IMPLEMENTATION and ends in `.md`, including labels such as "Download the approved plan".
2. If activating that exact control triggers a Playwright `download` event, capture it and call `download.saveAs({dest!r})`.

B) DIRECT-HREF AUTHENTICATED FETCH + SYNTHETIC DOWNLOAD
3. If the scoped `.md` control has a usable http(s) or same-origin href but activation opens a preview instead of a download, resolve the href to an absolute URL and fetch it from the SAME authenticated Playwright browser context using `page.context().request.get(...)` (or equivalent Playwright context request API). Do not print response bytes.
4. Require the response to be successful and non-empty. Keep the bytes inside Playwright/Node variables. Convert those in-memory bytes only inside the Playwright call into a temporary browser Blob/object URL, trigger a synthetic `<a download>` while `page.waitForEvent('download')` is armed, then `download.saveAs({dest!r})`. The bytes must never pass through model output.

C) CHATGPT FILE PREVIEW FALLBACK
5. If the file card/link opens ChatGPT's internal document preview instead of downloading, allow that preview to open in the same browser context. Inside the preview locate the `.md` filename and its actual Download control/link. First try the real download event. If the preview exposes a usable download href, use strategy B on that href.
6. A preview rendering itself is NOT success. Success requires browser-produced bytes saved at `{dest}`.

ROBUSTNESS / SAFETY:
- If multiple `.md` candidates remain ambiguous inside the scoped assistant turn, save nothing and report AMBIGUOUS.
- Do not inspect or choose `.md` files from older turns, sidebar/history, user messages, or another chat.
- If ChatGPT is still generating, save nothing and report GENERATING.
- Do not create a file from `innerText`, rendered Markdown, code blocks, snapshots, model prose, Base64, or reconstructed content.
- If a real browser download closes/replaces a page, recover the remaining ChatGPT tab from the same context before continuing; never launch a second browser/profile.
- NEVER expose the downloaded plan bytes/content in the assistant response.

After the attempt output exactly one short line:
PLAN_ARTIFACT_ACQUIRE=PASS method=download-event
or PLAN_ARTIFACT_ACQUIRE=PASS method=direct-href-fetch
or PLAN_ARTIFACT_ACQUIRE=PASS method=preview-download
or PLAN_ARTIFACT_ACQUIRE=GENERATING
or PLAN_ARTIFACT_ACQUIRE=NOT_FOUND
or PLAN_ARTIFACT_ACQUIRE=AMBIGUOUS
or PLAN_ARTIFACT_ACQUIRE=ERROR:<SHORT_REASON>

The controller ignores model-written PASS unless `{dest}` exists and independently passes UTF-8/content/structure validation."""

def _promote_downloaded_plan_artifact(source_path, run_id, candidate_sha='', source_message_id='', transport_protocol='chatgpt-downloadable-md-v2'):
    source=Path(source_path)
    if not source.exists() or not source.is_file():
        raise RuntimeError('PLAN_ARTIFACT_NOT_DOWNLOADED')
    raw=source.read_bytes()
    if len(raw) < 1500:
        raise RuntimeError(f'PLAN_ARTIFACT_TOO_SHORT bytes={len(raw)}')
    if len(raw) > 1000000:
        raise RuntimeError(f'PLAN_ARTIFACT_TOO_LARGE bytes={len(raw)}')
    try:
        text=raw.decode('utf-8','strict')
    except UnicodeDecodeError as e:
        raise RuntimeError('PLAN_ARTIFACT_UTF8_INVALID') from e
    low=text.lower()
    required=('plan','semaphore')
    missing=[x for x in required if x not in low]
    if missing:
        raise RuntimeError('PLAN_ARTIFACT_MISSING_ANCHORS:'+','.join(missing))
    if not any(x in low for x in ('implementation','implementacion','implementación','backlog','team','equipo','complete_go','release','remediation','remediacion','remediación')):
        raise RuntimeError('PLAN_ARTIFACT_NOT_IMPLEMENTATION_PLAN')
    if not any(x in low for x in ('backlog','task','tarea')):
        raise RuntimeError('PLAN_ARTIFACT_MISSING_BACKLOG')
    if not any(x in low for x in ('role','roles','team','equipo')):
        raise RuntimeError('PLAN_ARTIFACT_MISSING_ROLES')
    if len([x for x in text.splitlines() if x.strip()]) < 15:
        raise RuntimeError('PLAN_ARTIFACT_INSUFFICIENT_STRUCTURE')
    sha=hashlib.sha256(raw).hexdigest()
    d=plan_handoff_dir(run_id)
    ts=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    filename=f'IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_{ts}.md'
    final=d/filename
    tmp=final.with_suffix('.md.tmp')
    tmp.write_bytes(raw); os.chmod(tmp,0o600); os.replace(tmp,final)
    meta=final.with_suffix('.json')
    meta.write_text(json.dumps({
      'candidate_sha':str(candidate_sha or ''), 'source_message_id':str(source_message_id or ''),
      'plan_sha256':sha, 'plan_len':len(raw), 'payload_path':str(final),
      'transport_protocol':str(transport_protocol or 'chatgpt-downloadable-md-v2'), 'materialized_at':now()
    },indent=2))
    return filename,text,final,sha

def _plan_artifact_handoff_key(candidate_sha='', source_message_id=''):
    candidate=(str(candidate_sha or '')[:16] or 'no-sha')
    sid=str(source_message_id or '').strip()
    if not sid:
        return candidate+'-latest'
    return candidate+'-'+hashlib.sha256(sid.encode('utf-8')).hexdigest()[:12]


def _plan_artifact_acquisition_method(response):
    text=str(response or '')
    m=re.search(r'PLAN_ARTIFACT_ACQUIRE=PASS\s+method=([a-z0-9_-]+)',text,re.I)
    return (m.group(1).lower() if m else 'browser-acquisition')


def materialize_downloadable_plan_artifact(st, state_path, source_message_id='', source_locator=None):
    run_id=st['run_id']; candidate=str(st.get('candidate_sha') or st.get('baseline_sha') or '')
    source_message_id=str(source_message_id or '').strip()
    key=_plan_artifact_handoff_key(candidate,source_message_id)
    recs=st.setdefault('plan_artifact_handoffs',{})
    rec=recs.get(key) if isinstance(recs.get(key),dict) else {}
    prev=Path(rec.get('path','')) if rec.get('path') else None
    if prev and prev.exists():
        raw=prev.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
        if sha==rec.get('sha256') and len(raw)==int(rec.get('bytes') or -1) and str(rec.get('source_message_id') or '')==source_message_id:
            text=raw.decode('utf-8','strict')
            log(f'plan artifact handoff reused candidate={candidate} source_message={source_message_id or "latest"} bytes={len(raw)} sha={sha} path={prev}')
            return prev.name,text,prev

    browser_dir=dom_handoff_dir(run_id)
    browser_path=browser_dir/f'plan-artifact-{key}.md'
    try: browser_path.unlink(missing_ok=True)
    except TypeError:
        if browser_path.exists(): browser_path.unlink()

    worker=run_deterministic_plan_artifact_worker(st,browser_path,source_message_id,source_locator=source_locator,timeout=210)
    method=str(worker.get('method') or 'deterministic-playwright-worker')
    filename,text,final,sha=_promote_downloaded_plan_artifact(
        browser_path,run_id,candidate,source_message_id,
        transport_protocol='chatgpt-downloadable-md-v6:deterministic-node-playwright-multi-response:'+method
    )
    recs[key]={
      'path':str(final),'sha256':sha,'bytes':len(final.read_bytes()),
      'candidate_sha':candidate,'source_message_id':source_message_id,'materialized_at':now(),
      'transport_protocol':'chatgpt-downloadable-md-v6','acquisition_method':method,
      'worker_url':str(worker.get('url') or ''),'worker_module_root':str(worker.get('module_root') or '')
    }
    st['plan_artifact_last_error']=''; st['plan_artifact_last_success_at']=now()
    st['plan_artifact_last_acquisition_method']=method
    save_state(state_path,st)
    log(f'plan artifact materialized candidate={candidate} source_message={source_message_id or "latest"} protocol=chatgpt-downloadable-md-v7 deterministic_worker=1 method={method} bytes={recs[key]["bytes"]} sha={sha} path={final}')
    return filename,text,final

def plan_artifact_request_message():
    return prompt_file('plan_artifact_followup.txt',
        'Crea AHORA un archivo Markdown real y descargable (.md) que contenga exactamente el mismo plan de implementacion/remediacion que acabas de generar. Usa tu capacidad de generacion de archivos/adjuntos; el resultado debe aparecer en esta respuesta como un archivo descargable con fecha y hora en el nombre. No generes un plan distinto, no cambies su alcance, no ejecutes la implementacion y no pegues el plan completo solamente como texto inline. El archivo .md descargable es el unico artefacto autoritativo para continuar. Si no puedes crear un archivo descargable, dilo explicitamente en una frase breve.')


SEMANTIC_EVENTS = {
    'OPERATOR_ACTION_REQUESTED',
    'EVIDENCE_REQUESTED',
    'DIAGNOSIS_READY',
    'PLAN_READY',
    'PLAN_INLINE_ONLY',
    'PLAN_ARTIFACT_MISSING',
    'SELF_CONTINUE',
    'FINAL_GO',
    'HUMAN_BLOCKED',
    'NO_CHANGE',
}


def broker_observe_response(st, purpose='observe-response'):
    chat_url=str(st.get('chat_url') or '')
    if not chat_url: raise RuntimeError('BROKER_CHAT_URL_MISSING')
    project_url=str(st.get('project_url') or chat_url.split('/c/',1)[0])
    run_id=str(st.get('run_id') or 'observe')
    browser_broker_call(run_id,'NAVIGATE_URL',{'url':chat_url},timeout=60)
    args=broker_project_args(project_url); args['chatUrl']=chat_url
    obj=browser_broker_call(run_id,'OBSERVE_RESPONSE',args,timeout=max(60,ASSISTANT_RESPONSE_TIMEOUT_MS/1000))
    ev=obj.get('evidence') if isinstance(obj.get('evidence'),dict) else {}
    if ev.get('url'): st['chat_url']=str(ev.get('url'))
    return ev


def semantic_text_prompt(st, obs):
    phase=str(st.get('phase') or ''); stage=str(st.get('failure_stage') or '')
    text=str(obs.get('assistant_text') or '')
    blocks=((obs.get('turn_structure') or {}).get('code_blocks') or [])
    return f'''ROLE: AI_LOOP_TEXT_ONLY_SEMANTIC_INSPECTOR_V4_1.
You have NO browser authority and must not call Playwright or any external tool. Classify only the controller-supplied latest assistant text.
Controller context: phase={phase}; failure_stage={stage}; candidate_sha={st.get('candidate_sha') or ''}.
Browser observation is authoritative for generation state and message identity:
generation_state={obs.get('generation_state')}
source_message_id={obs.get('assistant_message_id','')}
source_text_sha256={obs.get('assistant_text_sha256','')}
code_blocks_metadata={json.dumps(blocks,ensure_ascii=False)}

LATEST ASSISTANT TEXT BEGIN
{text[:60000]}
LATEST ASSISTANT TEXT END

Choose semantic_event exactly one of: OPERATOR_ACTION_REQUESTED, EVIDENCE_REQUESTED, DIAGNOSIS_READY, PLAN_READY, PLAN_INLINE_ONLY, PLAN_ARTIFACT_MISSING, SELF_CONTINUE, FINAL_GO, HUMAN_BLOCKED, NO_CHANGE.
Do not treat plan backlog items, examples, quoted historical commands, or code blocks as current operator actions unless the prose explicitly instructs the external operator to execute them now.
Output exactly:
AI_LOOP_SEMANTIC_EVENT_BEGIN
{{"schema_version":1,"observation":"SETTLED","semantic_event":"...","confidence":0.0,"source_message_id":"","source_turn_testid":"","source_text_sha256":"","source_turn_index":-1,"chat_url":"","rationale":"short factual reason"}}
AI_LOOP_SEMANTIC_EVENT_END'''


def semantic_inspector_prompt(st):
    phase=str(st.get('phase') or '')
    stage=str(st.get('failure_stage') or '')
    candidate=str(st.get('candidate_sha') or '')
    return f'''ROLE: AI_LOOP_SEMANTIC_INSPECTOR_V1.
Use Playwright browser tools only. Do NOT send any ChatGPT message. Do NOT execute shell commands. Do NOT download files. Do NOT infer state from old messages.
Open/stay in exactly this ChatGPT conversation:
{st.get('chat_url','')}

Controller context (context only; never override what is visibly in the latest response):
phase={phase}
failure_stage={stage}
candidate_sha={candidate}

TASK:
Inspect ONLY the latest GPT-5.6 Sol assistant response and the live UI state around that response. Interpret its natural-language intent semantically. Do not treat code examples, backlog task IDs, quoted prior actions, diagnostic snippets, filenames, or shell blocks as operator requests unless the latest assistant response explicitly directs the external operator to execute them now.

First determine observation exactly one of:
- GENERATING: current response is still streaming/thinking/using tools or the latest user message has no completed assistant answer.
- RATE_LIMIT: UI has an active rate-limit/too-many-requests condition.
- SETTLED: latest assistant response is complete and stable.

If SETTLED, choose exactly one semantic_event:
- OPERATOR_ACTION_REQUESTED: Sol explicitly directs the external operator to execute one or more concrete actions now. Examples/backlog/code embedded in a plan do NOT qualify.
- EVIDENCE_REQUESTED: Sol explicitly asks the external operator for additional evidence but has not yet provided an executable command/action definition.
- DIAGNOSIS_READY: latest response is the completed diagnosis requested by the controller.
- PLAN_READY: latest response says/proves the requested remediation implementation plan is available as an actual downloadable .md file/attachment in this response.
- PLAN_INLINE_ONLY: latest response contains/substantially presents the remediation implementation plan inline, but no actual downloadable .md artifact is present.
- PLAN_ARTIFACT_MISSING: latest response is about the requested plan/artifact but does not provide a usable downloadable .md plan.
- SELF_CONTINUE: Sol explicitly says it has a next step it itself can perform without operator/user input.
- FINAL_GO: Sol explicitly declares final GO/COMPLETE_GO for the implementation.
- HUMAN_BLOCKED: Sol explicitly requires human-only input such as MFA, credentials, approval, selection, or clarification.
- NO_CHANGE: none of the above.

IMPORTANT:
- A plan containing B01/B02/B08-style backlog IDs or fenced commands is still PLAN_READY/PLAN_INLINE_ONLY, not OPERATOR_ACTION_REQUESTED, unless the response explicitly asks the external operator to run them now.
- Never claim a downloadable artifact merely because the response contains inline Markdown, a filename in prose, or a code block. PLAN_READY requires a visible file/attachment/download control in the latest response.
- This is interpretation only. You propose the event; the deterministic controller validates whether the transition is legal and independently verifies files, SHA, CI, actions, and GO invariants.

Output exactly one JSON object between literal markers and no prose outside them:
AI_LOOP_SEMANTIC_EVENT_BEGIN
{{"schema_version":1,"observation":"GENERATING|RATE_LIMIT|SETTLED","semantic_event":"OPERATOR_ACTION_REQUESTED|EVIDENCE_REQUESTED|DIAGNOSIS_READY|PLAN_READY|PLAN_INLINE_ONLY|PLAN_ARTIFACT_MISSING|SELF_CONTINUE|FINAL_GO|HUMAN_BLOCKED|NO_CHANGE","confidence":0.0,"source_message_id":"","source_turn_testid":"","source_text_sha256":"","source_turn_index":-1,"chat_url":"","rationale":"short factual reason only"}}
AI_LOOP_SEMANTIC_EVENT_END

For GENERATING or RATE_LIMIT use semantic_event="NO_CHANGE". confidence must be between 0 and 1. source_message_id should be the latest assistant message DOM/test id when available.'''


def _schema_version_matches(value, allowed=(1,)):
    """Bounded schema decoder: never call int() on untrusted protocol tokens."""
    if isinstance(value, bool) or value is None:
        return False
    vals=set(int(x) for x in allowed)
    if isinstance(value, int):
        return value in vals
    if isinstance(value, float):
        return value.is_integer() and int(value) in vals
    token=str(value).strip()
    if token.isdigit():
        return int(token) in vals
    if token.endswith('.0') and token[:-2].isdigit():
        return int(token[:-2]) in vals
    low=token.lower()
    for v in vals:
        if low in {f'v{v}', f'schema_v{v}', f'schema-version-{v}'}:
            return True
    return False


def parse_semantic_event_response(text):
    text=_strip_ansi(text)
    begin='AI_LOOP_SEMANTIC_EVENT_BEGIN'; end='AI_LOOP_SEMANTIC_EVENT_END'
    if begin not in text or end not in text:
        raise RuntimeError('SEMANTIC_EVENT_MARKERS_MISSING')
    raw=text.split(begin,1)[1].split(end,1)[0].strip()
    try:
        obj=json.loads(raw)
    except Exception as e:
        raise RuntimeError(f'SEMANTIC_EVENT_JSON_INVALID:{e}') from e
    if not isinstance(obj,dict):
        raise RuntimeError('SEMANTIC_EVENT_NOT_OBJECT')
    if not _schema_version_matches(obj.get('schema_version'), (1,)):
        raise RuntimeError('SEMANTIC_EVENT_SCHEMA_VERSION_INVALID')
    obs=str(obj.get('observation') or '')
    if obs not in {'GENERATING','RATE_LIMIT','SETTLED'}:
        raise RuntimeError('SEMANTIC_EVENT_OBSERVATION_INVALID:'+obs)
    ev=str(obj.get('semantic_event') or '')
    if ev not in SEMANTIC_EVENTS:
        raise RuntimeError('SEMANTIC_EVENT_TYPE_INVALID:'+ev)
    try: conf=float(obj.get('confidence',0))
    except Exception: conf=0.0
    if not (0.0 <= conf <= 1.0):
        raise RuntimeError('SEMANTIC_EVENT_CONFIDENCE_INVALID')
    return {
        'schema_version':1,
        'observation':obs,
        'semantic_event':ev,
        'confidence':conf,
        'source_message_id':str(obj.get('source_message_id') or ''),
        'source_turn_testid':str(obj.get('source_turn_testid') or ''),
        'source_text_sha256':str(obj.get('source_text_sha256') or '').lower(),
        'source_turn_index':int(obj.get('source_turn_index',-1)) if str(obj.get('source_turn_index',-1)).lstrip('-').isdigit() else -1,
        'chat_url':str(obj.get('chat_url') or ''),
        'rationale':str(obj.get('rationale') or '')[:1200],
    }


def semantic_inspect(st, purpose='semantic-inspect'):
    obs=broker_observe_response(st,purpose)
    gen=str(obs.get('generation_state') or '')
    if gen in {'GENERATING','RATE_LIMIT','NO_ASSISTANT'}:
        return {'schema_version':1,'observation':'RATE_LIMIT' if gen=='RATE_LIMIT' else 'GENERATING','semantic_event':'NO_CHANGE','confidence':1.0,'source_message_id':str(obs.get('assistant_message_id') or ''),'source_turn_testid':'','source_text_sha256':str(obs.get('assistant_text_sha256') or ''),'source_turn_index':-1,'chat_url':str(obs.get('url') or st.get('chat_url') or ''),'rationale':'deterministic browser observation '+gen.lower()}
    text=oc_raw_turn(semantic_text_prompt(st,obs),purpose)
    sem=parse_semantic_event_response(text)
    sem['observation']='SETTLED'
    sem['source_message_id']=str(obs.get('assistant_message_id') or '')
    sem['source_text_sha256']=str(obs.get('assistant_text_sha256') or '').lower()
    sem['source_turn_index']=int(((obs.get('turn_structure') or {}).get('assistant_count') or 1)-1)
    sem['chat_url']=str(obs.get('url') or st.get('chat_url') or '')
    return sem

def semantic_fingerprint(sem):
    # Same settled assistant message + same proposed semantic event must have a
    # stable identity even if the model paraphrases its rationale on a later
    # inspection. This is the core anti-loop key.
    source=str(sem.get('source_message_id') or '').strip()
    event=str(sem.get('semantic_event') or '')
    observation=str(sem.get('observation') or '')
    if source:
        basis='\n'.join([source,event,observation])
    else:
        # Fallback only when the UI does not expose a source id.
        basis='\n'.join([event,observation,str(sem.get('chat_url') or ''),str(sem.get('rationale') or '')])
    return hashlib.sha256(basis.encode()).hexdigest()[:20]



def response_identity_prompt(st):
    return f'''ROLE: AI_LOOP_RESPONSE_IDENTITY_PROBE_V1.
Use Playwright browser tools only. Do NOT send any ChatGPT message. Do NOT interpret meaning. Do NOT download files. Do NOT execute shell commands.
Open/stay in exactly this ChatGPT conversation:
{st.get('chat_url','')}

TASK:
Inspect only the latest assistant response identity and whether it is still generating.
- GENERATING: the latest assistant response is visibly streaming/thinking/using tools, or the latest user message has no completed assistant answer yet.
- RATE_LIMIT: an active too-many-requests/rate-limit UI is visible.
- SETTLED: the latest assistant response is complete and not generating.
- NO_ASSISTANT: there is no assistant response yet.

Use DOM attributes for identity. Prefer the closest latest assistant conversation turn data-testid / message id. Also compute a SHA-256 of normalized latest assistant-turn innerText (collapse whitespace, trim) in browser JavaScript when possible; this hash is identity only, not semantic evidence.
Do not summarize the response and do not classify it.

Output exactly one JSON object between literal markers and no prose outside them:
AI_LOOP_RESPONSE_IDENTITY_BEGIN
{{"schema_version":1,"observation":"GENERATING|RATE_LIMIT|SETTLED|NO_ASSISTANT","source_message_id":"","source_turn_testid":"","source_turn_index":-1,"content_sha256":"","chat_url":""}}
AI_LOOP_RESPONSE_IDENTITY_END
'''


def parse_response_identity(text):
    text=_strip_ansi(text)
    begin='AI_LOOP_RESPONSE_IDENTITY_BEGIN'; end='AI_LOOP_RESPONSE_IDENTITY_END'
    if begin not in text or end not in text:
        raise RuntimeError('RESPONSE_IDENTITY_MARKERS_MISSING')
    raw=text.split(begin,1)[1].split(end,1)[0].strip()
    try: obj=json.loads(raw)
    except Exception as e: raise RuntimeError(f'RESPONSE_IDENTITY_JSON_INVALID:{e}') from e
    if not isinstance(obj,dict) or not _schema_version_matches(obj.get('schema_version'), (1,)):
        raise RuntimeError('RESPONSE_IDENTITY_SCHEMA_INVALID')
    obs=str(obj.get('observation') or '')
    if obs not in {'GENERATING','RATE_LIMIT','SETTLED','NO_ASSISTANT'}:
        raise RuntimeError('RESPONSE_IDENTITY_OBSERVATION_INVALID:'+obs)
    mid=str(obj.get('source_message_id') or '').strip()
    sha=str(obj.get('content_sha256') or '').strip().lower()
    if sha and not re.fullmatch(r'[0-9a-f]{64}',sha):
        raise RuntimeError('RESPONSE_IDENTITY_SHA256_INVALID')
    ti=obj.get('source_turn_index',-1)
    try: ti=int(ti)
    except Exception: ti=-1
    return {'schema_version':1,'observation':obs,'source_message_id':mid,'source_turn_testid':str(obj.get('source_turn_testid') or ''),'source_turn_index':ti,'content_sha256':sha,'chat_url':str(obj.get('chat_url') or '')}


def inspect_response_identity(st, purpose='response-identity'):
    obs=broker_observe_response(st,purpose)
    gen=str(obs.get('generation_state') or '')
    mapping={'GENERATING':'GENERATING','RATE_LIMIT':'RATE_LIMIT','SETTLED':'SETTLED','NO_ASSISTANT':'NO_ASSISTANT'}
    return {'schema_version':1,'observation':mapping.get(gen,'NO_ASSISTANT'),'source_message_id':str(obs.get('assistant_message_id') or ''),'source_turn_testid':'','content_sha256':str(obs.get('assistant_text_sha256') or '').lower(),'turn_index':int(((obs.get('turn_structure') or {}).get('assistant_count') or 1)-1),'chat_url':str(obs.get('url') or st.get('chat_url') or '')}

def response_identity_key(obj):
    mid=str((obj or {}).get('source_message_id') or '').strip()
    if mid: return 'msg:'+mid
    sha=str((obj or {}).get('content_sha256') or '').strip().lower()
    if sha: return 'sha:'+sha
    return ''


def semantic_source_identity_key(sem):
    obj=sem or {}
    testid=str(obj.get('source_turn_testid') or '').strip()
    if testid: return 'turn:'+testid
    mid=str(obj.get('source_message_id') or '').strip()
    if mid: return 'msg:'+mid
    sha=str(obj.get('source_text_sha256') or '').strip().lower()
    if sha: return 'sha:'+sha
    return ''


def mark_settled_message_terminal(st, sem, reason, artifact_verified=False):
    key=semantic_source_identity_key(sem) or ('semfp:'+semantic_fingerprint(sem))
    ledger=st.setdefault('settled_message_ledger',{})
    rec=ledger.setdefault(key,{})
    rec.update({
        'source_message_id':str(sem.get('source_message_id') or ''),
        'source_turn_testid':str(sem.get('source_turn_testid') or ''),
        'source_text_sha256':str(sem.get('source_text_sha256') or ''),
        'source_turn_index':int(sem.get('source_turn_index',-1) or -1),
        'semantic_fingerprint':semantic_fingerprint(sem),
        'semantic_event':str(sem.get('semantic_event') or ''),
        'observation':str(sem.get('observation') or ''),
        'terminal':True,
        'reason':str(reason or ''),
        'artifact_verified':bool(artifact_verified),
        'recorded_at':now(),
    })
    return key


def begin_wait_for_new_assistant(st, after_identity_key, purpose):
    st['wait_new_assistant_message']={
        'active':True,
        'after_identity_key':str(after_identity_key or ''),
        'purpose':str(purpose or ''),
        'started_at':now(),
        'poll_streak':0,
        'last_probe_at':'',
        'last_seen_identity_key':'',
    }


def clear_wait_for_new_assistant(st):
    st['wait_new_assistant_message']={}


def new_message_poll_delay(st):
    w=st.setdefault('wait_new_assistant_message',{})
    streak=int(w.get('poll_streak',0) or 0)+1
    w['poll_streak']=streak
    return min(NEW_MESSAGE_POLL_MAX_SECONDS, max(1,NEW_MESSAGE_POLL_BASE_SECONDS*streak))


def settled_message_already_terminal(st, sem):
    key=semantic_source_identity_key(sem) or ('semfp:'+semantic_fingerprint(sem))
    rec=(st.get('settled_message_ledger') or {}).get(key)
    return bool(isinstance(rec,dict) and rec.get('terminal'))


def semantic_allowed(st, sem):
    event=str(sem.get('semantic_event') or '')
    phase=str(st.get('phase') or '')
    stage=str(st.get('failure_stage') or '')
    if sem.get('observation') in {'GENERATING','RATE_LIMIT'}:
        return True,''
    common={'HUMAN_BLOCKED','NO_CHANGE'}
    if phase=='IMPLEMENTING':
        allowed=common|{'OPERATOR_ACTION_REQUESTED','SELF_CONTINUE','EVIDENCE_REQUESTED'}
    elif phase=='FINAL_REVIEW':
        allowed=common|{'OPERATOR_ACTION_REQUESTED','EVIDENCE_REQUESTED','SELF_CONTINUE','FINAL_GO'}
    elif phase=='FAILURE_ANALYSIS':
        if stage in {'EVIDENCE','EVIDENCE_COLLECTING','EVIDENCE_DELIVERED'}:
            allowed=common|{'OPERATOR_ACTION_REQUESTED','EVIDENCE_REQUESTED','DIAGNOSIS_READY'}
        elif stage=='DIAGNOSIS_SENT':
            allowed=common|{'OPERATOR_ACTION_REQUESTED','EVIDENCE_REQUESTED','DIAGNOSIS_READY'}
        elif stage in {'REPLAN_SENT','PLAN_TEXT_REQUESTED','PLAN_ARTIFACT_REQUESTED','PLAN_ARTIFACT_REPAIR_REQUIRED','PLAN_ARTIFACT_CORRECTIVE_REQUIRED','PLAN_ARTIFACT_WAIT_NEW_MESSAGE','PLAN_ARTIFACT_BLOCKED','PLAN_ARTIFACT_BLOCKED_FINAL'}:
            allowed=common|{'OPERATOR_ACTION_REQUESTED','EVIDENCE_REQUESTED','PLAN_READY','PLAN_INLINE_ONLY','PLAN_ARTIFACT_MISSING'}
        else:
            allowed=common|{'OPERATOR_ACTION_REQUESTED','EVIDENCE_REQUESTED','DIAGNOSIS_READY','PLAN_READY','PLAN_INLINE_ONLY','PLAN_ARTIFACT_MISSING'}
    else:
        allowed=common
    if event not in allowed:
        return False,f'SEMANTIC_TRANSITION_NOT_ALLOWED phase={phase} stage={stage} event={event}'
    if float(sem.get('confidence',0) or 0) < SEMANTIC_MIN_CONFIDENCE and event not in {'NO_CHANGE','HUMAN_BLOCKED'}:
        return False,f'SEMANTIC_CONFIDENCE_BELOW_THRESHOLD event={event} confidence={sem.get("confidence")} threshold={SEMANTIC_MIN_CONFIDENCE}'
    return True,''


def record_semantic_observation(st, state_path, sem, accepted, reason=''):
    fp=semantic_fingerprint(sem)
    hist=st.setdefault('semantic_history',[])
    rec={
        'observed_at':now(),'fingerprint':fp,'phase':st.get('phase'),'failure_stage':st.get('failure_stage',''),
        'observation':sem.get('observation'),'semantic_event':sem.get('semantic_event'),
        'confidence':sem.get('confidence'),'source_message_id':sem.get('source_message_id',''),
        'source_turn_testid':sem.get('source_turn_testid',''),'source_text_sha256':sem.get('source_text_sha256',''),
        'source_turn_index':sem.get('source_turn_index',-1),
        'accepted':bool(accepted),'reason':str(reason or ''),'rationale':sem.get('rationale','')
    }
    hist.append(rec)
    if len(hist)>200: del hist[:-200]
    st['last_semantic_event']=rec
    save_state(state_path,st)
    return fp


def semantic_to_event(sem):
    obs=sem.get('observation')
    event=sem.get('semantic_event')
    if obs=='GENERATING': state='GENERATING'
    elif obs=='RATE_LIMIT': state='RATE_LIMIT'
    elif event=='FINAL_GO': state='GO'
    elif event=='SELF_CONTINUE': state='CONTINUE'
    else: state='NO_ACTIONS'
    return {
        'state':state,'chat_url':sem.get('chat_url',''),'sol_text':sem.get('rationale',''),
        'needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'',
        'error':'','delivery_status':'NONE','semantic_event':event,
        'semantic_confidence':sem.get('confidence',0),'semantic_source_message_id':sem.get('source_message_id',''),
    }


def browser_action_extract_prompt(chat_url, source_message_id=''):
    return f'''ROLE: EXPLICIT_OPERATOR_ACTION_EXTRACTOR_V1.
Use Playwright browser tools only. Do NOT send any ChatGPT message. Do NOT execute commands.
Open/stay in exactly this conversation:
{chat_url}
Semantic source assistant message id (when available): {source_message_id}

Inspect ONLY the latest settled GPT-5.6 Sol assistant response (prefer that exact source id). Extract actions ONLY when that response explicitly instructs the external operator to execute them NOW.
Never classify as actions: code examples, backlog tasks, implementation-plan steps, quoted commands, historical commands/results, diagnostic snippets, or commands that Sol itself says not to execute yet.
For each true current operator action, locate its ONE unambiguous fenced command code element and compute exact DOM textContent UTF-8 SHA-256 and byte length in browser JavaScript. Return only metadata using the standard AI_LOOP_EVENT contract. If there is no explicit current operator action, return NO_ACTIONS. Never return literal command text/Base64/chunks.'''


def one_transition_per_semantic_fingerprint(st, fp, purpose):
    ledger=st.setdefault('semantic_transition_ledger',{})
    key=f'{fp}:{purpose}'
    if key in ledger:
        return False
    ledger[key]={'recorded_at':now(),'phase':st.get('phase'),'failure_stage':st.get('failure_stage','')}
    return True


def semantic_action_selection_prompt(st, sem, obs):
    text=str(obs.get('assistant_text') or '')
    blocks=((obs.get('turn_structure') or {}).get('code_blocks') or [])
    return f'''ROLE: AI_LOOP_TEXT_ONLY_ACTION_SELECTOR_V4_1.
NO browser/tool calls. From the controller-provided latest assistant text, select only fenced code blocks that are explicitly instructed to the external operator to execute NOW.
Never select examples, implementation-plan backlog commands, historical commands/results, or code shown only for explanation.
Allowed targets: local, vps, github-readonly. Use vps only for the remote production/VPS environment. Use github-readonly only for read-only GitHub inspection. Otherwise local.
Latest assistant text:
{text[:60000]}
Code-block metadata:
{json.dumps(blocks,ensure_ascii=False)}
Output exactly one JSON object between markers:
AI_LOOP_ACTION_SELECTION_BEGIN
{{"schema_version":1,"actions":[{{"id":"B01","block_index":0,"target":"local|vps","timeout_seconds":180}}]}}
AI_LOOP_ACTION_SELECTION_END
Use [] when no explicit current action exists.'''


def parse_action_selection(text):
    txt=_strip_ansi(str(text or '')); b='AI_LOOP_ACTION_SELECTION_BEGIN'; e='AI_LOOP_ACTION_SELECTION_END'
    if b not in txt or e not in txt: raise RuntimeError('ACTION_SELECTION_MARKERS_MISSING')
    raw=txt.split(b,1)[1].split(e,1)[0].strip(); obj=json.loads(raw)
    if not isinstance(obj,dict) or not _schema_version_matches(obj.get('schema_version'),(1,)): raise RuntimeError('ACTION_SELECTION_SCHEMA_INVALID')
    out=[]
    for i,a in enumerate(obj.get('actions') or []):
        if not isinstance(a,dict): continue
        target=str(a.get('target') or 'local')
        if target not in {'local','vps','github-readonly'}: raise RuntimeError('ACTION_SELECTION_TARGET_INVALID')
        try: idx=int(a.get('block_index'))
        except Exception: raise RuntimeError('ACTION_SELECTION_BLOCK_INDEX_INVALID')
        try: tout=max(1,min(3600,int(a.get('timeout_seconds') or DEFAULT_ACTION_TIMEOUT)))
        except Exception: tout=DEFAULT_ACTION_TIMEOUT
        out.append({'id':str(a.get('id') or f'A{i+1:02d}'),'block_index':idx,'target':target,'timeout_seconds':tout})
    return out


def extract_and_run_semantic_actions(st, state_path, repo_dir, sem):
    sfp=semantic_fingerprint(sem)
    obs=broker_observe_response(st,'action-select-'+sfp[:10])
    blocks=((obs.get('turn_structure') or {}).get('code_blocks') or [])
    if not blocks:
        log(f'semantic action proposal had no fenced blocks fp={sfp}; no execution')
        return None
    raw=oc_raw_turn(semantic_action_selection_prompt(st,sem,obs),'select-explicit-operator-actions-'+sfp[:10])
    selections=parse_action_selection(raw)
    if not selections:
        st.setdefault('semantic_action_mismatches',[]).append({'at':now(),'semantic_fp':sfp,'semantic_event':sem.get('semantic_event'),'source_message_id':sem.get('source_message_id',''),'reason':'semantic-intent-without-current-action-block-selection'})
        save_state(state_path,st); log(f'semantic action proposal had no selected current action fp={sfp}; no execution'); return None
    by_idx={int(x.get('block_index')):x for x in blocks if isinstance(x,dict) and str(x.get('block_index','')).lstrip('-').isdigit()}
    materialized=[]
    for sel in selections:
        meta=by_idx.get(sel['block_index'])
        if not meta: raise RuntimeError('ACTION_SELECTED_BLOCK_NOT_IN_BROWSER_METADATA')
        aid=_safe_action_id(sel['id']); d=action_handoff_dir(st['run_id']); outp=d/f"{aid}-{str(meta.get('sha256'))[:16]}.sh"
        args={'blockIndex':sel['block_index'],'expectedSha':str(meta.get('sha256') or ''),'expectedBytes':int(meta.get('bytes') or 0),'outputPath':str(outp)}
        got=browser_broker_call(st['run_id'],'MATERIALIZE_CODE_BLOCK',args,timeout=60).get('evidence') or {}
        rawb=Path(str(got.get('path') or outp)).read_bytes(); command=rawb.decode('utf-8','strict')
        sha=hashlib.sha256(rawb).hexdigest(); ln=len(rawb)
        if sha!=str(meta.get('sha256') or '') or ln!=int(meta.get('bytes') or 0): raise RuntimeError('ACTION_BROKER_MATERIALIZATION_INTEGRITY_MISMATCH')
        materialized.append({'id':aid,'target':sel['target'],'command':command,'payload_path':str(outp),'payload_transport':'dom_file','command_sha256':sha,'command_len':ln,'timeout_seconds':sel['timeout_seconds'],'transport_integrity_verified':True,'transport_protocol':'browser-broker-dom-v1'})
    st['secure_action_pending']=False; st['secure_action_reissue_required']=False; st['secure_action_last_verified_at']=now(); save_state(state_path,st)
    register_pending_actions(st,state_path,materialized,'semantic:'+sfp)
    return drain_pending_actions(st,state_path,repo_dir)

def is_plan_artifact_stage(st):
    return (
        str(st.get('phase'))=='FAILURE_ANALYSIS'
        and str(st.get('failure_stage') or '') in {
            'REPLAN_SENT','PLAN_TEXT_REQUESTED','PLAN_ARTIFACT_REQUESTED','PLAN_ARTIFACT_REPAIR_REQUIRED','PLAN_ARTIFACT_CORRECTIVE_REQUIRED','PLAN_ARTIFACT_WAIT_NEW_MESSAGE','PLAN_ARTIFACT_BLOCKED','PLAN_ARTIFACT_BLOCKED_FINAL'
        }
    )


def reconcile_stale_secure_action_for_plan_stage(st):
    """Clear only orphaned legacy secure-action fences once FAILURE_ANALYSIS reached plan production."""
    if str(st.get('phase'))!='FAILURE_ANALYSIS':
        return False
    stage=str(st.get('failure_stage') or '')
    plan_stages={'REPLAN_SENT','PLAN_TEXT_REQUESTED','PLAN_ARTIFACT_REQUESTED','PLAN_ARTIFACT_REPAIR_REQUIRED','PLAN_ARTIFACT_CORRECTIVE_REQUIRED','PLAN_ARTIFACT_WAIT_NEW_MESSAGE','PLAN_ARTIFACT_BLOCKED','PLAN_ARTIFACT_BLOCKED_FINAL'}
    if stage not in plan_stages:
        return False
    if has_pending_actions(st) or st.get('secure_action_reissue_required'):
        return False
    if not st.get('secure_action_pending'):
        return False
    st.setdefault('legacy_stale_secure_action_fences',[]).append({
        'cleared_at':now(), 'phase':st.get('phase'), 'failure_stage':stage,
        'reissue_ids':list(st.get('secure_action_reissue_ids') or []),
        'reason':'failure-analysis-plan-stage-with-no-pending-or-reissue-action'
    })
    st['secure_action_pending']=False
    st['secure_action_reissue_ids']=[]
    st['secure_action_pending_followups']={}
    return True


def _promote_dom_plan_file(source_path, run_id, candidate_sha=''):
    source=Path(source_path)
    if not source.exists() or not source.is_file():
        raise RuntimeError('PLAN_DOM_FILE_NOT_CREATED')
    raw=source.read_bytes()
    if len(raw) < 2000:
        raise RuntimeError(f'PLAN_DOM_FILE_TOO_SHORT bytes={len(raw)}')
    if len(raw) > 500000:
        raise RuntimeError(f'PLAN_DOM_FILE_TOO_LARGE bytes={len(raw)}')
    try:
        text=raw.decode('utf-8','strict')
    except UnicodeDecodeError as e:
        raise RuntimeError('PLAN_DOM_FILE_UTF8_INVALID') from e
    low=text.lower()
    required=('plan','semaphore')
    missing=[x for x in required if x not in low]
    if missing:
        raise RuntimeError('PLAN_DOM_FILE_MISSING_ANCHORS:'+','.join(missing))
    if not any(x in low for x in ('implementation','backlog','team','complete_go','release')):
        raise RuntimeError('PLAN_DOM_FILE_NOT_IMPLEMENTATION_PLAN')
    if len([x for x in text.splitlines() if x.strip()]) < 20:
        raise RuntimeError('PLAN_DOM_FILE_INSUFFICIENT_STRUCTURE')
    sha=hashlib.sha256(raw).hexdigest()
    d=plan_handoff_dir(run_id)
    ts=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    filename=f'IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_{ts}.md'
    final=d/filename
    tmp=final.with_suffix('.md.tmp')
    tmp.write_bytes(raw); os.chmod(tmp,0o600); os.replace(tmp,final)
    meta=final.with_suffix('.json')
    meta.write_text(json.dumps({
      'candidate_sha':str(candidate_sha or ''), 'plan_sha256':sha,
      'plan_len':len(raw), 'payload_path':str(final),
      'transport_protocol':'playwright-dom-plan-download-v1', 'materialized_at':now()
    },indent=2))
    return filename,text,final,sha


def materialize_latest_plan_from_dom(st, state_path):
    run_id=st['run_id']; candidate=str(st.get('candidate_sha') or st.get('baseline_sha') or '')
    key=(candidate[:16] or 'no-sha')
    recs=st.setdefault('plan_dom_handoffs',{})
    rec=recs.get(key) if isinstance(recs.get(key),dict) else {}
    prev=Path(rec.get('path','')) if rec.get('path') else None
    if prev and prev.exists():
        raw=prev.read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        if sha==rec.get('sha256') and len(raw)==int(rec.get('bytes') or -1):
            text=raw.decode('utf-8','strict')
            log(f'plan DOM handoff reused candidate={candidate} bytes={len(raw)} sha={sha} path={prev}')
            return prev.name,text

    browser_dir=dom_handoff_dir(run_id)
    browser_path=browser_dir/f'plan-{key}.md'
    try: browser_path.unlink(missing_ok=True)
    except TypeError:
        if browser_path.exists(): browser_path.unlink()

    response=oc_side_effect_turn(
        plan_dom_file_prompt(st['chat_url'],browser_path,candidate),
        f'plan-dom-file-v220-{key}'
    )
    deadline=time.time()+10
    while time.time()<deadline and not browser_path.exists():
        time.sleep(.25)
    filename,text,final,sha=_promote_dom_plan_file(browser_path,run_id,candidate)
    recs[key]={
      'path':str(final),'sha256':sha,'bytes':len(final.read_bytes()),
      'candidate_sha':candidate,'materialized_at':now(),
      'browser_response_tail':str(response or '')[-500:]
    }
    st['plan_dom_last_error']=''; st['plan_dom_last_success_at']=now()
    save_state(state_path,st)
    log(f'plan handoff materialized candidate={candidate} protocol=playwright-dom-plan-download-v1 bytes={recs[key]["bytes"]} sha={sha} path={final}')
    return filename,text


def action_dom_file_prompt(chat_url, action, dest_path):
    aid=str(action['id']); sha=str(action['command_sha256']); clen=int(action['command_len'])
    dest=str(dest_path)
    filename=Path(dest).name
    return f"""ROLE: ACTION_PAYLOAD_DOM_FILE_TRANSPORT_V3.
Use Playwright browser tools only. Do NOT send any ChatGPT message. Do NOT execute the operator command. Do NOT ask for a PLAN or authorization: Sol already issued this action; this turn only transports its exact bytes from the browser DOM into a local file.
Open/stay in exactly this conversation:
{chat_url}

Action id: {aid}
Expected UTF-8 byte length: {clen}
Expected SHA-256: {sha}
Destination file (exact): {dest}
Download filename: {filename}

MANDATORY BYTE-PRESERVING METHOD:
1. Find the MOST RECENT settled GPT-5.6 Sol assistant message that defines action id {aid!r}. A newer message that merely says the action is still pending does not cancel it. If a newer response explicitly cancels/supersedes it, stop with ERROR.
2. Identify the ONE unambiguous fenced command code element belonging to this action. Never use snapshot prose or rendered Markdown text as payload.
3. Use Playwright's browser_run_code capability (Playwright code executed with the page object), not model text, to keep the command bytes inside Playwright:
   - obtain the chosen code element's literal `textContent` inside the Playwright call;
   - create a Blob/download from that exact textContent without normalizing/retyping/reconstructing it;
   - use `page.waitForEvent('download')` and `download.saveAs({dest!r})` to save the browser-produced file directly to the exact destination path above;
   - do not return the command text, Base64, chunks, escaped content, or any payload excerpt in the tool result or assistant response.
4. It is acceptable for the Playwright run-code result to contain only a tiny status such as `saved=true`. The controller, not you, will read the saved file and independently verify exact byte length and SHA-256 before execution.
5. If browser_run_code is unavailable, the code element is ambiguous, download/saveAs fails, or the exact destination cannot be written, DO NOT fall back to Base64/chunks/model transcription. Return ERROR.
6. Never use OpenCode bash/read/write/edit tools. Never execute the saved command.

After the browser save attempt, output exactly ONE small line and nothing else:
AI_LOOP_DOM_FILE_HANDOFF=PASS
or
AI_LOOP_DOM_FILE_HANDOFF=ERROR:<SHORT_UPPERCASE_REASON>

The controller ignores PASS unless `{dest}` actually exists and independently matches bytes={clen} and sha256={sha}."""


def oc_side_effect_turn(prompt, purpose):
    """Browser-only CLI turn where success is proven by a controller-side filesystem effect."""
    return _run_opencode_cli(prompt,purpose,OPENCODE_TURN_TIMEOUT)

def _promote_dom_handoff_file(action, source_path, run_id):
    source=Path(source_path)
    expected_len=int(action['command_len']); expected_sha=str(action['command_sha256']).lower()
    if not source.exists() or not source.is_file():
        raise RuntimeError('ACTION_DOM_FILE_NOT_CREATED')
    raw=source.read_bytes()
    if len(raw)!=expected_len:
        raise RuntimeError(f'ACTION_DOM_FILE_LENGTH_MISMATCH expected={expected_len} observed={len(raw)}')
    calc=hashlib.sha256(raw).hexdigest()
    if calc!=expected_sha:
        raise RuntimeError(f'ACTION_DOM_FILE_SHA256_MISMATCH expected={expected_sha} observed={calc}')
    try: command=raw.decode('utf-8','strict')
    except UnicodeDecodeError as e: raise RuntimeError('ACTION_DOM_FILE_UTF8_INVALID') from e
    if not command.strip():
        raise RuntimeError('ACTION_DOM_FILE_EMPTY')
    d=action_handoff_dir(run_id)
    stem=f"{_safe_action_id(action.get('id'))}-{expected_sha[:16]}"
    payload=d/(stem+'.sh'); meta=d/(stem+'.json')
    tmp=payload.with_suffix('.sh.tmp'); tmp.write_bytes(raw); os.chmod(tmp,0o600); os.replace(tmp,payload)
    meta.write_text(json.dumps({
      'action_id':action.get('id'),'target':action.get('target'),
      'command_sha256':expected_sha,'command_len':expected_len,
      'browser_source_path':str(source),'payload_path':str(payload),
      'transport_protocol':'playwright-dom-download-v1','materialized_at':now()
    },indent=2))
    out=dict(action)
    out.update({
      'command':command,'payload_path':str(payload),
      'transport_integrity_verified':True,'payload_transport':'dom_file',
      'transport_protocol':'playwright-dom-download-v1'
    })
    return out


def materialize_action_payload(action, chat_url, run_id):
    """Save exact command DOM textContent to a browser download, then verify/promote controller-side."""
    ok,_=verify_action_transport(action)
    if ok: return action
    expected_len=int(action.get('command_len') or 0); expected_sha=str(action.get('command_sha256') or '').lower()
    if expected_len<=0 or not re.fullmatch(r'[0-9a-f]{64}',expected_sha):
        raise RuntimeError('ACTION_HANDOFF_METADATA_INVALID')

    # Reuse only controller-owned verified payloads, never old model-transcribed chunks.
    d=action_handoff_dir(run_id)
    stem=f"{_safe_action_id(action.get('id'))}-{expected_sha[:16]}"
    promoted=d/(stem+'.sh')
    if promoted.exists():
        raw=promoted.read_bytes()
        if len(raw)==expected_len and hashlib.sha256(raw).hexdigest()==expected_sha:
            try: command=raw.decode('utf-8','strict')
            except UnicodeDecodeError: command=''
            if command.strip():
                out=dict(action); out.update({'command':command,'payload_path':str(promoted),'transport_integrity_verified':True,'payload_transport':'dom_file','transport_protocol':'playwright-dom-download-v1'})
                log(f'action DOM handoff reused id={action.get("id")} bytes={expected_len} sha={expected_sha} path={promoted}')
                return out

    browser_dir=dom_handoff_dir(run_id)
    browser_path=browser_dir/(stem+'.sh')
    # Never trust a previous unverified browser file. Start from absence.
    try: browser_path.unlink(missing_ok=True)
    except TypeError:
        if browser_path.exists(): browser_path.unlink()

    text=oc_side_effect_turn(
        action_dom_file_prompt(chat_url,action,browser_path),
        f'action-dom-file-v215-{_safe_action_id(action.get("id"))}'
    )
    # The model response is advisory only. The file + controller hash/length are authoritative.
    deadline=time.time()+10
    while time.time()<deadline and not browser_path.exists():
        time.sleep(0.25)
    try:
        out=_promote_dom_handoff_file(action,browser_path,run_id)
    except Exception as e:
        # Preserve a tiny diagnostic, but never retain a mismatched payload under the expected name.
        bad=None
        if browser_path.exists():
            try:
                bad=browser_path.with_suffix(f'.rejected-{int(time.time())}.bin')
                os.replace(browser_path,bad)
            except Exception:
                pass
        suffix=f' browser_response={text[-500:]!r}' if text else ''
        if bad: suffix+=f' rejected_path={bad}'
        raise RuntimeError(str(e)+suffix)
    log(f'action handoff materialized id={action.get("id")} protocol=playwright-dom-download-v1 bytes={expected_len} sha={expected_sha} path={out.get("payload_path")}')
    return out


def verify_action_transport(action):
    if not isinstance(action,dict): return False,'action is not an object'
    if not action.get('transport_integrity_verified'):
        return False,'missing verified secure-action transport marker'
    command=str(action.get('command') or '')
    sha=str(action.get('command_sha256') or '').lower()
    if not command or not re.fullmatch(r'[0-9a-f]{64}',sha):
        return False,'missing command or sha256'
    raw=command.encode('utf-8')
    calc=hashlib.sha256(raw).hexdigest()
    if calc != sha:
        return False,f'sha256 mismatch expected={sha} observed={calc}'
    try: expected_len=int(action.get('command_len'))
    except Exception: return False,'invalid command_len'
    if expected_len != len(raw):
        return False,f'length mismatch expected={expected_len} observed={len(raw)}'
    return True,''


SECURE_ACTION_TRANSPORT_ERROR_PREFIXES = (
    'INCOMPLETE_OR_UNVERIFIED_ACTION_PAYLOAD',
    'INCOMPLETE_OR_UNVERIFIED_ACTION_METADATA',
    'ACTION_METADATA_LENGTH_INVALID',
    'ACTION_METADATA_TRANSPORT_UNSUPPORTED',
    'UNSAFE_LEGACY_ACTION_TRANSPORT',
    'INCOMPLETE_ACTION_COMMAND_EXTRACTION',
    'ACTION_PAYLOAD_BASE64_INVALID',
    'ACTION_PAYLOAD_UTF8_INVALID',
    'ACTION_PAYLOAD_SHA256_MISMATCH',
    'ACTION_PAYLOAD_LENGTH_INVALID',
    'ACTION_PAYLOAD_LENGTH_MISMATCH',
    'ACTION_PAYLOAD_EMPTY',
    'PENDING_ACTION_NOT_EXTRACTED',
)

def is_secure_action_transport_error(err):
    text=str(err or '')
    return any(text == p or text.startswith(p + ' ') or text.startswith(p + ' expected=') for p in SECURE_ACTION_TRANSPORT_ERROR_PREFIXES)

def secure_action_fence_active(st):
    return bool(st.get('secure_action_pending') or st.get('secure_action_reissue_required'))


def _validate_event(ev):
    if not isinstance(ev,dict):
        raise RuntimeError('OpenCode event is not an object')

    raw_state=str(ev.get('state') or '')
    raw_event=str(ev.get('event') or '')
    raw_status=str(ev.get('status') or '')
    action_status=str(ev.get('action_status') or '')
    state=raw_state or (raw_event if raw_event in {'GENERATING','RATE_LIMIT','WAITING','SETTLED','BLOCKED'} else '')

    if 'ISSUED_BY_CHATGPT_NOT_EXECUTED' in action_status.upper():
        state='ERROR'; ev=dict(ev); ev['error']='PENDING_ACTION_NOT_EXTRACTED'

    raw_actions=ev.get('actions') if isinstance(ev.get('actions'),list) else []
    if state=='WAITING':
        state='CONTINUE' if raw_status.upper()=='CONTINUE' else 'NO_ACTIONS'
    elif state=='SETTLED':
        if raw_actions:
            state='ACTIONS'
        elif raw_status.upper()=='CONTINUE':
            state='CONTINUE'
        else:
            state='NO_ACTIONS'
    elif state=='BLOCKED':
        state='NO_ACTIONS'

    allowed={'GENERATING','RATE_LIMIT','ACTIONS','CONTINUE','NO_ACTIONS','GO','PLAN_READY','ERROR'}
    if state not in allowed:
        raise RuntimeError(f'Invalid OpenCode event state: {state!r}')

    blocked_state = raw_state == 'BLOCKED' or raw_event == 'BLOCKED'
    out={
      'state':state,
      'chat_url':str(ev.get('chat_url') or ev.get('conversation_url') or ''),
      'sol_text':str(ev.get('sol_text') or ev.get('summary') or ''),
      'needs_operator_capabilities':bool(ev.get('needs_operator_capabilities',False) or blocked_state),
      'actions':raw_actions,
      'plan_filename':str(ev.get('plan_filename') or ''),
      'plan_markdown':str(ev.get('plan_markdown') or ''),
      'error':str(ev.get('error') or ''),
      'delivery_status':str(ev.get('delivery_status') or 'NONE'),
      'ui_surface':str(ev.get('ui_surface') or ''),
      'ui_model':str(ev.get('ui_model') or ''),
      'ui_reasoning':str(ev.get('ui_reasoning') or ''),
      'chat_policy_status':str(ev.get('chat_policy_status') or 'NOT_CHECKED'),
    }
    if out['delivery_status'] not in {'NONE','SENT','ALREADY_SENT','NOT_SENT_GENERATING','NOT_SENT_RATE_LIMIT'}:
        out['delivery_status']='NONE'

    clean=[]
    for i,a in enumerate(out['actions']):
        # v2.11 intentionally rejects legacy literal command transport. Once text
        # has crossed rendered Markdown/snapshot transcription, byte integrity is
        # not provable. Sol must be re-inspected via DOM textContent envelope.
        if isinstance(a,dict) and a.get('command') and not a.get('command_b64'):
            return {
              'state':'ERROR','chat_url':out['chat_url'],'sol_text':out['sol_text'],
              'needs_operator_capabilities':False,'actions':[],
              'plan_filename':'','plan_markdown':'',
              'error':'UNSAFE_LEGACY_ACTION_TRANSPORT','delivery_status':out['delivery_status']
            }
        try:
            clean.append(_decode_action_descriptor(a,i))
        except ValueError as e:
            return {
              'state':'ERROR','chat_url':out['chat_url'],'sol_text':out['sol_text'],
              'needs_operator_capabilities':False,'actions':[],
              'plan_filename':'','plan_markdown':'',
              'error':str(e),'delivery_status':out['delivery_status']
            }
    out['actions']=clean
    if out['actions']:
        out['state']='ACTIONS'
    return out


def parse_event_response(obj):
    structured=((obj or {}).get('info') or {}).get('structured') if isinstance(obj,dict) else None
    if structured is None and isinstance(obj,dict): structured=obj.get('structured')
    if isinstance(structured,dict): return _validate_event(structured)
    parts=(obj or {}).get('parts',[]) if isinstance(obj,dict) else []
    text='\n'.join(str(p.get('text','')) for p in parts if isinstance(p,dict) and p.get('type')=='text')
    begin='AI_LOOP_EVENT_BEGIN'; end='AI_LOOP_EVENT_END'

    # v2.36 hardening: CLI transcripts can contain marker-looking fragments from tool chatter
    # or echoed prompt text. Scan ALL complete marker pairs and accept the newest valid event
    # rather than failing on the first malformed pair (observed tails: ` / ` and ` and `).
    marker_candidates=[]; pos=0; marker_errors=[]
    while True:
        i=text.find(begin,pos)
        if i < 0: break
        j=text.find(end,i+len(begin))
        if j < 0: break
        marker_candidates.append(text[i+len(begin):j].strip())
        pos=j+len(end)
    for raw in reversed(marker_candidates):
        try:
            return _validate_event(json.loads(raw))
        except Exception as e:
            marker_errors.append(f'{type(e).__name__}:{e}')

    stripped=text.strip()
    try: return _validate_event(json.loads(stripped))
    except Exception: pass
    dec=json.JSONDecoder()
    for m in re.finditer(r'\{', text):
        try:
            candidate,_=dec.raw_decode(text[m.start():])
            return _validate_event(candidate)
        except Exception:
            continue
    low=text.lower()
    if ('issued' in low and 'preflight' in low and ('not yet been executed' in low or 'not executed' in low or 'pending execution' in low)):
        return _validate_event({
            'state':'ERROR','chat_url':'','sol_text':text[-16000:],
            'needs_operator_capabilities':False,'actions':[],
            'plan_filename':'','plan_markdown':'',
            'error':'PENDING_ACTION_NOT_EXTRACTED','delivery_status':'NONE'
        })
    if ('external_operator_not_exposed' in low or
        'operator environment' in low or
        'operator terminal' in low or
        'vps wrapper' in low) and ('missing' in low or 'not exposed' in low or 'not available' in low or 'blocked' in low):
        return _validate_event({
            'state':'NO_ACTIONS','chat_url':'','sol_text':text[-16000:],
            'needs_operator_capabilities':True,'actions':[],
            'plan_filename':'','plan_markdown':'',
            'error':'EXTERNAL_OPERATOR_BRIDGE_REQUIRED','delivery_status':'NONE'
        })
    if marker_candidates:
        detail=(marker_errors[0] if marker_errors else 'NO_VALID_MARKED_EVENT')
        raise RuntimeError(f'Invalid marked OpenCode event JSON after scanning {len(marker_candidates)} candidate(s): {detail}; tail={marker_candidates[-1][-2000:]}')
    raise RuntimeError(f'No structured AI_LOOP_EVENT in OpenCode response: {text[-3000:]}')

def delete_oc_session(sid):
    try: api_json('DELETE',f'/session/{sid}',None,timeout=20)
    except Exception as e: log(f'WARN delete {sid}: {e}')


def _browser_profile_conflict(value):
    low=str(value or '').lower()
    return ('browser is already in use' in low and 'user-data-dir' in low) or ('browser is already in use for' in low)


def _session_alive(sid):
    if not sid: return False
    try:
        obj=api_json('GET',f'/session/{sid}',None,timeout=10)
        return isinstance(obj,dict) and (not obj.get('id') or str(obj.get('id'))==str(sid))
    except Exception:
        return False


def _terminate_dedicated_browser_profile_processes():
    """Terminate only the dedicated ai-loop Playwright/Chromium profile, preserving on-disk cookies/session."""
    profile=str(BROWSER_PROFILE)
    killed=[]
    try:
        cp=subprocess.run(['ps','-eo','pid=,args='],capture_output=True,text=True,timeout=10)
        for line in cp.stdout.splitlines():
            line=line.strip()
            if not line: continue
            try: pid_s,args=line.split(None,1); pid=int(pid_s)
            except Exception: continue
            if pid==os.getpid() or profile not in args: continue
            low=args.lower()
            if not any(tok in low for tok in ('chromium','chrome','playwright','@playwright/mcp','node')):
                continue
            try:
                os.kill(pid,signal.SIGTERM); killed.append(pid)
            except ProcessLookupError:
                pass
            except PermissionError:
                pass
        if killed: time.sleep(2)
    except Exception as e:
        log(f'WARN dedicated browser cleanup inspection failed: {e}')
    for name in ('SingletonLock','SingletonSocket','SingletonCookie'):
        try: (BROWSER_PROFILE/name).unlink(missing_ok=True)
        except Exception: pass
    return killed


def _playwright_tool_unavailable(value):
    low=str(value or '').lower()
    signals=(
        'no playwright browser tool is available',
        'playwright browser tool is not available',
        'playwright tools are unavailable',
        'playwright tool is unavailable',
        'no playwright tool',
    )
    return any(x in low for x in signals)


def _playwright_probe_result(obj):
    """Return (ok, detail) only when playwright_browser_tabs actually completed."""
    if not isinstance(obj,dict):
        return False,'NON_OBJECT_RESPONSE'
    parts=obj.get('parts',[])
    text=[]
    for part in parts if isinstance(parts,list) else []:
        if not isinstance(part,dict): continue
        if part.get('type')=='text' and part.get('text'):
            text.append(str(part.get('text')))
        if part.get('type')=='tool':
            tool=str(part.get('tool') or '')
            state=part.get('state') if isinstance(part.get('state'),dict) else {}
            status=str(state.get('status') or '').lower()
            if tool=='playwright_browser_tabs' or tool.endswith('.playwright_browser_tabs'):
                if status in ('completed','complete','success','succeeded'):
                    return True,'playwright_browser_tabs completed'
                err=str(state.get('error') or '')
                return False,'PLAYWRIGHT_BROWSER_TABS_'+(status.upper() or 'UNKNOWN')+(':'+err[:500] if err else '')
    joined='\n'.join(text)
    if _playwright_tool_unavailable(joined):
        return False,'PLAYWRIGHT_TOOL_UNAVAILABLE:'+joined[-500:]
    return False,'PLAYWRIGHT_BROWSER_TABS_NOT_CALLED:'+joined[-500:]


def probe_playwright_capability(sid, timeout=120):
    provider,model=split_model(); agent=resolve_transport_agent()
    prompt="CAPABILITY PROBE ONLY. Call the Playwright tool `playwright_browser_tabs` exactly once with its list-tabs action. Do not navigate, click, type, open a second browser, or interact with ChatGPT/Semaphore. After the tool call, output exactly PLAYWRIGHT_CAPABILITY=PASS. If the tool is unavailable, output PLAYWRIGHT_CAPABILITY=ERROR:NO_PLAYWRIGHT_TOOL."
    body={'model':{'providerID':provider,'modelID':model},'tools':DISABLED_TOOLS,'parts':[{'type':'text','text':prompt}]}
    if agent: body['agent']=agent
    try:
        obj=api_json('POST',f'/session/{sid}/message',body,timeout=max(10,min(int(timeout),120)))
    except Exception as e:
        return False,'PROBE_REQUEST_ERROR:'+str(e)[-700:]
    return _playwright_probe_result(obj)


def _hard_recover_browser_owner_session(reason):
    """One hard recovery: restart dedicated localhost OpenCode server, then recreate owner session."""
    global _BROWSER_OWNER_SID
    st=_BROWSER_OWNER_STATE; state_path=_BROWSER_OWNER_STATE_PATH
    if not isinstance(st,dict) or state_path is None:
        raise RuntimeError('BROWSER_OWNER_HARD_RECOVERY_UNAVAILABLE:'+str(reason))
    old=_BROWSER_OWNER_SID or str(st.get('browser_owner_session_id') or '')
    if old:
        try: abort_oc_session(old)
        except Exception: pass
    killed_browser=_terminate_dedicated_browser_profile_processes()
    killed_server=_terminate_local_opencode_server()
    time.sleep(1)
    ensure_opencode_server()
    sid=create_oc_session(f'ai-loop-v3 browser-owner {st.get("run_id","")} hard-recovered')
    _BROWSER_OWNER_SID=sid
    st['browser_owner_session_id']=sid
    st['browser_owner_recoveries']=int(st.get('browser_owner_recoveries',0) or 0)+1
    st['browser_owner_server_restarts']=int(st.get('browser_owner_server_restarts',0) or 0)+1
    st['browser_owner_last_recovery_reason']=str(reason)[:500]
    st['browser_owner_last_recovered_at']=now()
    save_state(state_path,st)
    log(f'browser owner hard-recovered old_sid={old} new_sid={sid} server_pids={killed_server} browser_pids={killed_browser} reason={str(reason)[:300]}')
    return sid


def ensure_browser_owner_playwright_capability(st, state_path):
    """Startup gate: prove durable owner can actually call playwright_browser_tabs."""
    sid=_BROWSER_OWNER_SID or str(st.get('browser_owner_session_id') or '')
    if not sid:
        raise RuntimeError('PLAYWRIGHT_CAPABILITY_PROBE_NO_OWNER_SESSION')
    ok,detail=probe_playwright_capability(sid)
    if ok:
        st['browser_owner_playwright_capability']='PASS'
        st['browser_owner_playwright_probe_at']=now()
        save_state(Path(state_path),st)
        log(f'PLAYWRIGHT_CAPABILITY=PASS sid={sid}')
        return sid
    log(f'WARN PLAYWRIGHT_CAPABILITY probe failed sid={sid} detail={detail}; performing one hard OpenCode restart')
    sid=_hard_recover_browser_owner_session('playwright-capability:'+detail)
    ok,detail2=probe_playwright_capability(sid)
    st['browser_owner_playwright_probe_at']=now()
    st['browser_owner_playwright_capability']='PASS' if ok else 'FAIL'
    st['browser_owner_playwright_probe_error']='' if ok else str(detail2)[:1000]
    save_state(Path(state_path),st)
    if not ok:
        raise RuntimeError('PLAYWRIGHT_CAPABILITY_UNAVAILABLE_AFTER_RECOVERY:'+str(detail2))
    log(f'PLAYWRIGHT_CAPABILITY=PASS sid={sid} after_hard_recovery=1')
    return sid


def bind_browser_owner_session(st, state_path):
    """Bind all Playwright/OpenCode turns for this controller run to ONE durable OpenCode session."""
    global _BROWSER_OWNER_SID, _BROWSER_OWNER_STATE, _BROWSER_OWNER_STATE_PATH
    _BROWSER_OWNER_STATE=st; _BROWSER_OWNER_STATE_PATH=Path(state_path)
    ensure_opencode_server()
    saved=str(st.get('browser_owner_session_id') or '')
    if saved and _session_alive(saved):
        _BROWSER_OWNER_SID=saved
        st['browser_owner_last_bound_at']=now(); save_state(Path(state_path),st)
        log(f'browser owner session reused sid={saved}')
        return saved
    if saved:
        log(f'browser owner session stale sid={saved}; creating replacement')
    # A missing/stale owner may leave a dedicated Chromium profile lock behind.
    killed=_terminate_dedicated_browser_profile_processes()
    if killed: log(f'dedicated browser profile cleanup terminated_pids={killed}')
    sid=create_oc_session(f'ai-loop-v3 browser-owner {st.get("run_id","")}')
    _BROWSER_OWNER_SID=sid
    st['browser_owner_session_id']=sid
    st['browser_owner_created_at']=now()
    st['browser_owner_recoveries']=int(st.get('browser_owner_recoveries',0) or 0)
    save_state(Path(state_path),st)
    log(f'browser owner session created sid={sid}')
    return sid


def _recover_browser_owner_session(reason):
    global _BROWSER_OWNER_SID
    st=_BROWSER_OWNER_STATE; state_path=_BROWSER_OWNER_STATE_PATH
    if not isinstance(st,dict) or state_path is None:
        raise RuntimeError('BROWSER_OWNER_RECOVERY_UNAVAILABLE:'+str(reason))
    old=_BROWSER_OWNER_SID or str(st.get('browser_owner_session_id') or '')
    if old:
        abort_oc_session(old); delete_oc_session(old)
    killed=_terminate_dedicated_browser_profile_processes()
    sid=create_oc_session(f'ai-loop-v3 browser-owner {st.get("run_id","")} recovered')
    _BROWSER_OWNER_SID=sid
    st['browser_owner_session_id']=sid
    st['browser_owner_recoveries']=int(st.get('browser_owner_recoveries',0) or 0)+1
    st['browser_owner_last_recovery_reason']=str(reason)[:500]
    st['browser_owner_last_recovered_at']=now()
    save_state(state_path,st)
    log(f'browser owner recovered old_sid={old} new_sid={sid} killed_pids={killed} reason={str(reason)[:300]}')
    return sid


def _browser_session_for_turn(purpose):
    if _BROWSER_OWNER_SID:
        return _BROWSER_OWNER_SID, False
    return create_oc_session(f'ai-loop-v3 {purpose} {int(time.time())}'), True

def oc_turn(prompt, purpose):
    text=_run_opencode_cli(prompt + event_contract_text(),purpose,OPENCODE_TURN_TIMEOUT)
    # Reuse the hardened event parser, treating the complete CLI transcript as one text part.
    return parse_event_response({'parts':[{'type':'text','text':text}]})


def oc_raw_turn(prompt, purpose):
    # Browser-only turn without the ChatGPT event contract. The CLI transcript is returned
    # verbatim (ANSI stripped) so downstream parsers can find their explicit evidence markers.
    return _run_opencode_cli(prompt,purpose,OPENCODE_TURN_TIMEOUT)

def semaphore_collect_prompt(repo, branch, sha, run_id, pipeline_id):
    return f'''ROLE: SEMAPHORE_READONLY_EVIDENCE_COLLECTOR.
Use Playwright browser tools only. Do NOT interact with ChatGPT. Do NOT use bash/read/write/edit/task.
Use the existing persistent browser profile. GitHub may already be authenticated even when Semaphore shows its login interstitial.

Use the browser created by THIS serialized `opencode run` turn. Never launch a second browser process or another user-data-dir instance.
Inspect existing tabs first: reuse an existing Semaphore tab if present; otherwise open ONE new tab in this same browser context so the ChatGPT tab remains untouched.
Start from https://me.semaphoreci.com .

Read-only invariants:
- Never click Run, Rerun, Retry, Stop, Cancel, Edit, Promote, Schedule, or any mutation control.
- Never modify repository, CI settings, secrets, jobs, artifacts, or organization settings.
- Never infer from "latest". The exact identifiers below are mandatory anchors.
- OAuth recovery is allowed ONLY by clicking Semaphore's GitHub login/continue button. Never type credentials, passwords, OTP/MFA codes, recovery codes, or account data.

Repository: {repo}
Branch: {branch}
Exact candidate SHA: {sha}
Exact Semaphore workflow/run id: {run_id}
Exact Semaphore pipeline id: {pipeline_id}

Authentication recovery protocol (maximum 3 recovery clicks total in this turn):
1. If Semaphore content is already authenticated, continue directly to evidence collection.
2. If Semaphore shows a login/interstitial page with a visible control whose accessible name is exactly or substantially one of:
   - "Login with GitHub"
   - "Log in with GitHub"
   - "Sign in with GitHub"
   - "Continue with GitHub"
   click that GitHub control ONCE, then wait for navigation/network settling.
3. Re-check the resulting page:
   - If authenticated Semaphore content is visible, set auth_recovery_attempted=true and auth_recovery_succeeded=true, then continue.
   - If redirected to a GitHub page that requires entering credentials, password, OTP/MFA, recovery code, device confirmation, account selection requiring human choice, or any consent beyond a simple already-authorized redirect, STOP and return AUTH_REQUIRED_HUMAN. Do not enter or choose anything.
   - If returned to the Semaphore login interstitial, another click is allowed, up to 3 total. After 3 unsuccessful recovery clicks return AUTH_REQUIRED_HUMAN.
4. Never classify the mere Semaphore login interstitial as terminal AUTH_REQUIRED before trying the GitHub recovery above.
5. If a simple GitHub OAuth redirect/authorization completes automatically without human input, that is allowed; continue to the exact run/pipeline afterward.

Evidence tasks after authentication:
1. Locate the exact workflow/pipeline using the IDs above and verify the candidate SHA. If the IDs or SHA do not match, return NOT_FOUND or ERROR; do not substitute another pipeline.
2. Record pipeline status/result and all failed blocks/jobs.
3. Open EVERY failed job read-only. Prefer the Raw log view when available.
4. For each failed job capture block name, job name/id, exit status if visible, job URL, the first concrete failure/error lines, and raw log text.
5. For log_text: include the complete raw log when <=60000 characters. If larger, include the first 5000 and last 50000 characters and set log_truncated=true with log_total_chars.
6. Do not diagnose or propose fixes.

Output exactly one JSON object between these literal markers and no prose outside them:
CI_EVIDENCE_BEGIN
{{"status":"PASS|AUTH_REQUIRED_HUMAN|NOT_FOUND|ERROR","repo":"{repo}","branch":"{branch}","candidate_sha":"{sha}","verified_candidate_sha":"","run_id":"{run_id}","pipeline_id":"{pipeline_id}","pipeline_status":"","pipeline_result":"","auth_recovery_attempted":false,"auth_recovery_succeeded":false,"auth_recovery_attempts":0,"failed_jobs":[{{"block":"","job":"","job_id":"","job_url":"","exit_status":"","failure_lines":"","log_text":"","log_truncated":false,"log_total_chars":0}}],"summary":"","error":""}}
CI_EVIDENCE_END
'''


def _clean_md_value(value):
    v=str(value or '').strip()
    v=re.sub(r'^[-*\s]+','',v)
    v=v.strip('`*_ \t')
    return v.strip()


def normalize_ci_evidence_prose(text, expected=None):
    """Conservatively recover exact Semaphore evidence when transport ignores JSON."""
    expected=expected or {}
    low=text.lower()
    base={
      'repo':str(expected.get('repo') or ''), 'branch':str(expected.get('branch') or ''),
      'candidate_sha':str(expected.get('candidate_sha') or ''), 'verified_candidate_sha':'',
      'run_id':str(expected.get('run_id') or ''), 'pipeline_id':str(expected.get('pipeline_id') or ''),
      'pipeline_status':'', 'pipeline_result':'', 'failed_jobs':[], 'summary':'', 'error':'',
      'normalized_from_prose':True,
    }
    if any(x in low for x in ('auth_required_human','semaphore_auth_required_human','human authentication required','credentials required','mfa required','otp required')):
        base['status']='AUTH_REQUIRED_HUMAN'; base['error']='SEMAPHORE_AUTH_REQUIRED_HUMAN'; base['summary']=text[-6000:]
        return base
    if any(x in low for x in ('semaphore_auth=required','authentication required','login is required','login page')):
        # Legacy prose is treated as human-required only after the v2.16 collector has attempted the GitHub interstitial recovery.
        base['status']='AUTH_REQUIRED_HUMAN'; base['error']='SEMAPHORE_AUTH_REQUIRED_HUMAN'; base['summary']=text[-6000:]
        return base
    missing=[]
    for k in ('candidate_sha','run_id','pipeline_id'):
        val=str(expected.get(k) or '')
        if val and val.lower() not in low:
            missing.append(k)
    if missing:
        base['status']='ERROR'; base['error']='PROSE_MISSING_EXACT_ANCHORS:'+','.join(missing); base['summary']=text[-12000:]
        return base
    exp_sha=str(expected.get('candidate_sha') or '')
    if exp_sha:
        base['verified_candidate_sha']=exp_sha
    else:
        m=re.search(r'\b[0-9a-f]{40}\b',text,re.I)
        if m: base['candidate_sha']=base['verified_candidate_sha']=m.group(0).lower()
    if re.search(r'\bresult\s*:\s*(?:\*\*)?failed',text,re.I) or re.search(r'\bpipeline\b[^\n]{0,80}\bfailed\b',text,re.I):
        base['pipeline_result']='failed'; base['pipeline_status']='done'
    elif re.search(r'\bresult\s*:\s*(?:\*\*)?success',text,re.I):
        base['pipeline_result']='success'; base['pipeline_status']='done'
    job=''
    for pat in (r'Only failed job\s*:\s*(?:\*\*)?([^\n*]+)',r'failed job\s*:\s*(?:\*\*)?([^\n*]+)',r'Job\s*:\s*(?:\*\*)?([^\n*]+)'):
        m=re.search(pat,text,re.I)
        if m:
            job=_clean_md_value(m.group(1)); break
    jid=''
    m=re.search(r'Job ID\s*:\s*`?([0-9a-f-]{16,})`?',text,re.I)
    if m: jid=m.group(1)
    block=''
    m=re.search(r'Block\s*:\s*`?([^\n`]+)',text,re.I)
    if m: block=_clean_md_value(m.group(1))
    step=''
    m=re.search(r'(?:command\s+)?step\s*`?(\d+)`?',text,re.I)
    if m: step=m.group(1)
    exit_status=''
    m=re.search(r'(?:exit(?:\s+status|\s+code)?|EXIT_STATUS)\s*[:=]\s*`?(-?\d+)',text,re.I)
    if m: exit_status=m.group(1)
    failure_lines=[]
    if step: failure_lines.append('reported_command_step='+step)
    for line in text.splitlines():
        ll=line.lower()
        if any(tok in ll for tok in ('error:', 'failed at', 'failure', 'blocker=', 'exit_status=')):
            failure_lines.append(line.strip())
        if len(failure_lines)>=12: break
    if job:
        base['failed_jobs']=[{'block':block,'job':job,'job_id':jid,'job_url':'','exit_status':exit_status,
          'failure_lines':'\n'.join(failure_lines),'log_text':text,'log_truncated':False,'log_total_chars':len(text),'reported_step':step}]
    anchors_ok=not missing and bool(base.get('candidate_sha')) and bool(base.get('run_id')) and bool(base.get('pipeline_id'))
    failure_ok=(base.get('pipeline_result')=='failed' and bool(base['failed_jobs']))
    if anchors_ok and failure_ok:
        base['status']='PASS'; base['summary']='CI evidence normalized conservatively from unstructured OpenCode prose; exact SHA/run/pipeline anchors were verified literally.'
    else:
        base['status']='ERROR'; base['error']='PROSE_EVIDENCE_INCOMPLETE'; base['summary']=text[-12000:]
    return base


def parse_ci_evidence_text(text, expected=None):
    begin='CI_EVIDENCE_BEGIN'; end='CI_EVIDENCE_END'
    raw=''
    if begin in text and end in text:
        raw=text.split(begin,1)[1].split(end,1)[0].strip()
    else:
        stripped=text.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            raw=stripped
    if not raw:
        return normalize_ci_evidence_prose(text, expected)
    try:
        obj=json.loads(raw)
    except Exception:
        return normalize_ci_evidence_prose(text, expected)
    if not isinstance(obj,dict):
        return normalize_ci_evidence_prose(text, expected)
    status=str(obj.get('status') or '').upper()
    if status not in {'PASS','AUTH_REQUIRED','AUTH_REQUIRED_HUMAN','NOT_FOUND','ERROR'}:
        return normalize_ci_evidence_prose(text, expected)
    obj['status']=status
    if status=='AUTH_REQUIRED':
        obj['status']='AUTH_REQUIRED_HUMAN'
        obj.setdefault('error','SEMAPHORE_AUTH_REQUIRED_HUMAN')
    if not isinstance(obj.get('failed_jobs'),list): obj['failed_jobs']=[]
    obj.setdefault('auth_recovery_attempted',False)
    obj.setdefault('auth_recovery_succeeded',False)
    obj.setdefault('auth_recovery_attempts',0)
    obj.setdefault('normalized_from_prose',False)
    return obj


def failure_identity_key(provider, sha, run_id, pipeline_id):
    raw='\0'.join([str(provider or '').strip().lower(),str(sha or '').strip().lower(),str(run_id or '').strip(),str(pipeline_id or '').strip()])
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def collect_semaphore_evidence(st, state_path, info):
    sha=str(info.get('sha') or st.get('candidate_sha') or st.get('baseline_sha') or '')
    run_id=str(info.get('run_id') or '')
    pipeline_id=str(info.get('pipeline_id') or '')
    if not sha or not run_id or not pipeline_id:
        raise RuntimeError(f'Semaphore evidence requires exact sha/run_id/pipeline_id; got sha={sha!r} run={run_id!r} pipeline={pipeline_id!r}')
    key=failure_identity_key('semaphore',sha,run_id,pipeline_id)
    evid=st.setdefault('semaphore_evidence',{})
    rec=evid.get(key) if isinstance(evid.get(key),dict) else {}
    path=Path(rec.get('path','')) if rec.get('path') else None
    if path and path.exists() and rec.get('status')=='PASS':
        return key,path,json.loads(path.read_text())
    req={'repo':st['repo'],'branch':st['branch'],'sha':sha,'runId':run_id,'pipelineId':pipeline_id,'url':os.environ.get('AI_LOOP_SEMAPHORE_URL','https://me.semaphoreci.com')}
    r=browser_broker_call(st.get('run_id') or 'semaphore','SEMAPHORE_READONLY',req,timeout=max(120,int(os.environ.get('AI_LOOP_CI_TOTAL_TIMEOUT_SECONDS','900'))))
    obj=r.get('evidence') if isinstance(r.get('evidence'),dict) else {}
    status=str(obj.get('status') or '').upper(); obj['status']=status if status in {'PASS','AUTH_REQUIRED_HUMAN','NOT_FOUND','ERROR'} else 'ERROR'
    if obj.get('status')=='PASS' and str(obj.get('verified_candidate_sha') or '') not in {'',sha}:
        obj['status']='ERROR'; obj['error']=f'CANDIDATE_SHA_MISMATCH expected={sha} observed={obj.get("verified_candidate_sha")}'
    d=RUNS_ROOT/st['run_id']/'ci'/'semaphore'; d.mkdir(parents=True,exist_ok=True)
    out=d/f'{key}.json'; out.write_text(json.dumps(obj,indent=2,ensure_ascii=False))
    text_out=d/f'{key}.txt'; text_out.write_text(render_semaphore_evidence(obj))
    evid[key]={'path':str(out),'text_path':str(text_out),'status':obj.get('status'),'provider':'semaphore','sha':sha,'run_id':run_id,'pipeline_id':pipeline_id,'identity_version':3,'collected_at':now()}
    save_state(state_path,st)
    return key,out,obj


def _yaml_unquote(v):
    v=str(v or '').strip()
    if len(v)>=2 and v[0]==v[-1] and v[0] in ('"',"'"):
        return v[1:-1]
    return v


def extract_semaphore_job_commands(yaml_text, job_name):
    if not job_name: return [], ''
    lines=yaml_text.splitlines(); start=None; job_indent=None
    name_re=re.compile(r'^(\s*)-?\s*name\s*:\s*(.+?)\s*$')
    for i,line in enumerate(lines):
        m=name_re.match(line)
        if m and _yaml_unquote(m.group(2)).strip()==job_name.strip():
            start=i; job_indent=len(m.group(1)); break
    if start is None: return [], ''
    end=len(lines)
    for i in range(start+1,len(lines)):
        if not lines[i].strip() or lines[i].lstrip().startswith('#'): continue
        indent=len(lines[i])-len(lines[i].lstrip(' '))
        if indent<=job_indent and re.match(r'^\s*-\s*(name\s*:|task\s*:|block\s*:)',lines[i]):
            end=i; break
    segment=lines[start:end]; commands=[]; ci=None; cindent=None
    for j,line in enumerate(segment):
        m=re.match(r'^(\s*)commands\s*:\s*$',line)
        if m: ci=j; cindent=len(m.group(1)); break
    if ci is not None:
        j=ci+1
        while j<len(segment):
            line=segment[j]
            if not line.strip() or line.lstrip().startswith('#'):
                j+=1; continue
            indent=len(line)-len(line.lstrip(' '))
            if indent<=cindent: break
            m=re.match(r'^(\s*)-\s*(.*)$',line)
            if not m:
                j+=1; continue
            item_indent=len(m.group(1)); val=m.group(2).rstrip()
            if val in ('|','|-','|+','>','>-','>+'):
                block=[]; j+=1
                while j<len(segment):
                    ln=segment[j]
                    if ln.strip():
                        ind=len(ln)-len(ln.lstrip(' '))
                        if ind<=item_indent: break
                        block.append(ln[min(len(ln),item_indent+2):])
                    else: block.append('')
                    j+=1
                commands.append('\n'.join(block).strip()); continue
            commands.append(_yaml_unquote(val)); j+=1
    lo=max(0,start-8); hi=min(len(lines),end+8)
    context='\n'.join(f'{i+1:04d}: {lines[i]}' for i in range(lo,hi))
    return [c for c in commands if c.strip()], context


def safe_ci_repro_command(command):
    c=str(command or '').strip()
    if not c: return False,'empty'
    if c=='checkout': return False,'semaphore checkout replaced by exact detached temp clone'
    low=c.lower()
    banned=[r'\bssh\b',r'\bscp\b',r'\bsftp\b',r'vps-ssh',r'\bcurl\b',r'\bwget\b',r'\bgh\b',r'\bsemaphore\b',
      r'\bsudo\b',r'\bsystemctl\b',r'\bservice\b',r'\bdocker\b',r'\bkubectl\b',r'\bmysql\b',r'\bpsql\b',
      r'\bkill\b',r'\bpkill\b',r'\bnohup\b',r'\bcrontab\b',r'\bgit\s+(push|commit|reset|clean|checkout|switch|merge|rebase|tag)\b',
      r'\b(rm|mv|cp|chmod|chown|setfacl|touch|truncate|install|mkdir)\b',r'\bpip(?:3)?\s+install\b',
      r'\b(apt|apt-get|dnf|yum|pacman|npm|pnpm|yarn)\b',r'/opt/',r'/var/',r'/tmp/log',r'(^|[^<])>{1,2}\s*[^&]',r'\btee\b']
    for pat in banned:
        if re.search(pat,low,re.M): return False,'unsafe pattern '+pat
    if not re.search(r'(unittest|pytest|py_compile|bash\s+-n|python(?:3)?\s+-m\s+(?:compileall|unittest|pytest))',low):
        return False,'not recognized as a validation/test command'
    return True,''


def collect_local_failure_investigation(st, state_path, info, sem_obj, repo_dir):
    sha=str(info.get('sha') or st.get('candidate_sha') or st.get('baseline_sha') or '')
    run_id=str(info.get('run_id') or ''); pipeline_id=str(info.get('pipeline_id') or '')
    key=hashlib.sha256(f'{sha}\0{run_id}\0{pipeline_id}\0local-v211'.encode()).hexdigest()[:20]
    store=st.setdefault('local_failure_evidence',{}); rec=store.get(key) if isinstance(store.get(key),dict) else {}
    p=Path(rec.get('path','')) if rec.get('path') else None
    if p and p.exists() and rec.get('status')=='PASS': return key,p,json.loads(p.read_text())
    obj={'status':'ERROR','candidate_sha':sha,'run_id':run_id,'pipeline_id':pipeline_id,'head':'','parent':'','tree':'','worktree_clean':False,
         'failed_job':'','failed_block':'','reported_step':'','semaphore_yaml_files':[],'job_yaml_context':'','extracted_commands':[],
         'executions':[],'reproduction_status':'NOT_EXECUTED','summary':'','error':''}
    jobs=sem_obj.get('failed_jobs') or []; job=jobs[0] if jobs and isinstance(jobs[0],dict) else {}
    obj['failed_job']=str(job.get('job') or ''); obj['failed_block']=str(job.get('block') or ''); obj['reported_step']=str(job.get('reported_step') or '')
    if not obj['reported_step']:
        m=re.search(r'(?:command\s+)?step\s*[=:]?\s*`?(\d+)',str(job.get('failure_lines') or ''),re.I)
        if m: obj['reported_step']=m.group(1)
    tmp=Path(tempfile.mkdtemp(prefix='ai-loop-ci-repro-')); clone=tmp/'repo'
    try:
        def run(argv,timeout=180): return subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
        clone_url=os.environ.get('AI_LOOP_REPO_CLONE_URL','git@github.com:Trochez/bot_trading.git')
        cp=run(['git','clone','--no-checkout',clone_url,str(clone)],300)
        if cp.returncode: raise RuntimeError('TEMP_CLONE_FAILED: '+cp.stderr[-2000:])
        cp=run(['git','-C',str(clone),'checkout','--detach',sha],180)
        if cp.returncode: raise RuntimeError('TEMP_CHECKOUT_FAILED: '+cp.stderr[-2000:])
        obj['head']=run(['git','-C',str(clone),'rev-parse','HEAD']).stdout.strip()
        obj['tree']=run(['git','-C',str(clone),'show','-s','--format=%T','HEAD']).stdout.strip()
        obj['parent']=run(['git','-C',str(clone),'rev-parse','HEAD^']).stdout.strip()
        obj['worktree_clean']=not bool(run(['git','-C',str(clone),'status','--porcelain=v1','--untracked-files=all']).stdout.strip())
        if obj['head']!=sha: raise RuntimeError(f'HEAD_MISMATCH expected={sha} observed={obj["head"]}')
        semdir=clone/'.semaphore'; yamls=[]
        if semdir.exists(): yamls=sorted([x for x in semdir.rglob('*') if x.is_file() and x.suffix.lower() in ('.yml','.yaml')])
        obj['semaphore_yaml_files']=[str(x.relative_to(clone)) for x in yamls]
        chosen=[]; context=''
        for yf in yamls:
            cmds,ctx=extract_semaphore_job_commands(yf.read_text(errors='replace'),obj['failed_job'])
            if cmds: chosen=cmds; context=f'FILE={yf.relative_to(clone)}\n'+ctx; break
        obj['extracted_commands']=chosen; obj['job_yaml_context']=context[:30000]
        for idx,cmd in enumerate(chosen,1):
            safe,reason=safe_ci_repro_command(cmd)
            recx={'index':idx,'command':cmd,'safe':safe,'skip_reason':reason,'exit_code':None,'stdout':'','stderr':'','timed_out':False}
            if safe:
                try:
                    cp=subprocess.run(['bash','-lc',cmd],cwd=str(clone),capture_output=True,text=True,timeout=900)
                    recx.update({'exit_code':cp.returncode,'stdout':cp.stdout[-30000:],'stderr':cp.stderr[-30000:]})
                except subprocess.TimeoutExpired as e:
                    recx.update({'exit_code':124,'timed_out':True,'stdout':str(e.stdout or '')[-30000:],'stderr':str(e.stderr or '')[-30000:]})
            obj['executions'].append(recx)
        ran=[x for x in obj['executions'] if x['safe']]
        obj['reproduction_status']='FAILED_REPRODUCED' if any(x.get('exit_code')!=0 for x in ran) else ('SAFE_VALIDATIONS_PASS' if ran else 'NOT_EXECUTED_NO_SAFE_EXTRACTED_COMMAND')
        obj['status']='PASS'; obj['summary']='Exact-SHA temporary-clone investigation completed without mutating source repo, production VPS, or Semaphore.'
    except Exception as e:
        obj['status']='ERROR'; obj['error']=str(e); obj['summary']='Local exact-SHA investigation could not complete.'
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
    d=RUNS_ROOT/st['run_id']/'ci'/'local-reproduction'; d.mkdir(parents=True,exist_ok=True)
    out=d/f'{key}.json'; out.write_text(json.dumps(obj,indent=2,ensure_ascii=False))
    txt=d/f'{key}.txt'; txt.write_text(render_local_failure_evidence(obj))
    store[key]={'path':str(out),'text_path':str(txt),'status':obj.get('status'),'collected_at':now()}; save_state(state_path,st)
    log(f"local exact-SHA investigation status={obj.get('status')} reproduction={obj.get('reproduction_status')} sha={sha}")
    return key,out,obj


def render_local_failure_evidence(obj):
    lines=['===== LOCAL EXACT-SHA FAILURE INVESTIGATION =====',f"STATUS={obj.get('status','')}",f"CANDIDATE_SHA={obj.get('candidate_sha','')}",
      f"HEAD={obj.get('head','')}",f"PARENT={obj.get('parent','')}",f"TREE={obj.get('tree','')}",f"WORKTREE_CLEAN={obj.get('worktree_clean',False)}",
      f"FAILED_BLOCK={obj.get('failed_block','')}",f"FAILED_JOB={obj.get('failed_job','')}",f"REPORTED_STEP={obj.get('reported_step','')}",
      f"REPRODUCTION_STATUS={obj.get('reproduction_status','')}",f"SUMMARY={obj.get('summary','')}",f"ERROR={obj.get('error','')}",
      'SEMAPHORE_YAML_FILES='+json.dumps(obj.get('semaphore_yaml_files') or []),'--- JOB YAML CONTEXT ---',str(obj.get('job_yaml_context',''))]
    for x in obj.get('executions') or []:
        lines += [f"--- COMMAND {x.get('index')} safe={x.get('safe')} rc={x.get('exit_code')} ---",str(x.get('command','')),
                  f"SKIP_REASON={x.get('skip_reason','')}",'STDOUT:',str(x.get('stdout','')),'STDERR:',str(x.get('stderr',''))]
    lines.append('===== END LOCAL INVESTIGATION ====='); return '\n'.join(lines)


def send_failure_evidence_bundle(st, state_path, key, sem_obj, local_obj, purpose='failure-evidence-bundle'):
    deliveries=st.setdefault('failure_evidence_deliveries',{})
    if deliveries.get(key): return None
    text=render_semaphore_evidence(sem_obj)+'\n\n'+render_local_failure_evidence(local_obj)
    attach=stage_text(st['run_id'],f'failure-evidence-bundle-{key}.txt',text)
    msg=(f"Combined read-only failure evidence is attached for exact candidate_sha={sem_obj.get('candidate_sha')} run_id={sem_obj.get('run_id')} "
         f"pipeline_id={sem_obj.get('pipeline_id')}. Semaphore evidence and exact-SHA temporary-clone investigation are included. "
         f"Local reproduction status={local_obj.get('reproduction_status')}. Review this evidence before diagnosis; request only additional exact operator actions if needed. Do not rerun Semaphore yet.")
    ev=guarded_send(st,state_path,msg,purpose,str(attach),delivery_id='failure-evidence-'+key)
    if ev.get('delivery_status') in {'SENT','ALREADY_SENT'}:
        deliveries[key]={'delivered_at':now(),'attachment':str(attach),'provider':'semaphore','candidate_sha':sem_obj.get('candidate_sha'),'run_id':sem_obj.get('run_id'),'pipeline_id':sem_obj.get('pipeline_id'),'identity_version':2,'local_status':local_obj.get('reproduction_status')}; st['failure_stage']='EVIDENCE_DELIVERED'; save_state(state_path,st)
    return ev


def render_semaphore_evidence(obj):
    lines=[
      '===== SEMAPHORE EXACT FAILURE EVIDENCE =====',
      f"STATUS={obj.get('status','')}",
      f"REPO={obj.get('repo','')}",
      f"BRANCH={obj.get('branch','')}",
      f"CANDIDATE_SHA={obj.get('candidate_sha','')}",
      f"VERIFIED_CANDIDATE_SHA={obj.get('verified_candidate_sha','')}",
      f"RUN_ID={obj.get('run_id','')}",
      f"PIPELINE_ID={obj.get('pipeline_id','')}",
      f"PIPELINE_STATUS={obj.get('pipeline_status','')}",
      f"PIPELINE_RESULT={obj.get('pipeline_result','')}",
      f"SUMMARY={obj.get('summary','')}",
      f"ERROR={obj.get('error','')}",
    ]
    for i,j in enumerate(obj.get('failed_jobs') or [],1):
        lines += [
          f'----- FAILED JOB {i} -----',
          f"BLOCK={j.get('block','')}", f"JOB={j.get('job','')}", f"JOB_ID={j.get('job_id','')}",
          f"JOB_URL={j.get('job_url','')}", f"EXIT_STATUS={j.get('exit_status','')}",
          f"LOG_TRUNCATED={j.get('log_truncated',False)}", f"LOG_TOTAL_CHARS={j.get('log_total_chars',0)}",
          'FAILURE_LINES:', str(j.get('failure_lines','')), 'RAW_LOG:', str(j.get('log_text','')),
        ]
    lines.append('===== END SEMAPHORE EVIDENCE =====')
    return '\n'.join(lines)


def send_semaphore_evidence(st, state_path, key, path, obj, purpose='semaphore-failure-evidence'):
    deliveries=st.setdefault('semaphore_evidence_deliveries',{})
    if deliveries.get(key):
        return None
    text=render_semaphore_evidence(obj)
    attach=stage_text(st['run_id'],f'semaphore-evidence-{key}.txt',text)
    msg=(f"Read-only Semaphore evidence collected for the exact candidate failure. "
         f"candidate_sha={obj.get('candidate_sha')} run_id={obj.get('run_id')} pipeline_id={obj.get('pipeline_id')}. "
         "The complete collected job evidence is attached. Review it before diagnosis and request only additional exact operator evidence if still needed.")
    ev=guarded_send(st,state_path,msg,purpose,str(attach),delivery_id='semaphore-evidence-'+key)
    if ev.get('delivery_status') in {'SENT','ALREADY_SENT'}:
        deliveries[key]={'delivered_at':now(),'path':str(path)}
        save_state(state_path,st)
    return ev

def _norm_ui_label(value):
    return re.sub(r'\s+',' ',str(value or '').strip()).lower()


def chat_policy_pass(ev):
    """Strict fail-closed proof for the authoritative ChatGPT Web surface/model."""
    if not isinstance(ev,dict):
        return False
    if str(ev.get('chat_policy_status') or '').upper()!='PASS':
        return False
    surface=_norm_ui_label(ev.get('ui_surface'))
    model=_norm_ui_label(ev.get('ui_model'))
    reasoning=_norm_ui_label(ev.get('ui_reasoning'))
    if surface != CHATGPT_REQUIRED_SURFACE:
        return False
    if any(x in surface for x in CHATGPT_FORBIDDEN_SURFACES):
        return False
    if model != _norm_ui_label(CHATGPT_REQUIRED_MODEL):
        return False
    if reasoning != _norm_ui_label(CHATGPT_REQUIRED_REASONING):
        return False
    return True


def browser_chat_policy_guard_prompt(target_url):
    return f'''ROLE: CHATGPT_CHAT_POLICY_GUARD.
Use Playwright browser tools only. Do NOT send any ChatGPT message. Do NOT attach a file. Do NOT create a task in Work or Codex.
Open/stay at exactly this ChatGPT URL:\n{target_url}\n
MANDATORY PRODUCT POLICY FOR THIS ai-loop:
- AUTHORITATIVE SURFACE = normal Chat only.
- FORBIDDEN SURFACES = Work and Codex.
- REQUIRED MODEL = GPT-5.6 Sol.
- REQUIRED REASONING = High.
- GPT-5.6 Sol Light, Instant, Medium, any Luna/Terra selection, Work, Codex, Astra-through-Work, or an unreadable/unknown model state are NOT valid fallbacks.
- The global page title "ChatGPT: Chat, Work, Create & Code with AI" is not proof of the active surface.

Use multiple live UI signals, preferring accessible names/roles and visible selected controls over CSS position. Known examples are advisory, not the only accepted labels:
- Work signal: active Work mode or composer text such as "Work on anything".
- Normal Chat signal: active Chat mode and a normal chat composer such as "Chat with ChatGPT" or "Ask ChatGPT".

RECOVERY, WITHOUT SENDING:
1. Detect the currently active product surface. If Work or Codex is active, switch the UI to normal Chat WITHOUT submitting a message and WITHOUT starting a Work/Codex task.
2. Preserve the current /c/ conversation when target_url is a conversation. If switching to Chat would destroy/replace the current thread, do not continue: return ERROR with error=CHAT_SURFACE_SWITCH_WOULD_REPLACE_THREAD.
3. Open the model/reasoning picker. Select GPT-5.6 Sol and set reasoning to High. Never select Work/Codex merely to obtain GPT-6 Astra.
4. Close the picker and independently re-read the visible selected state.
5. PASS only when the live UI proves all three simultaneously: surface=CHAT, model=GPT-5.6 Sol, reasoning=High.
6. If the UI says Light, Instant, Medium, Work, Codex, another model, or the required state cannot be proven, return ERROR. Do not silently continue.

On PASS return state=NO_ACTIONS, delivery_status=NONE, ui_surface="CHAT", ui_model="GPT-5.6 Sol", ui_reasoning="High", chat_policy_status="PASS".
On failure return state=ERROR, delivery_status=NONE, chat_policy_status="FAIL" and a precise error such as CHAT_SURFACE_UNVERIFIED, MODEL_GUARD_UNVERIFIED, or REASONING_HIGH_UNAVAILABLE. Never claim PASS from memory or from model prose; verify the live UI.'''


def browser_chat_model_probe_prompt(target_url):
    return f'''ROLE: CHATGPT_MODEL_SELECTOR_PROBE.
Use Playwright browser tools only. Do NOT send a ChatGPT message, do NOT attach a file, and do NOT create Work/Codex tasks.
Stay at exactly this URL:
{target_url}

This is a recovery probe used only when the ordinary guard proved normal Chat and High reasoning but could not read the model label. The goal is to deterministically prove or repair the selected model without relying on page title, assistant prose, memory, or a guessed label.

MANDATORY target:
- surface = normal Chat
- model = GPT-5.6 Sol
- reasoning = High
- Work/Codex = forbidden

Use this exact evidence procedure:
1. First verify the active surface is normal Chat. If Work/Codex is active, switch to Chat without sending anything; if that cannot be proven, fail CHAT_SURFACE_UNVERIFIED.
2. Use playwright_browser_run_code to inspect LIVE UI controls outside assistant-message article content. Enumerate candidate elements matching button, [role=button], [role=menuitemradio], [role=option], [aria-checked], and [data-state]. For each candidate collect only short visible text, aria-label, title, role, aria-checked, aria-selected, and data-state. Filter for strings containing GPT, 5.6, Sol, model, High, Medium, Light, Instant, or reasoning. Do not use text inside article assistant messages as selector proof.
3. Locate the model selector from accessible/visible UI evidence. Open it if necessary. Once open, inspect menuitemradio/option/check-state controls again. A model is proven selected only when one of these is true:
   a. a checked/selected model option has visible/accessibility text matching GPT-5.6 Sol; or
   b. you click the exact visible GPT-5.6 Sol option, close/reopen the selector, and the option is then visibly checked/selected.
   A header label by itself is advisory, not sufficient if the picker can be opened.
4. If GPT-5.6 Sol is visible but not selected, click exactly that model option. Never choose Work, Codex, Astra, Luna, Terra, Light, Instant, or Medium as a substitute.
5. Verify reasoning High with the same selected-state principle: inspect the reasoning control/options and prove High is checked/selected. If needed, select High and reopen/re-read to prove it persisted.
6. Close menus without sending anything.
7. Re-run a compact playwright_browser_run_code evidence scan after selection. Return PASS only if the live controls prove Chat + GPT-5.6 Sol + High simultaneously.

IMPORTANT normalization rule: the UI may split the product/model label across nested spans or expose the model only in the OPEN picker. If the checked/selected option's combined innerText/aria-label contains both "5.6" and "Sol" and identifies GPT/ChatGPT model selection, normalize ui_model exactly to "GPT-5.6 Sol". Do not leave ui_model empty merely because the closed header omits the model name.

Put a concise evidence summary (max 800 characters) in sol_text, for example which selected/checked control proved the model and reasoning. Never copy assistant answer prose into this evidence field.

On PASS return state=NO_ACTIONS, delivery_status=NONE, ui_surface="CHAT", ui_model="GPT-5.6 Sol", ui_reasoning="High", chat_policy_status="PASS".
On failure return state=ERROR, delivery_status=NONE, chat_policy_status="FAIL", preserve any surface/reasoning values actually proven, and use a precise error. If the model selector exists but no selected model can be proven, use error=MODEL_SELECTOR_STATE_UNVERIFIED. If GPT-5.6 Sol is unavailable, use error=REQUIRED_MODEL_UNAVAILABLE.'''


CHAT_POLICY_BEGIN='AI_LOOP_CHAT_POLICY_EVENT_V1_BEGIN'
CHAT_POLICY_END='AI_LOOP_CHAT_POLICY_EVENT_V1_END'
CHAT_POLICY_PROOF_V2='AI_LOOP_CHAT_POLICY_PROOF_V2|'


def chat_policy_event_contract_text(guard_kind='full-policy-guard'):
    kind=str(guard_kind or 'full-policy-guard')
    return f'''
CHAT POLICY OUTPUT CONTRACT v2 (mandatory):
After all Playwright work is complete, make one FINAL `playwright_browser_run_code` proof call that re-reads the live URL and selected UI controls. The tool result must return one single ASCII line and your final answer must copy that exact line verbatim.
Required line format:
{CHAT_POLICY_PROOF_V2}guard={kind}|status=PASS|chat_url=<encodeURIComponent(live URL)>|surface=CHAT|model=GPT-5.6 Sol|reasoning=High|policy=PASS|error=NONE
For ERROR use status=ERROR, policy=FAIL and a short ASCII error code. For rate limiting use status=RATE_LIMIT.
Rules:
- The proof line MUST originate from the FINAL Playwright run_code tool result, not from prose or memory.
- guard MUST be exactly {kind}.
- PASS requires surface=CHAT, model=GPT-5.6 Sol, reasoning=High, policy=PASS.
- Never output generic AI_LOOP_EVENT markers in this policy turn.
- Compatibility only: the legacy dedicated JSON envelope below may also be emitted, but the v2 proof line is authoritative when present.
{CHAT_POLICY_BEGIN}
{{"schema_version":1,"guard_kind":"{kind}","status":"PASS|ERROR|RATE_LIMIT","chat_url":"...","error":"","ui_surface":"CHAT|WORK|CODEX|UNKNOWN","ui_model":"GPT-5.6 Sol or empty","ui_reasoning":"High or empty","chat_policy_status":"PASS|FAIL","evidence":"short live-UI evidence"}}
{CHAT_POLICY_END}
'''

def _chat_policy_schema_v1(value):
    """Accept only the explicit v1 schema encodings emitted by the dedicated policy protocol."""
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, int):
        return value == 1
    if isinstance(value, float):
        return value == 1.0
    token=str(value).strip()
    return token in {'1','1.0','V1','v1','AI_LOOP_CHAT_POLICY_EVENT_V1'}


def parse_chat_policy_response(text, expected_guard_kind='full-policy-guard'):
    """Parse tool-result proof first; legacy dedicated JSON is compatibility only."""
    from urllib.parse import unquote
    txt=_strip_ansi(str(text or ''))
    expected=str(expected_guard_kind or 'full-policy-guard')

    proof_objs=[]; proof_errors=[]
    for m in re.finditer(re.escape(CHAT_POLICY_PROOF_V2)+r'[^\r\n`]*', txt):
        line=m.group(0).strip()
        try:
            fields={}
            for part in line.split('|')[1:]:
                if '=' not in part: continue
                k,v=part.split('=',1); fields[k.strip()]=v.strip()
            if str(fields.get('guard') or '') != expected:
                raise ValueError('CHAT_POLICY_GUARD_KIND_MISMATCH')
            status=str(fields.get('status') or '').upper()
            if status not in {'PASS','ERROR','RATE_LIMIT'}:
                raise ValueError('CHAT_POLICY_STATUS_INVALID')
            obj={
              'status':status,'chat_url':unquote(str(fields.get('chat_url') or '')),
              'error':'' if str(fields.get('error') or '').upper() in {'','NONE'} else str(fields.get('error') or ''),
              'ui_surface':str(fields.get('surface') or ''),'ui_model':str(fields.get('model') or ''),
              'ui_reasoning':str(fields.get('reasoning') or ''),'chat_policy_status':str(fields.get('policy') or ''),
              'evidence':'chat-policy v2 Playwright proof',
            }
            proof_objs.append(obj)
        except Exception as e:
            proof_errors.append(str(e))
    if proof_objs:
        obj=proof_objs[-1]
    else:
        candidates=[]; pos=0
        while True:
            i=txt.find(CHAT_POLICY_BEGIN,pos)
            if i < 0: break
            j=txt.find(CHAT_POLICY_END,i+len(CHAT_POLICY_BEGIN))
            if j < 0: break
            candidates.append(txt[i+len(CHAT_POLICY_BEGIN):j].strip())
            pos=j+len(CHAT_POLICY_END)
        obj=None; last_error='CHAT_POLICY_MARKERS_MISSING' if not candidates else 'NO_VALID_CHAT_POLICY_ENVELOPE'
        for raw in reversed(candidates):
            try:
                cand=json.loads(raw)
            except Exception as e:
                last_error='CHAT_POLICY_JSON_INVALID:'+str(e); continue
            if not isinstance(cand,dict) or not _chat_policy_schema_v1(cand.get('schema_version')):
                last_error='CHAT_POLICY_SCHEMA_INVALID'; continue
            if str(cand.get('guard_kind') or '') != expected:
                last_error='CHAT_POLICY_GUARD_KIND_MISMATCH'; continue
            status=str(cand.get('status') or '').upper()
            if status not in {'PASS','ERROR','RATE_LIMIT'}:
                last_error='CHAT_POLICY_STATUS_INVALID'; continue
            obj=cand; break
        if obj is None:
            detail=proof_errors[-1] if proof_errors else last_error
            raise RuntimeError(detail)
    status=str(obj.get('status') or '').upper()
    state='NO_ACTIONS' if status=='PASS' else ('RATE_LIMIT' if status=='RATE_LIMIT' else 'ERROR')
    delivery='NOT_SENT_RATE_LIMIT' if status=='RATE_LIMIT' else 'NONE'
    return _validate_event({
      'state':state,'chat_url':str(obj.get('chat_url') or ''),'sol_text':str(obj.get('evidence') or '')[:1600],
      'needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'',
      'error':str(obj.get('error') or ''),'delivery_status':delivery,
      'ui_surface':str(obj.get('ui_surface') or ''),'ui_model':str(obj.get('ui_model') or ''),
      'ui_reasoning':str(obj.get('ui_reasoning') or ''),'chat_policy_status':str(obj.get('chat_policy_status') or ''),
    })

def chat_policy_oc_turn(prompt, purpose, guard_kind='full-policy-guard'):
    raw=oc_raw_turn(prompt + chat_policy_event_contract_text(guard_kind), purpose)
    return parse_chat_policy_response(raw,guard_kind)


def _record_chat_policy(st, ev, purpose=''):
    if not isinstance(st,dict):
        return
    rec={
      'at':now(),'purpose':str(purpose),'chat_url':str(ev.get('chat_url') or st.get('chat_url') or ''),
      'ui_surface':str(ev.get('ui_surface') or ''),'ui_model':str(ev.get('ui_model') or ''),
      'ui_reasoning':str(ev.get('ui_reasoning') or ''),'status':str(ev.get('chat_policy_status') or ''),
    }
    hist=st.setdefault('chat_policy_audit',[])
    if isinstance(hist,list):
        hist.append(rec)
        if len(hist)>50: del hist[:-50]
    st['chat_policy_last']=rec


# ---------------------------------------------------------------------------
# v3 adaptive DOM-guided browser transport
# ---------------------------------------------------------------------------
ADAPTIVE_OBS_PREFIX='AI_LOOP_BROWSER_OBS_V1|'
ADAPTIVE_PREFLIGHT_PREFIX='AI_LOOP_BOOTSTRAP_PREFLIGHT_V1|'
ADAPTIVE_PRESEND_PREFIX='AI_LOOP_BOOTSTRAP_PRESEND_V1|'
ADAPTIVE_SENDTX_PREFIX='AI_LOOP_BOOTSTRAP_SENDTX_V1|'


def _b64url_decode_json(token):
    raw=str(token or '').strip()
    raw += '=' * ((4-len(raw)%4)%4)
    data=base64.urlsafe_b64decode(raw.encode('ascii'))
    obj=json.loads(data.decode('utf-8'))
    if not isinstance(obj,dict):
        raise ValueError('ADAPTIVE_OBSERVATION_NOT_OBJECT')
    return obj


def _parse_adaptive_payload_line(text, prefix, nonce):
    """Parse only deterministic Playwright run_code output; never model prose/JSON."""
    txt=_strip_ansi(str(text or ''))
    needle=f'{prefix}nonce={nonce}|payload='
    vals=[]
    for m in re.finditer(re.escape(needle)+r'([A-Za-z0-9_-]+)',txt):
        try:
            vals.append(_b64url_decode_json(m.group(1)))
        except Exception:
            continue
    if not vals:
        raise RuntimeError(f'ADAPTIVE_PLAYWRIGHT_PROOF_MISSING prefix={prefix} nonce={nonce}; tail='+txt[-1800:].replace('\n',' ')[:1800])
    return vals[-1]


def _adaptive_project_id(project_url):
    m=re.search(r'/g/(g-p-[^/]+)',str(project_url or ''))
    return m.group(1) if m else ''


def _adaptive_delivery_id(run_id, plan_filename, plan_path):
    h=hashlib.sha256()
    h.update(str(run_id).encode()); h.update(b'\0')
    h.update(str(plan_filename).encode()); h.update(b'\0')
    try:
        h.update(Path(plan_path).read_bytes())
    except Exception:
        h.update(str(plan_path).encode())
    return h.hexdigest()[:24]


def _adaptive_obs_js(nonce, project_url, delivery_id='', plan_filename='', implement_text='', mode='OBSERVE'):
    """Return JS whose exact proof prefix is constructed at runtime so prompt echo cannot satisfy the parser."""
    cfg={
      'nonce':str(nonce),'projectUrl':str(project_url),'projectId':_adaptive_project_id(project_url),
      'deliveryId':str(delivery_id),'planFilename':str(plan_filename),'implementText':str(implement_text),
      'mode':str(mode),
    }
    cfgj=json.dumps(cfg,separators=(',',':'))
    return r'''async page => {
  const cfg = '''+cfgj+r''';
  return await page.evaluate((cfg) => {
    const norm = s => String(s||'').replace(/\s+/g,' ').trim();
    const low = s => norm(s).toLowerCase();
    const vis = el => { try { const r=el.getBoundingClientRect(); const st=getComputedStyle(el); return r.width>0&&r.height>0&&st.visibility!=='hidden'&&st.display!=='none'; } catch(e){return false;} };
    const attr = (el,n) => el.getAttribute(n)||'';
    const selected = el => attr(el,'aria-checked')==='true'||attr(el,'aria-selected')==='true'||attr(el,'aria-pressed')==='true'||attr(el,'data-state')==='checked'||attr(el,'data-state')==='selected'||attr(el,'data-state')==='active';
    const all=[...document.querySelectorAll('button,[role="button"],[role="menuitemradio"],[role="option"],[role="tab"],[aria-checked],[aria-selected],[aria-pressed],[data-state],a[href],textarea,[contenteditable="true"],input[type="file"]')].filter(vis);
    const desc=all.slice(0,700).map(el=>({
      tag:el.tagName.toLowerCase(), role:attr(el,'role'), text:norm(el.innerText||el.textContent).slice(0,220), aria:norm(attr(el,'aria-label')).slice(0,220),
      title:norm(attr(el,'title')).slice(0,160), checked:attr(el,'aria-checked'), selected:attr(el,'aria-selected'), pressed:attr(el,'aria-pressed'), state:attr(el,'data-state'), href:attr(el,'href').slice(0,500), isSelected:selected(el)
    }));
    const sig = d => low([d.text,d.aria,d.title].join(' '));
    const rel=desc.filter(d=>/(chat|work|codex|gpt|5\.6|sol|high|medium|light|instant|reason|model|new chat|attach|upload|file)/i.test(sig(d))).slice(0,120);
    const selectedRel=rel.filter(d=>d.isSelected);
    const bodyLow=low(document.body.innerText||'');
    const composerEls=all.filter(el=>el.matches('textarea,[contenteditable="true"]'));
    const composerText=norm(composerEls.map(el=>el.value||el.innerText||el.textContent||'').join(' '));
    const normalComposer=composerEls.some(el=>/(ask|message|chat|prompt)/i.test([attr(el,'placeholder'),attr(el,'aria-label')].join(' '))) || composerEls.length>0;
    const stateTexts=selectedRel.map(sig);
    let surface='UNKNOWN';
    const workPhrase=bodyLow.includes('work on anything');
    const codexPhrase=bodyLow.includes('codex') && rel.some(d=>/(codex)/i.test(sig(d))&&d.isSelected);
    if(stateTexts.some(t=>/\bwork\b/.test(t)) || workPhrase) surface='WORK';
    else if(stateTexts.some(t=>/\bcodex\b/.test(t)) || codexPhrase) surface='CODEX';
    else if(stateTexts.some(t=>/(^|\b)chat(\b|$)/.test(t))) surface='CHAT';
    else if(normalComposer && !workPhrase && !rel.some(d=>d.isSelected&&/(work|codex)/i.test(sig(d)))) surface='CHAT';
    const modelProof=rel.find(d=>d.isSelected && /5\.6/.test(sig(d)) && /sol/.test(sig(d))) || rel.find(d=>!['menuitemradio','option'].includes(String(d.role||'').toLowerCase()) && d.tag==='button' && /5\.6/.test(sig(d))&&/sol/.test(sig(d)));
    const model=modelProof?'GPT-5.6 Sol':'';
    const reasonProof=rel.find(d=>d.isSelected && /(^|\b)high(\b|$)/.test(sig(d))) || rel.find(d=>!['menuitemradio','option'].includes(String(d.role||'').toLowerCase()) && d.tag==='button' && /(^|\b)high(\b|$)/.test(sig(d)));
    const reasoning=reasonProof?'High':'';
    const turnNodes=[...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"],article[data-testid^="conversation-turn"]')].filter(vis);
    const uniq=[]; const seen=new Set(); for(const el of turnNodes){ if(!seen.has(el)){seen.add(el);uniq.push(el);} }
    const userNodes=[...document.querySelectorAll('[data-message-author-role="user"]')].filter(vis);
    let userTexts=userNodes.map(el=>norm(el.innerText||el.textContent)).filter(Boolean);
    if(!userTexts.length){
      userTexts=uniq.filter(el=>/user/i.test(attr(el,'data-testid'))||el.querySelector('[data-message-author-role="user"]')).map(el=>norm(el.innerText||el.textContent)).filter(Boolean);
    }
    const url=location.href;
    const projectId=cfg.projectId;
    const projectLinks=desc.filter(d=>projectId && String(d.href||'').includes(projectId));
    const selectedProject=projectLinks.some(d=>d.isSelected);
    const project=!!projectId && (url.includes(projectId) || selectedProject);
    const deliveryPresent=!!cfg.deliveryId && userTexts.some(t=>t.includes(cfg.deliveryId));
    const filenamePresent=!!cfg.planFilename && bodyLow.includes(low(cfg.planFilename));
    const messagePrefix=low(String(cfg.implementText||'').slice(0,80));
    const messagePresent=!!messagePrefix && userTexts.some(t=>low(t).includes(messagePrefix));
    const key=cfg.deliveryId?('ai_loop_bootstrap_'+cfg.deliveryId):'';
    let ledger={}; try { if(key) ledger=JSON.parse(localStorage.getItem(key)||'{}')||{}; } catch(e){}
    const diagnostics={
      url, projectId, project, turnCount:uniq.length, userTurnCount:userTexts.length, composerText:composerText.slice(0,500),
      surface, model, reasoning, deliveryPresent, filenamePresent, messagePresent,
      selectedControls:selectedRel.slice(0,30), relevantControls:rel.slice(0,50), projectLinks:projectLinks.slice(0,12),
      htmlExcerpt:rel.slice(0,24).map(d=>JSON.stringify(d)).join('\n').slice(0,12000)
    };
    const out={schema:'AI_LOOP_BROWSER_OBS_V1',mode:cfg.mode,url,project,turn_count:uniq.length,user_turn_count:userTexts.length,composer_text:composerText.slice(0,600),surface,model,reasoning,delivery_present:deliveryPresent,filename_present:filenamePresent,message_present:messagePresent,ledger,diagnostics};
    const utf8=s=>unescape(encodeURIComponent(s));
    const b64url=s=>btoa(utf8(s)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
    const prefix='AI_LOOP_BROWSER_'+'OBS_V1|';
    return prefix+'nonce='+cfg.nonce+'|payload='+b64url(JSON.stringify(out));
  }, cfg);
}'''


def _adaptive_preflight_js(nonce, project_url, delivery_id):
    cfg={'nonce':str(nonce),'projectUrl':str(project_url),'projectId':_adaptive_project_id(project_url),'deliveryId':str(delivery_id)}
    cfgj=json.dumps(cfg,separators=(',',':'))
    return r'''async page => {
 const cfg='''+cfgj+r''';
 return await page.evaluate(cfg=>{
  const norm=s=>String(s||'').replace(/\s+/g,' ').trim(), low=s=>norm(s).toLowerCase();
  const vis=el=>{try{const r=el.getBoundingClientRect(),st=getComputedStyle(el);return r.width>0&&r.height>0&&st.display!=='none'&&st.visibility!=='hidden';}catch(e){return false;}};
  const attr=(e,n)=>e.getAttribute(n)||'';
  const sel=e=>attr(e,'aria-checked')==='true'||attr(e,'aria-selected')==='true'||attr(e,'aria-pressed')==='true'||['checked','selected','active'].includes(attr(e,'data-state'));
  const nodes=[...document.querySelectorAll('button,[role="button"],[role="menuitemradio"],[role="option"],[role="tab"],[aria-checked],[aria-selected],[aria-pressed],[data-state],a[href],textarea,[contenteditable="true"]')].filter(vis);
  const D=nodes.map(e=>({tag:e.tagName.toLowerCase(),t:norm(e.innerText||e.textContent).slice(0,220),a:norm(attr(e,'aria-label')).slice(0,220),r:attr(e,'role'),h:attr(e,'href'),s:sel(e)}));
  const sig=d=>low(d.t+' '+d.a); const rel=D.filter(d=>/(chat|work|codex|gpt|5\.6|sol|high|medium|light|instant|reason|model)/i.test(sig(d)));
  const sr=rel.filter(d=>d.s).map(sig); const composer=nodes.some(e=>e.matches('textarea,[contenteditable="true"]')); const bodyLow=low(document.body.innerText||'');
  const workPhrase=bodyLow.includes('work on anything');
  let surface=(sr.some(t=>/\bwork\b/.test(t))||workPhrase)?'WORK':sr.some(t=>/\bcodex\b/.test(t))?'CODEX':sr.some(t=>/\bchat\b/.test(t))?'CHAT':(composer&&!workPhrase?'CHAT':'UNKNOWN');
  const model=rel.some(d=>d.s&&/5\.6/.test(sig(d))&&/sol/.test(sig(d)))||rel.some(d=>d.tag==='button'&&!['menuitemradio','option'].includes(String(d.r||'').toLowerCase())&&/5\.6/.test(sig(d))&&/sol/.test(sig(d)))?'GPT-5.6 Sol':'';
  const reasoning=rel.some(d=>d.s&&/(^|\b)high(\b|$)/.test(sig(d)))||rel.some(d=>d.tag==='button'&&!['menuitemradio','option'].includes(String(d.r||'').toLowerCase())&&/(^|\b)high(\b|$)/.test(sig(d)))?'High':'';
  const turns=[...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"],article[data-testid^="conversation-turn"]')].filter(vis);
  const project=!!cfg.projectId && (location.href.includes(cfg.projectId)||D.some(d=>d.h&&d.h.includes(cfg.projectId)&&d.s));
  const ready=project&&turns.length===0&&surface==='CHAT'&&model==='GPT-5.6 Sol'&&reasoning==='High';
  const key='ai_loop_bootstrap_'+cfg.deliveryId; const ledger={delivery_id:cfg.deliveryId,ready,project,empty:turns.length===0,surface,model,reasoning,ready_url:location.href,ready_at:new Date().toISOString(),send_ready:false,sent:false};
  if(ready) localStorage.setItem(key,JSON.stringify(ledger));
  const out={ready,project,empty:turns.length===0,surface,model,reasoning,url:location.href,ledger};
  const enc=s=>btoa(unescape(encodeURIComponent(s))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); const prefix='AI_LOOP_BOOTSTRAP_'+'PREFLIGHT_V1|';
  return prefix+'nonce='+cfg.nonce+'|payload='+enc(JSON.stringify(out));
 },cfg);
}'''


def _adaptive_presend_js(nonce, delivery_id, plan_filename, full_message):
    cfg={'nonce':str(nonce),'deliveryId':str(delivery_id),'planFilename':str(plan_filename),'fullMessage':str(full_message)}
    cfgj=json.dumps(cfg,separators=(',',':'))
    return r'''async page => {
 const cfg='''+cfgj+r''';
 return await page.evaluate(cfg=>{
  const norm=s=>String(s||'').replace(/\s+/g,' ').trim(); const vis=el=>{try{const r=el.getBoundingClientRect(),st=getComputedStyle(el);return r.width>0&&r.height>0&&st.display!=='none'&&st.visibility!=='hidden';}catch(e){return false;}};
  const turns=[...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"],article[data-testid^="conversation-turn"]')].filter(vis);
  const comps=[...document.querySelectorAll('textarea,[contenteditable="true"]')].filter(vis); const composer=norm(comps.map(e=>e.value||e.innerText||e.textContent||'').join(' ')); const body=norm(document.body.innerText||'');
  const key='ai_loop_bootstrap_'+cfg.deliveryId; let ledger={}; try{ledger=JSON.parse(localStorage.getItem(key)||'{}')||{};}catch(e){}
  const markerOk=composer.includes(cfg.deliveryId); const msgOk=composer.includes(norm(cfg.fullMessage).slice(0,80)); const fileOk=body.includes(cfg.planFilename); const sendReady=!!ledger.ready&&turns.length===0&&markerOk&&msgOk&&fileOk;
  if(sendReady){ledger.send_ready=true;ledger.send_ready_at=new Date().toISOString();ledger.plan_filename=cfg.planFilename;localStorage.setItem(key,JSON.stringify(ledger));}
  const out={send_ready:sendReady,empty:turns.length===0,marker_ok:markerOk,message_ok:msgOk,file_ok:fileOk,composer_text:composer.slice(0,700),url:location.href,ledger};
  const enc=s=>btoa(unescape(encodeURIComponent(s))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); const prefix='AI_LOOP_BOOTSTRAP_'+'PRESEND_V1|';
  return prefix+'nonce='+cfg.nonce+'|payload='+enc(JSON.stringify(out));
 },cfg);
}'''


def _adaptive_send_transaction_js(nonce, project_url, delivery_id, plan_filename, full_message):
    """Atomic browser transaction: re-check presend state, click Send once, then prove the user turn."""
    cfg={
      'nonce':str(nonce),'projectId':_adaptive_project_id(project_url),'deliveryId':str(delivery_id),
      'planFilename':str(plan_filename),'fullMessage':str(full_message),
    }
    cfgj=json.dumps(cfg,separators=(',',':'))
    return r'''async page => {
 const cfg='''+cfgj+r''';
 const inspect = async () => await page.evaluate(cfg=>{
  const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
  const vis=el=>{try{const r=el.getBoundingClientRect(),st=getComputedStyle(el);return r.width>0&&r.height>0&&st.display!=='none'&&st.visibility!=='hidden';}catch(e){return false;}};
  const turns=[...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"],article[data-testid^="conversation-turn"]')].filter(vis);
  const users=[...document.querySelectorAll('[data-message-author-role="user"]')].filter(vis).map(e=>norm(e.innerText||e.textContent)).filter(Boolean);
  const comps=[...document.querySelectorAll('textarea,[contenteditable="true"]')].filter(vis);
  const composer=norm(comps.map(e=>e.value||e.innerText||e.textContent||'').join(' '));
  const body=norm(document.body.innerText||'');
  const key='ai_loop_bootstrap_'+cfg.deliveryId; let ledger={}; try{ledger=JSON.parse(localStorage.getItem(key)||'{}')||{};}catch(e){}
  const marker='[AI_LOOP_DELIVERY id='+cfg.deliveryId+']';
  const deliveryPresent=users.some(t=>t.includes(marker)||t.includes(cfg.deliveryId));
  const messagePresent=users.some(t=>t.includes(norm(cfg.fullMessage).slice(0,80)));
  const markerOk=composer.includes(cfg.deliveryId);
  const msgOk=composer.includes(norm(cfg.fullMessage).slice(0,80));
  const fileOk=body.includes(cfg.planFilename);
  const project=!!cfg.projectId && location.href.includes(cfg.projectId);
  return {url:location.href,project,turnCount:turns.length,userTexts:users.slice(-8),composer,markerOk,msgOk,fileOk,deliveryPresent,messagePresent,ledger,key};
 },cfg);
 let before=await inspect();
 if(before.deliveryPresent && before.project && /\/c\//.test(before.url)){
   const led=before.ledger||{}; led.sent=true; led.send_status='ALREADY_SENT'; led.sent_url=before.url; led.sent_at=new Date().toISOString();
   await page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:before.key,v:led});
   const out={status:'ALREADY_SENT',sent:false,clicked:false,url:before.url,project:true,delivery_present:true,message_present:before.messagePresent,ledger:led,error:''};
   const enc=s=>btoa(unescape(encodeURIComponent(s))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); const prefix='AI_LOOP_BOOTSTRAP_'+'SENDTX_V1|';
   return prefix+'nonce='+cfg.nonce+'|payload='+enc(JSON.stringify(out));
 }
 const ledger=before.ledger||{};
 const sendReady=!!ledger.ready&&!!ledger.send_ready&&before.project&&before.turnCount===0&&before.markerOk&&before.msgOk&&before.fileOk;
 if(!sendReady){
   const out={status:'ERROR',sent:false,clicked:false,url:before.url,project:before.project,delivery_present:false,message_present:false,ledger,error:'PRESEND_NOT_READY',before};
   const enc=s=>btoa(unescape(encodeURIComponent(s))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); const prefix='AI_LOOP_BOOTSTRAP_'+'SENDTX_V1|';
   return prefix+'nonce='+cfg.nonce+'|payload='+enc(JSON.stringify(out));
 }
 const candidates=[
   page.locator('[data-testid="send-button"]:visible'),
   page.locator('button[aria-label*="Send" i]:visible'),
   page.getByRole('button',{name:/send|submit/i})
 ];
 let btn=null;
 for(const loc of candidates){ try{ if(await loc.count()){btn=loc.first();break;} }catch(e){} }
 if(!btn){
   const out={status:'ERROR',sent:false,clicked:false,url:before.url,project:before.project,delivery_present:false,message_present:false,ledger,error:'SEND_BUTTON_NOT_FOUND'};
   const enc=s=>btoa(unescape(encodeURIComponent(s))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); const prefix='AI_LOOP_BOOTSTRAP_'+'SENDTX_V1|';
   return prefix+'nonce='+cfg.nonce+'|payload='+enc(JSON.stringify(out));
 }
 const armed={...ledger,send_transaction_armed:true,send_transaction_armed_at:new Date().toISOString()};
 await page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:before.key,v:armed});
 await btn.click();
 const deadline=Date.now()+30000; let after=before;
 while(Date.now()<deadline){ await page.waitForTimeout(500); after=await inspect(); if(after.deliveryPresent&&after.project&&/\/c\//.test(after.url)) break; }
 const ok=after.deliveryPresent&&after.project&&/\/c\//.test(after.url);
 const led={...(after.ledger||armed),sent:ok,send_status:ok?'SENT':'AMBIGUOUS',sent_url:after.url,sent_at:new Date().toISOString()};
 await page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:after.key,v:led});
 const out={status:ok?'SENT':'AMBIGUOUS',sent:ok,clicked:true,url:after.url,project:after.project,delivery_present:after.deliveryPresent,message_present:after.messagePresent,ledger:led,error:ok?'':'SEND_CLICKED_BUT_DELIVERY_NOT_PROVEN'};
 const enc=s=>btoa(unescape(encodeURIComponent(s))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); const prefix='AI_LOOP_BOOTSTRAP_'+'SENDTX_V1|';
 return prefix+'nonce='+cfg.nonce+'|payload='+enc(JSON.stringify(out));
}'''


def _adaptive_possible_send_in_transcript(transcript, delivery_id=''):
    """Conservative ambiguity detector: any send click/transaction after composer mutation forbids blind retry."""
    txt=_strip_ansi(str(transcript or ''))
    low=txt.lower()
    send_click=bool(re.search(r'playwright_browser_click[^\n]{0,500}(send prompt|send-button|submit|aria-label.{0,80}send)',low,re.S))
    send_tx=bool(re.search(r'playwright_browser_run_code[^\n]{0,6000}(sendtx_v1|send_transaction_armed|data-testid.{0,80}send-button|btn\.click\(\))',low,re.S))
    marker=(str(delivery_id) in txt) if delivery_id else False
    composer_mutation=('playwright_browser_type' in low or 'playwright_browser_fill' in low) and marker
    return bool(send_click or send_tx or composer_mutation)


def adaptive_recovery_prompt(project_url, delivery_id, plan_filename, implement_text, nonce):
    marker=f'[AI_LOOP_DELIVERY id={delivery_id}]'
    final=_adaptive_obs_js(nonce,project_url,delivery_id,plan_filename,implement_text,mode='RECOVERY_READONLY')
    return f'''ROLE: ADAPTIVE_CHATGPT_DELIVERY_RECOVERY_V3_2.
Use Playwright browser tools only. READ-ONLY RECOVERY. Never type, attach, create a new chat, or click Send/Submit.
PROJECT ROOT: {project_url}
DELIVERY MARKER: {marker}

Goal: locate an already-existing conversation inside this project containing the exact marker above after a prior ambiguous browser send.
1. Navigate to the project root if needed.
2. Inspect the currently shown conversation first.
3. If the marker is not present, inspect project-local recent chat links from the live DOM and open at most 12 candidate chats, newest/relevant first. Do not leave this project.
4. If the marker is found in a USER turn, leave that conversation open.
5. Whether found or not, your LAST browser action must be the exact observer below. Do not emit your own JSON/proof markers.
```javascript
{final}
```
Your prose is ignored.'''


def _recover_delivery_via_browser(project_url, delivery_id, plan_filename, implement_text, purpose='adaptive-delivery-recovery', attempts=2, candidate_urls=None, allow_negative=False):
    """Recover a previous delivery or, when requested, prove it did not persist.

    Positive authority is always an exact delivery marker in a project user turn.
    Negative authority requires a complete scan seeded from controller diagnostics + Chrome history,
    an intact history DB, and no browser ledger marking the delivery as sent.
    """
    last_error='RECOVERY_NOT_PROVEN'
    explicit=_merge_chat_candidates(candidate_urls or [])
    history=_chrome_history_project_chat_urls(project_url,limit=120)
    merged=_merge_chat_candidates(explicit,history.get('urls') or [],limit=160)
    direct={}
    try:
        direct=run_deterministic_bootstrap_observer(project_url,delivery_id,purpose,max_chats=max(20,len(merged)+8),timeout=210,candidate_urls=merged)
        if bool(direct.get('found')) and bool(direct.get('project')) and '/c/' in _norm_chat_url(direct.get('url') or ''):
            direct['recovery_resolution']='FOUND'
            direct['history_scan']=history
            direct['explicit_candidates']=explicit
            return direct, json.dumps(direct)
        if allow_negative and merged and _negative_delivery_reconciliation(direct,history,explicit):
            direct['recovery_resolution']='NOT_SENT_PROVEN'
            direct['not_sent_proven']=True
            direct['history_scan']=history
            direct['explicit_candidates']=explicit
            log(f"BOOTSTRAP_OBSERVER NEGATIVE_PROOF delivery_id={delivery_id} history_urls={len(history.get('urls') or [])} explicit_urls={len(explicit)} visited={len(direct.get('visited') or [])} ledger_sent={bool((direct.get('ledger') or {}).get('sent'))}")
            return direct, json.dumps(direct)
        last_error='DETERMINISTIC_RECOVERY_MARKER_NOT_FOUND'
    except Exception as e:
        last_error=str(e)

    # Secondary lane: model-guided read-only DOM navigation. It still cannot type/upload/send.
    for n in range(1,max(1,int(attempts))+1):
        nonce=hashlib.sha256(f'recover|{delivery_id}|{n}|{time.time_ns()}'.encode()).hexdigest()[:18]
        transcript=''
        try:
            transcript=oc_raw_turn(adaptive_recovery_prompt(project_url,delivery_id,plan_filename,implement_text,nonce),f'{purpose}-guided-{n}')
            obs=_parse_adaptive_payload_line(transcript,ADAPTIVE_OBS_PREFIX,nonce)
            url=str(obs.get('url') or '')
            if bool(obs.get('project')) and bool(obs.get('delivery_present')) and '/c/' in _norm_chat_url(url):
                obs['recovery_resolution']='FOUND_GUIDED'
                return obs, transcript
            last_error='GUIDED_RECOVERY_MARKER_NOT_FOUND'
        except Exception as e:
            last_error=str(e)
        if n<int(attempts): time.sleep(2)

    # Re-run deterministic negative proof after guided navigation because it may have exposed/visited a hidden chat.
    if allow_negative:
        try:
            history2=_chrome_history_project_chat_urls(project_url,limit=140)
            merged2=_merge_chat_candidates(explicit,history.get('urls') or [],history2.get('urls') or [],limit=180)
            direct2=run_deterministic_bootstrap_observer(project_url,delivery_id,purpose+'-final-negative',max_chats=max(24,len(merged2)+8),timeout=240,candidate_urls=merged2)
            if bool(direct2.get('found')) and bool(direct2.get('project')) and '/c/' in _norm_chat_url(direct2.get('url') or ''):
                direct2['recovery_resolution']='FOUND_FINAL'
                return direct2,json.dumps(direct2)
            if _negative_delivery_reconciliation(direct2,history2,explicit):
                direct2['recovery_resolution']='NOT_SENT_PROVEN'
                direct2['not_sent_proven']=True
                direct2['history_scan']=history2
                direct2['explicit_candidates']=explicit
                log(f"BOOTSTRAP_OBSERVER NEGATIVE_PROOF_FINAL delivery_id={delivery_id} history_urls={len(history2.get('urls') or [])} explicit_urls={len(explicit)} visited={len(direct2.get('visited') or [])}")
                return direct2,json.dumps(direct2)
        except Exception as e:
            last_error=str(e)
    raise RuntimeError(last_error)

def _diag_possible_send(diag_path, delivery_id=''):
    try:
        obj=json.loads(Path(diag_path).read_text(encoding='utf-8'))
        txt=str(obj.get('transcript_tail') or '')
        return _adaptive_possible_send_in_transcript(txt,delivery_id)
    except Exception:
        return False


def _prior_ambiguous_bootstraps(plan_filename, current_run_id='', limit=12):
    out=[]
    try:
        files=sorted(STATE_ROOT.glob('*.v3.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    except Exception:
        files=[]
    for sp in files[:80]:
        try:
            obj=json.loads(sp.read_text(encoding='utf-8'))
        except Exception:
            continue
        if str(obj.get('run_id') or '')==str(current_run_id or ''): continue
        ab=obj.get('adaptive_bootstrap') if isinstance(obj.get('adaptive_bootstrap'),dict) else {}
        if str(ab.get('plan_filename') or '')!=str(plan_filename): continue
        did=str(ab.get('delivery_id') or '')
        if not did: continue
        status=str(ab.get('status') or '')
        if status in {'AMBIGUITY_RESOLVED_NOT_SENT','AMBIGUITY_QUARANTINED','PLAN_SENT_VERIFIED','PLAN_SENT_VERIFIED_RECOVERED','FAILED_NO_SEND','RETRY_SAFE_NO_SEND'}:
            continue
        diags=[]
        if ab.get('diag'): diags.append(str(ab.get('diag')))
        for q in obj.get('adaptive_browser_diagnostics') or []:
            if q not in diags: diags.append(str(q))
        possible=(status in {'AMBIGUOUS_SEND','SEND_ATTEMPTED','AMBIGUOUS_SEND_UNRESOLVED','AMBIGUOUS_PREVIOUS_DELIVERY'}) or any(_diag_possible_send(q,did) for q in diags[-6:])
        if possible:
            out.append({'run_id':str(obj.get('run_id') or ''),'delivery_id':did,'status':status,'diag':diags[-1] if diags else '', 'diag_paths':diags[-8:], 'state_path':str(sp), 'at':str(ab.get('at') or obj.get('updated_at') or '')})
        if len(out)>=int(limit): break
    return out

def adaptive_policy_prompt(target_url, nonce):
    js=_adaptive_obs_js(nonce,target_url,mode='POLICY')
    return f'''ROLE: ADAPTIVE_CHATGPT_UI_NAVIGATOR_V3.
Use Playwright browser tools only. Do not send a message, attach a file, or create Work/Codex tasks.
Target URL: {target_url}
Goal: leave this exact conversation/project on normal Chat, GPT-5.6 Sol, reasoning High.

Adaptive procedure:
- Inspect the live accessibility tree, semantic DOM, aria labels/roles, and when useful compact outerHTML. Do not use coordinates or brittle nth-child selectors.
- If Work or Codex is active, switch to normal Chat without sending anything and without changing conversation identity.
- Discover current model/reasoning controls from live DOM. Select exactly GPT-5.6 Sol and High. Never fall back to Light/Instant/Medium/Luna/Terra/Work/Codex.
- If the closed header hides the model, open the picker and leave it open for the final verifier if needed so checked/selected DOM state is observable.
- Do not emit JSON or any AI_LOOP event. Your prose is ignored.
- Your LAST browser action must be playwright_browser_run_code using the exact verifier below.

FINAL DETERMINISTIC VERIFIER JS:
```javascript
{js}
```
'''


def adaptive_bootstrap_prompt(project_url, plan_path, plan_filename, implement_text, run_id, delivery_id, nonce_pre, nonce_send, nonce_tx):
    marker=f'[AI_LOOP_DELIVERY id={delivery_id}]'
    full_message=marker+'\n'+str(implement_text)
    pre=_adaptive_preflight_js(nonce_pre,project_url,delivery_id)
    presend=_adaptive_presend_js(nonce_send,delivery_id,plan_filename,full_message)
    sendtx=_adaptive_send_transaction_js(nonce_tx,project_url,delivery_id,plan_filename,full_message)
    return f'''ROLE: ADAPTIVE_CHATGPT_PROJECT_BOOTSTRAP_V3_2.
Use Playwright browser tools only. Built-in read/bash/write/edit/task tools are forbidden.

OBJECTIVE
Create ONE brand-new normal Chat conversation inside this exact project, configure GPT-5.6 Sol + High, attach the exact plan, and deliver exactly one implementation message.
PROJECT ROOT: {project_url}
PLAN FILE: {plan_path}
PLAN FILENAME: {plan_filename}
DELIVERY ID: {delivery_id}
MESSAGE TO TYPE (including marker):
{full_message}

This is a goal-directed UI task. Analyze live accessibility tree/DOM/ARIA/HTML and adapt to the UI actually present. Never use remembered coordinates or brittle nth-child selectors. Your final prose is ignored.

STRICT SEND AUTHORITY
- NEVER click Send/Submit with playwright_browser_click, keyboard Enter, or any generic action.
- The ONLY operation allowed to submit the message is the exact SEND TRANSACTION run_code supplied below.
- If that transaction is not executed, nothing should be sent.
- If it clicks Send but cannot prove delivery, do not send again.

FRESH CHAT + POLICY
1. Navigate to the project root. It may display an old conversation. Never type/attach into a page with existing user/assistant turns.
2. Use the project-local Chat/New chat/compose entrypoint discovered from live DOM to obtain an EMPTY draft in this project. Work and Codex are forbidden.
3. Configure GPT-5.6 Sol and reasoning High using selected/checked controls. If needed inspect menuitemradio/option/aria-checked/data-state/outerHTML.
4. Execute this exact preflight run_code until ready=true. Do not attach/type before ready=true:
```javascript
{pre}
```

ATTACH + TYPE, BUT DO NOT SEND
5. Open the visible "Add files" / attachment control FIRST. Call playwright_browser_file_upload only after the related chooser/modal state exists. If upload says no related modal state, reopen the attachment control and retry; do not restart the entire bootstrap.
6. Attach exactly `{plan_path}` and type exactly the message above.
7. Execute this exact pre-send verifier. Repair attachment/composer until send_ready=true:
```javascript
{presend}
```

ATOMIC SEND + PROOF
8. Once send_ready=true, execute the following exact run_code. It re-verifies all conditions, is the ONLY code allowed to click Send, waits for the user turn + persistent /c/ URL, updates the idempotency ledger, and returns the controller proof:
```javascript
{sendtx}
```
9. After the SEND TRANSACTION call, STOP. Do not click Send or perform another delivery action. Your prose is ignored.
'''

def _adaptive_observation_to_event(obs):
    surface=str(obs.get('surface') or ''); model=str(obs.get('model') or ''); reasoning=str(obs.get('reasoning') or '')
    policy=(surface=='CHAT' and model=='GPT-5.6 Sol' and reasoning=='High')
    return _validate_event({'state':'NO_ACTIONS' if policy else 'ERROR','chat_url':str(obs.get('url') or ''),'sol_text':json.dumps(obs.get('diagnostics') or {},ensure_ascii=False)[:1600],'needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'' if policy else 'ADAPTIVE_POLICY_UNVERIFIED','delivery_status':'NONE','ui_surface':surface,'ui_model':model,'ui_reasoning':reasoning,'chat_policy_status':'PASS' if policy else 'FAIL'})


def _persist_browser_diag(st, purpose, obs=None, transcript=''):
    if not isinstance(st,dict) or not st.get('run_id'):
        return ''
    root=RUNS_ROOT/str(st['run_id'])/'browser'/'adaptive'; root.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'); safe=re.sub(r'[^A-Za-z0-9_.-]+','-',str(purpose))[:80]
    path=root/f'{stamp}-{safe}.json'
    payload={'at':now(),'purpose':purpose,'observation':obs or {},'transcript_tail':_strip_ansi(str(transcript or ''))[-12000:]}
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    st.setdefault('adaptive_browser_diagnostics',[]).append(str(path))
    if len(st['adaptive_browser_diagnostics'])>50:
        st['adaptive_browser_diagnostics']=st['adaptive_browser_diagnostics'][-50:]
    return str(path)

def ensure_chat_policy(st, state_path, target_url, purpose='pre-send'):
    """v4: direct Node/Playwright policy guard. No LLM or transcript proof is authoritative."""
    run_id=str((st or {}).get('run_id') or 'policy') if isinstance(st,dict) else 'policy'
    last_error=''
    for attempt in range(1,3):
        try:
            obs=run_deterministic_chat_policy(target_url,run_id,purpose,timeout=120)
            url=str(obs.get('url') or target_url)
            ev=_validate_event({'state':'NO_ACTIONS','chat_url':url,'sol_text':'deterministic policy verified','needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':'NONE','ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'})
            if isinstance(st,dict): st['chat_url']=url
            _record_chat_policy(st,ev,purpose)
            if state_path is not None and isinstance(st,dict): save_state(Path(state_path),st)
            log('CHAT_SURFACE PASS surface=chat work=false codex=false purpose='+str(purpose)+' verifier=direct-playwright-worker-v4')
            log('MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high purpose='+str(purpose)+' verifier=direct-playwright-worker-v4')
            return ev
        except Exception as e:
            last_error=str(e)
            log(f'DETERMINISTIC_CHAT_POLICY RETRY attempt={attempt} purpose={purpose} error={last_error[:700]}')
            if attempt<2: time.sleep(1)
    raise RuntimeError('CHATGPT_CHAT_POLICY_GUARD_FAILED:'+last_error[:900])


def browser_inspect_prompt(chat_url):
    return f'''ROLE: OPERATOR_TRANSPORT_ONLY.
Use Playwright browser tools only. Built-in read/bash/write/edit/task tools are forbidden and unavailable.
Open/stay in exactly this ChatGPT conversation:\n{chat_url}\n
CRITICAL READ FENCE — generation always has precedence over old completed messages:
1. First inspect the LIVE conversation state, not only the last completed assistant article.
2. If a visible rate-limit dialog/banner says "Too many requests", "making requests too quickly", "temporarily limited", or equivalent, you may click only its harmless acknowledgement button (for example "Got it"), then return state RATE_LIMIT and delivery_status NONE. Do not send any chat message.
3. If ANY current-response indicator shows ChatGPT is still working — visible Stop/Stop answering/Stop generating control, Thinking/Working/Researching indicator, active tool activity belonging to the current response, streaming response, or equivalent — return state GENERATING and delivery_status NONE immediately. Do not classify an older completed answer as the latest answer.
4. If it appears idle, capture the complete latest assistant response identity, wait {RESPONSE_SETTLE_SECONDS} seconds with Playwright, and inspect again. If the response identity/content changed, a generation indicator appeared, or a newer assistant response began, return GENERATING. Only a response unchanged across both observations is SETTLED.
5. Only after SETTLED may you classify its content below.

Inspect the COMPLETE latest SETTLED GPT-5.6 Sol response in the browser DOM, not a truncated snapshot.
Extract ONLY operator actions that Sol explicitly requested. Do not invent commands, fixes, diagnoses or architecture decisions.

ACTION METADATA EXTRACTION IS MANDATORY:
- For every action, identify the exact fenced command code block in the latest assistant message.
- Read that DOM code element's literal textContent using Playwright DOM/evaluate. NEVER copy it from snapshot prose or rendered Markdown.
- In browser JavaScript, UTF-8 encode the exact textContent and compute SHA-256 over those exact bytes.
- Return payload_transport="dom_file", command_sha256, and command_len (UTF-8 byte length). DO NOT return the command or Base64 payload in AI_LOOP_EVENT.
- The controller will use a separate Playwright-only turn to save this exact DOM textContent directly as a browser download into a fixed local handoff file; payload bytes never pass through model text.
- This preserves __file__, __name__, URLs, quotes, heredocs, backslashes and newlines byte-for-byte without Base64/chunks/JSON payload transport.
- If the command is not in an unambiguous fenced code block, DOM evaluate cannot read it exactly, or SHA/length cannot be proven, return ERROR with error=INCOMPLETE_OR_UNVERIFIED_ACTION_METADATA and actions=[]. Never reconstruct or repair it.

Target local means the local repo/operator machine. Target vps means a command Sol explicitly requested for the production VPS; do not wrap it in ssh here. If Sol labels a block as VPS, remote, production server, production runtime, or asks to inspect paths under /opt/bot_trad or /var/lib/bot-trading-gru-p2, classify it as target=vps even when the shell command itself contains no ssh. If the exact command itself invokes /opt/ai-loop/bin/vps-ssh, classify it as target=local because the wrapper is executed locally. Never rewrite payload bytes.
CRITICAL ACTION PRIORITY: if the settled Sol response contains one or more operator actions, return ACTIONS even if the same response also says continue/proceed/wait. ACTIONS always has higher priority than CONTINUE.
If Sol explicitly declares final GO, return GO.
If Sol produced a complete new implementation PLAN markdown, return PLAN_READY with exact filename/content.
If Sol finished, requested no concrete operator command, and explicitly says it has a next implementation/validation/review/commit step that it itself will perform without user/operator input, return CONTINUE. CONTINUE only applies to a SETTLED answer. Do NOT use CONTINUE while any current response is generating, or when Sol is waiting for a user decision, clarification, credential, approval, missing file, or exact operator evidence.
If Sol finished but requested no concrete operator command, did not declare GO/plan, and did not explicitly indicate self-continuation, return NO_ACTIONS.
Set needs_operator_capabilities=true only if Sol is blocked because it needs terminal/operator capability but did not yet provide exact commands.
IMPORTANT: the external operator is controller-side and is NOT supposed to appear as a native ChatGPT tool. If Sol says EXTERNAL_OPERATOR_NOT_EXPOSED, operator terminal missing, repo/VPS wrapper missing from its own assistant runtime, or asks to expose the operator connector, return NO_ACTIONS with needs_operator_capabilities=true.
Return the current /c/... URL in chat_url.
Return concise sol_text sufficient to identify the latest settled turn (max 16000 chars).
For this inspection-only operation always set delivery_status="NONE".'''

def browser_recover_action_prompt(chat_url, action_ids):
    ids=', '.join(str(x) for x in (action_ids or []) if x) or 'unknown'
    return f'''ROLE: SECURE_ACTION_METADATA_RECOVERY.
Use Playwright browser tools only. Do NOT send any ChatGPT message and do NOT execute any command.
Open/stay in exactly this conversation:
{chat_url}

A controller restart is recovering pending action ids: {ids}.
Inspect the newest settled assistant response first. If it still says one of these actions is required/pending, you may search backward in this same conversation for the MOST RECENT assistant message that defines that exact action id with one unambiguous fenced command block. If a newer assistant response explicitly cancels or supersedes an action, do not recover it.

For each still-required action: read the literal fenced code DOM textContent, UTF-8 encode it in browser JavaScript, compute SHA-256 and UTF-8 byte length. Return ACTIONS metadata only: id, target, payload_transport="dom_file", command_sha256, command_len, timeout_seconds. Never return command text, Base64, or chunks.
ACTIONS outranks CONTINUE. If no recoverable action definition exists, return NO_ACTIONS. Do not ask for a PLAN; this is read-only transport recovery.'''


def browser_send_prompt(chat_url, message, attachment='', delivery_id=''):
    attach = f'''Attach this existing local file through the browser before sending:\n{attachment}\nDo not read it with any OpenCode file tool.''' if attachment else 'No attachment is required.'
    marker = f'[AI_LOOP_DELIVERY id={delivery_id}]' if delivery_id else ''
    if marker and marker not in message:
        message = marker + '\n' + message
    return f'''ROLE: OPERATOR_TRANSPORT_ONLY.
Use Playwright browser tools only. Built-in read/bash/write/edit/task tools are forbidden and unavailable.
Open/stay in exactly this ChatGPT conversation:\n{chat_url}\n
AUTHORITATIVE CHAT POLICY — RECHECK IMMEDIATELY BEFORE THIS SEND:
- Use normal Chat only. Work and Codex are forbidden for this delivery.
- Required web model: GPT-5.6 Sol.
- Required reasoning: High.
- If Work is active (including a composer such as "Work on anything"), switch to normal Chat without replacing the current conversation.
- If the selected model/reasoning is Light, Instant, Medium, Luna, Terra, Work/Astra, Codex/Astra, unknown, or unreadable, select GPT-5.6 Sol + High and verify the live selected controls again.
- If normal Chat + GPT-5.6 Sol + High cannot be proven, DO NOT TYPE, ATTACH OR SEND. Return ERROR with chat_policy_status=FAIL.
- On successful live verification set ui_surface=CHAT, ui_model=GPT-5.6 Sol, ui_reasoning=High, chat_policy_status=PASS in the event.

ABSOLUTE PRE-SEND FENCE. NEVER submit a message while ChatGPT is thinking or while a prior delivery is unanswered.
Before typing, attaching, clicking Send, or pressing Enter:
1. Inspect the LIVE conversation state. A visible Stop/Stop answering/Stop generating control, Thinking/Working/Researching indicator, active current-response tool activity, streaming response, or equivalent means ChatGPT IS BUSY. In that case DO NOT TYPE OR SEND ANYTHING. Return state GENERATING with delivery_status="NOT_SENT_GENERATING".
2. If a rate-limit dialog/banner says "Too many requests", "making requests too quickly", "temporarily limited", or equivalent, you may click only its harmless acknowledgement button. DO NOT send a chat message. Return state RATE_LIMIT with delivery_status="NOT_SENT_RATE_LIMIT".
3. Inspect conversation ordering. If the latest visible user message has no completed assistant response after it, treat ChatGPT as busy even if a Stop button is momentarily absent. Return GENERATING / NOT_SENT_GENERATING.
4. If it appears idle, capture the complete latest assistant response identity, wait {RESPONSE_SETTLE_SECONDS} seconds, and inspect again. If anything changed or a generation indicator appeared, return GENERATING / NOT_SENT_GENERATING.
5. If the exact marker {marker!r} is already visible in a user message, DO NOT send it again. Return state NO_ACTIONS with delivery_status="ALREADY_SENT" immediately. Do not classify the assistant response in this delivery turn.
6. Immediately before the final Send/Enter action, re-check for a Stop/Thinking/Working/streaming indicator. If busy, do not submit.

{attach}
Only after ALL fences above pass, send the following message ONCE, exactly as supplied between markers:
---BEGIN MESSAGE---
{message}
---END MESSAGE---
After submit, verify in the live DOM that the exact marker {marker!r} is visible in the newly created user message. If it is visible, return state NO_ACTIONS with delivery_status="SENT" immediately. Do NOT wait for, summarize, or classify the new assistant response in this same OpenCode turn. Response inspection is a separate controller step.
If the submit action appeared to occur but the exact marker cannot be proven visible, return ERROR with delivery_status="NONE". Never submit it a second time in the same turn.
Do not execute any operator command yourself. Return current /c/... URL.'''

def _norm_chat_url(url):
    # Normalize a ChatGPT URL for freshness comparisons without query/hash noise.
    u=str(url or '').strip()
    if not u:
        return ''
    u=u.split('#',1)[0].split('?',1)[0].rstrip('/')
    return u


def _project_chat_prefix(project_url):
    return _norm_chat_url(project_url) + '/c/'


def fresh_project_location_pass(project_url, forbidden_chat_url, url):
    project=_norm_chat_url(project_url)
    final=_norm_chat_url(url)
    if not final:
        return False
    if final != project and not final.startswith(project + '/c/'):
        return False
    forbidden=_norm_chat_url(forbidden_chat_url)
    if forbidden and '/c/' in forbidden and final == forbidden:
        return False
    return True


def fresh_project_chat_pass(project_url, forbidden_chat_url, ev):
    """Creation proof is intentionally independent from model-policy proof in v2.40."""
    if not isinstance(ev,dict):
        return False
    if str(ev.get('state') or '')!='NO_ACTIONS' or str(ev.get('delivery_status') or '')!='NONE':
        return False
    proof=re.sub(r'\s+',' ',str(ev.get('sol_text') or '')).strip()
    if 'FRESH_PROJECT_CHAT=PASS' not in proof or 'empty=1' not in proof or 'project=1' not in proof:
        return False
    return fresh_project_location_pass(project_url,forbidden_chat_url,ev.get('chat_url'))

def fresh_project_delivery_pass(project_url, forbidden_chat_url, ev):
    """Delivery identity is independent from model-policy proof; policy is guarded before/after send."""
    if not isinstance(ev,dict):
        return False
    if str(ev.get('delivery_status') or '') not in {'SENT','ALREADY_SENT'}:
        return False
    final=_norm_chat_url(ev.get('chat_url'))
    prefix=_project_chat_prefix(project_url)
    if not final.startswith(prefix) or len(final) <= len(prefix):
        return False
    forbidden=_norm_chat_url(forbidden_chat_url)
    if forbidden and '/c/' in forbidden and final == forbidden:
        return False
    return True

def browser_create_fresh_project_chat_prompt(project_url, forbidden_chat_url='', attempt=1, previous_error=''):
    forbidden=_norm_chat_url(forbidden_chat_url)
    return f"""ROLE: OPERATOR_TRANSPORT_ONLY_FRESH_PROJECT_CHAT.
CREATE_ATTEMPT={int(attempt)}
PREVIOUS_ERROR={previous_error or '(none)'}
Use Playwright browser tools only. Built-in read/bash/write/edit/task tools are forbidden and unavailable.

PROJECT ROOT:
{project_url}

HARD FRESH-CHAT FENCE - DO NOT ATTACH, TYPE OR SEND ANY MESSAGE IN THIS TURN.
This turn has exactly one responsibility: create and prove a brand-new EMPTY Chat draft inside this exact ChatGPT project. MODEL/REASONING POLICY IS NOT PART OF THIS TURN; the deterministic controller validates GPT-5.6 Sol + High in a separate no-send turn immediately afterward.

The historical /c/ URL observed before creation is:
{forbidden or '(none recorded)'}
It is FORBIDDEN for plan delivery.

Procedure:
1. Inspect current URL. If needed navigate to the exact PROJECT ROOT. Any /c/ shown immediately after opening the project is historical unless independently proven fresh; never type/attach/send there.
2. Inside this exact project, activate the project-scoped normal `Chat` entrypoint or project-local `New chat`/compose entrypoint. Never choose Work or Codex. Never select a conversation-history item.
3. Prefer semantic role/name/aria-label/href inspection. Do not use coordinates or brittle nth-child selectors.
4. After the new-draft action, use live DOM/run_code to prove BOTH:
   - project=1: the active draft belongs to PROJECT ROOT above;
   - empty=1: ZERO existing user/assistant conversation turns are present.
5. URL may remain the project root until first send, or become a new project /c/. If it is /c/, it must differ from the historical URL and from any initial historical /c/.
6. Do NOT open the model/reasoning picker here. Do NOT fail creation merely because the model label is not visible. The next controller phase owns Chat/Sol/High proof.
7. Do NOT attach the plan. Do NOT type. Do NOT send.

On PASS return creation proof only. Valid creation errors are NEW_PROJECT_CHAT_NOT_CREATED, NEW_CHAT_NOT_EMPTY, NEW_CHAT_WRONG_PROJECT, or NEW_CHAT_EQUALS_HISTORICAL. `NEW_CHAT_POLICY_NOT_PROVEN` is obsolete and MUST NOT be used in this phase."""

def browser_send_fresh_plan_prompt(project_url, fresh_draft_url, forbidden_chat_url, plan_path, implement_text):
    forbidden=_norm_chat_url(forbidden_chat_url)
    return f"""ROLE: OPERATOR_TRANSPORT_ONLY_FRESH_PLAN_SEND.
Use Playwright browser tools only. Built-in read/bash/write/edit/task tools are forbidden and unavailable.

The deterministic controller has already completed TWO independent no-send gates: (a) fresh empty project draft and (b) Chat + GPT-5.6 Sol + High policy in that exact draft.
PROJECT={project_url}
FRESH_DRAFT={fresh_draft_url}
FORBIDDEN_HISTORICAL_CHAT={forbidden or '(none recorded)'}

CRITICAL: do not navigate/reload, do not open project history, do not open any other /c/, and do not change model/reasoning. Stay in the currently visible fresh draft.

Immediately before typing/attachment, prove with live DOM:
1. Current project context is the exact project above.
2. There are ZERO existing user/assistant conversation turns. If not empty, send nothing and return ERROR FRESH_DRAFT_NO_LONGER_EMPTY.
3. Current URL is not the forbidden historical /c/. It may equal project root or a distinct new project /c/.
4. Active product surface is normal Chat, not Work/Codex. Do not reopen/change the model picker in this send turn; the controller just proved Sol High separately.
5. If a rate-limit/banner or active generation exists, send nothing and return RATE_LIMIT/ERROR as appropriate.

Only after all checks pass:
- Attach exactly: {plan_path}
- Send exactly this implementation message ONCE:
---BEGIN MESSAGE---
{implement_text}
---END MESSAGE---

After submit prove:
A. the exact implementation message is visible as the FIRST user conversation turn;
B. resulting URL begins with {_project_chat_prefix(project_url)};
C. resulting /c/ URL is not the forbidden historical URL;
D. active surface is still normal Chat (not Work/Codex).
Do NOT wait for or classify the assistant response. Never retry a submit whose outcome is uncertain."""

def browser_start_plan_prompt(project_url, plan_path, implement_text):
    # Compatibility wrapper; v2.34 start_new_chat uses the split two-phase flow.
    return browser_create_fresh_project_chat_prompt(project_url,'') + '\n\nNEXT TURN ONLY (controller owned):\n' + browser_send_fresh_plan_prompt(project_url,project_url,'',plan_path,implement_text)

def event_fingerprint(ev):
    basis=(ev.get('chat_url','')+'\n'+ev.get('sol_text','')+'\n'+json.dumps(ev.get('actions',[]),sort_keys=True)+'\n'+str(ev.get('semantic_event',''))+'\n'+str(ev.get('semantic_source_message_id','')))
    return hashlib.sha256(basis.encode()).hexdigest()[:20]

def action_key(action):
    aid=str(action.get('id') or '')
    target=str(action.get('target') or '')
    command=str(action.get('command') or '')
    digest=hashlib.sha256((target+'\0'+command).encode()).hexdigest()[:20]
    return f'{aid}:{digest}'

def github_head(repo, branch):
    last=''
    for attempt in range(1,4):
        cp=subprocess.run(['gh','api',f'repos/{repo}/commits/{branch}','--jq','.sha'],capture_output=True,text=True,timeout=60)
        if cp.returncode==0 and cp.stdout.strip(): return cp.stdout.strip()
        last=(cp.stderr or cp.stdout)[-1000:]
        if attempt<3: time.sleep(2**attempt)
    raise RuntimeError('gh head failed after retries: '+last)

def ci_status(sha):
    cp=subprocess.run([str(CI_STATUS),sha],capture_output=True,text=True,timeout=120)
    if cp.returncode and not cp.stdout.strip(): raise RuntimeError('ci-status failed: '+cp.stderr[-1000:])
    try: return json.loads(cp.stdout)
    except Exception: return {'sha':sha,'status':'UNKNOWN','raw':cp.stdout[-2000:],'stderr':cp.stderr[-1000:]}

def _tmp_log_mutation_reason(command):
    """Return a reason only for mutations *to* /tmp/log; read-only copies/snapshots out are allowed."""
    # Analyze per shell line/segment conservatively. This is policy defense-in-depth,
    # not a full shell parser.
    for raw in command.splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '/tmp/log' not in line:
            continue
        low=line.lower()
        # Metadata/content mutations where any /tmp/log operand is unsafe.
        if re.search(r'\b(chmod|chown|setfacl|rm|mv|touch|truncate)\b', low):
            return '/tmp/log mutation forbidden by production invariant'
        # mkdir/install targeting /tmp/log are unsafe.
        if re.search(r'\b(mkdir|install)\b[^\n]*?/tmp/log(?:/|\b)', low):
            return '/tmp/log mutation forbidden by production invariant'
        # Output redirection / tee into /tmp/log is unsafe; input redirection is fine.
        if re.search(r'(?<!<)(?:>|>>|2>|2>>)\s*["\']?/tmp/log(?:/|\b)', line):
            return '/tmp/log mutation forbidden by production invariant'
        if re.search(r'\btee\b[^\n]*?(?:\s|^)["\']?/tmp/log(?:/|\b)', low):
            return '/tmp/log mutation forbidden by production invariant'
        # cp is allowed when /tmp/log is only a source, but never when destination is there.
        if re.search(r'\bcp\b', low):
            try:
                toks=shlex.split(line, posix=True)
            except Exception:
                toks=line.split()
            # Strip simple shell suffixes and options; destination is final non-control token.
            controls={'||','&&',';','|'}
            if 'cp' in toks:
                idx=toks.index('cp')
                args=[]
                for t in toks[idx+1:]:
                    if t in controls: break
                    if not t.startswith('-'): args.append(t)
                if len(args)>=2 and args[-1].startswith('/tmp/log'):
                    return '/tmp/log mutation forbidden by production invariant'
        # Catch common inline Python writes to /tmp/log while permitting stat/read/hash/open(...,'r').
        if re.search(r'(?:write_text|write_bytes|unlink|rename|replace|mkdir)\s*\(', low) and '/tmp/log' in low:
            return '/tmp/log mutation forbidden by production invariant'
        if re.search(r'open\s*\(\s*["\']/tmp/log[^\n]*?["\']\s*,\s*["\'][wax+]', low):
            return '/tmp/log mutation forbidden by production invariant'
    return ''

def _safe_tmp_rm_rf_cleanup(command):
    # Narrow exception for cleanup of a temporary validation clone.
    # Only exactly: TMP="$(mktemp -d /tmp/<safe>.XXXXXX)" + rm -rf "$TMP" + trap cleanup EXIT.
    matches=list(re.finditer(r'\brm\s+-rf\b',command,re.IGNORECASE))
    if len(matches) != 1:
        return False
    rm_lines=[line.strip() for line in command.splitlines() if re.search(r'\brm\s+-rf\b',line,re.IGNORECASE)]
    if len(rm_lines) != 1 or not re.fullmatch(r'rm\s+-rf\s+"\$TMP"',rm_lines[0]):
        return False
    if not re.search(r'(?m)^\s*TMP="\$\(mktemp\s+-d\s+/tmp/[A-Za-z0-9._-]+\.XXXXXX\)"\s*$',command):
        return False
    if not re.search(r'(?m)^\s*trap\s+cleanup\s+EXIT\s*$',command):
        return False
    return True


def forbidden_reason(command, target):
    c=command.lower()
    hard=[r'\bgit\s+commit\b',r'\bgit\s+push\b',r'\bgit\s+reset\b',r'\bgit\s+clean\b',r'\bshutdown\b',r'\breboot\b']
    for p in hard:
        if re.search(p,c): return f'policy forbids {p}'
    if re.search(r'\brm\s+-rf\b',c) and not _safe_tmp_rm_rf_cleanup(command):
        return r'policy forbids \brm\s+-rf\b'
    if re.search(r'(^|[;&|()]|\bsudo\s+|\benv\s+)(?:\s*)(ssh|sshpass|scp|sftp)\b',c):
        return 'raw remote transport forbidden; target=vps must use controller-owned vps-ssh wrapper'
    reason=_tmp_log_mutation_reason(command)
    if reason: return reason
    return ''

def run_action(action, repo_dir):
    aid=action['id']; target=action['target']; cmd=action['command']; tout=int(action.get('timeout_seconds') or DEFAULT_ACTION_TIMEOUT)
    ok,transport_reason=verify_action_transport(action)
    start=now()
    if not ok:
        return {'id':aid,'target':target,'command':cmd,'started_at':start,'finished_at':now(),'exit_code':125,'stdout':'','stderr':'TRANSPORT_REJECTED: '+transport_reason,'timed_out':False}
    reason=forbidden_reason(cmd,target)
    if reason:
        return {'id':aid,'target':target,'command':cmd,'started_at':start,'finished_at':now(),'exit_code':126,'stdout':'','stderr':'POLICY_BLOCKED: '+reason,'timed_out':False}
    try:
        if target=='local':
            cp=subprocess.run(['bash','-lc',cmd],cwd=str(repo_dir),capture_output=True,text=True,timeout=tout)
        elif target=='github-readonly':
            low=cmd.lower()
            mutation_tokens=('gh pr merge','gh pr create','gh issue create','gh release create','gh repo edit','gh api --method post','gh api -x post','gh api --method put','gh api -x put','gh api --method patch','gh api -x patch','gh api --method delete','gh api -x delete','git push','git commit','git tag')
            if any(t in low for t in mutation_tokens):
                return {'id':aid,'target':target,'command':cmd,'started_at':start,'finished_at':now(),'exit_code':126,'stdout':'','stderr':'POLICY_BLOCKED: github-readonly mutation forbidden','timed_out':False}
            cp=subprocess.run(['bash','-lc',cmd],cwd=str(repo_dir),capture_output=True,text=True,timeout=tout)
        else:
            cp=subprocess.run([str(VPS_WRAPPER),cmd],capture_output=True,text=True,timeout=tout)
        return {'id':aid,'target':target,'command':cmd,'started_at':start,'finished_at':now(),'exit_code':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,'timed_out':False}
    except subprocess.TimeoutExpired as e:
        return {'id':aid,'target':target,'command':cmd,'started_at':start,'finished_at':now(),'exit_code':124,
                'stdout':(e.stdout or '') if isinstance(e.stdout,str) else ((e.stdout or b'').decode(errors='replace')),
                'stderr':'TIMEOUT\n'+((e.stderr or '') if isinstance(e.stderr,str) else ((e.stderr or b'').decode(errors='replace'))),'timed_out':True}

def render_results(results):
    parts=[]
    for r in results:
        parts.append('\n'.join([
          f"===== ACTION {r['id']} target={r['target']} =====",
          f"COMMAND:\n{r['command']}",
          f"EXIT_STATUS={r['exit_code']}",f"TIMED_OUT={str(r['timed_out']).lower()}",
          '--- STDOUT ---',r['stdout'],'--- STDERR ---',r['stderr'],f"===== END {r['id']} ====="
        ]))
    return '\n\n'.join(parts)

def save_state(path, state):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state,indent=2,sort_keys=True))
    os.replace(tmp,path)

def load_state(path):
    return json.loads(path.read_text())

def prompt_file(name, fallback=''):
    txt=read_text(PROMPTS/name).strip()
    return txt or fallback

def stage_text(run_id, filename, text):
    d=UPLOAD_ROOT/run_id
    d.mkdir(parents=True,exist_ok=True)
    p=d/filename
    p.write_text(text)
    return p

def stage_file(run_id, source_path, filename=''):
    source=Path(source_path)
    if not source.exists() or not source.is_file():
        raise RuntimeError('PLAN_STAGE_SOURCE_MISSING:'+str(source))
    d=UPLOAD_ROOT/run_id
    d.mkdir(parents=True,exist_ok=True)
    name=filename or source.name
    p=d/name
    tmp=p.with_suffix(p.suffix+'.tmp')
    shutil.copyfile(source,tmp)
    os.replace(tmp,p)
    return p

def generating_delay(st):
    streak=int(st.get('generating_streak',0))+1
    st['generating_streak']=streak
    seq=[POLL_GENERATING_BASE, max(POLL_GENERATING_BASE,90), max(POLL_GENERATING_BASE,120), max(POLL_GENERATING_BASE,180), max(POLL_GENERATING_BASE,240), POLL_GENERATING_MAX]
    return min(POLL_GENERATING_MAX, seq[min(streak-1,len(seq)-1)])

def reset_generating(st):
    st['generating_streak']=0

def register_rate_limit(st):
    """Persist an adaptive rate-limit backoff: 300s, 420s, 540s, ..."""
    streak=int(st.get('rate_limit_streak',0) or 0)+1
    st['rate_limit_streak']=streak
    st['last_rate_limit_epoch']=time.time()
    delay=RATE_LIMIT_BASE + RATE_LIMIT_STEP*(streak-1)
    until=time.time()+delay
    st['rate_limit_until_epoch']=until
    st['next_send_not_before_epoch']=max(float(st.get('next_send_not_before_epoch',0) or 0),until)
    return delay

def clear_rate_limit(st):
    """A non-rate-limited browser observation resets the consecutive ban streak."""
    st['rate_limit_streak']=0
    st['rate_limit_until_epoch']=0

def _sleep_until_send_allowed(st, state_path, purpose):
    now_epoch=time.time()
    not_before=max(float(st.get('next_send_not_before_epoch',0) or 0), float(st.get('rate_limit_until_epoch',0) or 0))
    last=float(st.get('last_send_epoch',0) or 0)
    not_before=max(not_before, last+MIN_SEND_INTERVAL)
    remaining=max(0,not_before-now_epoch)
    if remaining > 0:
        log(f'send guard purpose={purpose} cooldown={int(remaining)}s; no ChatGPT message will be sent')
    while remaining > 0:
        time.sleep(min(30,remaining))
        remaining=max(0,not_before-time.time())

def guarded_send(st, state_path, message, purpose, attachment='', delivery_id=''):
    """v4 deterministic send: direct Node/Playwright owns typing, attachment and the only send click."""
    marker=f'[AI_LOOP_DELIVERY id={delivery_id}]' if delivery_id else ''
    exact_message=str(message)
    if marker and marker not in exact_message:
        exact_message=marker+'\n'+exact_message
    while True:
        _sleep_until_send_allowed(st,state_path,purpose)
        ensure_chat_policy(st,state_path,st['chat_url'],purpose)
        result=run_deterministic_chat_send(st['chat_url'],exact_message,delivery_id or hashlib.sha256((purpose+'\0'+exact_message).encode()).hexdigest()[:24],run_id=st.get('run_id',''),attachment=attachment,timeout=180)
        status=str(result.get('status') or '').upper()
        if result.get('url'):
            st['chat_url']=str(result.get('url'))
        if status in {'SENT','ALREADY_SENT'}:
            ev=_validate_event({'state':'NO_ACTIONS','chat_url':st['chat_url'],'sol_text':'deterministic delivery '+status.lower(),'needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':status,'ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'})
            if status=='SENT':
                st['last_send_epoch']=time.time()
                st['next_send_not_before_epoch']=st['last_send_epoch']+MIN_SEND_INTERVAL
                st['last_delivery_id']=delivery_id
                reset_generating(st)
                save_state(state_path,st)
                log(f'delivery sent purpose={purpose} id={delivery_id} transport=persistent-browser-broker-v1; minimum inter-message gap={MIN_SEND_INTERVAL}s')
                return ev
            st['last_send_epoch']=max(float(st.get('last_send_epoch',0) or 0),time.time())
            st['next_send_not_before_epoch']=max(float(st.get('next_send_not_before_epoch',0) or 0),st['last_send_epoch']+MIN_SEND_INTERVAL)
            st['last_delivery_id']=delivery_id or st.get('last_delivery_id','')
            save_state(state_path,st)
            return ev
        if status=='NOT_SENT_RATE_LIMIT':
            delay=register_rate_limit(st); save_state(state_path,st)
            log(f'RATE_LIMIT detected before deterministic delivery purpose={purpose}; streak={st["rate_limit_streak"]} quiet cooldown={delay}s')
            time.sleep(min(delay,30))
            continue
        if status=='NOT_SENT_GENERATING':
            delay=generating_delay(st); save_state(state_path,st)
            log(f'GENERATING detected before deterministic delivery purpose={purpose}; retry_in={delay}s')
            time.sleep(min(delay,30))
            continue
        if status=='AMBIGUOUS_SEND' or bool(result.get('clicked')):
            log(f'DETERMINISTIC_SEND AMBIGUOUS purpose={purpose} id={delivery_id}; blind resend forbidden')
            obs=run_deterministic_bootstrap_observer(st.get('project_url') or st['chat_url'].split('/c/',1)[0],delivery_id,run_id=st.get('run_id',''),max_chats=12,timeout=120,candidate_urls=[st['chat_url']])
            if bool(obs.get('found')):
                st['chat_url']=str(obs.get('url') or st['chat_url'])
                st['last_send_epoch']=time.time(); st['next_send_not_before_epoch']=st['last_send_epoch']+MIN_SEND_INTERVAL; st['last_delivery_id']=delivery_id
                save_state(state_path,st)
                return _validate_event({'state':'NO_ACTIONS','chat_url':st['chat_url'],'sol_text':'ambiguous deterministic send recovered','needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':'ALREADY_SENT','ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'})
            raise RuntimeError('CHATGPT_AMBIGUOUS_SEND_UNRESOLVED_DIRECT:'+str(result.get('error') or 'UNKNOWN')[:900])
        raise RuntimeError('CHATGPT_DETERMINISTIC_SEND_FAILED:'+str(result.get('error') or status or 'UNKNOWN')[:900])

def send_results(st, state_path, run_id, results, action_keys):
    text=render_results(results)
    message='Operator completed the exact requested actions. Review the literal evidence below and continue with the implementation. Do not repeat completed actions unless the evidence explicitly requires it.'
    attachment=''
    if len(text.encode())>INLINE_EVIDENCE_LIMIT:
        p=stage_text(run_id,f'operator-evidence-{int(time.time())}.txt',text)
        attachment=str(p)
        message += '\nThe complete literal operator evidence is attached.'
    else:
        message += '\n\n--- BEGIN OPERATOR EVIDENCE ---\n'+text+'\n--- END OPERATOR EVIDENCE ---'
    delivery_id=hashlib.sha256(('results:'+','.join(sorted(action_keys))).encode()).hexdigest()[:20]
    return guarded_send(st,state_path,message,'send-results',attachment,delivery_id)

def register_pending_actions(st, state_path, actions, source_fp=''):
    pending=st.setdefault('pending_actions',{})
    delivered=set(st.setdefault('delivered_actions',[]))
    for a in actions:
        ok,reason=verify_action_transport(a)
        if not ok:
            raise RuntimeError('Refusing to register unverified operator action: '+reason)
        key=action_key(a)
        if key in delivered:
            continue
        pending[key]={'action':a,'source_fp':source_fp,'registered_at':now(),'transport_integrity_verified':True}
    save_state(state_path,st)


def has_pending_actions(st):
    delivered=set(st.get('delivered_actions') or [])
    pending=st.get('pending_actions') if isinstance(st.get('pending_actions'),dict) else {}
    return any(k not in delivered for k in pending)


def drain_pending_actions(st, state_path, repo_dir):
    pending=st.setdefault('pending_actions',{})
    delivered=set(st.setdefault('delivered_actions',[]))
    todo=[(k,v) for k,v in list(pending.items()) if k not in delivered and isinstance(v,dict) and isinstance(v.get('action'),dict)]
    if not todo:
        return None
    run_action_dir=RUNS_ROOT/st['run_id']/'actions'
    run_action_dir.mkdir(parents=True,exist_ok=True)
    st.setdefault('action_results',{})
    st.setdefault('processed_actions',[])
    results=[]; keys=[]
    for key,rec in todo:
        a=rec['action']; keys.append(key)
        result_path=st['action_results'].get(key,'')
        rerun=not (result_path and Path(result_path).exists())
        if not rerun:
            r=json.loads(Path(result_path).read_text())
            if int(r.get('exit_code',0))==126 and str(r.get('stderr','')).startswith('POLICY_BLOCKED:') and not forbidden_reason(a['command'],a['target']):
                rerun=True
                log(f"retry formerly policy-blocked action {a.get('id')} under current policy")
            else:
                log(f"reuse persisted pending action result {a.get('id')}")
        if rerun:
            r=run_action(a,repo_dir)
            rp=run_action_dir/(hashlib.sha256(key.encode()).hexdigest()[:20]+'.json')
            rp.write_text(json.dumps(r,indent=2))
            st['action_results'][key]=str(rp)
            if key not in st['processed_actions']:
                st['processed_actions'].append(key)
            save_state(state_path,st)
            log(f"action {a.get('id')} target={a.get('target')} rc={r['exit_code']} timeout={r['timed_out']}")
        results.append(r)
    if not results:
        return None
    ev=send_results(st,state_path,st['run_id'],results,keys)
    if ev and ev.get('delivery_status') in {'SENT','ALREADY_SENT'}:
        for key in keys:
            if key not in st['delivered_actions']:
                st['delivered_actions'].append(key)
            pending.pop(key,None)
        save_state(state_path,st)
    return ev


FRESH_BOOTSTRAP_BEGIN='AI_LOOP_FRESH_PROJECT_EVENT_V1_BEGIN'
FRESH_BOOTSTRAP_END='AI_LOOP_FRESH_PROJECT_EVENT_V1_END'
FRESH_BOOTSTRAP_PROOF_V2='AI_LOOP_FRESH_PROJECT_PROOF_V2|'
FRESH_BOOTSTRAP_PROOF_V3='AI_LOOP_FRESH_PROJECT_PROOF_V3|'


def fresh_project_event_contract_text(phase):
    phase=str(phase or '').upper()
    if phase not in {'CREATE','SEND'}:
        raise ValueError('INVALID_FRESH_BOOTSTRAP_PHASE:'+phase)
    delivery='NONE' if phase=='CREATE' else 'SENT'
    return f'''
FRESH PROJECT BOOTSTRAP PROOF CONTRACT v3 (mandatory):
After Playwright work is complete, make one FINAL `playwright_browser_run_code` proof call against the live page. It must return one single ASCII line and your final answer must copy it verbatim.
Required line format:
{FRESH_BOOTSTRAP_PROOF_V3}phase={phase}|status=PASS|chat_url=<encodeURIComponent(live URL)>|delivery={delivery}|empty=<1 or 0>|project=<1 or 0>|error=NONE
For ERROR use status=ERROR and a short ASCII error code. For rate limiting use status=RATE_LIMIT, delivery=NOT_SENT_RATE_LIMIT.
Rules:
- Proof MUST originate from the FINAL Playwright run_code result, not prose/memory.
- phase MUST be exactly {phase}.
- CREATE PASS requires delivery=NONE, empty=1, project=1. Chat/model/reasoning proof is deliberately NOT part of CREATE.
- SEND PASS requires delivery=SENT or ALREADY_SENT and project=1. Chat/model/reasoning are guarded by separate controller policy turns before/after SEND.
- Never output generic AI_LOOP_EVENT markers in this bootstrap turn.
- Compatibility: v2/v1 bootstrap evidence may still be parsed, but v3 is authoritative when present.
'''

def _fresh_v2_decode_url(value):
    try:
        from urllib.parse import unquote
        return unquote(str(value or ''))
    except Exception:
        return str(value or '')


def _fresh_v3_candidate_to_obj(fields, phase):
    if str(fields.get('phase') or '').upper()!=phase:
        raise ValueError('FRESH_BOOTSTRAP_PHASE_MISMATCH')
    status=str(fields.get('status') or '').upper()
    if status not in {'PASS','ERROR','RATE_LIMIT'}:
        raise ValueError('FRESH_BOOTSTRAP_STATUS_INVALID')
    delivery=str(fields.get('delivery') or 'NONE').upper()
    if delivery not in {'NONE','SENT','ALREADY_SENT','NOT_SENT_RATE_LIMIT'}:
        raise ValueError('FRESH_BOOTSTRAP_DELIVERY_INVALID')
    chat_url=_fresh_v2_decode_url(fields.get('chat_url') or '')
    if status=='PASS' and not chat_url.startswith('https://chatgpt.com/g/'):
        raise ValueError('FRESH_BOOTSTRAP_URL_INVALID')
    empty=str(fields.get('empty') or '0')=='1'
    project=str(fields.get('project') or '0')=='1'
    if status=='PASS' and phase=='CREATE' and not (delivery=='NONE' and empty and project):
        raise ValueError('FRESH_BOOTSTRAP_CREATE_PROOF_INCOMPLETE')
    if status=='PASS' and phase=='SEND' and not (delivery in {'SENT','ALREADY_SENT'} and project):
        raise ValueError('FRESH_BOOTSTRAP_SEND_PROOF_INCOMPLETE')
    return {
      'schema_version':3,'phase':phase,'status':status,'chat_url':chat_url,
      'error':'' if str(fields.get('error') or '').upper() in {'','NONE'} else str(fields.get('error') or ''),
      'delivery_status':delivery,'ui_surface':'','ui_model':'','ui_reasoning':'','chat_policy_status':'NOT_CHECKED',
      'empty':empty,'project':project,'evidence':'fresh bootstrap v3 Playwright proof',
    }


def _fresh_v2_candidate_to_obj(fields, phase):
    if str(fields.get('phase') or '').upper()!=phase:
        raise ValueError('FRESH_BOOTSTRAP_PHASE_MISMATCH')
    status=str(fields.get('status') or '').upper()
    if status not in {'PASS','ERROR','RATE_LIMIT'}:
        raise ValueError('FRESH_BOOTSTRAP_STATUS_INVALID')
    delivery=str(fields.get('delivery') or 'NONE').upper()
    if delivery not in {'NONE','SENT','ALREADY_SENT','NOT_SENT_RATE_LIMIT'}:
        raise ValueError('FRESH_BOOTSTRAP_DELIVERY_INVALID')
    return {
      'schema_version':2,'phase':phase,'status':status,
      'chat_url':_fresh_v2_decode_url(fields.get('chat_url') or ''),
      'error':'' if str(fields.get('error') or '').upper() in {'','NONE'} else str(fields.get('error') or ''),
      'delivery_status':delivery,
      'ui_surface':str(fields.get('surface') or ''),
      'ui_model':str(fields.get('model') or ''),
      'ui_reasoning':str(fields.get('reasoning') or ''),
      'chat_policy_status':str(fields.get('policy') or ''),
      'empty':str(fields.get('empty') or '0')=='1',
      'project':str(fields.get('project') or '0')=='1',
      'evidence':'fresh bootstrap v2 Playwright proof',
    }


def _fresh_obj_valid(cand, phase):
    if not isinstance(cand,dict): return False
    if not _schema_version_matches(cand.get('schema_version'), (1,2,3)): return False
    if str(cand.get('phase') or '').upper()!=phase: return False
    if str(cand.get('status') or '').upper() not in {'PASS','ERROR','RATE_LIMIT'}: return False
    return True


def _fresh_event_from_obj(obj, phase):
    status=str(obj.get('status') or '').upper()
    delivery=str(obj.get('delivery_status') or 'NONE').upper()
    if status=='RATE_LIMIT':
        state='RATE_LIMIT'; delivery='NOT_SENT_RATE_LIMIT'
    elif status=='ERROR':
        state='ERROR'
    else:
        state='NO_ACTIONS'
    prefix='FRESH_PROJECT_CHAT=PASS' if phase=='CREATE' else 'FRESH_PROJECT_DELIVERY=PASS'
    proof=''
    if status=='PASS':
        if phase=='CREATE':
            proof=f'{prefix} empty={1 if bool(obj.get("empty")) else 0} project={1 if bool(obj.get("project")) else 0}'
        else:
            proof=prefix
    evidence=str(obj.get('evidence') or '')[:1600]
    return _validate_event({
      'state':state,'chat_url':str(obj.get('chat_url') or ''),'sol_text':(proof+' '+evidence).strip(),
      'needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'',
      'error':str(obj.get('error') or ''),'delivery_status':delivery,
      'ui_surface':str(obj.get('ui_surface') or ''),'ui_model':str(obj.get('ui_model') or ''),
      'ui_reasoning':str(obj.get('ui_reasoning') or ''),'chat_policy_status':str(obj.get('chat_policy_status') or ''),
    })


def parse_fresh_project_bootstrap_response(text, expected_phase):
    """Parse fresh-project proof from Playwright transcript; v3 decouples freshness from model policy."""
    txt=_strip_ansi(str(text or ''))
    phase=str(expected_phase or '').upper()
    if phase not in {'CREATE','SEND'}:
        raise RuntimeError('FRESH_BOOTSTRAP_PHASE_INVALID:'+phase)

    proof_errors=[]
    # v2.40 authoritative v3 proof.
    v3=[]
    for m in re.finditer(re.escape(FRESH_BOOTSTRAP_PROOF_V3)+r'[^\r\n`]*', txt):
        line=m.group(0).strip()
        try:
            fields={}
            for part in line.split('|')[1:]:
                if '=' not in part: continue
                k,v=part.split('=',1); fields[k.strip()]=v.strip()
            cand=_fresh_v3_candidate_to_obj(fields,phase)
            if _fresh_obj_valid(cand,phase): v3.append(cand)
        except Exception as e:
            proof_errors.append('v3:'+str(e))
    if v3:
        return _fresh_event_from_obj(v3[-1],phase)

    # v2.38/v2.39 compatibility proof. Require a real ChatGPT project URL so an echoed
    # contract placeholder cannot be mistaken for browser evidence.
    v2=[]
    for m in re.finditer(re.escape(FRESH_BOOTSTRAP_PROOF_V2)+r'[^\r\n`]*', txt):
        line=m.group(0).strip()
        try:
            fields={}
            for part in line.split('|')[1:]:
                if '=' not in part: continue
                k,v=part.split('=',1); fields[k.strip()]=v.strip()
            cand=_fresh_v2_candidate_to_obj(fields,phase)
            if cand.get('status')=='PASS' and not str(cand.get('chat_url') or '').startswith('https://chatgpt.com/g/'):
                raise ValueError('FRESH_BOOTSTRAP_URL_INVALID')
            if _fresh_obj_valid(cand,phase): v2.append(cand)
        except Exception as e:
            proof_errors.append('v2:'+str(e))
    if v2:
        return _fresh_event_from_obj(v2[-1],phase)

    # Legacy v1 JSON marker pairs.
    candidates=[]; pos=0
    while True:
        i=txt.find(FRESH_BOOTSTRAP_BEGIN,pos)
        if i < 0: break
        j=txt.find(FRESH_BOOTSTRAP_END,i+len(FRESH_BOOTSTRAP_BEGIN))
        if j < 0: break
        candidates.append(txt[i+len(FRESH_BOOTSTRAP_BEGIN):j].strip())
        pos=j+len(FRESH_BOOTSTRAP_END)
    dec=json.JSONDecoder(); last_error='NO_VALID_ENVELOPE'
    for raw in reversed(candidates):
        try:
            cand=json.loads(raw)
            if _fresh_obj_valid(cand,phase): return _fresh_event_from_obj(cand,phase)
        except Exception as e:
            last_error='FRESH_BOOTSTRAP_JSON_INVALID:'+str(e)
        for mm in re.finditer(r'\{',raw):
            try:
                cand,_=dec.raw_decode(raw[mm.start():])
                if _fresh_obj_valid(cand,phase): return _fresh_event_from_obj(cand,phase)
            except Exception:
                continue

    # Last compatibility fallback: schema-constrained JSON anywhere in transcript.
    anywhere=[]
    for mm in re.finditer(r'\{',txt):
        try:
            cand,_=dec.raw_decode(txt[mm.start():])
            if _fresh_obj_valid(cand,phase): anywhere.append(cand)
        except Exception:
            continue
    if anywhere:
        return _fresh_event_from_obj(anywhere[-1],phase)

    detail=(proof_errors[-1] if proof_errors else last_error)
    if not candidates and not proof_errors:
        detail='FRESH_BOOTSTRAP_PROOF_MISSING'
    raise RuntimeError(detail+'; tail='+txt[-1800:].replace('\n',' ')[:1800])

def fresh_project_oc_turn(prompt, purpose, phase):
    raw=oc_raw_turn(prompt + fresh_project_event_contract_text(phase), purpose)
    return parse_fresh_project_bootstrap_response(raw,phase)


def browser_fresh_draft_policy_prompt(project_url, fresh_draft_url, forbidden_chat_url=''):
    forbidden=_norm_chat_url(forbidden_chat_url)
    return f'''ROLE: CHATGPT_FRESH_DRAFT_POLICY_GUARD.
Use Playwright browser tools only. DO NOT send, type, attach, navigate, reload, choose history, or create another chat.
You are already on the controller-proven fresh EMPTY draft for this exact project:
PROJECT={project_url}
EXPECTED_DRAFT={fresh_draft_url}
FORBIDDEN_HISTORICAL_CHAT={forbidden or '(none recorded)'}

FIRST, inspect the current live page IN PLACE. If current URL is outside this project, equals the forbidden historical /c/, or any existing user/assistant turn is visible, fail with FRESH_DRAFT_IDENTITY_LOST and do nothing else.

Then verify/repair only these UI settings in place, without navigation:
- surface = normal Chat (Work/Codex forbidden)
- model = GPT-5.6 Sol
- reasoning = High
Use selected-state evidence from accessible controls. If the closed header omits model text, open the model picker and prove the selected/check state there. Close menus when done. Do not send anything.

PASS only when the current fresh draft is still the same project draft and live controls prove Chat + GPT-5.6 Sol + High. On PASS report the current live URL.''' 


def ensure_fresh_draft_chat_policy(st, state_path, project_url, fresh_draft_url, forbidden_chat_url, purpose='start-plan-fresh-draft'):
    last=None
    for attempt in range(1,3):
        prompt=browser_fresh_draft_policy_prompt(project_url,fresh_draft_url,forbidden_chat_url)
        ev=chat_policy_oc_turn(prompt,f'{purpose}-chat-policy-guard','fresh-draft-policy')
        last=ev
        if ev.get('chat_url') and isinstance(st,dict):
            st['chat_url']=ev['chat_url']
        loc_ok=fresh_project_location_pass(project_url,forbidden_chat_url,ev.get('chat_url') or fresh_draft_url)
        if chat_policy_pass(ev) and loc_ok:
            _record_chat_policy(st,ev,purpose)
            if state_path is not None and isinstance(st,dict): save_state(Path(state_path),st)
            log('FRESH_PROJECT_POLICY PASS surface=chat model=gpt-5.6-sol reasoning=high purpose='+str(purpose))
            return ev
        _record_chat_policy(st,ev,purpose)
        if state_path is not None and isinstance(st,dict): save_state(Path(state_path),st)
        evidence=re.sub(r'\s+',' ',str(ev.get('sol_text') or '')).strip()[:600]
        err=str(ev.get('error') or ('FRESH_DRAFT_LOCATION_UNVERIFIED' if not loc_ok else 'UNVERIFIED'))
        log(f'FRESH_PROJECT_POLICY FAIL attempt={attempt} purpose={purpose} surface={ev.get("ui_surface","")} model={ev.get("ui_model","")} reasoning={ev.get("ui_reasoning","")} error={err} evidence={evidence!r}')
        if attempt<2: time.sleep(5)
    raise RuntimeError('CHATGPT_FRESH_DRAFT_POLICY_GUARD_FAILED:'+str((last or {}).get('error') or 'UNVERIFIED'))


def start_new_chat(project_url, run_id, plan_filename, plan_markdown, st=None, state_path=None, plan_source_path=None):
    """v4.1 persistent-broker bootstrap. OpenCode/LLM has no browser authority in create/attach/send/observe paths."""
    if not plan_filename:
        plan_filename=f'IMPLEMENTATION_PLAN_{int(time.time())}.md'
    p=stage_file(run_id,plan_source_path,plan_filename) if plan_source_path else stage_text(run_id,plan_filename,plan_markdown)
    implement=prompt_file('implement.txt','team pipeline: 1. implement completely attached .md plan 2. unique commit push in current branch (feature/GRU)')
    if st is None: st={}
    reentry_quarantine=[]

    # New-loop isolation: old ambiguous deliveries are metadata only. Never reopen/adopt an old conversation.
    prior=_prior_ambiguous_bootstraps(plan_filename,run_id)
    if prior:
        log(f'DETERMINISTIC_NEW_LOOP prior_ambiguous={len(prior)} plan={plan_filename}; historical chat adoption disabled; quarantining prior deliveries')
        for rec in prior:
            did=rec['delivery_id']
            candidates=_prior_state_candidate_urls(rec,project_url)
            history=_chrome_history_project_chat_urls(project_url,limit=120)
            evidence={'delivery_id':did,'run_id':rec['run_id'],'resolution':'QUARANTINED_NEW_LOOP_FRESH_CHAT_REQUIRED','candidate_urls':candidates,'history_candidate_urls':history.get('urls') or [],'history_scan_ok':bool(history.get('ok')),'at':now()}
            sp=Path(str(rec.get('state_path') or ''))
            if sp.is_file():
                try:
                    obj=json.loads(sp.read_text(encoding='utf-8'))
                    ab=obj.get('adaptive_bootstrap') if isinstance(obj.get('adaptive_bootstrap'),dict) else {}
                    ab.update({'status':'AMBIGUITY_QUARANTINED','ambiguity_resolution':evidence,'resolved_at':now()})
                    obj['adaptive_bootstrap']=ab; save_state(sp,obj)
                except Exception: pass
            reentry_quarantine.append(evidence)
            log(f'DETERMINISTIC_NEW_LOOP QUARANTINE prior_run={rec["run_id"]} delivery_id={did}; old chat will NOT be opened/adopted')
        st['prior_delivery_quarantine']=reentry_quarantine
        if state_path is not None: save_state(Path(state_path),st)

    if reentry_quarantine:
        implement += ('\n\nAI_LOOP_REENTRY_GUARD: A previous browser delivery for this same plan was ambiguous. '
                      'Before making ANY repository mutation or commit, inspect the current feature/GRU branch, remote HEAD, CI state, and the attached plan invariants. '
                      'Treat current repository/CI state as authoritative. If the plan implementation or its required final commit already exists, DO NOT create, amend, revert, cherry-pick, or push a duplicate commit; continue only the remaining validation/deployment/GO work required by the plan. '
                      'If another implementation is still active, do not race it; reconcile state first.')

    delivery_id=_adaptive_delivery_id(run_id,plan_filename,p)
    st['adaptive_bootstrap']={'delivery_id':delivery_id,'project_url':project_url,'plan_filename':plan_filename,'status':'STARTING_DIRECT_WORKER','at':now(),'transport':'persistent-browser-broker-v1'}
    if state_path is not None: save_state(Path(state_path),st)

    last_error='UNVERIFIED'
    for attempt in range(1,3):
        result={}
        try:
            result=run_deterministic_browser_bootstrap(project_url,str(p),plan_filename,implement,run_id,delivery_id,timeout=180)
        except Exception as e:
            last_error=str(e)
            result={'status':'ERROR','error':last_error,'clicked':False,'safeToRetry':True}
        status=str(result.get('status') or '').upper()
        clicked=bool(result.get('clicked'))
        url=str(result.get('url') or '')
        last_error=str(result.get('error') or last_error or 'UNKNOWN')
        if status=='PASS':
            ledger=result.get('ledger') if isinstance(result.get('ledger'),dict) else {}
            ledger_ok=(str(ledger.get('delivery_id') or '')==delivery_id and str(ledger.get('send_status') or '').upper()=='SENT')
            if not url or not ledger_ok:
                raise RuntimeError('BROKER_BOOTSTRAP_INVALID_SUCCESS_PROOF')
            st['chat_url']=url
            st['adaptive_bootstrap'].update({'status':'PLAN_SENT_VERIFIED','chat_url':url,'attempt':attempt,'worker_result':result,'at':now()})
            clear_rate_limit(st)
            if state_path is not None: save_state(Path(state_path),st)
            log(f'DETERMINISTIC_BOOTSTRAP PASS chat={url} delivery_id={delivery_id} attempt={attempt} transport=persistent-browser-broker-v1')
            return _validate_event({'state':'NO_ACTIONS','chat_url':url,'sol_text':'persistent broker bootstrap verified','needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':'SENT','ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'})

        if status=='AMBIGUOUS_SEND' or clicked or not bool(result.get('safeToRetry',not clicked)):
            st['adaptive_bootstrap'].update({'status':'AMBIGUOUS_SEND','attempt':attempt,'last_error':last_error[:1200],'worker_result':result,'send_retry_forbidden':True,'at':now()})
            if state_path is not None: save_state(Path(state_path),st)
            log(f'DETERMINISTIC_BOOTSTRAP AMBIGUOUS_SEND attempt={attempt} delivery_id={delivery_id} error={last_error[:700]}; blind resend forbidden')
            # Direct read-only observer is also model-free. It is the only recovery authority after a click.
            obs=run_deterministic_bootstrap_observer(project_url,delivery_id,run_id=run_id,max_chats=24,timeout=150,candidate_urls=[url] if url else [])
            if bool(obs.get('found')) and bool(obs.get('project')):
                rec_url=str(obs.get('url'))
                st['chat_url']=rec_url
                st['adaptive_bootstrap'].update({'status':'PLAN_SENT_VERIFIED_RECOVERED','chat_url':rec_url,'final_observation':obs,'recovered_after_ambiguous_send':True,'at':now()})
                if state_path is not None: save_state(Path(state_path),st)
                log(f'DETERMINISTIC_RECOVERY PASS current_run chat={rec_url} delivery_id={delivery_id}')
                return _validate_event({'state':'NO_ACTIONS','chat_url':rec_url,'sol_text':'ambiguous send recovered by direct observer','needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':'ALREADY_SENT','ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'})
            st['adaptive_bootstrap'].update({'status':'AMBIGUOUS_SEND_UNRESOLVED','recovery_observation':obs,'at':now()})
            if state_path is not None: save_state(Path(state_path),st)
            raise RuntimeError('CHATGPT_AMBIGUOUS_SEND_UNRESOLVED_DIRECT_WORKER:'+last_error[:900])

        st['adaptive_bootstrap'].update({'status':'RETRY_SAFE_NO_SEND','attempt':attempt,'last_error':last_error[:1200],'worker_result':result,'send_retry_forbidden':False,'at':now()})
        if state_path is not None: save_state(Path(state_path),st)
        log(f'DETERMINISTIC_BOOTSTRAP RETRY_SAFE_NO_SEND attempt={attempt} error={last_error[:700]}')
        if attempt<2: time.sleep(1)

    st['adaptive_bootstrap']['status']='FAILED_NO_SEND'
    if state_path is not None: save_state(Path(state_path),st)
    raise RuntimeError('CHATGPT_DETERMINISTIC_BOOTSTRAP_FAILED_NO_SEND:'+last_error[:1000])

def main():
    load_env()
    def _term(signum, frame):
        log(f'controller signal={signum}; stopping browser broker')
        _browser_broker_stop()
        raise SystemExit(128+int(signum))
    signal.signal(signal.SIGTERM,_term); signal.signal(signal.SIGINT,_term)
    ap=argparse.ArgumentParser()
    ap.add_argument('--state',required=True)
    ap.add_argument('--bootstrap-plan',default='')
    ap.add_argument('--adopt-chat',default='')
    args=ap.parse_args()
    state_path=Path(args.state)
    lock_path=state_path.with_suffix(state_path.suffix+'.lock')
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    global_lock_path=STATE_ROOT/'.ai-loopd.global.lock'
    global_lock_fp=open(global_lock_path,'w')
    try:
        fcntl.flock(global_lock_fp, fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(f'Another ai-loop controller is already active: {global_lock_path}')
    lock_fp=open(lock_path,'w')
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(f'Another ai-loopd-v2 owns {lock_path}')
    cfg=load_project(); repo_dir=Path(cfg['repo_dir'])
    if state_path.exists(): st=load_state(state_path)
    else:
        name=state_path.name
        run_id=name[:-len('.v2.json')] if name.endswith('.v2.json') else ('R'+datetime.now().strftime('%Y%m%dT%H%M%S'))
        baseline=github_head(cfg['repo'],cfg['branch'])
        st={'run_id':run_id,'repo':cfg['repo'],'branch':cfg['branch'],'project_url':cfg['project_url'],
            'chat_url':args.adopt_chat,'baseline_sha':baseline,'candidate_sha':None,'phase':'IMPLEMENTING',
            'iteration':0,'processed_turns':[],'processed_actions':[],'action_results':{},'delivered_actions':[],'pending_actions':{},'followups':{},'proceeds':{},'last_ci':None,'failure_stage':'','semaphore_evidence':{},'semaphore_evidence_deliveries':{},'local_failure_evidence':{},'failure_evidence_deliveries':{},'quarantined_actions':{},'secure_action_reissue_required':False,'secure_action_reissue_ids':[],'secure_action_pending':False,'secure_action_pending_followups':{},'started_at':now(),'generating_streak':0,'last_send_epoch':0,'next_send_not_before_epoch':0,'rate_limit_until_epoch':0,'rate_limit_streak':0,'last_rate_limit_epoch':0,'browser_owner_session_id':'','browser_owner_recoveries':0,'browser_owner_server_restarts':0,'failure_identity_version':2,'send_guard_version':26,'chat_policy_guard_version':0,'chat_policy_audit':[],'chat_policy_last':{},'opencode_transport_mode':'cli-run-in-process','plan_artifact_handoffs':{},'plan_artifact_failures':{},'plan_artifact_requests':{},'plan_artifact_attempts':{},'plan_artifact_last_error':'','plan_artifact_blocked_until_epoch':0,'semantic_history':[],'semantic_transition_ledger':{},'semantic_action_mismatches':[],'semantic_plan_artifact_requests':{},'semantic_unclassified':{},'semantic_inspector_version':1,'semantic_authority':'proposal-only-controller-validates','adaptive_browser_version':1,'adaptive_browser_diagnostics':[],'adaptive_bootstrap':{},'settled_message_ledger':{},'wait_new_assistant_message':{},'plan_artifact_corrective_requests':{},'plan_artifact_corrective_candidate_requests':{},'immutable_settled_version':1,'plan_artifact_acquisition_version':3,'browser_profile_clean_exit_version':1,'deterministic_artifact_worker_version':3,'artifact_turn_identity_version':2,'plan_artifact_dom_schema_version':2,'plan_artifact_network_capture_version':1,'plan_artifact_transport_version':1,'plan_artifact_locator_repairs':{},'plan_artifact_dom_schema_repairs':{},'plan_artifact_network_repairs':{},'plan_artifact_transport_repairs':{},'plan_artifact_direct_worker_pending':{}}
        save_state(state_path,st)
    if int(st.get('send_guard_version',0) or 0) < 2:
        st['send_guard_version']=2
        st['generating_streak']=0
        st['last_send_epoch']=float(st.get('last_send_epoch',0) or 0)
        st['rate_limit_until_epoch']=max(float(st.get('rate_limit_until_epoch',0) or 0), time.time()+STARTUP_QUIET_SECONDS)
        st['next_send_not_before_epoch']=max(float(st.get('next_send_not_before_epoch',0) or 0), st['rate_limit_until_epoch'])
        save_state(state_path,st)
        log(f'v2.6 send-guard migration: startup quiet window={STARTUP_QUIET_SECONDS}s')
    if int(st.get('send_guard_version',0) or 0) < 3:
        st['send_guard_version']=3
        st['rate_limit_streak']=0
        st['last_rate_limit_epoch']=0
        # Replace any legacy fixed 900s ban window with at most the new 300s base window.
        legacy_until=float(st.get('rate_limit_until_epoch',0) or 0)
        if legacy_until > time.time():
            st['rate_limit_until_epoch']=min(legacy_until,time.time()+RATE_LIMIT_BASE)
            st['next_send_not_before_epoch']=min(float(st.get('next_send_not_before_epoch',0) or 0),st['rate_limit_until_epoch']) if float(st.get('next_send_not_before_epoch',0) or 0) > 0 else st['rate_limit_until_epoch']
        save_state(state_path,st)
        log(f'v2.9 adaptive rate-limit migration: base={RATE_LIMIT_BASE}s step={RATE_LIMIT_STEP}s')
    if int(st.get('send_guard_version',0) or 0) < 4:
        st['send_guard_version']=4
        st.setdefault('pending_actions',{})
        st.setdefault('semaphore_evidence',{})
        st.setdefault('semaphore_evidence_deliveries',{})
        save_state(state_path,st)
        log('v2.9 controller migration: strict routing + pending-action priority + Semaphore browser evidence')
    if int(st.get('send_guard_version',0) or 0) < 5:
        st['send_guard_version']=5
        st.setdefault('local_failure_evidence',{})
        st.setdefault('failure_evidence_deliveries',{})
        save_state(state_path,st)
        log('v2.10 migration: robust CI evidence normalization + exact-SHA local failure investigation')
    if int(st.get('send_guard_version',0) or 0) < 6:
        st['send_guard_version']=6
        quarantine=st.setdefault('quarantined_actions',{})
        reissue=[]
        pending=st.setdefault('pending_actions',{})
        delivered=set(st.setdefault('delivered_actions',[]))
        for key,rec in list(pending.items()):
            if key in delivered or not isinstance(rec,dict) or not isinstance(rec.get('action'),dict):
                continue
            action=rec['action']
            ok,_reason=verify_action_transport(action)
            if ok:
                continue
            quarantine[key]={
              'action':action,
              'source_fp':rec.get('source_fp',''),
              'registered_at':rec.get('registered_at',''),
              'action_result_path':st.get('action_results',{}).get(key,''),
              'quarantined_at':now(),
              'reason':'LEGACY_OR_UNVERIFIED_ACTION_TRANSPORT',
            }
            reissue.append(str(action.get('id') or key))
            pending.pop(key,None)
        if reissue:
            st['secure_action_reissue_required']=True
            st['secure_action_reissue_ids']=sorted(set(reissue))
        else:
            st.setdefault('secure_action_reissue_required',False)
            st.setdefault('secure_action_reissue_ids',[])
        save_state(state_path,st)
        log(f'v2.11 migration: secure action envelopes + decoupled delivery; quarantined_unverified_actions={len(reissue)}')
    if int(st.get('send_guard_version',0) or 0) < 7:
        st['send_guard_version']=7
        st.setdefault('secure_action_pending_followups',{})
        # If a prior secure-action transport failed or legacy action remains quarantined,
        # preserve a durable fence across restart. CONTINUE and generic followups are
        # forbidden until a byte-verified action is captured.
        q=st.get('quarantined_actions') if isinstance(st.get('quarantined_actions'),dict) else {}
        terr=st.get('transport_errors') if isinstance(st.get('transport_errors'),dict) else {}
        if q or terr:
            st['secure_action_pending']=True
            st['secure_action_reissue_required']=True
            if not st.get('secure_action_reissue_ids'):
                ids=[]
                for rec in q.values():
                    if isinstance(rec,dict) and isinstance(rec.get('action'),dict):
                        ids.append(str(rec['action'].get('id') or 'unknown'))
                st['secure_action_reissue_ids']=sorted(set(ids))
        else:
            st.setdefault('secure_action_pending',False)
            st.setdefault('secure_action_reissue_required',False)
        save_state(state_path,st)
        log(f'v2.12 migration: secure-action pending fence + transport-error reissue; secure_action_pending={bool(st.get("secure_action_pending"))}')
    if int(st.get('send_guard_version',0) or 0) < 8:
        st['send_guard_version']=8
        st.setdefault('action_handoffs',{})
        st.setdefault('action_handoff_errors',{})
        if st.get('secure_action_pending'):
            st['secure_action_reissue_required']=False
        save_state(state_path,st)
        log(f'v2.13 migration: controller-owned chunked file handoff; secure_action_pending={bool(st.get("secure_action_pending"))} reissue_required={bool(st.get("secure_action_reissue_required"))}')
    if int(st.get('send_guard_version',0) or 0) < 9:
        st['send_guard_version']=9
        st.setdefault('action_handoffs',{})
        st.setdefault('action_handoff_errors',{})
        # v2.14 uses a fresh .linepart*.b64u namespace, so malformed v2.13
        # JSON-chunk artifacts are never trusted or reused.
        if st.get('secure_action_pending'):
            st['secure_action_reissue_required']=False
        save_state(state_path,st)
        log(f'v2.14 migration: non-JSON Base64URL line chunks + per-chunk SHA256; secure_action_pending={bool(st.get("secure_action_pending"))}')
    if int(st.get('send_guard_version',0) or 0) < 10:
        st['send_guard_version']=10
        st.setdefault('action_handoffs',{})
        st.setdefault('action_handoff_errors',{})
        # v2.15 never trusts legacy chunk/model-transcribed payload pieces. It keeps
        # only action metadata and materializes exact bytes via Playwright download.saveAs.
        if st.get('secure_action_pending'):
            st['secure_action_reissue_required']=False
        save_state(state_path,st)
        log(f'v2.15 migration: direct Playwright DOM-download file handoff; secure_action_pending={bool(st.get("secure_action_pending"))}')
    if int(st.get('send_guard_version',0) or 0) < 11:
        st['send_guard_version']=11
        st.setdefault('semaphore_auth_recovery',{})
        save_state(state_path,st)
        log('v2.16 migration: Semaphore GitHub OAuth interstitial auto-recovery enabled; human auth remains fenced')
    if int(st.get('send_guard_version',0) or 0) < 12:
        st['send_guard_version']=12
        st.setdefault('browser_owner_session_id','')
        st.setdefault('browser_owner_recoveries',0)
        st['failure_identity_version']=2
        legacy=st.setdefault('legacy_failure_evidence_deliveries',{})
        current=st.get('failure_evidence_deliveries') if isinstance(st.get('failure_evidence_deliveries'),dict) else {}
        if current:
            legacy.update(current)
            st['failure_evidence_deliveries']={}
        save_state(state_path,st)
        log('v2.17 migration: single durable OpenCode/Playwright browser owner + provider-scoped exact failure evidence identity')
    if int(st.get('send_guard_version',0) or 0) < 13:
        st['send_guard_version']=13
        st.setdefault('browser_owner_server_restarts',0)
        st.setdefault('browser_owner_playwright_capability','')
        st.setdefault('browser_owner_playwright_probe_at','')
        save_state(state_path,st)
        log('v2.18 migration: forced fresh OpenCode/MCP lifecycle + real Playwright capability gate + one-shot hard recovery')
    if int(st.get('send_guard_version',0) or 0) < 14:
        st['send_guard_version']=14
        if st.get('browser_owner_session_id'):
            st['legacy_browser_owner_session_id']=st.get('browser_owner_session_id')
        st['browser_owner_session_id']=''
        st['opencode_transport_mode']='cli-run-in-process'
        st.setdefault('opencode_cli_playwright_capability','')
        st.setdefault('opencode_cli_playwright_probe_at','')
        save_state(state_path,st)
        log('v2.19 migration: serialized in-process opencode run transport; HTTP serve/session browser transport retired')
    if int(st.get('send_guard_version',0) or 0) < 15:
        st['send_guard_version']=15
        st.setdefault('plan_dom_handoffs',{})
        st.setdefault('plan_dom_failures',{})
        st.setdefault('plan_dom_last_error','')
        save_state(state_path,st)
        log('v2.20 migration: deterministic DOM-to-file plan materialization; repeated request-plan-text loop retired')
    if int(st.get('send_guard_version',0) or 0) < 16:
        st['send_guard_version']=16
        st.setdefault('plan_artifact_handoffs',{})
        st.setdefault('plan_artifact_failures',{})
        st.setdefault('plan_artifact_requests',{})
        st.setdefault('plan_artifact_attempts',{})
        st.setdefault('plan_artifact_last_error','')
        st.setdefault('plan_artifact_blocked_until_epoch',0)
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.21 migration: downloadable .md plan artifact contract + stale secure-action reconciliation + bounded plan watchdog'+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 17:
        st['send_guard_version']=17
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        st['plan_artifact_stage_priority_version']=1
        save_state(state_path,st)
        log('v2.22 migration: plan-artifact stage has absolute priority over generic Sol ACTIONS inspection; downloadable .md only'+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 18:
        st['send_guard_version']=18
        st.setdefault('semantic_history',[])
        st.setdefault('semantic_transition_ledger',{})
        st.setdefault('semantic_action_mismatches',[])
        st.setdefault('semantic_plan_artifact_requests',{})
        st.setdefault('semantic_unclassified',{})
        st['semantic_inspector_version']=1
        st['semantic_authority']='proposal-only-controller-validates'
        migrated_repair=0
        if str(st.get('phase'))=='FAILURE_ANALYSIS' and str(st.get('failure_stage') or '')=='PLAN_ARTIFACT_BLOCKED':
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            key=str(st.get('candidate_sha') or 'unknown')[:16]
            st.setdefault('plan_artifact_attempts',{})[key]=0
            st['plan_artifact_blocked_until_epoch']=0
            migrated_repair=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.23 migration: AI semantic inspector proposes canonical events; deterministic FSM validates transitions/effects; plan artifact repair is bounded'+(' plan_artifact_repair_required=1' if migrated_repair else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 19:
        st['send_guard_version']=19
        st.setdefault('settled_message_ledger',{})
        st.setdefault('wait_new_assistant_message',{})
        st.setdefault('plan_artifact_corrective_requests',{})
        st.setdefault('plan_artifact_corrective_candidate_requests',{})
        st['immutable_settled_version']=1
        migrated_corrective=0
        # v2.24: a SETTLED assistant response is immutable evidence. If v2.23
        # exhausted physical download attempts against the same PLAN_READY message,
        # do not semantically reinterpret it after a 900s timer. Mark that message
        # terminal and send at most one corrective request asking for a real .md, then
        # wait for a NEW assistant message identity.
        cur_stage=str(st.get('failure_stage') or '')
        cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
        exhausted=int((st.get('plan_artifact_attempts') or {}).get(cand_key,0) or 0) >= PLAN_ARTIFACT_MAX_ATTEMPTS
        if str(st.get('phase'))=='FAILURE_ANALYSIS' and (cur_stage=='PLAN_ARTIFACT_BLOCKED' or (cur_stage=='PLAN_ARTIFACT_REPAIR_REQUIRED' and exhausted)):
            last=st.get('last_semantic_event') or {}
            if str(last.get('observation') or '')=='SETTLED':
                sem={
                    'observation':'SETTLED',
                    'semantic_event':str(last.get('semantic_event') or 'PLAN_ARTIFACT_MISSING'),
                    'confidence':float(last.get('confidence',1.0) or 1.0),
                    'source_message_id':str(last.get('source_message_id') or ''),
                    'chat_url':str(st.get('chat_url') or ''),
                    'rationale':str(last.get('rationale') or ''),
                }
                mark_settled_message_terminal(st,sem,'v2.24 migration: v2.23 physical plan artifact attempts exhausted')
                st['failure_stage']='PLAN_ARTIFACT_CORRECTIVE_REQUIRED'
                st['plan_artifact_blocked_until_epoch']=0
                migrated_corrective=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.24 migration: immutable SETTLED response evidence + one corrective plan-artifact request + wait-for-new-assistant-message; 900s semantic reinspection retired'+(' plan_artifact_corrective_required=1' if migrated_corrective else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 20:
        st['send_guard_version']=20
        st['plan_artifact_acquisition_version']=2
        st['browser_profile_clean_exit_version']=1
        migrated_artifact_acquisition=0
        # v2.25 upgrades artifact acquisition, not semantic meaning. If the latest
        # SETTLED evidence is already PLAN_READY but v2.24 could not physically save
        # its attachment, retry that SAME response exactly once through the new
        # source-message-scoped acquisition strategy (download event -> authenticated
        # href fetch -> ChatGPT preview download). Do not ask Sol for another plan.
        last=st.get('last_semantic_event') or {}
        stage=str(st.get('failure_stage') or '')
        last_error=str(st.get('plan_artifact_last_error') or '')
        if (str(st.get('phase'))=='FAILURE_ANALYSIS'
            and str(last.get('observation') or '')=='SETTLED'
            and str(last.get('semantic_event') or '')=='PLAN_READY'
            and (stage in {'PLAN_ARTIFACT_REPAIR_REQUIRED','PLAN_ARTIFACT_BLOCKED_FINAL','PLAN_ARTIFACT_CORRECTIVE_REQUIRED'}
                 or 'PLAN_ARTIFACT_NOT_DOWNLOADED' in last_error)):
            cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            st.setdefault('plan_artifact_attempts',{})[cand_key]=0
            st['plan_artifact_last_error']=''
            st['plan_artifact_blocked_until_epoch']=0
            clear_wait_for_new_assistant(st)
            sid=str(last.get('source_message_id') or '').strip()
            if sid:
                lkey='msg:'+sid
                rec=(st.setdefault('settled_message_ledger',{})).get(lkey)
                if isinstance(rec,dict) and rec.get('terminal') and not rec.get('artifact_verified'):
                    rec['terminal']=False
                    rec['v225_reopened_for_artifact_acquisition']=True
                    rec['v225_reopened_at']=now()
            migrated_artifact_acquisition=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.25 migration: source-message-scoped artifact acquisition + ChatGPT preview/href fallback + clean Chrome profile exit state'+(' plan_artifact_acquisition_retry=1' if migrated_artifact_acquisition else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 21:
        st['send_guard_version']=21
        st['plan_artifact_acquisition_version']=3
        st['deterministic_artifact_worker_version']=1
        st.setdefault('plan_artifact_direct_worker_pending',{})
        migrated_direct=0
        # v2.26 removes Luna/OpenCode from physical artifact acquisition. If v2.25
        # already proved the newest immutable response is PLAN_READY but could not save
        # its visible .md, reopen exactly that source message for a deterministic Node
        # Playwright worker. Do not ask Sol for another plan and do not semantically
        # reinterpret the same settled response.
        last=st.get('last_semantic_event') or {}
        stage=str(st.get('failure_stage') or '')
        sid=str(last.get('source_message_id') or '').strip()
        if (str(st.get('phase'))=='FAILURE_ANALYSIS'
            and str(last.get('observation') or '')=='SETTLED'
            and str(last.get('semantic_event') or '')=='PLAN_READY'
            and sid
            and (stage in {'PLAN_ARTIFACT_REPAIR_REQUIRED','PLAN_ARTIFACT_BLOCKED_FINAL','PLAN_ARTIFACT_CORRECTIVE_REQUIRED','PLAN_ARTIFACT_WAIT_NEW_MESSAGE'}
                 or 'PLAN_ARTIFACT_NOT_DOWNLOADED' in str(st.get('plan_artifact_last_error') or ''))):
            cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            st.setdefault('plan_artifact_attempts',{})[cand_key]=0
            st['plan_artifact_last_error']=''
            st['plan_artifact_blocked_until_epoch']=0
            clear_wait_for_new_assistant(st)
            st['plan_artifact_direct_worker_pending']={
              'source_message_id':sid,'candidate_sha':str(st.get('candidate_sha') or ''),
              'scheduled_at':now(),'reason':'v2.26 deterministic artifact acquisition migration'
            }
            lkey='msg:'+sid.replace('msg:','')
            rec=(st.setdefault('settled_message_ledger',{})).get(lkey)
            if isinstance(rec,dict) and rec.get('terminal') and not rec.get('artifact_verified'):
                rec['terminal']=False
                rec['v226_reopened_for_deterministic_artifact_worker']=True
                rec['v226_reopened_at']=now()
            migrated_direct=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.26 migration: deterministic Node Playwright artifact worker; AI interprets, controller acquires/verifies bytes'+(' direct_artifact_retry=1' if migrated_direct else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 22:
        st['send_guard_version']=22
        st['plan_artifact_acquisition_version']=4
        st['deterministic_artifact_worker_version']=2
        st['artifact_turn_identity_version']=1
        st.setdefault('plan_artifact_locator_repairs',{})
        migrated_locator=0
        # v2.27 repairs the precise v2.26 failure mode: semantic source_message_id
        # may be an internal ChatGPT UUID and is not guaranteed to exist in DOM attrs.
        # Reopen the already-proven PLAN_READY response for ONE deterministic worker
        # pass that resolves physical turn identity by testid -> text hash -> turn index
        # -> latest assistant turn containing the downloadable plan artifact.
        last=st.get('last_semantic_event') or {}
        stage=str(st.get('failure_stage') or '')
        if (str(st.get('phase'))=='FAILURE_ANALYSIS'
            and str(last.get('observation') or '')=='SETTLED'
            and str(last.get('semantic_event') or '')=='PLAN_READY'
            and stage in {'PLAN_ARTIFACT_BLOCKED_FINAL','PLAN_ARTIFACT_REPAIR_REQUIRED'}):
            cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
            sid=str(last.get('source_message_id') or '').strip()
            locator={
              'source_message_id':sid,
              'source_turn_testid':str(last.get('source_turn_testid') or ''),
              'source_text_sha256':str(last.get('source_text_sha256') or ''),
              'source_turn_index':last.get('source_turn_index',-1),
              'candidate_sha':str(st.get('candidate_sha') or ''),
              'scheduled_at':now(),
              'reason':'v2.27 deterministic assistant-turn locator repair',
              'allow_latest_artifact_fallback':True,
            }
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            st.setdefault('plan_artifact_attempts',{})[cand_key]=0
            st['plan_artifact_last_error']=''
            st['plan_artifact_blocked_until_epoch']=0
            clear_wait_for_new_assistant(st)
            st['plan_artifact_direct_worker_pending']=locator
            st['plan_artifact_locator_repairs'][cand_key]={
              'scheduled_at':now(),'source_message_id':sid,'status':'PENDING'
            }
            migrated_locator=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.27 migration: deterministic assistant-turn identity repair + locator fallback; source message UUID is advisory, not a DOM locator'+(' locator_repair=1' if migrated_locator else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 23:
        st['send_guard_version']=23
        st['plan_artifact_acquisition_version']=5
        st['deterministic_artifact_worker_version']=3
        st['artifact_turn_identity_version']=2
        st['plan_artifact_dom_schema_version']=2
        st.setdefault('plan_artifact_dom_schema_repairs',{})
        migrated_dom_schema=0
        # v2.28 repairs the v2.27 structural failure where ChatGPT rendered the
        # downloadable plan but the current DOM no longer exposed
        # [data-message-author-role=assistant], producing turns:[]. Reopen only the
        # already-proven PLAN_READY response. The model is not called again; the
        # deterministic worker discovers physical turns from conversation-turn,
        # article, role, message-id, and artifact-control signals with diagnostics.
        last=st.get('last_semantic_event') or {}
        stage=str(st.get('failure_stage') or '')
        last_error=str(st.get('plan_artifact_last_error') or '')
        if (str(st.get('phase'))=='FAILURE_ANALYSIS'
            and str(last.get('observation') or '')=='SETTLED'
            and str(last.get('semantic_event') or '')=='PLAN_READY'
            and stage in {'PLAN_ARTIFACT_BLOCKED_FINAL','PLAN_ARTIFACT_REPAIR_REQUIRED'}
            and ('ASSISTANT_TURN_LOCATOR_FAILED' in last_error or 'PLAN_ARTIFACT_NOT_ACQUIRED' in last_error or stage=='PLAN_ARTIFACT_BLOCKED_FINAL')):
            cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
            sid=str(last.get('source_message_id') or '').strip()
            locator={
              'source_message_id':sid,
              'source_turn_testid':str(last.get('source_turn_testid') or ''),
              'source_text_sha256':str(last.get('source_text_sha256') or ''),
              'source_turn_index':last.get('source_turn_index',-1),
              'candidate_sha':str(st.get('candidate_sha') or ''),
              'scheduled_at':now(),
              'reason':'v2.28 DOM-schema-independent physical turn discovery repair',
              'allow_latest_artifact_fallback':True,
              'allow_dom_schema_independent_discovery':True,
            }
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            st.setdefault('plan_artifact_attempts',{})[cand_key]=0
            st['plan_artifact_last_error']=''
            st['plan_artifact_blocked_until_epoch']=0
            clear_wait_for_new_assistant(st)
            st['plan_artifact_direct_worker_pending']=locator
            st['plan_artifact_dom_schema_repairs'][cand_key]={
              'scheduled_at':now(),'source_message_id':sid,'status':'PENDING',
              'reason':'v2.27 turns-empty DOM schema repair'
            }
            migrated_dom_schema=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.28 migration: DOM-schema-independent turn discovery + multi-signal assistant/artifact classification + structural DOM diagnostics'+(' dom_schema_repair=1' if migrated_dom_schema else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 24:
        st['send_guard_version']=24
        st['plan_artifact_acquisition_version']=6
        st['deterministic_artifact_worker_version']=4
        st['plan_artifact_network_capture_version']=1
        st.setdefault('plan_artifact_network_repairs',{})
        migrated_network=0
        # v2.29 repairs the v2.28 failure where the correct physical turn/control was
        # found, but a 539-byte metadata/preview response was accepted repeatedly as
        # the artifact candidate. Reopen the already-proven PLAN_READY response only
        # for deterministic multi-response capture. The worker validates every body
        # against the controller's plan contract, follows metadata pointers, hashes
        # rejected candidates, and limits visible preview interactions.
        last=st.get('last_semantic_event') or {}
        stage=str(st.get('failure_stage') or '')
        last_error=str(st.get('plan_artifact_last_error') or '')
        if (str(st.get('phase'))=='FAILURE_ANALYSIS'
            and str(last.get('observation') or '')=='SETTLED'
            and str(last.get('semantic_event') or '')=='PLAN_READY'
            and stage in {'PLAN_ARTIFACT_BLOCKED_FINAL','PLAN_ARTIFACT_REPAIR_REQUIRED'}
            and ('PLAN_ARTIFACT_TOO_SHORT' in last_error or 'PLAN_ARTIFACT_NO_VALID_CANDIDATE' in last_error or stage=='PLAN_ARTIFACT_BLOCKED_FINAL')):
            cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
            sid=str(last.get('source_message_id') or '').strip()
            locator={
              'source_message_id':sid,
              'source_turn_testid':str(last.get('source_turn_testid') or ''),
              'source_text_sha256':str(last.get('source_text_sha256') or ''),
              'source_turn_index':last.get('source_turn_index',-1),
              'candidate_sha':str(st.get('candidate_sha') or ''),
              'scheduled_at':now(),
              'reason':'v2.29 strict multi-response artifact candidate repair',
              'allow_latest_artifact_fallback':True,
              'strict_candidate_validation':True,
              'follow_metadata_pointers':True,
              'rejected_candidate_hashing':True,
              'bounded_preview_interaction':True,
            }
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            st.setdefault('plan_artifact_attempts',{})[cand_key]=0
            st['plan_artifact_last_error']=''
            st['plan_artifact_blocked_until_epoch']=0
            clear_wait_for_new_assistant(st)
            st['plan_artifact_direct_worker_pending']=locator
            st['plan_artifact_network_repairs'][cand_key]={
              'scheduled_at':now(),'source_message_id':sid,'status':'PENDING',
              'reason':'v2.28 repeated 539-byte preview metadata candidate repair'
            }
            lkey='msg:'+sid.replace('msg:','') if sid else ''
            rec=(st.setdefault('settled_message_ledger',{})).get(lkey) if lkey else None
            if isinstance(rec,dict) and rec.get('terminal') and not rec.get('artifact_verified'):
                rec['terminal']=False
                rec['v229_reopened_for_network_candidate_repair']=True
                rec['v229_reopened_at']=now()
            migrated_network=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.29 migration: multi-response artifact candidate capture + strict content validation + metadata-pointer follow + rejected-candidate hashing + bounded preview interaction'+(' network_candidate_repair=1' if migrated_network else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 25:
        st['send_guard_version']=25
        st['plan_artifact_acquisition_version']=7
        st['deterministic_artifact_worker_version']=5
        st['plan_artifact_transport_version']=1
        st.setdefault('plan_artifact_transport_repairs',{})
        migrated_transport=0
        # v2.31 repairs the v2.29 state where the correct turn/control was found but
        # candidates=0/rejected=0/ui_clicks=2 proved that the visible UI interaction
        # did not expose an observable HTTP candidate. Recovery is now zero-click
        # first: full DOM metadata, already-open preview, performance resources and
        # blob/data/sandbox schemes are inspected before at most ONE UI interaction.
        last=st.get('last_semantic_event') or {}
        stage=str(st.get('failure_stage') or '')
        last_error=str(st.get('plan_artifact_last_error') or '')
        if (str(st.get('phase'))=='FAILURE_ANALYSIS'
            and str(last.get('observation') or '')=='SETTLED'
            and str(last.get('semantic_event') or '')=='PLAN_READY'
            and stage in {'PLAN_ARTIFACT_BLOCKED_FINAL','PLAN_ARTIFACT_REPAIR_REQUIRED'}
            and ('PLAN_ARTIFACT_NO_VALID_CANDIDATE' in last_error or stage=='PLAN_ARTIFACT_BLOCKED_FINAL')):
            cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
            sid=str(last.get('source_message_id') or '').strip()
            locator={
              'source_message_id':sid,
              'source_turn_testid':str(last.get('source_turn_testid') or ''),
              'source_text_sha256':str(last.get('source_text_sha256') or ''),
              'source_turn_index':last.get('source_turn_index',-1),
              'candidate_sha':str(st.get('candidate_sha') or ''),
              'scheduled_at':now(),
              'reason':'v2.31 zero-click artifact transport repair',
              'allow_latest_artifact_fallback':True,
              'zero_click_first':True,
              'inspect_existing_preview':True,
              'allow_blob_data_sandbox':True,
              'max_ui_clicks':1,
            }
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            st.setdefault('plan_artifact_attempts',{})[cand_key]=0
            st['plan_artifact_last_error']=''
            st['plan_artifact_blocked_until_epoch']=0
            clear_wait_for_new_assistant(st)
            st['plan_artifact_direct_worker_pending']=locator
            st['plan_artifact_transport_repairs'][cand_key]={
              'scheduled_at':now(),'source_message_id':sid,'status':'PENDING',
              'reason':'v2.29 candidates=0 artifact transport repair'
            }
            lkey='msg:'+sid.replace('msg:','') if sid else ''
            rec=(st.setdefault('settled_message_ledger',{})).get(lkey) if lkey else None
            if isinstance(rec,dict) and rec.get('terminal') and not rec.get('artifact_verified'):
                rec['terminal']=False
                rec['v230_reopened_for_zero_click_transport_repair']=True
                rec['v230_reopened_at']=now()
            migrated_transport=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.31 migration: zero-click DOM artifact discovery + full element metadata + existing-preview inspection + blob/data/sandbox handling + single-interaction fallback'+(' artifact_transport_repair=1' if migrated_transport else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 26:
        st['send_guard_version']=26
        st['deterministic_artifact_worker_version']=6
        st['plan_artifact_runtime_guard_version']=1
        st.setdefault('plan_artifact_runtime_repairs',{})
        migrated_runtime=0
        # v2.31 repairs the v2.30 regression where shouldObserveResponse was
        # referenced by the deterministic worker but not defined. The saved run is
        # reopened exactly once at the physical artifact lane: no new plan request,
        # no semantic reinspection, and no CI restart.
        last=st.get('last_semantic_event') or {}
        stage=str(st.get('failure_stage') or '')
        last_error=str(st.get('plan_artifact_last_error') or '')
        runtime_signature=any(x in last_error for x in (
            'ARTIFACT_WORKER_JSON_MISSING','ARTIFACT_WORKER_RUNTIME_CRASH',
            'shouldObserveResponse is not defined','ReferenceError:'
        ))
        if (str(st.get('phase'))=='FAILURE_ANALYSIS'
            and str(last.get('observation') or '')=='SETTLED'
            and str(last.get('semantic_event') or '')=='PLAN_READY'
            and stage in {'PLAN_ARTIFACT_BLOCKED_FINAL','PLAN_ARTIFACT_REPAIR_REQUIRED'}
            and (runtime_signature or stage=='PLAN_ARTIFACT_BLOCKED_FINAL')):
            cand_key=str(st.get('candidate_sha') or 'unknown')[:16]
            sid=str(last.get('source_message_id') or '').strip()
            locator={
              'source_message_id':sid,
              'source_turn_testid':str(last.get('source_turn_testid') or ''),
              'source_text_sha256':str(last.get('source_text_sha256') or ''),
              'source_turn_index':last.get('source_turn_index',-1),
              'candidate_sha':str(st.get('candidate_sha') or ''),
              'scheduled_at':now(),
              'reason':'v2.31 deterministic worker runtime repair',
              'allow_latest_artifact_fallback':True,
              'zero_click_first':True,
              'inspect_existing_preview':True,
              'allow_blob_data_sandbox':True,
              'max_ui_clicks':1,
            }
            st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
            st.setdefault('plan_artifact_attempts',{})[cand_key]=0
            st['plan_artifact_last_error']=''
            st['plan_artifact_blocked_until_epoch']=0
            clear_wait_for_new_assistant(st)
            st['plan_artifact_direct_worker_pending']=locator
            st['plan_artifact_runtime_repairs'][cand_key]={
              'scheduled_at':now(),'source_message_id':sid,'status':'PENDING',
              'reason':'v2.30 ReferenceError shouldObserveResponse runtime repair'
            }
            lkey='msg:'+sid.replace('msg:','') if sid else ''
            rec=(st.setdefault('settled_message_ledger',{})).get(lkey) if lkey else None
            if isinstance(rec,dict) and rec.get('terminal') and not rec.get('artifact_verified'):
                rec['terminal']=False
                rec['v231_reopened_for_worker_runtime_repair']=True
                rec['v231_reopened_at']=now()
            migrated_runtime=1
        cleared=reconcile_stale_secure_action_for_plan_stage(st)
        save_state(state_path,st)
        log('v2.31 migration: deterministic artifact worker runtime repair + executable response-observer contract + fail-fast runtime crash classification'+(' worker_runtime_repair=1' if migrated_runtime else '')+(' stale_secure_action_cleared=1' if cleared else ''))
    if int(st.get('send_guard_version',0) or 0) < 27:
        st['send_guard_version']=27
        st['chat_policy_guard_version']=1
        st.setdefault('chat_policy_audit',[])
        st.setdefault('chat_policy_last',{})
        st['chat_policy_required_surface']='chat'
        st['chat_policy_required_model']='GPT-5.6 Sol'
        st['chat_policy_required_reasoning']='High'
        save_state(state_path,st)
        log('v2.33 migration: deterministic model-selector proof fallback for Chat + GPT-5.6 Sol High')
    if int(st.get('send_guard_version',0) or 0) < 28:
        st['send_guard_version']=28
        st['fresh_chat_guard_version']=1
        st.setdefault('fresh_chat_bootstrap',{})
        save_state(state_path,st)
        log('v2.34 migration: split fresh-project-chat creation from plan delivery; historical /c/ reuse is fail-closed')
    if int(st.get('send_guard_version',0) or 0) < 29:
        st['send_guard_version']=29
        st['fresh_chat_protocol_version']=2
        save_state(state_path,st)
        log('v2.35 migration: dedicated raw fresh-project bootstrap protocol; generic AI_LOOP_EVENT parser removed from CREATE/SEND bootstrap')
    if int(st.get('send_guard_version',0) or 0) < 30:
        st['send_guard_version']=30
        st['chat_policy_protocol_version']=2
        save_state(state_path,st)
        log('v2.36 migration: dedicated raw Chat-policy protocol + multi-marker generic event parser hardening')
        log('v2.37 migration: current Projects Chat entrypoint + bounded fresh-chat creation retries')
        log('v2.38 migration: Playwright-tool-result fresh-bootstrap proof + transcript-wide schema recovery')
        log('v2.39 migration: hardened Chat-policy schema parsing; known v1 marker alias accepted without unsafe int conversion')
    if int(st.get('send_guard_version',0) or 0) < 31:
        st['send_guard_version']=31
        st['chat_policy_protocol_version']=3
        st['fresh_chat_protocol_version']=3
        st['fresh_chat_policy_decoupled']=True
        save_state(state_path,st)
        log('v2.40 migration: fresh-chat creation decoupled from model-policy proof + Playwright policy proof v2 + bounded protocol schema parsing')
    if int(st.get('adaptive_browser_version',0) or 0)<1:
        st['adaptive_browser_version']=1
        st.setdefault('adaptive_browser_diagnostics',[])
        st.setdefault('adaptive_bootstrap',{})
        save_state(state_path,st)
        log('v3.0 migration: adaptive DOM-guided ChatGPT navigator + deterministic browser verifier + browser-local idempotency ledger; model-generated browser JSON retired')
    if int(st.get('adaptive_browser_version',0) or 0)<2:
        st['adaptive_browser_version']=2
        st.setdefault('adaptive_browser_diagnostics',[])
        st.setdefault('adaptive_bootstrap',{})
        save_state(state_path,st)
        log('v3.1 migration: atomic send transaction + prior ambiguous-delivery recovery + no blind resend after possible send')
        log('v3.2 migration: new-loop fresh-chat isolation + prior-run ambiguity quarantine + re-entry duplicate-commit guard; same-run ambiguity recovery hardened with state/diagnostics + Chrome history')
    if int(st.get('adaptive_browser_version',0) or 0)<3:
        st['adaptive_browser_version']=3
        st['browser_bootstrap_transport']='direct-node-playwright-v4'
        st['browser_policy_transport']='direct-node-playwright-v4'
        save_state(state_path,st)
        log('v4.0 migration: model-free direct Node/Playwright bootstrap + direct policy guard; OpenCode transcript proof removed from create/attach/send path')
    if int(st.get('adaptive_browser_version',0) or 0)<4:
        st['adaptive_browser_version']=4
        st['browser_broker_version']=1
        st['browser_bootstrap_transport']='persistent-browser-broker-v1'
        st['browser_policy_transport']='persistent-browser-broker-v1'
        st['semantic_browser_authority']='controller-broker-only'
        save_state(state_path,st)
        log('v4.1 migration: persistent single-owner browser broker + semantic project resolver + text-only OpenCode reasoning + event-driven browser waits')
        log('v4.2 migration: historical-chat forced project-root re-entry + bounded fresh-chat strategy + hidden-anchor project mapping + broker regression hardening')
    log(f"ai-loopd-v3 version={VERSION} run={st['run_id']} phase={st['phase']} baseline={st['baseline_sha']}")
    direct_startup=st.get('plan_artifact_direct_worker_pending') if isinstance(st.get('plan_artifact_direct_worker_pending'),dict) else {}
    artifact_only_startup=(str(st.get('phase'))=='FAILURE_ANALYSIS' and str(st.get('failure_stage') or '')=='PLAN_ARTIFACT_REPAIR_REQUIRED' and bool(direct_startup))
    if artifact_only_startup:
        log('PLAYWRIGHT_CLI_CAPABILITY=DEFERRED reason=deterministic-artifact-only-recovery; OpenCode browser will not be started before worker')

    # v4 bootstrap is direct Node/Playwright: do not pay for an OpenCode/LLM capability turn before the first send.
    if args.bootstrap_plan and not st.get('chat_url'):
        plan=Path(args.bootstrap_plan).read_text()
        ev=start_new_chat(st['project_url'],st['run_id'],Path(args.bootstrap_plan).name,plan,st,state_path,plan_source_path=args.bootstrap_plan)
        st['chat_url']=ev.get('chat_url') or st['chat_url']; save_state(state_path,st)
    elif args.adopt_chat:
        st['chat_url']=args.adopt_chat; save_state(state_path,st)

    if not st.get('chat_url'):
        raise SystemExit('No chat_url')

    # Only the post-bootstrap loop needs OpenCode. Capability probing is intentionally deferred until now.
    if not artifact_only_startup:
        ensure_opencode_server()
        log('OPENCODE_SEMANTIC_CAPABILITY=PASS mode=text-only browser_tools=disabled-by-controller')
        ensure_chat_policy(st,state_path,st['chat_url'],'startup')

    pending_event=None
    failure_prompt_sent=False
    diagnosis_sent=False
    replan_sent=False

    while True:
        try:
            if reconcile_stale_secure_action_for_plan_stage(st):
                save_state(state_path,st)
                log(f"stale secure-action fence reconciled phase={st.get('phase')} failure_stage={st.get('failure_stage')}")

            # v2.24 immutable-settled semantic plan-artifact lane.
            # AI interprets unstructured text ONCE per new settled assistant response.
            # The deterministic controller owns effects/transitions. If a settled
            # response lacks a physically verifiable .md, send at most ONE corrective
            # request and then wait only for a NEW assistant message identity. Never
            # semantically reinterpret the same settled message after a timer.
            if is_plan_artifact_stage(st) and not has_pending_actions(st) and not st.get('secure_action_reissue_required'):
                stage=str(st.get('failure_stage') or '')
                key=str(st.get('candidate_sha') or 'unknown')[:16]

                if pending_event is not None:
                    pe=pending_event; pending_event=None
                    ds=str(pe.get('delivery_status') or '')
                    if ds in {'SENT','ALREADY_SENT'}:
                        log(f'plan-lane delivery proven stage={stage}; controller will inspect only new settled evidence')
                        time.sleep(15)
                        continue
                    if pe.get('state')=='RATE_LIMIT':
                        delay=register_rate_limit(st); save_state(state_path,st)
                        log(f'RATE_LIMIT during plan-lane delivery; retry_in={delay}s')
                        time.sleep(delay); continue
                    if pe.get('state')=='GENERATING':
                        delay=generating_delay(st); save_state(state_path,st)
                        log(f'ChatGPT still generating during plan-lane delivery; retry_in={delay}s')
                        time.sleep(delay); continue

                direct_pending=st.get('plan_artifact_direct_worker_pending') if isinstance(st.get('plan_artifact_direct_worker_pending'),dict) else {}
                direct_identity_present=bool(direct_pending and (
                    str(direct_pending.get('source_message_id') or '').strip()
                    or str(direct_pending.get('source_turn_testid') or '').strip()
                    or str(direct_pending.get('source_text_sha256') or '').strip()
                    or int(direct_pending.get('source_turn_index',-1) or -1) >= 0
                ))
                if direct_identity_present:
                    sid=str(direct_pending.get('source_message_id') or '').strip()
                    # This path is intentionally semantic-free: v2.25 already classified this
                    # exact immutable assistant message as PLAN_READY. v2.26 only acquires and
                    # verifies the visible .md bytes deterministically.
                    plan_filename=plan=plan_path=None
                    last_error=''
                    for n in range(1,PLAN_ARTIFACT_MAX_ATTEMPTS+1):
                        try:
                            plan_filename,plan,plan_path=materialize_downloadable_plan_artifact(st,state_path,sid,direct_pending)
                            break
                        except Exception as e:
                            last_error=str(e)
                            st['plan_artifact_last_error']=last_error
                            st.setdefault('plan_artifact_attempts',{})[key]=n
                            save_state(state_path,st)
                            log(f'DETERMINISTIC_ARTIFACT_WORKER attempt={n}/{PLAN_ARTIFACT_MAX_ATTEMPTS} source_message={sid} error={e}; semantic_calls=0')
                            deterministic_locator_failure=any(code in last_error for code in ('ASSISTANT_TURN_LOCATOR_FAILED','AMBIGUOUS_PLAN_TURN','SOURCE_ASSISTANT_MESSAGE_NOT_FOUND'))
                            deterministic_transport_failure=('PLAN_ARTIFACT_NO_VALID_CANDIDATE' in last_error)
                            deterministic_runtime_failure=any(code in last_error for code in ('ARTIFACT_WORKER_RUNTIME_CRASH','WORKER_EXCEPTION:','ReferenceError:','SyntaxError:','TypeError:'))
                            if deterministic_locator_failure:
                                log(f'DETERMINISTIC_ARTIFACT_WORKER locator failure is structural; external retry loop stopped after attempt={n}')
                                break
                            if deterministic_transport_failure:
                                log(f'DETERMINISTIC_ARTIFACT_WORKER artifact transport failure is structural; external retry loop stopped after attempt={n}')
                                break
                            if deterministic_runtime_failure:
                                log(f'DETERMINISTIC_ARTIFACT_WORKER runtime/code failure is structural; external retry loop stopped after attempt={n}')
                                break
                            if n < PLAN_ARTIFACT_MAX_ATTEMPTS:
                                time.sleep(min(30,10*n))
                    if not plan_path:
                        if isinstance(st.get('plan_artifact_locator_repairs'),dict):
                            rr=st['plan_artifact_locator_repairs'].get(key)
                            if isinstance(rr,dict): rr.update({'status':'FAILED','completed_at':now(),'error':last_error})
                        if isinstance(st.get('plan_artifact_dom_schema_repairs'),dict):
                            rr2=st['plan_artifact_dom_schema_repairs'].get(key)
                            if isinstance(rr2,dict): rr2.update({'status':'FAILED','completed_at':now(),'error':last_error})
                        if isinstance(st.get('plan_artifact_network_repairs'),dict):
                            rr3=st['plan_artifact_network_repairs'].get(key)
                            if isinstance(rr3,dict): rr3.update({'status':'FAILED','completed_at':now(),'error':last_error})
                        if isinstance(st.get('plan_artifact_transport_repairs'),dict):
                            rr4=st['plan_artifact_transport_repairs'].get(key)
                            if isinstance(rr4,dict): rr4.update({'status':'FAILED','completed_at':now(),'error':last_error})
                        st['plan_artifact_direct_worker_pending']={}
                        st['failure_stage']='PLAN_ARTIFACT_BLOCKED_FINAL'
                        st['plan_artifact_last_error']=last_error or 'DETERMINISTIC_ARTIFACT_WORKER_FAILED'
                        save_state(state_path,st)
                        log(f'PLAN_ARTIFACT_BLOCKED_FINAL deterministic artifact worker exhausted source_message={sid}; no new plan request, no semantic reinspection')
                        continue

                    last=st.get('last_semantic_event') or {}
                    sem_verified={
                      'observation':'SETTLED','semantic_event':'PLAN_READY',
                      'confidence':float(last.get('confidence',1.0) or 1.0),
                      'source_message_id':sid,
                      'source_turn_testid':str(direct_pending.get('source_turn_testid') or ''),
                      'source_text_sha256':str(direct_pending.get('source_text_sha256') or ''),
                      'source_turn_index':direct_pending.get('source_turn_index',-1),
                      'chat_url':str(st.get('chat_url') or ''),
                      'rationale':'controller verified downloadable .md bytes with deterministic artifact worker'
                    }
                    mark_settled_message_terminal(st,sem_verified,'downloadable .md physically verified by deterministic artifact worker',artifact_verified=True)
                    if isinstance(st.get('plan_artifact_locator_repairs'),dict):
                        rr=st['plan_artifact_locator_repairs'].get(key)
                        if isinstance(rr,dict): rr.update({'status':'PASS','completed_at':now()})
                    if isinstance(st.get('plan_artifact_dom_schema_repairs'),dict):
                        rr2=st['plan_artifact_dom_schema_repairs'].get(key)
                        if isinstance(rr2,dict): rr2.update({'status':'PASS','completed_at':now()})
                    if isinstance(st.get('plan_artifact_network_repairs'),dict):
                        rr3=st['plan_artifact_network_repairs'].get(key)
                        if isinstance(rr3,dict): rr3.update({'status':'PASS','completed_at':now()})
                    if isinstance(st.get('plan_artifact_transport_repairs'),dict):
                        rr4=st['plan_artifact_transport_repairs'].get(key)
                        if isinstance(rr4,dict): rr4.update({'status':'PASS','completed_at':now()})
                    st['plan_artifact_direct_worker_pending']={}
                    st['iteration']=int(st.get('iteration',0))+1
                    st['baseline_sha']=github_head(st['repo'],st['branch'])
                    st['candidate_sha']=None
                    st['phase']='IMPLEMENTING'; st['failure_stage']=''
                    st['secure_action_pending']=False; st['secure_action_reissue_required']=False; st['secure_action_reissue_ids']=[]
                    clear_wait_for_new_assistant(st)
                    # OpenCode/Playwright is needed again only now, after deterministic
                    # artifact acquisition has completed and closed its browser context.
                    ensure_opencode_server()
                    log('OPENCODE_SEMANTIC_CAPABILITY=PASS mode=text-only browser_tools=disabled-by-controller')
                    ev2=start_new_chat(st['project_url'],st['run_id'],plan_filename,plan,st,state_path,plan_source_path=plan_path)
                    st['chat_url']=ev2.get('chat_url') or st['chat_url']; st['followups']={}; st['proceeds']={}
                    save_state(state_path,st)
                    pending_event=ev2; failure_prompt_sent=diagnosis_sent=replan_sent=False
                    log(f"started new implementation chat from deterministic downloadable .md artifact iteration={st['iteration']} url={st['chat_url']}")
                    continue

                if stage=='PLAN_ARTIFACT_BLOCKED':
                    # Compatibility path for a state written after startup/migration.
                    # No 900s semantic reinspection: move directly to the one-shot repair.
                    st['failure_stage']='PLAN_ARTIFACT_CORRECTIVE_REQUIRED'
                    st['plan_artifact_blocked_until_epoch']=0
                    save_state(state_path,st)
                    log('PLAN_ARTIFACT_BLOCKED promoted to PLAN_ARTIFACT_CORRECTIVE_REQUIRED; same-message 900s semantic retry retired')
                    continue

                if stage=='PLAN_ARTIFACT_BLOCKED_FINAL':
                    # Terminal for this automated plan-artifact recovery. No browser/model
                    # polling occurs. A human or a later explicit state repair can resume.
                    log('PLAN_ARTIFACT_BLOCKED_FINAL; no semantic inference, no artifact retry, no ChatGPT message; controller sleeping')
                    time.sleep(max(300,PLAN_ARTIFACT_BLOCKED_RECHECK_SECONDS))
                    continue

                if stage=='PLAN_ARTIFACT_CORRECTIVE_REQUIRED':
                    last=st.get('last_semantic_event') or {}
                    baseline_key=''
                    # Always establish the corrective baseline with the SAME identity-only
                    # probe used later by WAIT_NEW_ASSISTANT_MESSAGE. This avoids false
                    # 'new message' detection if semantic/source ids and DOM/test ids use
                    # different formats.
                    try:
                        ident=inspect_response_identity(st,'plan-corrective-baseline-identity')
                    except Exception as e:
                        ident={}
                        log(f'plan corrective baseline identity probe unavailable error={e}; trying semantic source id fallback')
                    if ident.get('chat_url'): st['chat_url']=ident['chat_url']
                    if ident.get('observation')=='RATE_LIMIT':
                        delay=register_rate_limit(st); save_state(state_path,st); time.sleep(delay); continue
                    if ident:
                        clear_rate_limit(st)
                        if ident.get('observation')!='SETTLED':
                            delay=generating_delay(st); save_state(state_path,st)
                            log(f'plan corrective waits for a settled baseline observation={ident.get("observation")} retry_in={delay}s')
                            time.sleep(delay); continue
                        baseline_key=response_identity_key(ident)
                    if not baseline_key and str(last.get('observation') or '')=='SETTLED':
                        mid=str(last.get('source_message_id') or '').strip()
                        if mid: baseline_key='msg:'+mid
                    if not baseline_key:
                        log('plan corrective baseline has no stable message identity; refusing duplicate-prone send; retry_in=60s')
                        time.sleep(60); continue

                    # Exactly ONE corrective plan-artifact request is allowed per failed
                    # candidate/replan cycle. A new assistant response that still fails the
                    # artifact contract cannot trigger an endless chain of corrective asks.
                    candidate_corr=st.setdefault('plan_artifact_corrective_candidate_requests',{})
                    if int(candidate_corr.get(key,0) or 0) >= 1:
                        st['failure_stage']='PLAN_ARTIFACT_BLOCKED_FINAL'
                        st['plan_artifact_last_error']='CORRECTIVE_REQUEST_ALREADY_USED_FOR_CANDIDATE:'+key
                        save_state(state_path,st)
                        log(f'PLAN_ARTIFACT_BLOCKED_FINAL candidate={key}; single corrective request already consumed; no further ChatGPT messages or semantic polling')
                        continue
                    corr=st.setdefault('plan_artifact_corrective_requests',{})
                    if int(corr.get(baseline_key,0) or 0) >= 1:
                        begin_wait_for_new_assistant(st,baseline_key,'plan-artifact-corrective')
                        st['failure_stage']='PLAN_ARTIFACT_WAIT_NEW_MESSAGE'
                        save_state(state_path,st)
                        log(f'corrective plan-artifact request already sent for immutable response={baseline_key}; waiting for NEW assistant message')
                        continue

                    # Record current settled evidence as terminal before sending. The same
                    # response can never be reinterpreted to cause another transition.
                    if str(last.get('observation') or '')=='SETTLED':
                        sem_last={
                            'observation':'SETTLED',
                            'semantic_event':str(last.get('semantic_event') or 'PLAN_ARTIFACT_MISSING'),
                            'confidence':float(last.get('confidence',1.0) or 1.0),
                            'source_message_id':str(last.get('source_message_id') or ''),
                            'chat_url':str(st.get('chat_url') or ''),
                            'rationale':str(last.get('rationale') or ''),
                        }
                        mark_settled_message_terminal(st,sem_last,'corrective .md request required')
                    did='plan-artifact-corrective-v224-'+hashlib.sha256(baseline_key.encode()).hexdigest()[:16]
                    evcorr=guarded_send(st,state_path,plan_artifact_request_message(),'plan-artifact-corrective-v224',delivery_id=did)
                    if str(evcorr.get('delivery_status') or '') not in {'SENT','ALREADY_SENT'}:
                        log('corrective plan-artifact request not proven; guarded_send will retry before state transition')
                        continue
                    corr[baseline_key]=1
                    candidate_corr[key]=int(candidate_corr.get(key,0) or 0)+1
                    begin_wait_for_new_assistant(st,baseline_key,'plan-artifact-corrective')
                    st['failure_stage']='PLAN_ARTIFACT_WAIT_NEW_MESSAGE'
                    st['plan_artifact_last_error']='WAITING_FOR_NEW_ASSISTANT_MESSAGE_AFTER_CORRECTIVE'
                    save_state(state_path,st)
                    log(f'plan artifact corrective request sent exactly once immutable_response={baseline_key}; WAIT_NEW_ASSISTANT_MESSAGE')
                    continue

                if stage=='PLAN_ARTIFACT_WAIT_NEW_MESSAGE':
                    w=st.get('wait_new_assistant_message') if isinstance(st.get('wait_new_assistant_message'),dict) else {}
                    after_key=str(w.get('after_identity_key') or '')
                    if not w.get('active') or not after_key:
                        st['failure_stage']='PLAN_ARTIFACT_CORRECTIVE_REQUIRED'
                        save_state(state_path,st)
                        log('WAIT_NEW_ASSISTANT_MESSAGE state lacked baseline identity; returning to one-shot corrective setup')
                        continue
                    try:
                        ident=inspect_response_identity(st,'wait-new-assistant-message')
                    except Exception as e:
                        delay=new_message_poll_delay(st); save_state(state_path,st)
                        log(f'WAIT_NEW_ASSISTANT_MESSAGE identity probe failed error={e}; no semantic inference; retry_in={delay}s')
                        time.sleep(delay); continue
                    if ident.get('chat_url'): st['chat_url']=ident['chat_url']
                    obs=str(ident.get('observation') or '')
                    if obs=='RATE_LIMIT':
                        delay=register_rate_limit(st); save_state(state_path,st)
                        log(f'WAIT_NEW_ASSISTANT_MESSAGE rate-limited; retry_in={delay}s')
                        time.sleep(delay); continue
                    clear_rate_limit(st)
                    current_key=response_identity_key(ident)
                    w['last_probe_at']=now(); w['last_seen_identity_key']=current_key
                    if obs in {'GENERATING','NO_ASSISTANT'}:
                        delay=new_message_poll_delay(st); save_state(state_path,st)
                        log(f'WAIT_NEW_ASSISTANT_MESSAGE observation={obs}; no semantic inference; retry_in={delay}s')
                        time.sleep(delay); continue
                    if not current_key or current_key==after_key:
                        delay=new_message_poll_delay(st); save_state(state_path,st)
                        log(f'WAIT_NEW_ASSISTANT_MESSAGE same immutable response={after_key}; semantic_calls=0 artifact_retries=0 retry_in={delay}s')
                        time.sleep(delay); continue
                    # A genuinely new settled assistant response is new evidence. Only now
                    # may the semantic inspector run again.
                    clear_wait_for_new_assistant(st)
                    st['failure_stage']='PLAN_ARTIFACT_REPAIR_REQUIRED'
                    st.setdefault('plan_artifact_attempts',{})[key]=0
                    st['plan_artifact_last_error']=''
                    save_state(state_path,st)
                    log(f'NEW_ASSISTANT_MESSAGE detected old={after_key} new={current_key}; semantic inspection re-enabled once for new evidence')
                    stage='PLAN_ARTIFACT_REPAIR_REQUIRED'

                try:
                    sem=semantic_inspect(st,'semantic-plan-artifact')
                except Exception as e:
                    u=st.setdefault('semantic_unclassified',{})
                    k=hashlib.sha256(str(e).encode()).hexdigest()[:16]
                    u[k]={'at':now(),'phase':st.get('phase'),'failure_stage':stage,'error':str(e)[:1000]}
                    save_state(state_path,st)
                    log(f'semantic inspector unavailable in plan lane error={e}; no state transition; retry_in={SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS}s')
                    time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS); continue

                if sem.get('chat_url'): st['chat_url']=sem['chat_url']
                # SETTLED responses are immutable evidence. If this exact message has
                # already been terminally handled, never reinterpret it.
                if sem.get('observation')=='SETTLED' and settled_message_already_terminal(st,sem):
                    skey=semantic_source_identity_key(sem) or ('semfp:'+semantic_fingerprint(sem))
                    corr=st.setdefault('plan_artifact_corrective_requests',{})
                    if int(corr.get(skey,0) or 0) < 1:
                        st['failure_stage']='PLAN_ARTIFACT_CORRECTIVE_REQUIRED'
                        save_state(state_path,st)
                        log(f'SAME_SETTLED_EVIDENCE terminal={skey}; semantic transition suppressed; one corrective request remains')
                    else:
                        begin_wait_for_new_assistant(st,skey,'plan-artifact-corrective')
                        st['failure_stage']='PLAN_ARTIFACT_WAIT_NEW_MESSAGE'
                        save_state(state_path,st)
                        log(f'SAME_SETTLED_EVIDENCE terminal={skey}; semantic_calls_for_same_message=0 on subsequent loops; waiting for NEW assistant message')
                    continue

                allowed,reason=semantic_allowed(st,sem)
                sfp=record_semantic_observation(st,state_path,sem,allowed,reason)
                log(f"semantic event observation={sem.get('observation')} event={sem.get('semantic_event')} confidence={sem.get('confidence'):.2f} fp={sfp} phase={st.get('phase')} stage={stage}")
                if not allowed:
                    st.setdefault('semantic_unclassified',{})[sfp]={'at':now(),'reason':reason,'semantic':sem}
                    save_state(state_path,st)
                    log(f'{reason}; controller rejected proposed transition; retry_in={SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS}s')
                    time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS); continue

                if sem.get('observation')=='RATE_LIMIT':
                    delay=register_rate_limit(st); save_state(state_path,st)
                    log(f'RATE_LIMIT semantic observation in plan lane; retry_in={delay}s')
                    time.sleep(delay); continue
                clear_rate_limit(st)
                if sem.get('observation')=='GENERATING':
                    delay=generating_delay(st); save_state(state_path,st)
                    log(f'ChatGPT generating semantic observation in plan lane; retry_in={delay}s')
                    time.sleep(delay); continue
                reset_generating(st); save_state(state_path,st)

                sevent=str(sem.get('semantic_event') or '')
                if sevent=='HUMAN_BLOCKED':
                    mark_settled_message_terminal(st,sem,'semantic human-only dependency')
                    st['failure_stage']='PLAN_ARTIFACT_BLOCKED_FINAL'
                    st['plan_artifact_last_error']='SEMANTIC_HUMAN_BLOCKED:'+str(sem.get('rationale') or '')
                    save_state(state_path,st)
                    log('PLAN_ARTIFACT_BLOCKED_FINAL human/input dependency; no automated semantic polling')
                    continue

                if sevent=='OPERATOR_ACTION_REQUESTED':
                    try:
                        pending_event=extract_and_run_semantic_actions(st,state_path,repo_dir,sem)
                    except Exception as e:
                        st['secure_action_pending']=True
                        st['secure_action_last_error']=str(e); st['secure_action_last_error_at']=now()
                        save_state(state_path,st)
                        log(f'explicit semantic operator action could not be safely materialized; fenced error={e}')
                        time.sleep(30)
                    continue

                if sevent=='EVIDENCE_REQUESTED':
                    if one_transition_per_semantic_fingerprint(st,sfp,'request-exact-evidence-command'):
                        save_state(state_path,st)
                        msg=("The external operator is available. For any additional evidence still required before the plan, provide the exact read-only command(s) to execute now, with action id, target local/vps, timeout, and one unambiguous fenced shell block per action. Do not embed example/backlog commands as operator actions.")
                        pending_event=guarded_send(st,state_path,msg,'semantic-evidence-command-request',delivery_id='semantic-evidence-'+sfp)
                    else:
                        log(f'evidence request already handled for semantic fp={sfp}; waiting for a new response')
                        time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS)
                    continue

                if sevent=='PLAN_READY':
                    # One semantic classification, then bounded PHYSICAL download retries.
                    # No semantic reinspection occurs between these retries.
                    plan_filename=plan=plan_path=None
                    last_error=''
                    for n in range(1,PLAN_ARTIFACT_MAX_ATTEMPTS+1):
                        try:
                            plan_filename,plan,plan_path=materialize_downloadable_plan_artifact(st,state_path,sem.get('source_message_id',''),sem)
                            break
                        except Exception as e:
                            last_error=str(e)
                            st['plan_artifact_last_error']=last_error
                            st.setdefault('plan_artifact_attempts',{})[key]=n
                            save_state(state_path,st)
                            log(f'PLAN_READY physical artifact verification attempt={n}/{PLAN_ARTIFACT_MAX_ATTEMPTS} error={e}; semantic_reinspection=0')
                            if n < PLAN_ARTIFACT_MAX_ATTEMPTS:
                                time.sleep(min(60,15*n))
                    if not plan_path:
                        terminal_key=mark_settled_message_terminal(st,sem,'PLAN_READY but physical .md download verification failed: '+last_error)
                        st['failure_stage']='PLAN_ARTIFACT_CORRECTIVE_REQUIRED'
                        st['plan_artifact_last_error']=last_error
                        save_state(state_path,st)
                        log(f'PLAN_READY settled evidence terminalized={terminal_key}; physical artifact still missing after {PLAN_ARTIFACT_MAX_ATTEMPTS} retries; scheduling exactly one corrective request, no 900s semantic reinspection')
                        continue

                    terminal_key=mark_settled_message_terminal(st,sem,'downloadable .md physically verified',artifact_verified=True)
                    st['iteration']=int(st.get('iteration',0))+1
                    st['baseline_sha']=github_head(st['repo'],st['branch'])
                    st['candidate_sha']=None
                    st['phase']='IMPLEMENTING'; st['failure_stage']=''
                    st['secure_action_pending']=False; st['secure_action_reissue_required']=False; st['secure_action_reissue_ids']=[]
                    clear_wait_for_new_assistant(st)
                    ev2=start_new_chat(st['project_url'],st['run_id'],plan_filename,plan,st,state_path,plan_source_path=plan_path)
                    st['chat_url']=ev2.get('chat_url') or st['chat_url']; st['followups']={}; st['proceeds']={}
                    save_state(state_path,st)
                    pending_event=ev2
                    failure_prompt_sent=diagnosis_sent=replan_sent=False
                    log(f"started new implementation chat from one-shot semantic classification + controller-verified downloadable .md plan terminal={terminal_key} iteration={st['iteration']} url={st['chat_url']}")
                    continue

                if sevent in {'PLAN_INLINE_ONLY','PLAN_ARTIFACT_MISSING','NO_CHANGE'}:
                    terminal_key=mark_settled_message_terminal(st,sem,f'{sevent}: real downloadable .md absent')
                    st['failure_stage']='PLAN_ARTIFACT_CORRECTIVE_REQUIRED'
                    st['plan_artifact_last_error']='SEMANTIC_'+sevent
                    save_state(state_path,st)
                    log(f'{sevent} settled evidence terminalized={terminal_key}; scheduling exactly one corrective .md request; same message will never be semantically re-read')
                    continue

                log(f'plan semantic event {sevent} produced no allowed effect; no transition')
                time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS)
                continue

            # v2.15 recovery: recover SMALL action metadata from the already-issued
            # Sol action. Exact payload bytes are later saved DOM->browser-download->file.
            if st.get('secure_action_pending') and not st.get('secure_action_reissue_required') and not has_pending_actions(st) and pending_event is None:
                ids=st.get('secure_action_reissue_ids') or []
                if ids:
                    sem_recover=semantic_inspect(st,'recover-secure-action-text-only')
                    if sem_recover.get('observation')=='SETTLED' and sem_recover.get('semantic_event')=='OPERATOR_ACTION_REQUESTED':
                        pending_event=extract_and_run_semantic_actions(st,state_path,repo_dir,sem_recover)
                    else:
                        st['secure_action_reissue_required']=True
                        save_state(state_path,st)
                        log('secure action recovery could not prove a current action from text-only semantic inspection; scheduling reissue')

            # v2.11 migration fence: never execute a legacy/unverified action captured
            # through rendered text. Ask Sol once to reissue still-needed actions in
            # fenced code blocks; the browser transport will capture DOM textContent
            # and provide DOM-derived SHA256/length metadata before controller execution.
            if st.get('secure_action_reissue_required'):
                ids=', '.join(st.get('secure_action_reissue_ids') or []) or 'unknown'
                msg=("Transport-integrity upgrade: pending operator action payloads from the previous transport were quarantined because their byte-exact command integrity could not be proven. "
                     f"Quarantined action ids: {ids}. Do not rely on or repeat any malformed captured command. "
                     "Reissue each action that is still required, preserving its intent, as ONE unambiguous fenced shell code block per action, with action id, target (local or vps), and timeout stated outside the code block. "
                     "Do not ask the operator to reconstruct or manually repair command text. The external transport will read the fenced block directly from DOM textContent and verify its UTF-8 SHA256 before execution. "
                     "Continue from the evidence already present in this chat. Do not create a commit, push, or rerun Semaphore merely because of this transport reissue request.")
                did='secure-action-reissue-'+hashlib.sha256(ids.encode()).hexdigest()[:20]
                pe=guarded_send(st,state_path,msg,'secure-action-reissue',delivery_id=did)
                if pe.get('delivery_status') in {'SENT','ALREADY_SENT'}:
                    st['secure_action_reissue_required']=False
                    st['secure_action_pending']=True
                    st['secure_action_reissue_delivered_at']=now()
                    save_state(state_path,st)
                pending_event=pe
                continue

            # Durable operator work has absolute priority over browser continuation.
            # A restart cannot lose an action that Sol already issued.
            if has_pending_actions(st):
                log(f'pending operator actions detected count={len(st.get("pending_actions",{}))}; draining before any CONTINUE/followup')
                pe=drain_pending_actions(st,state_path,repo_dir)
                if pe is not None:
                    pending_event=pe
                continue

            # If this saved run already knows about an exact Semaphore failure but
            # v2.8 never collected browser evidence, collect/deliver it once now.
            last_ci=st.get('last_ci') if isinstance(st.get('last_ci'),dict) else {}
            if str(last_ci.get('status','')).upper()=='FAILURE' and str(last_ci.get('provider','')).lower()=='semaphore':
                sha0=str(last_ci.get('sha') or st.get('candidate_sha') or st.get('baseline_sha') or '')
                rid0=str(last_ci.get('run_id') or '')
                pid0=str(last_ci.get('pipeline_id') or '')
                if sha0 and rid0 and pid0:
                    ekey0=failure_identity_key('semaphore',sha0,rid0,pid0)
                    if not st.setdefault('failure_evidence_deliveries',{}).get(ekey0):
                        ekey0,epath0,eobj0=collect_semaphore_evidence(st,state_path,last_ci)
                        if eobj0.get('status')=='PASS':
                            lkey0,lpath0,lobj0=collect_local_failure_investigation(st,state_path,last_ci,eobj0,repo_dir)
                            if lobj0.get('status')=='PASS':
                                pending_event=send_failure_evidence_bundle(st,state_path,ekey0,eobj0,lobj0,'failure-recovery-evidence')
                                if pending_event is not None: continue
                            else:
                                log(f"Local failure investigation recovery not ready status={lobj0.get('status')} error={lobj0.get('error','')}"); time.sleep(60); continue
                        elif eobj0.get('status') in {'AUTH_REQUIRED','AUTH_REQUIRED_HUMAN'}:
                            log('SEMAPHORE_AUTH_REQUIRED_HUMAN: GitHub OAuth auto-recovery could not complete without human input; no ChatGPT message sent; diagnosis remains fenced'); time.sleep(300); continue
                        else:
                            log(f"Semaphore evidence recovery not ready status={eobj0.get('status')} error={eobj0.get('error','')}"); time.sleep(60); continue

            head=github_head(st['repo'],st['branch'])
            if st.get('candidate_sha') is None and head != st['baseline_sha']:
                st['candidate_sha']=head; st['phase']='WAIT_CI'; save_state(state_path,st)
                log(f'new candidate SHA {head}; entering WAIT_CI')

            if st['phase']=='WAIT_CI':
                sha=st['candidate_sha']; info=ci_status(sha); st['last_ci']=info; save_state(state_path,st)
                status=str(info.get('status','UNKNOWN')).upper()
                log(f"CI {status} provider={info.get('provider')} run={info.get('run_id')} sha={sha}")
                if status in ('PENDING','RUNNING','QUEUED','UNKNOWN',''):
                    time.sleep(POLL_CI); continue
                if status=='SUCCESS':
                    st['phase']='FINAL_REVIEW'; save_state(state_path,st)
                    msg=(f"Exact candidate CI is SUCCESS. candidate_sha={sha} provider={info.get('provider')} "
                         f"run_id={info.get('run_id')} pipeline_id={info.get('pipeline_id')}. "
                         "Perform the final review now. Do not create any additional commit. Explicitly declare GO only if the complete implementation is ready.")
                    pending_event=guarded_send(st,state_path,msg,'ci-success',delivery_id='ci-success-'+sha[:12])
                    continue
                st['phase']='FAILURE_ANALYSIS'; st['failure_stage']='EVIDENCE_COLLECTING'; save_state(state_path,st)
                failure_prompt_sent=True
                if str(info.get('provider','')).lower()=='semaphore':
                    ekey,epath,eobj=collect_semaphore_evidence(st,state_path,info)
                    if eobj.get('status')=='PASS':
                        lkey,lpath,lobj=collect_local_failure_investigation(st,state_path,info,eobj,repo_dir)
                        if lobj.get('status')!='PASS':
                            log(f"Local failure investigation status={lobj.get('status')} error={lobj.get('error','')}; diagnosis remains fenced"); time.sleep(60); continue
                        pending_event=send_failure_evidence_bundle(st,state_path,ekey,eobj,lobj)
                        if pending_event is None:
                            # Evidence was already delivered/proven. Do not fall back to
                            # the legacy unstructured classifier here; the next loop runs
                            # the semantic inspector and the deterministic FSM validates
                            # whatever transition it proposes.
                            log('failure evidence delivery already proven; semantic interpretation deferred to next settled-response inspection')
                            time.sleep(30)
                        continue
                    if eobj.get('status') in {'AUTH_REQUIRED','AUTH_REQUIRED_HUMAN'}:
                        log('SEMAPHORE_AUTH_REQUIRED_HUMAN: GitHub OAuth auto-recovery could not complete without human input; diagnosis remains fenced')
                        time.sleep(300); continue
                    log(f"Semaphore evidence collector status={eobj.get('status')} error={eobj.get('error','')}; diagnosis remains fenced")
                    time.sleep(60); continue
                st['failure_stage']='EVIDENCE_DELIVERED'; save_state(state_path,st)
                msg=(f"CI FAILURE for exact candidate SHA {sha}. Provider={info.get('provider')} run_id={info.get('run_id')} "
                     f"pipeline_id={info.get('pipeline_id')} raw_state={info.get('raw_state')} raw_result={info.get('raw_result')}. "
                     "Review this exact failure. Request any additional operator evidence with exact commands before diagnosis.")
                pending_event=guarded_send(st,state_path,msg,'ci-failure',delivery_id='ci-failure-'+sha[:12])
                continue

            # v2.23: PLAN_ARTIFACT_BLOCKED is not auto-promoted back to REQUESTED.
            # The semantic plan lane owns sparse read-only rechecks and never repeats a
            # message for the same response fingerprint.

            if pending_event is None:
                try:
                    sem=semantic_inspect(st,'semantic-inspect')
                except Exception as e:
                    u=st.setdefault('semantic_unclassified',{})
                    key=hashlib.sha256(str(e).encode()).hexdigest()[:16]
                    u[key]={'at':now(),'phase':st.get('phase'),'failure_stage':st.get('failure_stage',''),'error':str(e)[:1000]}
                    save_state(state_path,st)
                    log(f'semantic inspector could not classify latest unstructured response error={e}; no transition; retry_in={SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS}s')
                    time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS)
                    continue
                if sem.get('chat_url'): st['chat_url']=sem['chat_url']
                allowed,reason=semantic_allowed(st,sem)
                sfp=record_semantic_observation(st,state_path,sem,allowed,reason)
                log(f"semantic event observation={sem.get('observation')} event={sem.get('semantic_event')} confidence={sem.get('confidence'):.2f} fp={sfp} phase={st.get('phase')} stage={st.get('failure_stage','')}")
                if not allowed:
                    st.setdefault('semantic_unclassified',{})[sfp]={'at':now(),'reason':reason,'semantic':sem}
                    save_state(state_path,st)
                    log(f'{reason}; proposed transition rejected by deterministic FSM; retry_in={SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS}s')
                    time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS)
                    continue
                if sem.get('observation')=='SETTLED' and sem.get('semantic_event')=='OPERATOR_ACTION_REQUESTED':
                    try:
                        pending_event=extract_and_run_semantic_actions(st,state_path,repo_dir,sem)
                    except Exception as e:
                        st['secure_action_pending']=True
                        st['secure_action_last_error']=str(e); st['secure_action_last_error_at']=now()
                        save_state(state_path,st)
                        log(f'semantic explicit operator action extraction failed; execution fenced error={e}')
                        time.sleep(30)
                    if pending_event is None:
                        time.sleep(60)
                    continue
                if sem.get('observation')=='SETTLED' and sem.get('semantic_event')=='EVIDENCE_REQUESTED':
                    if one_transition_per_semantic_fingerprint(st,sfp,'request-exact-evidence-command'):
                        save_state(state_path,st)
                        msg=("The external operator is available. Provide the exact command(s) required for the additional evidence now, with action id, target local/vps, timeout, and one unambiguous fenced shell block per action. Do not provide examples or backlog pseudocode as actions.")
                        pending_event=guarded_send(st,state_path,msg,'semantic-evidence-command-request',delivery_id='semantic-evidence-'+sfp)
                    else:
                        log(f'evidence request already handled for semantic fp={sfp}; no repeated message')
                        time.sleep(60)
                    continue
                pending_event=semantic_to_event(sem)
            ev=pending_event; pending_event=None
            if ev.get('chat_url'): st['chat_url']=ev['chat_url']
            fp=event_fingerprint(ev)
            log(f"Sol event state={ev.get('state')} actions={len(ev.get('actions',[]))} fp={fp}")

            if ev.get('state')=='RATE_LIMIT':
                delay=register_rate_limit(st)
                save_state(state_path,st)
                log(f'RATE_LIMIT detected during inspection; no message will be sent; streak={st["rate_limit_streak"]} quiet cooldown={delay}s')
                time.sleep(delay); continue
            # Any non-rate-limited browser observation means the temporary ban cleared.
            clear_rate_limit(st)
            if ev.get('state')=='GENERATING':
                delay=generating_delay(st); save_state(state_path,st)
                log(f'ChatGPT still generating/unsettled; no message will be sent; inspect_again_in={delay}s')
                time.sleep(delay); continue
            reset_generating(st); save_state(state_path,st)
            # Delivery events only prove transport. They never authorize a state
            # transition from unstructured assistant content. The next loop runs the
            # semantic inspector on the completed assistant response.
            if ev.get('delivery_status') in {'SENT','ALREADY_SENT'} and not ev.get('semantic_event'):
                log(f"delivery-only event proven status={ev.get('delivery_status')}; semantic interpretation deferred to next settled response")
                time.sleep(30)
                continue
            if ev.get('state')=='ERROR':
                err=ev.get('error','')
                key=hashlib.sha256(err.encode()).hexdigest()[:16]
                te=st.setdefault('transport_errors',{})
                n=int(te.get(key,0))+1; te[key]=n; save_state(state_path,st)
                delay=min(120,15*(2**min(n-1,3)))
                log(f'operator transport ERROR attempt={n} retry_in={delay}s: '+err)
                if is_secure_action_transport_error(err):
                    st['secure_action_pending']=True
                    st['secure_action_reissue_required']=False
                    st['secure_action_last_error']=err
                    st['secure_action_last_error_at']=now()
                    save_state(state_path,st)
                    log('secure-action transport integrity failure fenced; v2.15 will recover metadata and materialize a verified DOM-download controller-owned file; no procede/followup')
                    continue
                time.sleep(delay); continue
            if ev.get('state')=='GO':
                sha=st.get('candidate_sha')
                if not sha: log('GO ignored: no candidate SHA'); time.sleep(10); continue
                head=github_head(st['repo'],st['branch']); ci=ci_status(sha)
                if head==sha and str(ci.get('status','')).upper()=='SUCCESS':
                    st['phase']='DONE'; st['go_confirmed']={'candidate_sha':sha,'declared_by':'GPT-5.6 Sol Web','chat_url':st['chat_url'],'observed_at':now()}
                    save_state(state_path,st)
                    (STATE_ROOT/'go_confirmed.json').write_text(json.dumps(st['go_confirmed'],indent=2))
                    log(f'DONE GO exact sha={sha}'); return
                log(f'GO not accepted: head={head} candidate={sha} ci={ci.get("status")}'); time.sleep(15); continue

            if ev.get('state')=='PLAN_READY':
                # v2.21: remediation plans in FAILURE_ANALYSIS are authoritative only as
                # downloadable .md artifacts. Inline/model-transcribed plan_markdown is ignored.
                if st.get('phase')=='FAILURE_ANALYSIS':
                    try:
                        plan_filename,plan,plan_path=materialize_downloadable_plan_artifact(st,state_path)
                    except Exception as e:
                        st['plan_artifact_last_error']=str(e); save_state(state_path,st)
                        log(f'PLAN_READY observed but downloadable .md artifact not ready: {e}')
                        # Continue into the bounded FAILURE_ANALYSIS artifact contract below.
                    else:
                        st['iteration']=int(st.get('iteration',0))+1
                        st['baseline_sha']=github_head(st['repo'],st['branch']); st['candidate_sha']=None; st['phase']='IMPLEMENTING'
                        ev2=start_new_chat(st['project_url'],st['run_id'],plan_filename,plan,st,state_path,plan_source_path=plan_path)
                        st['chat_url']=ev2.get('chat_url') or st['chat_url']; st['followups']={}; st['proceeds']={}; save_state(state_path,st)
                        pending_event=ev2; failure_prompt_sent=diagnosis_sent=replan_sent=False
                        log(f"started new implementation chat from downloadable plan artifact iteration={st['iteration']} url={st['chat_url']}")
                        continue
                else:
                    plan=ev.get('plan_markdown','')
                    plan_filename=ev.get('plan_filename','')
                    if not plan.strip():
                        try:
                            plan_filename,plan=materialize_latest_plan_from_dom(st,state_path)
                        except Exception as e:
                            st['plan_dom_last_error']=str(e); save_state(state_path,st)
                            log(f'plan DOM materialization not ready after PLAN_READY metadata-only response: {e}')
                            time.sleep(60); continue
                    st['iteration']=int(st.get('iteration',0))+1
                    st['baseline_sha']=github_head(st['repo'],st['branch']); st['candidate_sha']=None; st['phase']='IMPLEMENTING'
                    ev2=start_new_chat(st['project_url'],st['run_id'],plan_filename,plan,st,state_path)
                    st['chat_url']=ev2.get('chat_url') or st['chat_url']; st['followups']={}; st['proceeds']={}; save_state(state_path,st)
                    pending_event=ev2; failure_prompt_sent=diagnosis_sent=replan_sent=False
                    log(f"started new implementation chat iteration={st['iteration']} url={st['chat_url']}")
                    continue

            actions=ev.get('actions') or []
            if actions:
                st['secure_action_pending']=True; save_state(state_path,st)
                materialized=[]
                try:
                    for a in actions:
                        ok,_reason=verify_action_transport(a)
                        materialized.append(a if ok else materialize_action_payload(a,st['chat_url'],st['run_id']))
                except Exception as e:
                    err=str(e)
                    ah=st.setdefault('action_handoff_errors',{})
                    key=hashlib.sha256((fp+'\0'+err).encode()).hexdigest()[:20]
                    ah[key]={'error':err,'at':now(),'source_fp':fp}
                    st['secure_action_pending']=True
                    st['secure_action_reissue_required']=False
                    save_state(state_path,st)
                    log('action handoff not ready; execution fenced error='+err)
                    time.sleep(30)
                    continue
                st['secure_action_pending']=False
                st['secure_action_reissue_required']=False
                st['secure_action_last_verified_at']=now()
                save_state(state_path,st)
                register_pending_actions(st,state_path,materialized,fp)
                pending_event=drain_pending_actions(st,state_path,repo_dir)
                continue

            # No concrete operator actions. Re-check branch before any continuation/followup.
            head=github_head(st['repo'],st['branch'])
            if st.get('candidate_sha') is None and head != st['baseline_sha']:
                st['candidate_sha']=head; st['phase']='WAIT_CI'; save_state(state_path,st); continue

            # Sol sometimes finishes a turn by explicitly stating that it has another
            # internal implementation/validation/commit step to perform, but ChatGPT Web
            # waits for a user nudge before continuing. Treat that as a first-class state
            # and send exactly "procede" once for this Sol turn. This is intentionally
            # distinct from the generic no-commit followup.
            if ev.get('state')=='CONTINUE':
                # Hard invariant: transport-integrity recovery and operator evidence
                # always outrank CONTINUE. Never send procede while a secure action is
                # known to be required but has not yet been captured byte-exactly.
                if secure_action_fence_active(st):
                    log('CONTINUE fenced: secure action transport/result still pending; no procede will be sent')
                    sf=st.setdefault('secure_action_pending_followups',{})
                    if not sf.get(fp):
                        sf[fp]=1
                        if not (st.get('secure_action_reissue_ids') or []):
                            st['secure_action_reissue_required']=True
                        save_state(state_path,st)
                    time.sleep(15)
                    continue
                if has_pending_actions(st):
                    log('CONTINUE fenced: pending operator actions exist; no procede will be sent')
                    pending_event=drain_pending_actions(st,state_path,repo_dir)
                    continue
                proceeds=st.setdefault('proceeds',{})
                if int(proceeds.get(fp,0)) < 1:
                    log(f'auto-proceed Sol turn fp={fp}')
                    pe=guarded_send(st,state_path,'procede','auto-proceed',delivery_id='proceed-'+fp)
                    if pe.get('delivery_status') in {'SENT','ALREADY_SENT'}:
                        proceeds[fp]=1; save_state(state_path,st)
                    pending_event=pe
                    continue
                log(f'auto-proceed already delivered for turn {fp}; waiting for a new Sol turn')
                time.sleep(30)
                continue

            # A transport-corrupted/missing secure action is a hard dependency. Do not
            # fall through to the generic "what is missing" prompt, diagnosis, replan,
            # or final-review nudges. Ask once per settled Sol turn for the exact action
            # to be reissued, then wait.
            if secure_action_fence_active(st):
                sf=st.setdefault('secure_action_pending_followups',{})
                if not sf.get(fp):
                    sf[fp]=1
                    if not (st.get('secure_action_reissue_ids') or []):
                        st['secure_action_reissue_required']=True
                    save_state(state_path,st)
                    log(f'secure action pending on turn {fp}; read-only handoff recovery scheduled instead of generic followup')
                    continue
                log(f'secure action pending; handoff recovery already attempted for turn {fp}; waiting without spam')
                time.sleep(60)
                continue

            # Capability bridge takes precedence over diagnosis/replan/followups.
            # Sol's own ChatGPT runtime does not need to expose the terminal; it only
            # needs to specify exact commands for the external controller to execute.
            if ev.get('needs_operator_capabilities'):
                caps=st.setdefault('capability_deliveries',{})
                if int(caps.get(fp,0)) < 1:
                    caps[fp]=1; save_state(state_path,st)
                    p=prompt_file('operator_capabilities.txt',OPERATOR_CAPABILITIES_FALLBACK)
                    pending_event=guarded_send(st,state_path,p,'operator-capabilities',delivery_id='capabilities-'+fp)
                    continue
                log(f'operator capability bridge already delivered for turn {fp}; waiting for a new Sol turn')
                time.sleep(60)
                continue

            if st['phase']=='FAILURE_ANALYSIS':
                stage=st.get('failure_stage','EVIDENCE_DELIVERED')
                sevent=str(ev.get('semantic_event') or '')

                if sevent=='HUMAN_BLOCKED':
                    st['semantic_human_blocked']={'at':now(),'phase':st.get('phase'),'failure_stage':stage,'reason':ev.get('sol_text','')}
                    save_state(state_path,st)
                    log(f'semantic HUMAN_BLOCKED phase=FAILURE_ANALYSIS stage={stage}; no automated message/transition')
                    time.sleep(300)
                    continue

                if stage in ('EVIDENCE','EVIDENCE_COLLECTING','EVIDENCE_DELIVERED'):
                    if sevent=='DIAGNOSIS_READY':
                        p=prompt_file('replan.txt','/ralplan generate the best plan to cover and implement all points needed regarding the previous diagnosis. The main and mandatory objective is to pass the Semaphore job and reach COMPLETE_GO without any additional remediation commit. Do all deterministic tests needed before Semaphore so the unique implementation commit already contains everything required. The plan must specify team size, team roles and a backlog with atomic assigned tasks. MANDATORY OUTPUT CONTRACT: create the complete plan as a downloadable .md file with datetime in the filename. The downloadable .md attachment is the authoritative plan artifact. Do not provide the plan only as inline chat text.')
                        sfp=ev.get('semantic_source_message_id') or fp
                        if one_transition_per_semantic_fingerprint(st,str(sfp),'replan-after-diagnosis'):
                            st['failure_stage']='REPLAN_SENT'; save_state(state_path,st)
                            pending_event=guarded_send(st,state_path,p,'replan',delivery_id='replan-'+st['candidate_sha'][:12]); continue
                        log('diagnosis semantic event already consumed for replan transition; waiting for new response')
                        time.sleep(60); continue
                    if sevent in {'NO_CHANGE',''}:
                        purpose='diagnosis-request'
                        semid=ev.get('semantic_source_message_id') or fp
                        if one_transition_per_semantic_fingerprint(st,str(semid),purpose):
                            p=prompt_file('diagnosis.txt','/skillsbench the best diagnosis with the list of all granular causes of the last failure in .md file with datetime in filename')
                            st['failure_stage']='DIAGNOSIS_SENT'; save_state(state_path,st)
                            pending_event=guarded_send(st,state_path,p,'diagnosis',delivery_id='diagnosis-'+st['candidate_sha'][:12]); continue
                        log(f'evidence-stage semantic input already consumed fp={semid}; no repeated diagnosis request')
                        time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS); continue
                    log(f'failure evidence stage waiting on semantic event={sevent}; no transition')
                    time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS)
                    continue

                if stage=='DIAGNOSIS_SENT':
                    if sevent=='DIAGNOSIS_READY':
                        semid=ev.get('semantic_source_message_id') or fp
                        if one_transition_per_semantic_fingerprint(st,str(semid),'replan-after-diagnosis'):
                            p=prompt_file('replan.txt','/ralplan generate the best plan to cover and implement all points needed regarding the previous diagnosis. The main and mandatory objective is to pass the Semaphore job and reach COMPLETE_GO without any additional remediation commit. Do all deterministic tests needed before Semaphore so the unique implementation commit already contains everything required. The plan must specify team size, team roles and a backlog with atomic assigned tasks. MANDATORY OUTPUT CONTRACT: create the complete plan as a downloadable .md file with datetime in the filename. The downloadable .md attachment is the authoritative plan artifact. Do not provide the plan only as inline chat text.')
                            st['failure_stage']='REPLAN_SENT'; save_state(state_path,st)
                            pending_event=guarded_send(st,state_path,p,'replan',delivery_id='replan-'+st['candidate_sha'][:12]); continue
                        log('diagnosis already promoted to replan for this semantic response; waiting')
                        time.sleep(60); continue
                    log(f'DIAGNOSIS_SENT waiting for semantic DIAGNOSIS_READY; observed={sevent or "delivery/unknown"}; no blind replan')
                    time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS)
                    continue

                if stage in ('REPLAN_SENT','PLAN_TEXT_REQUESTED','PLAN_ARTIFACT_REQUESTED','PLAN_ARTIFACT_REPAIR_REQUIRED','PLAN_ARTIFACT_CORRECTIVE_REQUIRED','PLAN_ARTIFACT_WAIT_NEW_MESSAGE','PLAN_ARTIFACT_BLOCKED','PLAN_ARTIFACT_BLOCKED_FINAL'):
                    # This should normally be handled by the dedicated semantic plan lane
                    # at the top of the loop. Never fall back to generic plan/action logic.
                    log(f'plan-artifact stage reached generic tail stage={stage}; fenced and returned to dedicated semantic lane')
                    time.sleep(15)
                    continue

            if st['phase']=='FINAL_REVIEW':
                if ev.get('semantic_event')=='HUMAN_BLOCKED':
                    log('FINAL_REVIEW semantic HUMAN_BLOCKED; no automated followup')
                    time.sleep(300); continue
                semid=ev.get('semantic_source_message_id') or fp
                if one_transition_per_semantic_fingerprint(st,str(semid),'final-review-followup'):
                    save_state(state_path,st)
                    pending_event=guarded_send(st,state_path,'Continue the final review now and explicitly declare GO if the exact successful candidate is complete. Do not create any additional commit.','final-review-followup',delivery_id='final-review-'+st['candidate_sha'][:12])
                    continue
                log('final-review followup already sent for this semantic response; waiting for a new response')
                time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS); continue

            cnt=int(st['followups'].get(fp,0))
            if cnt < MAX_NO_ACTION_FOLLOWUPS:
                st['followups'][fp]=cnt+1; save_state(state_path,st)
                p=prompt_file('no_commit_followup.txt','Que hace falta para que hagas el commit con toda la implementacion completa?')
                pending_event=guarded_send(st,state_path,p,f'no-action-followup-{cnt+1}',delivery_id=f'followup-{fp}-{cnt+1}')
                continue

            log(f'No-action followup guard reached for turn {fp}; semantic backoff instead of re-inspecting every minute')
            time.sleep(SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS)

        except KeyboardInterrupt:
            log('stopped by operator'); return
        except Exception as e:
            log(f'ERROR {type(e).__name__}: {e}')
            time.sleep(15)

if __name__=='__main__': main()
