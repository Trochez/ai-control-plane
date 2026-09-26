#!/usr/bin/env python3
import base64, hashlib, importlib.util, inspect, json, tempfile
from pathlib import Path

P=Path(__file__).with_name('ai-loopd-v3.py')
spec=importlib.util.spec_from_file_location('ai_loopd_v3',P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.VERSION=='4.0.0'
print('SELFTEST_V3=PASS version='+m.VERSION)

# Deterministic verifier parser: accepts only nonce-bound Playwright payload line.
obj={'url':'https://chatgpt.com/g/g-p-x/c/new','project':True,'surface':'CHAT','model':'GPT-5.6 Sol','reasoning':'High'}
tok=base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip('=')
line='noise\nAI_LOOP_BROWSER_OBS_V1|nonce=n123|payload='+tok+'\nmodel prose ignored'
assert m._parse_adaptive_payload_line(line,m.ADAPTIVE_OBS_PREFIX,'n123')==obj
try:
    m._parse_adaptive_payload_line(line,m.ADAPTIVE_OBS_PREFIX,'wrong')
    raise AssertionError('wrong nonce accepted')
except RuntimeError:
    pass
print('SELFTEST_V3_NONCE_BOUND_PLAYWRIGHT_PROOF=PASS')

# Model final prose/JSON is explicitly non-authoritative.
pp=m.adaptive_policy_prompt('https://chatgpt.com/g/g-p-x/c/y','nonce1')
for token in ('accessibility tree','semantic DOM','outerHTML','Your prose is ignored','LAST browser action','GPT-5.6 Sol','High'):
    assert token in pp, token
assert 'AI_LOOP_EVENT_BEGIN' not in pp
print('SELFTEST_V3_MODEL_PROSE_NOT_AUTHORITY=PASS')

# Bootstrap uses adaptive navigation but submission is owned by an atomic deterministic send transaction.
bp=m.adaptive_bootstrap_prompt('https://chatgpt.com/g/g-p-x','/tmp/p.md','p.md','team pipeline: implement','R1','deadbeef','np','ns','nt')
for token in ('goal-directed UI task','accessibility tree/DOM/ARIA/HTML','EMPTY draft','send_ready=true','STRICT SEND AUTHORITY','ONLY operation allowed to submit','ATOMIC SEND + PROOF','Add files'):
    assert token in bp, token
assert 'Work and Codex are forbidden' in bp
assert '[AI_LOOP_DELIVERY id=deadbeef]' in bp
assert 'NEVER click Send/Submit with playwright_browser_click' in bp
print('SELFTEST_V3_ADAPTIVE_BOOTSTRAP_PROMPT=PASS')

# Atomic transaction itself owns the only send click and proves the resulting user turn.
txjs=m._adaptive_send_transaction_js('n','https://chatgpt.com/g/g-p-x','d','plan.md','[AI_LOOP_DELIVERY id=d]\nhello')
for token in ('ledger.send_ready','PRESEND_NOT_READY','send_transaction_armed','await btn.click()','SEND_CLICKED_BUT_DELIVERY_NOT_PROVEN','AI_LOOP_BOOTSTRAP_','SENDTX_V1'):
    assert token in txjs, token
print('SELFTEST_V3_ATOMIC_SEND_TRANSACTION=PASS')

# Known v2.40 failure family is retired from active start flow.
src=inspect.getsource(m.start_new_chat)
for retired in ('fresh_project_oc_turn','fresh_project_chat_pass','parse_fresh_project_bootstrap_response','NEW_CHAT_POLICY_NOT_PROVEN','FRESH_BOOTSTRAP_JSON_INVALID'):
    assert retired not in src, retired
assert 'ADAPTIVE_BOOTSTRAP PASS' in src
assert 'ADAPTIVE_SEND_TX PASS' in src
assert 'AMBIGUOUS_SEND' in src
assert 'blind resend forbidden' in src
assert "'/c/' in _norm_chat_url(url)" in src
print('SELFTEST_V3_V240_UNVERIFIED_REGRESSION_RETIRED=PASS')

# Freshness does not depend on project URL prefix after creation; DOM project evidence + ledger + unique delivery marker are authoritative.
assert 'url.startswith(project_url' not in src
assert 'project_ok' in src and 'delivery_ok' in src and 'ledger_ok' in src
print('SELFTEST_V3_DOM_PROJECT_IDENTITY_NOT_URL_PREFIX=PASS')

# Deterministic browser-local ledger gates sending from an empty project draft only.
pre=m._adaptive_preflight_js('n','https://chatgpt.com/g/g-p-x','d')
pres=m._adaptive_presend_js('n2','d','plan.md','[AI_LOOP_DELIVERY id=d]\nhello')
for token in ('turns.length===0','GPT-5.6 Sol','reasoning','localStorage.setItem','ready'):
    assert token in pre, token
for token in ('ledger.ready','turns.length===0','markerOk','fileOk','send_ready'):
    assert token in pres, token
print('SELFTEST_V3_PRE_SEND_LEDGER_GATES=PASS')

# Observer carries semantic/ARIA evidence and compact HTML-like control evidence for adaptive diagnosis.
obsjs=m._adaptive_obs_js('n','https://chatgpt.com/g/g-p-x','d','plan.md','hello')
for token in ('aria-checked','aria-selected','data-state','relevantControls','htmlExcerpt','data-message-author-role'):
    assert token in obsjs, token
print('SELFTEST_V3_DOM_HTML_DIAGNOSTICS=PASS')

# Policy guard no longer parses schema_version/model-generated JSON.
polsrc=inspect.getsource(m.ensure_chat_policy)
assert 'parse_chat_policy_response' not in polsrc
assert '_parse_adaptive_payload_line' in polsrc
assert 'adaptive_policy_prompt' in polsrc
print('SELFTEST_V3_POLICY_SCHEMA_PARSER_RETIRED=PASS')

# v3.0 regression: if OpenCode clicked Send but omitted the final proof, blind retry is forbidden.
log_tail='''⚙ playwright_browser_type {"text":"[AI_LOOP_DELIVERY id=abc]\nteam pipeline"}\n⚙ playwright_browser_click {"element":"Send prompt button","target":"[data-testid=\"send-button\"]"}'''
assert m._adaptive_possible_send_in_transcript(log_tail,'abc')
assert not m._adaptive_possible_send_in_transcript('only inspected DOM; no composer mutation','abc')
print('SELFTEST_V3_V300_MISSING_FINAL_PROOF_NO_BLIND_RETRY=PASS')

# Prior failed runs of the same plan are recoverable before a new delivery id is created.
with tempfile.TemporaryDirectory() as td:
    old_state=m.STATE_ROOT
    m.STATE_ROOT=Path(td)
    try:
        diag=Path(td)/'diag.json'; diag.write_text(json.dumps({'transcript_tail':log_tail}))
        state={'run_id':'ROLD','adaptive_bootstrap':{'delivery_id':'abc','plan_filename':'plan.md','status':'FAILED','diag':str(diag)},'adaptive_browser_diagnostics':[str(diag)]}
        (Path(td)/'ROLD.v3.json').write_text(json.dumps(state))
        found=m._prior_ambiguous_bootstraps('plan.md','RNEW')
        assert found and found[0]['delivery_id']=='abc'
    finally:
        m.STATE_ROOT=old_state
print('SELFTEST_V3_PRIOR_AMBIGUOUS_DELIVERY_DISCOVERY=PASS')


# Deterministic recovery worker is read-only: it may navigate project chats but never type/upload/send.
worker=Path(__file__).with_name('playwright-bootstrap-observer.cjs').read_text()
for token in ('launchPersistentContext','data-message-author-role="user"','deliveryId','maxChats','candidateUrls','scanComplete:true','found:true','found:false'):
    assert token in worker, token
for forbidden in ('file_upload','send-button','getByRole(\'button\',{name:/send','contenteditable','keyboard.press'):
    assert forbidden not in worker, forbidden
assert hasattr(m,'run_deterministic_bootstrap_observer')
print('SELFTEST_V3_DETERMINISTIC_READONLY_RECOVERY_WORKER=PASS')

# Simulate a complete adaptive bootstrap without any browser/model structured output.
orig_stage_text=m.stage_text; orig_prompt_file=m.prompt_file; orig_raw=m.oc_raw_turn; orig_parse=m._parse_adaptive_payload_line; orig_policy=m.ensure_chat_policy; orig_sleep=m.time.sleep; orig_prior=m._prior_ambiguous_bootstraps
try:
    m.stage_text=lambda *a,**k: Path('/tmp/fake-plan-v3.md')
    m.prompt_file=lambda *a,**k: 'team pipeline: implement'
    m.oc_raw_turn=lambda *a,**k: 'raw transcript without JSON event'
    m._prior_ambiguous_bootstraps=lambda *a,**k: []
    def fake_parse(text,prefix,nonce):
        if prefix==m.ADAPTIVE_PREFLIGHT_PREFIX:
            return {'ready':True,'project':True,'empty':True,'surface':'CHAT','model':'GPT-5.6 Sol','reasoning':'High','ledger':{'ready':True,'delivery_id':'ignored'}}
        if prefix==m.ADAPTIVE_PRESEND_PREFIX:
            return {'send_ready':True,'empty':True,'marker_ok':True,'message_ok':True,'file_ok':True,'ledger':{'ready':True,'send_ready':True}}
        if prefix==m.ADAPTIVE_SENDTX_PREFIX:
            return {'status':'SENT','sent':True,'clicked':True,'url':'https://chatgpt.com/g/g-p-x/c/newv31','project':True,'delivery_present':True,'message_present':True,'ledger':{'ready':True,'send_ready':True,'sent':True,'delivery_id':'FIXED'},'error':''}
        raise AssertionError(prefix)
    m._parse_adaptive_payload_line=fake_parse
    m._adaptive_delivery_id=lambda *a,**k:'FIXED'
    m.ensure_chat_policy=lambda st,state_path,target_url,purpose='': {'state':'NO_ACTIONS','chat_url':target_url,'sol_text':'','needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':'NONE','ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'}
    st={'run_id':'RTEST3','rate_limit_streak':0,'adaptive_browser_diagnostics':[]}
    out=m.start_new_chat('https://chatgpt.com/g/g-p-x','RTEST3','plan.md','body',st,None)
    assert out['delivery_status']=='SENT' and out['chat_url'].endswith('/c/newv31')
    assert st['adaptive_bootstrap']['status']=='PLAN_SENT_VERIFIED'
finally:
    m.stage_text=orig_stage_text; m.prompt_file=orig_prompt_file; m.oc_raw_turn=orig_raw; m._parse_adaptive_payload_line=orig_parse; m.ensure_chat_policy=orig_policy; m.time.sleep=orig_sleep; m._prior_ambiguous_bootstraps=orig_prior
print('SELFTEST_V3_BOOTSTRAP_STATE_MACHINE=PASS')


# A possible send with missing SENDTX proof must recover read-only, never run bootstrap attempt 2.
orig_stage_text=m.stage_text; orig_prompt_file=m.prompt_file; orig_raw=m.oc_raw_turn; orig_parse=m._parse_adaptive_payload_line; orig_policy=m.ensure_chat_policy; orig_sleep=m.time.sleep; orig_prior=m._prior_ambiguous_bootstraps; orig_recover=m._recover_delivery_via_browser
try:
    m.stage_text=lambda *a,**k: Path('/tmp/fake-plan-v31-amb.md')
    m.prompt_file=lambda *a,**k: 'team pipeline: implement'
    m._adaptive_delivery_id=lambda *a,**k:'AMBID'
    m._prior_ambiguous_bootstraps=lambda *a,**k: []
    calls=[]
    def amb_raw(prompt,purpose):
        calls.append(purpose)
        return '⚙ playwright_browser_type {"text":"[AI_LOOP_DELIVERY id=AMBID] team pipeline"}\n⚙ playwright_browser_click {"element":"Send prompt button","target":"[data-testid=send-button]"}'
    m.oc_raw_turn=amb_raw
    m._parse_adaptive_payload_line=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('proof missing'))
    m._recover_delivery_via_browser=lambda *a,**k: ({'url':'https://chatgpt.com/g/g-p-x/c/recovered','project':True,'delivery_present':True},'recovery transcript')
    m.ensure_chat_policy=lambda st,state_path,target_url,purpose='': {'state':'NO_ACTIONS','chat_url':target_url,'sol_text':'','needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':'NONE','ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'}
    st={'run_id':'RAMB','rate_limit_streak':0,'adaptive_browser_diagnostics':[]}
    with tempfile.TemporaryDirectory() as td:
        old_root=m.RUNS_ROOT; m.RUNS_ROOT=Path(td)
        try:
            out=m.start_new_chat('https://chatgpt.com/g/g-p-x','RAMB','plan.md','body',st,None)
        finally:
            m.RUNS_ROOT=old_root
    assert out['delivery_status']=='ALREADY_SENT'
    assert calls==['start-plan-adaptive-bootstrap-attempt-1'], calls
    assert st['adaptive_bootstrap']['status']=='PLAN_SENT_VERIFIED_RECOVERED'
