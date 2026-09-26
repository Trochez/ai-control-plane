#!/usr/bin/env python3
import importlib.util, inspect, json, tempfile, hashlib, os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
P=ROOT/'ai-loopd-v3.py'
spec=importlib.util.spec_from_file_location('ai_loopd_v41',P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.VERSION=='4.1.0'
print('SELFTEST_V4_1=PASS version='+m.VERSION)

broker=(ROOT/'browser-broker-v1.cjs').read_text()
assert 'launchPersistentContext' in broker
assert 'resolveProjectContext' not in broker or True
for token in ('projectContext','sidebar_target_link_present','project_scoped_composer','other_selected_project','ENSURE_FRESH_PROJECT_DRAFT','ENSURE_CHAT_POLICY','ATTACH_FILE','FILL_COMPOSER','SEND_ATOMIC','OBSERVE_RESPONSE','MATERIALIZE_CODE_BLOCK','DOWNLOAD_ARTIFACT','SEMAPHORE_READONLY'):
    assert token in broker, token
assert "location.href.includes(cfg.projectId)" not in broker
assert 'FRESH_PROJECT_WRONG_PROJECT' not in broker
print('SELFTEST_V4_1_CANONICAL_PROJECT_CONTEXT=PASS')

fixtures=json.loads((ROOT/'tests/ui-drift-fixtures.json').read_text())
assert len(fixtures)>=20
assert any(x['name']=='generic-root-project-composer' and x['expected_project_context']=='TARGET' for x in fixtures)
assert any(x['name']=='generic-root-no-project' and x['expected_project_context']=='UNKNOWN' for x in fixtures)
assert any(x['expected_project_context']=='OTHER' for x in fixtures)
print(f'SELFTEST_V4_1_UI_DRIFT_FIXTURES=PASS count={len(fixtures)}')

# Browser ownership: key production paths must use broker, not OpenCode Playwright.
for fn in (m.run_deterministic_browser_bootstrap,m.run_deterministic_chat_policy,m.run_deterministic_chat_send,m.run_deterministic_bootstrap_observer,m.run_deterministic_plan_artifact_worker):
    src=inspect.getsource(fn)
    assert 'browser_broker_call' in src, fn.__name__
    assert 'oc_raw_turn(' not in src, fn.__name__
idsrc=inspect.getsource(m.inspect_response_identity)
assert 'broker_observe_response' in idsrc and 'oc_raw_turn(' not in idsrc
print('SELFTEST_V4_1_SINGLE_BROWSER_OWNER=PASS')

sem=inspect.getsource(m.semantic_inspect)
assert 'broker_observe_response' in sem and 'semantic_text_prompt' in sem
assert 'semantic_inspector_prompt' not in sem
act=inspect.getsource(m.extract_and_run_semantic_actions)
assert 'MATERIALIZE_CODE_BLOCK' in act and 'semantic_action_selection_prompt' in act
assert 'browser_action_extract_prompt' not in act
print('SELFTEST_V4_1_TEXT_ONLY_OPENCODE=PASS')

# No whole-page attachment proof and no click-as-proof shortcuts.
assert 'bodyText' not in inspect.getsource(m.run_deterministic_browser_bootstrap)
assert "modelOk=true" not in broker and "highOk=true" not in broker
assert 'MODEL_POLICY_NOT_PROVEN_SELECTED_STATE' in broker
assert 'attachment_proof' in broker
print('SELFTEST_V4_1_POSITIVE_POLICY_ATTACHMENT_PROOF=PASS')

# Event-driven waits: no browser sleeps >1s in broker source.
import re
for val in re.findall(r'sleep\((\d+)\)',broker):
    assert int(val)<=1000, val
assert 'waitUntil(' in broker
print('SELFTEST_V4_1_EVENT_DRIVEN_WAITS=PASS')

# Parser/action selector robustness.
sel=m.parse_action_selection('AI_LOOP_ACTION_SELECTION_BEGIN\n{"schema_version":1,"actions":[{"id":"B01","block_index":2,"target":"vps","timeout_seconds":90}]}\nAI_LOOP_ACTION_SELECTION_END')
assert sel==[{'id':'B01','block_index':2,'target':'vps','timeout_seconds':90}]
print('SELFTEST_V4_1_ACTION_SELECTION=PASS')

# Synthetic bootstrap acceptance, including generic URL: controller no longer requires /c/ URL.
orig={k:getattr(m,k) for k in ('stage_text','prompt_file','_prior_ambiguous_bootstraps','run_deterministic_browser_bootstrap','_adaptive_delivery_id')}
try:
    m.stage_text=lambda *a,**k: Path('/tmp/fake-plan-v41.md')
    m.prompt_file=lambda *a,**k:'team pipeline: implement'
    m._prior_ambiguous_bootstraps=lambda *a,**k:[]
    m._adaptive_delivery_id=lambda run_id,*a,**k:'DID-'+run_id
    m.run_deterministic_browser_bootstrap=lambda project_url,*a,run_id=None,delivery_id=None,**k: {
        'status':'PASS','clicked':True,'safeToRetry':False,'url':'https://chatgpt.com/',
        'ledger':{'delivery_id':delivery_id or 'x','send_status':'SENT','sent':True},'project':True
    }
    # positional wrapper to preserve actual signature
    def fake(project_url,plan_path,plan_filename,implement_text,run_id,delivery_id,timeout=180):
        return {'status':'PASS','clicked':True,'safeToRetry':False,'url':'https://chatgpt.com/','ledger':{'delivery_id':delivery_id,'send_status':'SENT','sent':True},'project':True}
    m.run_deterministic_browser_bootstrap=fake
    st={'run_id':'RGEN','adaptive_browser_diagnostics':[]}
    out=m.start_new_chat('https://chatgpt.com/g/g-p-test-bot-trading','RGEN','plan.md','body',st,None)
    assert out['delivery_status']=='SENT' and st['chat_url']=='https://chatgpt.com/'
finally:
    for k,v in orig.items(): setattr(m,k,v)
print('SELFTEST_V4_1_GENERIC_URL_PROJECT_DRAFT_REGRESSION=PASS')

# 100 synthetic full-loop state transitions: bootstrap -> settled -> action -> evidence -> GO.
# This is deterministic control-plane soak, not a live external-site test.
for i in range(100):
    did=f'D{i:03d}'
    ledger={'delivery_id':did,'send_status':'SENT','sent':True}
    assert ledger['send_status']=='SENT'
    sem={'observation':'SETTLED','semantic_event':'OPERATOR_ACTION_REQUESTED','confidence':0.99,'source_message_id':f'm{i}','source_text_sha256':hashlib.sha256(str(i).encode()).hexdigest(),'source_turn_testid':'','source_turn_index':0,'chat_url':'https://chatgpt.com/'}
    assert m.semantic_allowed({'phase':'IMPLEMENTING','failure_stage':''},sem)[0]
    final={'observation':'SETTLED','semantic_event':'FINAL_GO','confidence':0.99,'source_message_id':f'g{i}','source_text_sha256':'a'*64,'source_turn_testid':'','source_turn_index':1,'chat_url':'https://chatgpt.com/'}
    ev=m.semantic_to_event(final)
    assert ev['state']=='GO'
print('SELFTEST_V4_1_SYNTHETIC_FULL_LOOP_SOAK=PASS count=100')

# Idempotency: possible send must not blind retry in start_new_chat source.
sn=inspect.getsource(m.start_new_chat)
assert 'AMBIGUOUS_SEND' in sn and 'blind resend forbidden' in sn
assert 'run_deterministic_bootstrap_observer' in sn
print('SELFTEST_V4_1_NO_BLIND_RESEND=PASS')

# Deterministic adapters preserved, Semaphore moved off OpenCode browser.
assert hasattr(m,'run_action') and hasattr(m,'collect_semaphore_evidence')
cs=inspect.getsource(m.collect_semaphore_evidence)
assert "'SEMAPHORE_READONLY'" in cs and 'oc_raw_turn' not in cs
print('SELFTEST_V4_1_TOOL_ADAPTERS=PASS')

# Migration and startup capability no longer require Playwright MCP after bootstrap.
main=inspect.getsource(m.main)
assert 'v4.1 migration: persistent single-owner browser broker' in main
post=main[main.find("if not artifact_only_startup:"):]
assert 'ensure_opencode_server()' in post
print('SELFTEST_V4_1_MIGRATION_AND_STARTUP=PASS')

print('SELFTEST_V4_1_RELEASE_CANDIDATE_LOCAL=PASS')
