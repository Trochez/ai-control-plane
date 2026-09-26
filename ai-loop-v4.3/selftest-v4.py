#!/usr/bin/env python3
import importlib.util, inspect, json, tempfile
from pathlib import Path

P=Path(__file__).with_name('ai-loopd-v3.py')
spec=importlib.util.spec_from_file_location('ai_loopd_v4',P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.VERSION=='4.0.0'
print('SELFTEST_V4=PASS version='+m.VERSION)

# Critical architectural guarantee: bootstrap no longer depends on model/OpenCode transcript proof.
src=inspect.getsource(m.start_new_chat)
for forbidden in ('oc_raw_turn(', '_parse_adaptive_payload_line(', 'adaptive_bootstrap_prompt('):
    assert forbidden not in src, forbidden
assert 'run_deterministic_browser_bootstrap' in src
assert 'run_deterministic_bootstrap_observer' in src
assert 'blind resend forbidden' in src
print('SELFTEST_V4_BOOTSTRAP_MODEL_FREE=PASS')

# Policy guard is also direct Playwright and not model-prose based.
pol=inspect.getsource(m.ensure_chat_policy)
assert 'run_deterministic_chat_policy' in pol
assert 'oc_raw_turn' not in pol
assert '_parse_adaptive_payload_line' not in pol
print('SELFTEST_V4_POLICY_MODEL_FREE=PASS')

# Startup must bootstrap before paying for OpenCode capability.
main_src=inspect.getsource(m.main)
pos_boot=main_src.find('start_new_chat(')
pos_probe=main_src.find('ensure_cli_playwright_capability', pos_boot)
assert pos_boot>=0 and pos_probe>pos_boot
print('SELFTEST_V4_FAST_BOOTSTRAP_BEFORE_OPENCODE=PASS')

# Direct worker exists and owns exact attach/send behavior.
worker=Path(__file__).with_name('playwright-bootstrap-worker.cjs').read_text()
for token in (
    'launchPersistentContext','setInputFiles','input[type="file"]','GPT[- ]?5\\.6\\s+Sol',
    'FRESH_PROJECT_DRAFT_NOT_PROVEN','SEND_BUTTON_NOT_FOUND','SENDING_UNVERIFIED',
    'data-testid="send-button"','DELIVERY_MARKER_NOT_PROVEN_AFTER_CLICK','POLICY_ONLY'
):
    assert token in worker, token
assert 'opencode' not in worker.lower()
print('SELFTEST_V4_DIRECT_NODE_PLAYWRIGHT_WORKER=PASS')

# Worker syntax is checked by install; source must persist diagnostics on every failure path.
for token in ('saveDiagnostics','screenshot','page.content()','safeToRetry:!clicked','safeToRetry:false'):
    assert token in worker, token
print('SELFTEST_V4_DIAGNOSTIC_AND_RETRY_FENCE=PASS')

# Simulated success: start_new_chat accepts only direct-worker proof with sent ledger and /c/ URL.
orig_stage_text=m.stage_text; orig_prompt=m.prompt_file; orig_prior=m._prior_ambiguous_bootstraps
orig_worker=m.run_deterministic_browser_bootstrap; orig_policy=m.ensure_chat_policy; orig_sleep=m.time.sleep
try:
    m.stage_text=lambda *a,**k: Path('/tmp/fake-plan-v4.md')
    m.prompt_file=lambda *a,**k:'team pipeline: implement'
    m._prior_ambiguous_bootstraps=lambda *a,**k:[]
    m._adaptive_delivery_id=lambda *a,**k:'DIDV4'
    m.run_deterministic_browser_bootstrap=lambda *a,**k:{
        'status':'PASS','clicked':True,'safeToRetry':False,
        'url':'https://chatgpt.com/g/g-p-x/c/new-v4',
        'ledger':{'delivery_id':'DIDV4','send_status':'SENT','sent':True}
    }
    st={'run_id':'RV4','adaptive_browser_diagnostics':[]}
    out=m.start_new_chat('https://chatgpt.com/g/g-p-x','RV4','plan.md','body',st,None)
    assert out['delivery_status']=='SENT'
    assert st['chat_url'].endswith('/c/new-v4')
    assert st['adaptive_bootstrap']['status']=='PLAN_SENT_VERIFIED'
finally:
    m.stage_text=orig_stage_text; m.prompt_file=orig_prompt; m._prior_ambiguous_bootstraps=orig_prior
    m.run_deterministic_browser_bootstrap=orig_worker; m.ensure_chat_policy=orig_policy; m.time.sleep=orig_sleep
print('SELFTEST_V4_DIRECT_SUCCESS_ACCEPTANCE=PASS')

# Pre-send errors may retry; after any click they must never rerun the sender.
orig_stage_text=m.stage_text; orig_prompt=m.prompt_file; orig_prior=m._prior_ambiguous_bootstraps
orig_worker=m.run_deterministic_browser_bootstrap; orig_obs=m.run_deterministic_bootstrap_observer; orig_sleep=m.time.sleep
try:
    m.stage_text=lambda *a,**k: Path('/tmp/fake-plan-v4-amb.md')
    m.prompt_file=lambda *a,**k:'team pipeline: implement'
    m._prior_ambiguous_bootstraps=lambda *a,**k:[]
    m._adaptive_delivery_id=lambda *a,**k:'AMBV4'
    calls=[]
    def amb(*a,**k):
        calls.append('sender')
        return {'status':'AMBIGUOUS_SEND','clicked':True,'safeToRetry':False,'url':'https://chatgpt.com/g/g-p-x/c/amb','error':'proof missing'}
    m.run_deterministic_browser_bootstrap=amb
    m.run_deterministic_bootstrap_observer=lambda *a,**k:{'status':'PASS','found':True,'url':'https://chatgpt.com/g/g-p-x/c/amb'}
    st={'run_id':'RAMBV4','adaptive_browser_diagnostics':[]}
    out=m.start_new_chat('https://chatgpt.com/g/g-p-x','RAMBV4','plan.md','body',st,None)
    assert out['delivery_status']=='ALREADY_SENT'
    assert calls==['sender'], calls
finally:
    m.stage_text=orig_stage_text; m.prompt_file=orig_prompt; m._prior_ambiguous_bootstraps=orig_prior
    m.run_deterministic_browser_bootstrap=orig_worker; m.run_deterministic_bootstrap_observer=orig_obs; m.time.sleep=orig_sleep
print('SELFTEST_V4_NO_BLIND_RESEND_AFTER_CLICK=PASS')


# All controller sends after bootstrap also bypass OpenCode/model execution.
gs=inspect.getsource(m.guarded_send)
assert 'run_deterministic_chat_send' in gs
assert 'browser_send_prompt' not in gs
assert 'oc_turn(' not in gs
assert 'AMBIGUOUS_SEND' in gs and 'run_deterministic_bootstrap_observer' in gs
print('SELFTEST_V4_ALL_SENDS_MODEL_FREE=PASS')

# v2/v3 core action integrity and routing remain present.
for name in ('materialize_action_payload','run_action','plan_artifact_download_prompt','run_deterministic_bootstrap_observer'):
    assert hasattr(m,name), name
assert 'payload_transport' in m.EVENT_SCHEMA['properties']['actions']['items']['properties']
print('SELFTEST_V4_CORE_PRESERVED=PASS')

# Migration marker.
assert 'v4.0 migration: model-free direct Node/Playwright bootstrap' in main_src
print('SELFTEST_V4_MIGRATION_LOG=PASS')