finally:
    m.stage_text=orig_stage_text; m.prompt_file=orig_prompt_file; m.oc_raw_turn=orig_raw; m._parse_adaptive_payload_line=orig_parse; m.ensure_chat_policy=orig_policy; m.time.sleep=orig_sleep; m._prior_ambiguous_bootstraps=orig_prior; m._recover_delivery_via_browser=orig_recover
print('SELFTEST_V3_AMBIGUOUS_SEND_RECOVERY_NO_RETRY=PASS')

# v3.2: deterministic negative reconciliation requires intact history + complete candidate scan + no sent ledger.
direct={'status':'PASS','found':False,'scanComplete':True,'visited':['https://chatgpt.com/g/g-p-x/c/a'],'ledger':{}}
hist={'ok':True,'urls':['https://chatgpt.com/g/g-p-x/c/a']}
assert m._negative_delivery_reconciliation(direct,hist,['https://chatgpt.com/g/g-p-x/c/a'])
assert not m._negative_delivery_reconciliation({**direct,'ledger':{'sent':True}},hist,['https://chatgpt.com/g/g-p-x/c/a'])
assert not m._negative_delivery_reconciliation(direct,{'ok':False,'urls':hist['urls']},hist['urls'])
assert not m._negative_delivery_reconciliation({**direct,'visited':[]},hist,hist['urls'])
print('SELFTEST_V3_NEGATIVE_DELIVERY_RECONCILIATION=PASS')

# Chrome history discovery is independent from project DOM links.
with tempfile.TemporaryDirectory() as td:
    old_profile=m.BROWSER_PROFILE
    m.BROWSER_PROFILE=Path(td)
    try:
        hp=Path(td)/'Default'; hp.mkdir(parents=True)
        import sqlite3
        con=sqlite3.connect(str(hp/'History'))
        con.execute('CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT, visit_count INTEGER, typed_count INTEGER, last_visit_time INTEGER, hidden INTEGER)')
        con.execute('INSERT INTO urls(url,title,visit_count,typed_count,last_visit_time,hidden) VALUES(?,?,?,?,?,?)',('https://chatgpt.com/g/g-p-x/c/history-chat','x',1,0,123,0))
        con.commit(); con.close()
        hm=m._chrome_history_project_chat_urls('https://chatgpt.com/g/g-p-x')
        assert hm['ok'] and 'https://chatgpt.com/g/g-p-x/c/history-chat' in hm['urls']
    finally:
        m.BROWSER_PROFILE=old_profile
print('SELFTEST_V3_CHROME_HISTORY_CHAT_DISCOVERY=PASS')

# Failed-run state/diagnostics yield explicit candidate chat URLs even when live project DOM exposes zero links.
with tempfile.TemporaryDirectory() as td:
    sp=Path(td)/'old.v3.json'; dp=Path(td)/'diag.json'
    sp.write_text(json.dumps({'chat_url':'https://chatgpt.com/g/g-p-x/c/from-state'}))
    dp.write_text(json.dumps({'transcript_tail':'navigated https://chatgpt.com/g/g-p-x/c/from-diag'}))
    rec={'state_path':str(sp),'diag_paths':[str(dp)]}
    urls=m._prior_state_candidate_urls(rec,'https://chatgpt.com/g/g-p-x')
    assert 'https://chatgpt.com/g/g-p-x/c/from-state' in urls and 'https://chatgpt.com/g/g-p-x/c/from-diag' in urls
print('SELFTEST_V3_PRIOR_STATE_CHAT_URL_RECOVERY=PASS')

# A prior ambiguity that remains inconclusive after exhaustive reconciliation is quarantined,
# then the new delivery proceeds only with an explicit re-entry/no-duplicate-commit guard.
orig_stage_text=m.stage_text; orig_prompt_file=m.prompt_file; orig_prior=m._prior_ambiguous_bootstraps; orig_recover=m._recover_delivery_via_browser
orig_raw=m.oc_raw_turn; orig_parse=m._parse_adaptive_payload_line; orig_policy=m.ensure_chat_policy; orig_sleep=m.time.sleep; orig_candidates=m._prior_state_candidate_urls
try:
    m.stage_text=lambda *a,**k: Path('/tmp/fake-plan-v32-quarantine.md')
    m.prompt_file=lambda *a,**k: 'team pipeline: implement'
    with tempfile.TemporaryDirectory() as td:
        sp=Path(td)/'ROLD.v3.json'; sp.write_text(json.dumps({'run_id':'ROLD','adaptive_bootstrap':{'delivery_id':'OLDID','plan_filename':'plan.md','status':'AMBIGUOUS_SEND'}}))
        m._prior_ambiguous_bootstraps=lambda *a,**k:[{'run_id':'ROLD','delivery_id':'OLDID','status':'AMBIGUOUS_SEND','diag':'','diag_paths':[],'state_path':str(sp)}]
        m._prior_state_candidate_urls=lambda *a,**k:[]
        recovery_calls=[]
        m._recover_delivery_via_browser=lambda *a,**k: (recovery_calls.append((a,k)) or (_ for _ in ()).throw(RuntimeError('prior-run recovery must not be used by a new loop')))
        prompts=[]
        m.oc_raw_turn=lambda prompt,purpose: (prompts.append(prompt) or 'raw')
        m._adaptive_delivery_id=lambda *a,**k:'NEWID'
        def qparse(text,prefix,nonce):
            if prefix==m.ADAPTIVE_PREFLIGHT_PREFIX: return {'ready':True,'project':True,'empty':True,'surface':'CHAT','model':'GPT-5.6 Sol','reasoning':'High','ledger':{'ready':True}}
            if prefix==m.ADAPTIVE_PRESEND_PREFIX: return {'send_ready':True,'empty':True,'marker_ok':True,'message_ok':True,'file_ok':True,'ledger':{'ready':True,'send_ready':True}}
            if prefix==m.ADAPTIVE_SENDTX_PREFIX: return {'status':'SENT','sent':True,'clicked':True,'url':'https://chatgpt.com/g/g-p-x/c/new-v32','project':True,'delivery_present':True,'message_present':True,'ledger':{'sent':True,'delivery_id':'NEWID'},'error':''}
            raise AssertionError(prefix)
        m._parse_adaptive_payload_line=qparse
        m.ensure_chat_policy=lambda st,state_path,target_url,purpose='': {'state':'NO_ACTIONS','chat_url':target_url,'sol_text':'','needs_operator_capabilities':False,'actions':[],'plan_filename':'','plan_markdown':'','error':'','delivery_status':'NONE','ui_surface':'CHAT','ui_model':'GPT-5.6 Sol','ui_reasoning':'High','chat_policy_status':'PASS'}
        m.time.sleep=lambda *_:None
        st={'run_id':'RNEW','adaptive_browser_diagnostics':[]}
        out=m.start_new_chat('https://chatgpt.com/g/g-p-x','RNEW','plan.md','body',st,None)
        assert out['delivery_status']=='SENT'
        assert st.get('prior_delivery_quarantine') and st['prior_delivery_quarantine'][0]['delivery_id']=='OLDID'
        assert any('AI_LOOP_REENTRY_GUARD' in q and 'DO NOT create, amend, revert, cherry-pick, or push a duplicate commit' in q for q in prompts)
        assert recovery_calls==[], recovery_calls
        old=json.loads(sp.read_text()); assert old['adaptive_bootstrap']['status']=='AMBIGUITY_QUARANTINED'
        assert old['adaptive_bootstrap']['ambiguity_resolution']['resolution']=='QUARANTINED_NEW_LOOP_FRESH_CHAT_REQUIRED'
finally:
    m.stage_text=orig_stage_text; m.prompt_file=orig_prompt_file; m._prior_ambiguous_bootstraps=orig_prior; m._recover_delivery_via_browser=orig_recover
    m.oc_raw_turn=orig_raw; m._parse_adaptive_payload_line=orig_parse; m.ensure_chat_policy=orig_policy; m.time.sleep=orig_sleep; m._prior_state_candidate_urls=orig_candidates
print('SELFTEST_V3_NEW_LOOP_NEVER_ADOPTS_OLD_CHAT=PASS')

# Failure diagnostics persist controller-owned evidence, rather than relying on model summary.
with tempfile.TemporaryDirectory() as td:
    old=m.RUNS_ROOT; m.RUNS_ROOT=Path(td)
    try:
        st={'run_id':'RDIAG','adaptive_browser_diagnostics':[]}
        path=m._persist_browser_diag(st,'test',{'x':1},'transcript')
        assert Path(path).is_file() and json.loads(Path(path).read_text())['observation']['x']==1
    finally:
        m.RUNS_ROOT=old
print('SELFTEST_V3_BROWSER_DIAGNOSTIC_ARTIFACT=PASS')

main_src=inspect.getsource(m.main)
assert 'v3.0 migration: adaptive DOM-guided ChatGPT navigator' in main_src
assert 'v3.1 migration: atomic send transaction' in main_src
assert 'v3.2 migration: new-loop fresh-chat isolation' in main_src
assert 'ai-loopd-v3 version=' in main_src
print('SELFTEST_V3_MIGRATION_AND_VERSION_LOG=PASS')

# Legacy action/file integrity architecture remains present.
for name in ('materialize_action_payload','run_action','plan_artifact_download_prompt'):
    assert hasattr(m,name), name
assert 'payload_transport' in m.EVENT_SCHEMA['properties']['actions']['items']['properties']
print('SELFTEST_V3_V2_CORE_PRESERVED=PASS')
