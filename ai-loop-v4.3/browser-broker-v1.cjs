#!/usr/bin/env node
'use strict';
const fs=require('fs');
const path=require('path');
const readline=require('readline');
const crypto=require('crypto');

function norm(s){return String(s||'').replace(/\s+/g,' ').trim();}
function low(s){return norm(s).toLowerCase();}
function sha(s){return crypto.createHash('sha256').update(Buffer.isBuffer(s)?s:Buffer.from(String(s||''),'utf8')).digest('hex');}
function classifySurfaceIdentity(observed={}){
  const work=observed.work===true||low(observed.surface)==='work';
  const codex=observed.codex===true||low(observed.surface)==='codex';
  const surface=low(observed.surface)||(work?'work':codex?'codex':'unknown');
  return {surface,work,codex,normalChat:surface==='chat'&&!work&&!codex};
}
function verifySurfaceTransition(before={},after={},expected={}){
  const b=classifySurfaceIdentity(before),a=classifySurfaceIdentity(after),reasons=[];
  if(expected.url&&String(after.url||'')!==String(expected.url))reasons.push('SURFACE_TRANSITION_URL_CHANGED');
  if(expected.conversationId&&String(after.conversationId||'')!==String(expected.conversationId))reasons.push('SURFACE_TRANSITION_CONVERSATION_CHANGED');
  if(expected.projectContext&&String(after.projectContext||'')!==String(expected.projectContext))reasons.push('SURFACE_TRANSITION_PROJECT_CHANGED');
  if(!a.normalChat)reasons.push('NORMAL_CHAT_SURFACE_NOT_PROVEN');
  return {pass:reasons.length===0,before:b,after:a,reasons};
}
function extractTurnProvenance(records=[],markers=[]){
  const ordered=records.filter(x=>x&&typeof x==='object'&&x.mainConversation!==false).map((x,i)=>({...x,index:Number.isInteger(x.index)?x.index:i})).sort((a,b)=>a.index-b.index);
  const targets=markers.map(String),out=[];
  for(const marker of targets){
    const hits=ordered.filter(x=>String(x.text||'').includes(marker));
    const user=hits.find(x=>x.role==='user');
    const reasons=[];
    if(hits.length!==1) reasons.push(hits.length?'MARKER_NOT_UNIQUE':'MARKER_NOT_FOUND');
    if(!user) reasons.push('MARKER_NOT_IN_MAIN_USER_MESSAGE');
    const following=user?ordered.find(x=>x.index>user.index&&x.role==='assistant'&&x.index<=(ordered.find(y=>y.index>user.index&&y.role==='user')?.index??Infinity)):null;
    if(!following) reasons.push('FOLLOWING_ASSISTANT_NOT_PROVEN');
    const record=x=>x?{role:String(x.role||''),message_id:String(x.message_id||''),turn_id:String(x.turn_id||''),testid:String(x.testid||''),index:x.index,text_sha256:sha(x.text||''),outerHTML_sha256:sha(x.outerHTML||''),main_conversation:x.mainConversation!==false}:null;
    if(user&&(!user.message_id||!user.turn_id||!user.testid)) reasons.push('OWNING_PROVENANCE_INCOMPLETE');
    if(following&&(!following.message_id||!following.turn_id||!following.testid)) reasons.push('FOLLOWING_ASSISTANT_PROVENANCE_INCOMPLETE');
    out.push({marker,proof:reasons.length===0,reasons,owner:record(user),following_assistant:record(following)});
  }
  return {markers:out,proof:out.length===targets.length&&out.every(x=>x.proof)};
}
function compareTurnProvenance(live={},historical={}){
  const mismatches=[];
  const fields=['role','message_id','turn_id','testid'];
  for(const marker of (live.markers||[])){
    const h=(historical.markers||[]).find(x=>x.marker===marker.marker);
    if(!h||!marker.owner||!h.owner){mismatches.push({marker:marker.marker,reason:'PROVENANCE_RECORD_MISSING'});continue;}
    for(const f of fields)if(String(marker.owner[f]||'')!==String(h.owner[f]||''))mismatches.push({marker:marker.marker,field:f,live:marker.owner[f]||'',historical:h.owner[f]||''});
  }
  return {pass:mismatches.length===0,mismatches};
}
function normalizeTurnInventory(input={}){
  const rawTurns=input.turns&&Array.isArray(input.turns.records)?input.turns.records:
    (Array.isArray(input.orderedTurns)?input.orderedTurns:(Array.isArray(input.turnRecords)?input.turnRecords:[]));
  const records=rawTurns.filter(x=>x&&typeof x==='object').map((x,i)=>({...x,index:Number.isInteger(x.index)?x.index:i}));
  records.sort((a,b)=>a.index-b.index);
  records.forEach((x,i)=>{x.index=i;});
  const deliveries=[];
  for(const user of records.filter(x=>x.role==='user')){
    const m=String(user.text||'').match(/\[AI_LOOP_DELIVERY id=([^\]]+)\]/);
    if(!m)continue;
    const next=records.slice(user.index+1).find(x=>x.role==='assistant'||x.role==='user');
    deliveries.push({delivery_id:m[1],user_turn_id:String(user.id||''),user_index:user.index,owner:{role:'user',message_id:String(user.message_id||''),turn_id:String(user.turn_id||''),testid:String(user.testid||''),text_sha256:sha(user.text||''),outerHTML_sha256:sha(user.outerHTML||''),main_conversation:user.mainConversation!==false},
     following_assistant:next&&next.role==='assistant'?{id:String(next.id||''),turn_id:String(next.turn_id||''),message_id:String(next.message_id||''),testid:String(next.testid||''),role:'assistant',text:String(next.text||''),index:next.index}:null,
      assistant_index:next&&next.role==='assistant'?next.index:null,next_turn_id:String(next?.id||''),next_turn_role:String(next?.role||'')});
  }
  const assistants=records.filter(x=>x.role==='assistant');
  return {turns:{user:records.filter(x=>x.role==='user').length,assistant:assistants.length,total:records.length,records},
    orderedTurns:records,turnRecords:records,latestAssistantTurn:assistants.length?assistants[assistants.length-1]:null,
    deliveryMatches:deliveries,deliveryReconciliation:deliveries};
}
function reconcileHistoricalDelivery(input={}){
  const deliveryId=String(input.deliveryId||'');
  const ledgerStatus=String(input.ledgerStatus||'');
  const evidence=input.evidence&&typeof input.evidence==='object'?input.evidence:{};
  const state=evidence.state&&typeof evidence.state==='object'?evidence.state:evidence;
  const authoritativeUrl=String(input.authoritativeUrl||'');
  const expectedProject=normProjectName(input.projectName||'');
  const reasons=[];
  if(!deliveryId) reasons.push('DELIVERY_ID_MISSING');
  if(!['SENDING','RECONCILED_SENT','SENT'].includes(ledgerStatus)) reasons.push('LEDGER_NOT_DELIVERY_STATE');
  if(authoritativeUrl && String(state.url||'')!==authoritativeUrl) reasons.push('HISTORICAL_URL_MISMATCH');
  if(expectedProject && String(state.projectContext||'')!=='TARGET') reasons.push('HISTORICAL_PROJECT_NOT_TARGET');
  const matches=[...(state.deliveryReconciliation||state.deliveryMatches||[])].filter(x=>String(x.delivery_id||'')===deliveryId);
  const match=matches[0];
  if(!match) reasons.push('IMMUTABLE_MARKER_NOT_PROVEN');
  if(match&&(!match.following_assistant||match.next_turn_role!=='assistant')) reasons.push('FOLLOWING_ASSISTANT_NOT_PROVEN');
  const assistant=match&&match.following_assistant;
  for(const field of ['id','turn_id','message_id','testid']) if(!assistant||!String(assistant[field]||'')) reasons.push(`ASSISTANT_${field.toUpperCase()}_MISSING`);
  if(!assistant||String(assistant.role||'')!=='assistant') reasons.push('ASSISTANT_ROLE_MISSING_OR_MISMATCH');
  const ok=reasons.length===0;
  return {delivery_id:deliveryId,delivery_status:ok?'RECONCILED_SENT':'DELIVERY_AMBIGUOUS',reconciliation_source:ok?'HISTORICAL_BROKER_DIAGNOSTIC':'NONE',resend_allowed:false,outbound_send_blocked:!ok,proof:ok,reasons};
}
function historicalImmutableProvenance(input={}){
  const evidence=input.evidence&&typeof input.evidence==='object'?input.evidence:{};
  const state=evidence.state&&typeof evidence.state==='object'?evidence.state:evidence;
  const markers=(input.markers||[]).map(String), expectedUrl=String(input.authoritativeUrl||''), expectedId=String(input.conversationId||'');
  const reasons=[], records=[];
  if(expectedUrl&&String(state.url||'')!==expectedUrl) reasons.push('HISTORICAL_URL_MISMATCH');
  if(expectedId&&String(state.conversationId||state.conversation_id||'')!==expectedId) reasons.push('HISTORICAL_CONVERSATION_ID_MISMATCH');
  for(const marker of markers){
    const hits=(state.markerProvenance||state.markers||state.deliveryReconciliation||[]).filter(x=>x&&String(x.marker||x.delivery_marker||x.text||'').includes(marker));
    if(hits.length!==1){ reasons.push(hits.length?'HISTORICAL_CONTRADICTORY_DUPLICATE':'HISTORICAL_MARKER_MISSING'); continue; }
    const x=hits[0], a=x.following_assistant||x.assistant||{};
    const artifact=x.artifact||state.artifact||{};
    const record={marker,conversation_id:String(x.conversationId||x.conversation_id||state.conversationId||state.conversation_id||''),owner:x.owner||x.owning_user||null,assistant:a,artifact_path:String(x.artifact_path||artifact.path||''),artifact_sha256:String(x.artifact_sha256||artifact.sha256||'')};
    if(!record.owner) reasons.push('HISTORICAL_OWNER_MISSING');
    if(!a||String(a.role||'')!=='assistant'||!a.message_id||!a.turn_id||!a.testid) reasons.push('HISTORICAL_ASSISTANT_PROVENANCE_INCOMPLETE');
    if(!record.artifact_path||!record.artifact_sha256) reasons.push('HISTORICAL_ARTIFACT_PROVENANCE_MISSING');
    records.push(record);
  }
  return {historical_immutable_provenance:reasons.length?'FAIL':'PASS',proof:!reasons.length,markers:records,reasons};
}
function renderedWitnessProof(input={}){
  const markers=(input.markers||[]).map(String), candidates=Array.isArray(input.candidates)?input.candidates:[], reasons=[], witnesses=[];
  for(const marker of markers){
    const all=candidates.filter(x=>String(x.marker||'')===marker), rendered=all.filter(x=>x.renderedMain===true);
    const accepted=rendered.filter(x=>x.visible===true&&x.inConversationRoot===true&&x.excluded!==true);
    const hidden=all.filter(x=>!accepted.includes(x));
    const record={marker,raw_dom_matches:all.length,hidden_or_script_matches:hidden.length,rendered_main_matches:accepted.length,witness:accepted.length===1?accepted[0]:null};
    witnesses.push(record);
    if(accepted.length!==1) reasons.push(accepted.length?'RENDERED_MAIN_MATCH_NOT_UNIQUE':'RENDERED_MAIN_MATCH_MISSING');
  }
  if(witnesses.length===2&&witnesses[0].witness&&witnesses[1].witness&&witnesses[0].witness.path===witnesses[1].witness.path) reasons.push('WITNESSES_NOT_INDEPENDENT');
  return {live_rendered_witness:reasons.length?'FAIL':'PASS',proof:!reasons.length,witnesses,reasons};
}
function rangeWitnessProof(input={}){
  const markers=(input.markers||[]).map(String), candidates=Array.isArray(input.candidates)?input.candidates:[], reasons=[], witnesses=[];
  const identity=x=>String(x.rangeIdentity||[x.startPath,x.startOffset,x.endPath,x.endOffset].join('|'));
  for(const marker of markers){
    const all=candidates.filter(x=>String(x.marker||'')===marker);
    const unique=new Map();
    for(const x of all){
      if(x.visible!==true||x.inConversationRoot!==true||x.excluded===true||x.positiveRect!==true)continue;
      const id=identity(x); if(!id||id==='|||')continue;
      if(!unique.has(id))unique.set(id,{...x,rangeIdentity:id});
    }
    const accepted=[...unique.values()];
    const record={marker,raw_dom_matches:all.length,unique_visible_ranges:accepted.length,witness:accepted.length===1?accepted[0]:null,ranges:accepted};
    witnesses.push(record);
    if(accepted.length!==1)reasons.push(accepted.length?'UNIQUE_VISIBLE_RANGE_NOT_UNIQUE':'UNIQUE_VISIBLE_RANGE_MISSING');
  }
  const failure=witnesses.find(x=>/failure-evidence/.test(x.marker)), diagnosis=witnesses.find(x=>/diagnosis/.test(x.marker));
  const order=failure&&diagnosis&&failure.witness&&diagnosis.witness&&Number.isFinite(failure.witness.documentOrder)&&Number.isFinite(diagnosis.witness.documentOrder)
    ? {failure_evidence_before_diagnosis:failure.witness.documentOrder<diagnosis.witness.documentOrder, failure_evidence:failure.witness.documentOrder, diagnosis:diagnosis.witness.documentOrder}:null;
  if(failure&&diagnosis&&(!order||!order.failure_evidence_before_diagnosis))reasons.push('RANGE_ORDER_INVALID');
  return {live_range_witness:reasons.length?'FAIL':'PASS',live_rendered_witness:reasons.length?'FAIL':'PASS',proof:!reasons.length,witnesses,range_order:order,reasons};
}
function dedupeRangeWitnesses(candidates=[],markers=[]){
  const out=[], reasons=[];
  for(const marker of markers.map(String)){
    const all=candidates.filter(x=>String(x.marker||'')===marker), unique=new Map();
    for(const x of all){
      if(x.visible!==true||x.inConversationRoot!==true||x.excluded===true||x.positiveRect!==true)continue;
      const id=String(x.rangeIdentity||[x.startPath,x.startOffset,x.endPath,x.endOffset].join('|'));
      if(id!=='|||')unique.set(id,{...x,rangeIdentity:id});
    }
    const ranges=[...unique.values()]; out.push({marker,raw_dom_matches:all.length,unique_visible_ranges:ranges.length,ranges});
    if(ranges.length!==1)reasons.push(ranges.length?'UNIQUE_VISIBLE_RANGE_NOT_UNIQUE':'UNIQUE_VISIBLE_RANGE_MISSING');
  }
  return {proof:!reasons.length,reasons,witnesses:out};
}
function crossSourceProvenance(input={}){
  const h=input.historical||{}, l=input.live||{}, markers=(input.markers||[]).map(String), reasons=[];
  if(h.historical_immutable_provenance!=='PASS') reasons.push('HISTORICAL_IMMUTABLE_PROVENANCE_NOT_PROVEN');
  if(l.live_range_witness!=='PASS'&&l.live_rendered_witness!=='PASS') reasons.push('LIVE_RANGE_WITNESS_NOT_PROVEN');
  if(String(input.historicalConversationId||'')!==String(input.liveConversationId||'')) reasons.push('CONVERSATION_ID_MISMATCH');
  const hm=(h.markers||[]).map(x=>x.marker).sort().join('|'), lm=(l.witnesses||[]).map(x=>x.marker).sort().join('|');
  if(hm!==markers.slice().sort().join('|')||lm!==markers.slice().sort().join('|')) reasons.push('MARKER_IDENTITY_MISMATCH');
  return {cross_source_provenance:reasons.length?'FAIL':'PASS',proof:!reasons.length,marker_equality:!reasons.includes('MARKER_IDENTITY_MISMATCH'),conversation_id_equality:!reasons.includes('CONVERSATION_ID_MISMATCH'),reasons};
}
function proveLiveConversation(input={}){
  const observed=input.observed&&typeof input.observed==='object'?input.observed:{};
  const expectedUrl=String(input.authoritativeUrl||'');
  const expectedId=String(input.conversationId||'');
  const reasons=[];
  if(!observed.activeAuthenticatedPage) reasons.push('ACTIVE_AUTHENTICATED_PAGE_MISSING');
  if(String(observed.url||'')!==expectedUrl) reasons.push('LIVE_URL_MISMATCH');
  if(String(observed.conversationId||'')!==expectedId) reasons.push('CONVERSATION_ID_MISMATCH');
  if(String(observed.projectContext||'')!=='TARGET') reasons.push('LIVE_PROJECT_NOT_TARGET');
  const surface=classifySurfaceIdentity(observed);
  if(!surface.normalChat) reasons.push('CHAT_SURFACE_NOT_PROVEN');
  const modeA=observed.immutableLiveTurnProvenance==='PASS';
  const modeB=observed.historicalImmutableProvenance==='PASS'&&(observed.liveRangeWitness==='PASS'||observed.liveRenderedWitness==='PASS')&&observed.crossSourceProvenance==='PASS';
  if(!modeA&&!modeB) reasons.push('CONVERSATION_IDENTITY_PROOF_NOT_PROVEN');
  if(observed.generationActive) reasons.push('GENERATION_ACTIVE');
  if(observed.composerAddressable!==true) reasons.push('COMPOSER_NOT_ADDRESSABLE');
  if(!modeA) observed.immutableFingerprint=null;
  else if(!observed.immutableFingerprint||!String(observed.immutableFingerprint.value||'')) reasons.push('IMMUTABLE_FINGERPRINT_MISSING');
  return {proof:reasons.length===0,live_conversation_proof:reasons.length===0?'PASS':'FAIL',live_conversation_identity_proof:reasons.length===0?'PASS':'FAIL',provenance_mode:modeA?'IMMUTABLE_LIVE':'HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS',live_turn_provenance:modeA?'PASS':'UNAVAILABLE_IN_CURRENT_UI',reasons,conversation_url:observed.url||'',conversation_id:observed.conversationId||'',project:observed.projectContext||'',surface:surface.surface,work:surface.work,codex:surface.codex,fingerprint:observed.immutableFingerprint||null};
}
function outboundGuard(input={}){
  const gates={staleLedgerReconciliation:input.staleLedgerReconciliation==='PASS',liveConversationProof:input.liveConversationProof==='PASS',chatSurface:input.chatSurface==='PASS',modelGuard:input.modelGuard==='PASS',outboundIdempotency:input.outboundIdempotency==='PASS'};
  const ok=Object.values(gates).every(Boolean);
  return {outbound_send:'BLOCKED',outbound_send_unlocked:false,reason:'AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION',gates};
}
function terminalOperatorAction(input={}){
  const state=String(input.state||'');
  return {execution:state==='FAILED_TERMINAL'?'FAILED_TERMINAL':state,retry_allowed:false,rerun_allowed:false,terminal:state==='FAILED_TERMINAL'};
}
function projectIdFrom(url){const m=String(url||'').match(/\/g\/(g-p-[^/]+)/);return m?m[1]:'';}
function projectNameFrom(url){
  const seg=String(url||'').match(/\/g\/(g-p-[^/]+)/);
  if(!seg)return '';
  const raw=seg[1];
  let m=raw.match(/^g-p-[0-9a-f]{32}-(.+)$/i);
  if(!m)m=raw.match(/^g-p-[A-Za-z0-9]{16,64}-(.+)$/);
  return m?m[1].replace(/-/g,'_'):'';
}
function normProjectName(s){return low(String(s||'').replace(/[_-]+/g,' '));}
function sameProjectName(a,b){const x=normProjectName(a),y=normProjectName(b);return !!x&&!!y&&x===y;}
const STANDARD_CHAT_SOL_MODEL='gpt-5.6-sol';
const STANDARD_CHAT_HIGH_CONTRACT='standard-chat-high=>gpt-5.6-sol-v1';
function loadPlaywright(moduleRoot){
  const tries=[]; if(moduleRoot){tries.push(path.join(moduleRoot,'playwright'));tries.push(path.join(moduleRoot,'playwright-core'));}
  tries.push('playwright');tries.push('playwright-core');let last;
  for(const n of tries){try{const m=require(n);if(m&&m.chromium)return m;}catch(e){last=e;}}
  throw new Error('PLAYWRIGHT_NODE_MODULE_UNAVAILABLE:'+String(last&&last.message||last||'unknown'));
}
function now(){return new Date().toISOString();}
function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function firstVisible(locator){const n=await locator.count().catch(()=>0);for(let i=0;i<n;i++){const x=locator.nth(i);if(await x.isVisible().catch(()=>false))return x;}return null;}

class Broker{
  constructor(cfg){
    this.cfg=cfg;this.context=null;this.page=null;this.epoch=crypto.randomBytes(8).toString('hex');
    this.pw=loadPlaywright(cfg.moduleRoot||'');
    this.timeouts={
      action:Number(cfg.actionTimeoutMs||process.env.AI_LOOP_BROWSER_ACTION_TIMEOUT_MS||8000),
      nav:Number(cfg.navigationTimeoutMs||process.env.AI_LOOP_BROWSER_NAVIGATION_TIMEOUT_MS||30000),
      settle:Number(cfg.settleTimeoutMs||process.env.AI_LOOP_BROWSER_SETTLE_TIMEOUT_MS||12000),
      hydration:Number(cfg.hydrationTimeoutMs||process.env.AI_LOOP_BROWSER_HYDRATION_TIMEOUT_MS||12000),
      response:Number(cfg.responseTimeoutMs||process.env.AI_LOOP_ASSISTANT_RESPONSE_TIMEOUT_MS||900000),
    };
    this.pollMs=Math.max(25,Number(cfg.pollIntervalMs||process.env.AI_LOOP_BROWSER_POLL_INTERVAL_MS||150));
  }
  async start(){
    const mode=String(this.cfg.browserMode||process.env.AI_LOOP_BROWSER_MODE||'headed_display').toLowerCase();
    const headless=mode==='headless';
    if(!headless&&!process.env.DISPLAY&&!this.cfg.display)throw new Error('BROWSER_DISPLAY_REQUIRED_FOR_HEADED_MODE');
    this.context=await this.pw.chromium.launchPersistentContext(this.cfg.browserProfile,{headless,executablePath:this.cfg.chromeExecutable||undefined,args:['--disable-blink-features=AutomationControlled']});
    this.page=this.context.pages()[0]||await this.context.newPage();
    this.page.setDefaultTimeout(this.timeouts.action);
    this.page.setDefaultNavigationTimeout(this.timeouts.nav);
  }
  async close(){if(this.context)await this.context.close().catch(()=>{});}
  async diag(op,err,extra={}){
    const dir=path.join(this.cfg.runDir||'/tmp','browser','broker-diagnostics');fs.mkdirSync(dir,{recursive:true});
    const stem=now().replace(/[:.]/g,'')+'-'+String(op).replace(/[^A-Za-z0-9_.-]/g,'_');
    const j=path.join(dir,stem+'.json'),h=path.join(dir,stem+'.html'),p=path.join(dir,stem+'.png');
    let st={};try{st=await this.observeContext(extra.projectUrl||'',extra.projectId||'',extra.projectName||'');}catch(_){ }
    fs.writeFileSync(j,JSON.stringify({schema_version:1,at:now(),op,error:String(err&&err.message||err),state:st,timeline:err&&err.timeline||[],extra},null,2));
    try{fs.writeFileSync(h,await this.page.content());}catch(_){ }
    try{await this.page.screenshot({path:p,fullPage:true});}catch(_){ }
    return {json:j,html:h,screenshot:p};
  }
  async waitUntil(fn,timeoutMs,label){const budget=Math.max(1,Number(timeoutMs)||1);const end=Date.now()+budget;let last;let observations=0;while(Date.now()<end){try{observations++;const v=await fn();if(v)return v;}catch(e){last=e;}await sleep(Math.min(this.pollMs,Math.max(1,end-Date.now())));}const e=new Error('WAIT_TIMEOUT:'+label+(last?':'+last.message:''));e.observations=observations;e.budget_ms=budget;throw e;}
  async resolveActiveComposer(){
    const snapshot=await this.page.evaluate(()=>{
      const visible=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};
      const text=e=>String(e?.innerText||e?.value||e?.textContent||'').replace(/\s+/g,' ').trim();
      const editors=[...document.querySelectorAll('div[contenteditable="true"],textarea')].filter(visible);
       const editor=editors.find(e=>{const hint=`${e.getAttribute('aria-label')||''} ${e.getAttribute('placeholder')||''}`;return /new chat|message/i.test(hint)&&!!(e.closest('form[data-chatgpt-composer]')||e.closest('[data-composer-body]')||e.closest('form'));})||editors.find(e=>e.closest('form[data-chatgpt-composer]')||e.closest('[data-composer-body]')||e.closest('form'))||editors[0];
      if(!editor)return {present:false,root_selector_kind:'none',attachments:[]};
       let root=editor.closest('form[data-chatgpt-composer]'),kind='data-chatgpt-composer';
      if(!root){root=editor.closest('[data-composer-body]');kind='data-composer-body';}
      if(!root){root=[...editor.closest('form')?.querySelectorAll('[data-composer-attachments],[data-visible-attachments]')||[]].length?editor.closest('form'):null;kind='semantic-form';}
      if(!root)return {present:true,root_selector_kind:'unproven',editable_visible:true,composer_text:text(editor),attachments:[]};
       // Never use the whole composer as an attachment region. Its normal
       // controls (Add files, model, dictation, voice) are not filenames.
       const regions=[...root.querySelectorAll('[data-composer-attachments],[data-visible-attachments],.composer-attachment-surface')]
         .filter(e=>visible(e));
       if(!regions.length)return {present:true,root_selector_kind:kind,project_name:(editor.getAttribute('aria-label')||'').replace(/^New chat in\s*/i,''),editable_visible:true,composer_text:text(editor),attachments:[],send_present:false,send_enabled:false};
       const region=regions.find(e=>e.matches('[data-composer-attachments],[data-visible-attachments]'))||regions[0];
       const removeNames=[...region.querySelectorAll('[aria-label]')].map(e=>(e.getAttribute('aria-label')||'').match(/^Remove\s+(.+)$/i)).filter(Boolean).map(m=>m[1].trim());
       const names=new Set(removeNames);
       const nameElements=[...region.querySelectorAll('[data-filename],[data-file-name],[data-attachment-name],.composer-attachment-surface .truncate,[data-composer-attachments] .truncate,[data-visible-attachments] .truncate')];
       for(const e of nameElements){const n=(e.getAttribute('data-filename')||e.getAttribute('data-file-name')||e.getAttribute('data-attachment-name')||e.getAttribute('title')||text(e)).trim();if(n&&n.length<300&&!/^(remove|attach|upload|add files)\b/i.test(n))names.add(n);}
       const attachments=[...names].filter(Boolean).map(name=>{const esc=CSS.escape(name);const nameControl=nameElements.some(e=>(e.getAttribute('data-filename')||e.getAttribute('data-file-name')||e.getAttribute('data-attachment-name')||e.getAttribute('title')||text(e)).trim()===name);const removeControl=[...region.querySelectorAll('[aria-label]')].some(e=>(e.getAttribute('aria-label')||'')===`Remove ${name}`);return {name,name_control:nameControl,remove_control:removeControl,uploading:/uploading|loading/i.test(region.innerText||''),error:/error|failed/i.test(region.innerText||''),selector_escape:esc};});
      const send=[...root.querySelectorAll('button,[role="button"]')].find(e=>visible(e)&&/send/i.test(e.getAttribute('aria-label')||e.innerText||''));
      return {present:true,root_selector_kind:kind,project_name:(editor.getAttribute('aria-label')||'').replace(/^New chat in\s*/i,''),editable_visible:true,composer_text:text(editor),attachments,send_present:!!send,send_enabled:!!send&&!send.disabled};
    }).catch(()=>({present:false,root_selector_kind:'none',attachments:[]}));
    return snapshot;
  }
  async _composerRoot(){
    const cp=await this.composer(); if(!cp) return null;
    const semantic=this.page.locator('form[data-chatgpt-composer]').filter({has:cp});
    if(await semantic.count().catch(()=>0)) return semantic.first();
    const body=this.page.locator('[data-composer-body]').filter({has:cp});
    if(await body.count().catch(()=>0)) return body.first();
    const form=cp.locator('xpath=ancestor::form[1]');
    if(await form.count().catch(()=>0)) return form;
    throw new Error('ACTIVE_COMPOSER_ROOT_UNPROVEN');
  }
  async composer(){const sels=['form[data-chatgpt-composer] div[contenteditable="true"][aria-label*="New chat" i]','div[contenteditable="true"][aria-label*="New chat" i]','div[contenteditable="true"][aria-label*="message" i]','div[contenteditable="true"]','textarea[placeholder*="message" i]','textarea'];for(const s of sels){const x=await firstVisible(this.page.locator(s));if(x)return x;}return null;}
  async turns(){const u=await this.page.locator('[data-message-author-role="user"]').count().catch(()=>0);const a=await this.page.locator('[data-message-author-role="assistant"]').count().catch(()=>0);return {user:u,assistant:a,total:u+a};}
  async observeContext(projectUrl='',projectId='',projectName=''){
    projectId=projectId||projectIdFrom(projectUrl);projectName=projectName||this.cfg.projectName||'bot_trading';
     const snapshot=await this.page.evaluate(({projectId,projectName})=>{
      const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
      const vis=e=>{try{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';}catch(_){return false;}};
       const attr=(e,n)=>e?.getAttribute(n)||'';
      const selected=e=>attr(e,'aria-current')==='page'||attr(e,'aria-selected')==='true'||attr(e,'aria-checked')==='true'||attr(e,'aria-pressed')==='true'||['checked','selected','active','on'].includes(attr(e,'data-state'));
      const esc=s=>String(s||'').replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
      const allLinks=[...document.querySelectorAll('a[href]')].map(e=>({href:e.href,text:norm(e.innerText||e.textContent),aria:norm(attr(e,'aria-label')),selected:selected(e),visible:vis(e)}));
      const links=allLinks.filter(x=>x.visible);
      const comps=[...document.querySelectorAll('div[contenteditable="true"],textarea')].filter(vis).map(e=>({aria:norm(attr(e,'aria-label')),placeholder:norm(attr(e,'placeholder')),text:norm(e.innerText||e.value||e.textContent)}));
      const controls=[...document.querySelectorAll('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="option"],[aria-selected],[aria-checked],[data-state]')].filter(vis).map(e=>({text:norm(e.innerText||e.textContent),aria:norm(attr(e,'aria-label')),title:norm(attr(e,'title')),role:attr(e,'role'),selected:selected(e),checked:attr(e,'aria-checked'),state:attr(e,'data-state'),expanded:attr(e,'aria-expanded'),navTarget:attr(e,'data-composer-navigation-target'),reasoningEffort:attr(e,'data-selected-reasoning-effort'),codexIntelligenceTrigger:attr(e,'data-codex-intelligence-trigger')}));
      const targetLinksAll=allLinks.filter(x=>projectId&&x.href.includes(projectId));
      const targetLinks=targetLinksAll.filter(x=>x.visible);
      const selectedTarget=targetLinksAll.some(x=>x.visible&&x.selected);
      const nameRe=projectName?new RegExp('(^|\\b)'+esc(projectName).replace(/[_-]+/g,'[_\\s-]+')+'(\\b|$)','i'):null;
       const projectNamePattern=projectName?esc(projectName).replace(/[_-]+/g,'[_\\s-]+'):'';
       const composerTarget=comps.some(c=>projectName&&new RegExp('new chat in\\s+'+projectNamePattern,'i').test(c.aria+' '+c.placeholder));
      const headerTarget=[...document.querySelectorAll('h1,h2,h3,[aria-label],[data-testid]')].filter(vis).some(e=>{const t=norm((e.innerText||e.textContent)+' '+attr(e,'aria-label'));return !!nameRe&&nameRe.test(t)&&!e.closest('[data-message-author-role]');});
      const activeProjectControls=[...document.querySelectorAll('[aria-label^="Change project:" i]')].filter(vis).map(e=>norm(attr(e,'aria-label').replace(/^Change project:\s*/i,'')));
      const activeProjectTarget=activeProjectControls.some(n=>projectName&&new RegExp('^'+projectNamePattern+'$','i').test(n));
      const activeProjectOther=activeProjectControls.some(n=>projectName&&!new RegExp('^'+projectNamePattern+'$','i').test(n));
      const otherSelected=allLinks.some(x=>x.visible&&x.selected&&/\/g\/g-p-/.test(x.href)&&projectId&&!x.href.includes(projectId));
       const composerOther=comps.some(c=>/new chat in\s+/i.test(c.aria+' '+c.placeholder)&&projectName&&!new RegExp(projectNamePattern,'i').test(c.aria+' '+c.placeholder));
      const urlTarget=!!projectId&&location.href.includes(projectId);
      const positive=[];
      if(urlTarget)positive.push('url_project_id');
      if(targetLinksAll.length)positive.push('project_anchor_mapped');
      if(targetLinks.length)positive.push('sidebar_target_link_present');
      if(selectedTarget)positive.push('selected_sidebar_project_id');
      if(composerTarget)positive.push('project_scoped_composer');
      if(headerTarget)positive.push('project_header');
      if(activeProjectTarget)positive.push('active_project_selector');
      const negative=[];if(otherSelected)negative.push('other_selected_project');if(composerOther)negative.push('other_project_composer');if(activeProjectOther)negative.push('other_active_project');
      let projectContext='UNKNOWN';
      if(negative.length)projectContext='OTHER';
      else if(urlTarget||selectedTarget||activeProjectTarget||(composerTarget&&targetLinksAll.length)||positive.filter(x=>x!=='sidebar_target_link_present').length>=2)projectContext='TARGET';
        // Conversation extraction is deliberately rooted in the rendered main
        // thread. Role nodes are authoritative; testid roots are a fallback
        // for ChatGPT variants where the role is attached to a descendant.
        const isExcluded=e=>!!e.closest('nav,aside,form,[data-composer-body],[contenteditable="true"]');
        const roleNodes=[...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"]')].filter(e=>vis(e)&&!isExcluded(e));
        const testidNodes=[...document.querySelectorAll('[data-testid]')].filter(e=>vis(e)&&!isExcluded(e)&&/conversation-turn|message-turn|chat-turn/i.test(attr(e,'data-testid')));
        const roots=[]; const rootSeen=new Set();
        const addRoot=(e,source)=>{
          if(!e)return;
          const root=e.closest('section[data-testid*="conversation-turn" i],div[data-testid*="conversation-turn" i],article[data-testid*="conversation-turn" i]')||e.closest('section')||e;
          if(!root||isExcluded(root)||rootSeen.has(root))return;
          rootSeen.add(root); roots.push({root,source});
        };
        roleNodes.forEach(e=>addRoot(e,'role')); testidNodes.forEach(e=>addRoot(e,'testid'));
        const turns=[],seen=new Set(),sourceCounts={role:0,testid:0};
        for(const item of roots){
          const e=item.root; const own=attr(e,'data-message-author-role');
          const nested=[e,...e.querySelectorAll('[data-message-author-role]')].find(x=>['user','assistant'].includes(attr(x,'data-message-author-role')));
          const marker=(attr(e,'data-testid')+' '+attr(e,'aria-label')).toLowerCase();
          const role=own||attr(nested,'data-message-author-role')||(/\buser\b/.test(marker)?'user':(/\bassistant\b|\bchatgpt\b/.test(marker)?'assistant':''));
          if(!['user','assistant'].includes(role))continue;
          const text=norm(e.innerText||e.textContent); if(!text)continue;
           const message_id=attr(nested,'data-message-id')||attr(e,'data-message-id');
           const testid=attr(e,'data-testid')||attr(nested,'data-testid');
            const turn_id=attr(e,'data-turn-id')||attr(nested,'data-turn-id')||'';
            const id=message_id||turn_id;
           const fingerprint=`${role}:${turn_id}:${message_id}:${text}`; if(seen.has(fingerprint))continue; seen.add(fingerprint);
           sourceCounts[item.source]=(sourceCounts[item.source]||0)+1;
            turns.push({role,turn_id,message_id,testid,id,text,outerHTML:e.outerHTML,mainConversation:true,index:turns.length,source:item.source});
        }
        turns.sort((a,b)=>{
          const ea=roleNodes.find(e=>attr(e,'data-message-id')===a.id)||testidNodes.find(e=>attr(e,'data-testid')===a.testid);
          const eb=roleNodes.find(e=>attr(e,'data-message-id')===b.id)||testidNodes.find(e=>attr(e,'data-testid')===b.testid);
          return (ea?.getBoundingClientRect().top||0)-(eb?.getBoundingClientRect().top||0);
        });
        turns.forEach((t,i)=>t.index=i);
         turns.forEach(t=>console.log('TURN',JSON.stringify(t)));
           const user=turns.filter(t=>t.role==='user').map(t=>t.text);
           const assistant=turns.filter(t=>t.role==='assistant').map(t=>t.text);
           const requiredMarkers=['failure-evidence-025d7f19b1dd83b26733','diagnosis-0c11a13e0c6c'];
           const pathOf=e=>{const p=[];for(let n=e;n&&n.nodeType===1&&p.length<24;n=n.parentElement){let i=1;for(let s=n.previousElementSibling;s;s=s.previousElementSibling)if(s.tagName===n.tagName)i++;p.unshift(`${n.tagName.toLowerCase()}:nth-of-type(${i})`);}return p.join('>');};
           const excluded=e=>!!e.closest('script,style,template,noscript,head,textarea,input,nav,aside,form,[contenteditable="true"]');
           const inMain=e=>!!e.closest('main,section[aria-label*="conversation" i],[data-testid*="conversation" i]')&&!excluded(e);
            const renderedWitnesses=[],rangeWitnesses=[];
            const conversationRoot=document.querySelector('main')||document.querySelector('section[aria-label*="conversation" i]');
            const textNodes=[],streamParts=[]; let stream='';
            const excludedText=e=>!!e.closest('script,style,template,noscript,head,textarea,input,nav,aside,form,[contenteditable="true"]');
            const visibleText=e=>{if(!e||excludedText(e)||!conversationRoot.contains(e))return false;const s=getComputedStyle(e),r=e.getBoundingClientRect(),check=typeof e.checkVisibility==='function'?e.checkVisibility():true;return r.width>0&&r.height>0&&s.display!=='none'&&!['hidden','collapse'].includes(s.visibility)&&Number(s.opacity)>0&&e.getAttribute('aria-hidden')!=='true'&&!e.hidden&&!!e.offsetParent&&check;};
            if(conversationRoot){const walker=document.createTreeWalker(conversationRoot,NodeFilter.SHOW_TEXT);let n;while(n=walker.nextNode()){if(!visibleText(n.parentElement))continue;const value=String(n.nodeValue||'');if(!value)continue;textNodes.push({node:n,start:stream.length,end:stream.length+value.length,path:pathOf(n.parentElement),sha256:sha(value)});streamParts.push(value);stream+=value;}}
            const streamSummary={root_path:conversationRoot?pathOf(conversationRoot):'',visible_text_nodes:textNodes.length,visible_stream_length:stream.length,stream_sha256:sha(stream),nodes:textNodes.map(x=>({path:x.path,start:x.start,end:x.end,sha256:x.sha256}))};
            for(const marker of requiredMarkers){let pos=0;const raw=[];while((pos=stream.indexOf(marker,pos))!==-1){const endPos=pos+marker.length;const start=textNodes.find(x=>pos>=x.start&&pos<x.end),end=textNodes.find(x=>endPos> x.start&&endPos<=x.end);if(start&&end){const range=document.createRange();range.setStart(start.node,pos-start.start);range.setEnd(end.node,endPos-end.start);const rects=[...range.getClientRects()].map(r=>({x:r.x,y:r.y,width:r.width,height:r.height}));const positive=rects.some(r=>r.width>0&&r.height>0);const id=`${start.path}|${pos-start.start}|${end.path}|${endPos-end.start}`;raw.push({marker,rangeIdentity:id,startPath:start.path,startOffset:pos-start.start,endPath:end.path,endOffset:endPos-end.start,visible:positive,inConversationRoot:true,excluded:false,positiveRect:positive,documentOrder:pos,rects,context_before:stream.slice(Math.max(0,pos-128),pos),context_after:stream.slice(endPos,endPos+128),context_sha256:sha(stream.slice(Math.max(0,pos-128),endPos+128)),before_sha256:sha(stream.slice(Math.max(0,pos-128),pos)),after_sha256:sha(stream.slice(endPos,endPos+128))});}pos=endPos;}
              renderedWitnesses.push(...raw);rangeWitnesses.push(...raw);}
            return {url:location.href,projectContext,projectEvidence:{positive,negative,targetLinks:targetLinks.slice(0,8),targetLinksAll:targetLinksAll.slice(0,8),selectedTarget,composerTarget,headerTarget,activeProjectTarget,activeProjectNames:activeProjectControls.slice(0,8)},composers:comps,controls:controls.slice(0,200),rawTurns:turns,renderedWitnesses,rangeWitnesses,visibleTextStream:streamSummary,userTexts:user,assistantTexts:assistant,turnInventory:{strategy_a:sourceCounts.role||0,strategy_b:sourceCounts.testid||0,total:turns.length}};
      },{projectId,projectName});
      snapshot.renderedWitnesses=(snapshot.renderedWitnesses||[]).map(w=>({...w,
        innerText_sha256:sha(w.excerpt||''),outerHTML_sha256:sha(w.excerpt||''),
        nearest_conversation_ancestor:w.inConversationRoot?'main':'',screenshot_clip_path:null}));
      const inventory=normalizeTurnInventory({turns:{records:snapshot.rawTurns||[]}});
     const reconciliation=inventory.deliveryMatches;
     if(reconciliation.some(x=>x.following_assistant)) console.log('FOLLOWING_ASSISTANT_FOUND',JSON.stringify(reconciliation.filter(x=>x.following_assistant)));
     console.log(`TURN_INVENTORY total=${inventory.turns.total} users=${inventory.turns.user} assistants=${inventory.turns.assistant}`);
     reconciliation.forEach(x=>{if(x.following_assistant)console.log(`DELIVERY_MATCH id=${x.delivery_id} user_index=${x.user_index} assistant_index=${x.assistant_index}`);});
     if(inventory.latestAssistantTurn)console.log(`LATEST_ASSISTANT index=${inventory.latestAssistantTurn.index} id=${inventory.latestAssistantTurn.id}`);
     return {...snapshot,...inventory,rawTurns:undefined};
   }
  async _freshTargetState(projectUrl,projectId,projectName){
    const q=await this.observeContext(projectUrl,projectId,projectName);
    const cp=await this.composer();
     const c=await this.resolveActiveComposer().catch(()=>({}));
    return q.projectContext==='TARGET'&&q.turns.total===0&&!!cp&&c.present===true&&c.root_selector_kind&&c.root_selector_kind!=='none'&&c.root_selector_kind!=='unproven'&&!norm(c.composer_text)&&!(c.attachments||[]).length?q:null;
  }
  async _waitFreshTarget(projectUrl,projectId,projectName,timeoutMs,label){
    return await this.waitUntil(()=>this._freshTargetState(projectUrl,projectId,projectName),timeoutMs,label);
  }
  async navigateProject(projectUrl,projectId,projectName,{forceRoot=false}={}){
    let s=await this.observeContext(projectUrl,projectId,projectName).catch(()=>({projectContext:'UNKNOWN',turns:{total:0}}));
    if(!forceRoot&&s.projectContext==='TARGET')return s;
    await this.page.goto(projectUrl,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});
    return await this.waitUntil(async()=>{const q=await this.observeContext(projectUrl,projectId,projectName);return q.projectContext==='TARGET'?q:null;},this.timeouts.settle,'project_context_target');
  }
  async _clickFreshChatCandidate(projectId,projectName){
    const attempts=[];
    const tryLoc=async(label,loc)=>{
      const n=await loc.count().catch(()=>0);
      for(let i=0;i<n;i++){
        const x=loc.nth(i);if(!(await x.isVisible().catch(()=>false)))continue;
        const href=await x.getAttribute('href').catch(()=>null);
        if(href&&/\/c\//.test(href))continue;
        attempts.push(label+':'+i);
        try{await x.click();return {clicked:true,label,index:i};}catch(_){ }
      }
      return null;
    };
    // Highest confidence: a control explicitly naming the project-scoped draft.
    let r=await tryLoc('project-scoped-new-chat',this.page.locator('button,[role="button"],a').filter({hasText:new RegExp('^New chat in\\s+'+String(projectName||'').replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/[_-]+/g,'[_\\s-]+')+'$','i')}));
    if(r)return {...r,attempts};
    // Official Projects UI: from a project, choose Chat to start a new project chat.
    // Prefer visible Chat controls in main/header rather than the global sidebar history.
    r=await tryLoc('project-chat-main',this.page.locator('main button,main [role="button"],header button,header [role="button"]').filter({hasText:/^Chat$/i}));
    if(r)return {...r,attempts};
    // New chat is safe only if it is not a historical /c/ link; post-action project proof is mandatory.
    r=await tryLoc('new-chat',this.page.locator('button,[role="button"],a').filter({hasText:/^New chat$/i}));
    if(r)return {...r,attempts};
    return {clicked:false,attempts};
  }
  async ensureFreshProjectDraft(args){
    const {projectUrl,projectId,projectName}=args;
    const trace=[];
    let fresh=await this._freshTargetState(projectUrl,projectId,projectName).catch(()=>null);
    if(fresh){fresh.freshDraftTrace=['already_fresh'];return fresh;}

    let before=await this.observeContext(projectUrl,projectId,projectName).catch(()=>({projectContext:'UNKNOWN',turns:{total:0},url:this.page.url()}));
    trace.push({step:'initial',url:this.page.url(),projectContext:before.projectContext,turns:before.turns&&before.turns.total});

    // Critical v4.1 regression fix: being in the correct project is NOT enough when the page is a historical /c/ chat.
    // Force the project root whenever a historical conversation is loaded, instead of returning early from navigateProject().
    const historical=!!(before.turns&&before.turns.total>0)||/\/c\//.test(this.page.url());
    if(historical||before.projectContext!=='TARGET'){
      await this.page.goto(projectUrl,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});
      trace.push({step:'forced_project_root',url:this.page.url()});
      fresh=await this._waitFreshTarget(projectUrl,projectId,projectName,Math.min(this.timeouts.settle,6000),'fresh_after_project_root').catch(()=>null);
      if(fresh){fresh.freshDraftTrace=trace;return fresh;}
    }

    // Re-assert project root/identity before trying any non-sending UI action.
    let s=await this.observeContext(projectUrl,projectId,projectName).catch(()=>({projectContext:'UNKNOWN',turns:{total:0}}));
    if(s.projectContext!=='TARGET'){
      await this.navigateProject(projectUrl,projectId,projectName,{forceRoot:true});
      trace.push({step:'navigate_project_force',url:this.page.url()});
      fresh=await this._waitFreshTarget(projectUrl,projectId,projectName,Math.min(this.timeouts.settle,4000),'fresh_after_force_project').catch(()=>null);
      if(fresh){fresh.freshDraftTrace=trace;return fresh;}
    }

    // Try bounded safe controls, verifying a target-project empty draft after each action.
    for(let attempt=1;attempt<=3;attempt++){
      const action=await this._clickFreshChatCandidate(projectId,projectName);
      trace.push({step:'fresh_control',attempt,action,url:this.page.url()});
      if(!action.clicked)break;
      fresh=await this._waitFreshTarget(projectUrl,projectId,projectName,3500,'fresh_after_control_'+attempt).catch(()=>null);
      if(fresh){fresh.freshDraftTrace=trace;return fresh;}

      // If a generic New chat escaped the project, immediately re-enter the target project before another candidate.
      s=await this.observeContext(projectUrl,projectId,projectName).catch(()=>({projectContext:'UNKNOWN'}));
      if(s.projectContext!=='TARGET'){
        await this.page.goto(projectUrl,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});
        trace.push({step:'reenter_project_after_candidate',attempt,url:this.page.url()});
        fresh=await this._waitFreshTarget(projectUrl,projectId,projectName,3000,'fresh_after_reenter_'+attempt).catch(()=>null);
        if(fresh){fresh.freshDraftTrace=trace;return fresh;}
      }
    }

    const err=new Error('FRESH_PROJECT_DRAFT_NOT_REACHED');
    err.freshDraftTrace=trace;
    throw err;
  }
  async selectedText(re){const st=await this.observeContext();return st.controls.some(c=>c.selected&&re.test((c.text+' '+c.aria+' '+c.title).trim()));}
  async clickMatching(re){const loc=this.page.locator('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="menuitem"],[role="option"],a');const n=await loc.count().catch(()=>0);let matches=0,chosen=null;for(let i=0;i<n;i++){const x=loc.nth(i);if(!(await x.isVisible().catch(()=>false)))continue;const fields=[await x.innerText().catch(()=>''),await x.getAttribute('aria-label').catch(()=>''),await x.getAttribute('title').catch(()=>''),await x.getAttribute('data-state').catch(()=>''),await x.getAttribute('aria-selected').catch(()=>''),await x.getAttribute('aria-checked').catch(()=> '')];if(fields.some(v=>re.test(norm(v)))){matches++;chosen=x;}}if(matches!==1)return false;await chosen.click();return true;}
  async policyState(){
    const st=await this.observeContext();
    const controls=st.controls||[];
    const label=c=>norm((c.text||'')+' '+(c.aria||'')+' '+(c.title||''));
    const workSelected=controls.some(c=>c.selected&&/^(Work|Codex)$/i.test(norm(c.text||c.aria||'')));
    const trigger=controls.find(c=>low(c.navTarget)==='reasoning')||controls.find(c=>/select chatgpt model/i.test(c.aria||''));
    let reasoning=low(trigger&&trigger.reasoningEffort||'');
    if(!reasoning&&trigger){const t=low(trigger.text||'');if(/^(instant|light|medium|high|extra high|xhigh)$/.test(t))reasoning=t;}
    if(!reasoning){const sel=controls.find(c=>c.selected&&/^(Instant|Light|Medium|High|Extra High|XHigh)$/i.test(norm(c.text||'')));reasoning=low(sel&&sel.text||'');}
    const reasoningOnlyUI=!!trigger&&(low(trigger.navTarget)==='reasoning'||String(trigger.reasoningEffort||'')!==''||String(trigger.codexIntelligenceTrigger||'')==='true');
    const chatSelected=controls.some(c=>c.selected&&/^Chat$/i.test(norm(c.text||c.aria||'')))||(!workSelected&&reasoningOnlyUI);
    const explicitSol=controls.some(c=>c.selected&&/GPT[- ]?5\.6\s+Sol/i.test(label(c)));
    const inferredSol=chatSelected&&!workSelected&&reasoningOnlyUI&&['medium','high','extra high','xhigh'].includes(reasoning);
    return {chat:chatSelected&&!workSelected,model:explicitSol||inferredSol,high:reasoning==='high',reasoning,modelName:(explicitSol||inferredSol)?STANDARD_CHAT_SOL_MODEL:'',modelProof:explicitSol?'explicit-selected-ui':(inferredSol?STANDARD_CHAT_HIGH_CONTRACT:''),reasoningProof:trigger&&trigger.reasoningEffort?'data-selected-reasoning-effort':(reasoning?'visible-selected-reasoning':''),surfaceProof:chatSelected?'selected-chat-control':'',trigger:trigger||null};
  }
  async ensurePolicy(args){
    const timeline=[];const started=Date.now();const budget=Math.max(1,Number(args.hydrationTimeoutMs||this.timeouts.hydration));
    const observe=async(stage)=>{const q=await this.policyState();timeline.push({stage,t_ms:Date.now()-started,chat:!!q.chat,work:!q.chat&&!!q.trigger,high:!!q.high,model:!!q.model,reasoning:q.reasoning||'',modelProof:q.modelProof||'',reasoningProof:q.reasoningProof||''});return q;};
    const remaining=()=>Math.max(1,budget-(Date.now()-started));
    try{
      if(args.targetUrl&&this.page.url()!==args.targetUrl)await this.page.goto(args.targetUrl,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});
      let state=await this.waitUntil(async()=>{const q=await observe('hydrate');return q.chat?q:null;},remaining(),'chat_policy_hydration_ready');
      if(!state.chat){
         if(!(await this.clickMatching(/^Chat$/i)))state=await this.waitUntil(async()=>{const q=await observe('surface_actionable');return q.chat?q:null;},remaining(),'chat_surface_actionable');
        if(!state.chat){if(!(await this.clickMatching(/^Chat$/i)))throw new Error('CHAT_SURFACE_NOT_ACTIONABLE');state=await this.waitUntil(async()=>{const q=await observe('chat_selected');return q.chat?q:null;},remaining(),'chat_surface_selected');}
      }
      if(!state.high){
        const trigger=await firstVisible(this.page.locator('button[data-composer-navigation-target="reasoning"],button[data-selected-reasoning-effort],button[aria-label*="Select ChatGPT model" i],button[aria-label*="reason" i],button[aria-label*="thinking" i]'));
        if(!trigger)throw new Error('REASONING_SELECTOR_NOT_FOUND');await trigger.click();
        const clicked=await this.waitUntil(async()=>this.clickMatching(/^High$/i),remaining(),'reasoning_high_actionable');if(!clicked)throw new Error('REASONING_HIGH_OPTION_NOT_FOUND');
        state=await this.waitUntil(async()=>{const q=await observe('reasoning_selected');return q.chat&&q.high?q:null;},remaining(),'high_reasoning_selected');
      }
      if(!state.model){const legacy=await firstVisible(this.page.locator('button[aria-label*="model" i]:not([data-composer-navigation-target="reasoning"])'));if(legacy){await legacy.click();if(await this.clickMatching(/GPT[- ]?5\.6\s+Sol/i))state=await this.waitUntil(async()=>{const q=await observe('model_selected');return q.model?q:null;},remaining(),'legacy_sol_selected');}}
      const final=await observe('final_policy');if(!final.chat||!final.model||!final.high){const e=new Error('MODEL_POLICY_NOT_PROVEN_SELECTED_STATE');e.timeline=timeline;throw e;}return {...final,surface:'chat',surface_selected:true,reasoning:'high',model_contract:'gpt-5.6-sol',proof:{surface:final.surfaceProof,reasoning:final.reasoningProof,model:final.modelProof},hydration_timeline:timeline,budget_ms:budget,elapsed_ms:Date.now()-started};
    }catch(err){err.timeline=timeline;err.hydration_budget_ms=budget;err.hydration_elapsed_ms=Date.now()-started;throw err;}
  }
  async attachFile(filePath,fileName,meta={}){
      const expectedSha=meta.sha256||sha(fs.readFileSync(filePath)); const expectedBytes=Number(meta.bytes||fs.statSync(filePath).size); const rootState=await this.resolveActiveComposer();
      if(rootState.root_selector_kind==='unproven')throw new Error('ACTIVE_COMPOSER_ROOT_UNPROVEN');
      const ledgerKey='ai_loop_attachment_'+String(meta.deliveryId||fileName); let old={}; try{old=await this.page.evaluate(k=>JSON.parse(localStorage.getItem(k)||'{}')||{},ledgerKey);}catch(_){ }
      const fileParts=String(fileName).match(/^(.*?)(\.[^.]+)?$/); const attachmentNameRe=new RegExp('^'+String(fileParts[1]).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?:\\([0-9]+\\))?'+String(fileParts[2]||'').replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$');
       const existing=(rootState.attachments||[]).filter(a=>attachmentNameRe.test(a.name));
       if((rootState.attachments||[]).some(a=>a.uploading))throw new Error('ATTACHMENT_UPLOAD_IN_PROGRESS');
       if((rootState.attachments||[]).some(a=>!a.name_control||!a.remove_control))throw new Error('CURRENT_COMPOSER_ATTACHMENT_UNREMOVABLE');
      if(existing.length===1&&!existing[0].error&&!existing[0].uploading&&old.sha256===expectedSha&&Number(old.bytes)===expectedBytes)return {status:'ALREADY_ATTACHED',filename:existing[0].name,sha256:expectedSha,bytes:expectedBytes,ledger:old};
      const c=await this.composer();if(!c)throw new Error('COMPOSER_NOT_FOUND');
      const staleNames=(rootState.attachments||[]).map(a=>a.name);
      const root=await this._composerRoot();
      for(const name of staleNames){
        await root.locator('button[aria-label^="Remove "]').evaluateAll((els,target)=>{
          for(const el of els){if(el.getAttribute('aria-label')===`Remove ${target}`)el.click();}
        },name).catch(()=>{});
      }
      if(staleNames.length)await this.waitUntil(async()=>{const s=await this.resolveActiveComposer();return !(s.attachments||[]).some(a=>staleNames.includes(a.name));},this.timeouts.settle,'stale_attachment_removal');
      let input=this.page.locator('form[data-chatgpt-composer] input[type="file"], [data-composer-body] input[type="file"]');
      const labels=this.page.locator('form[data-chatgpt-composer] input[type="file"][aria-label*="Attach files" i], [data-composer-body] input[type="file"][aria-label*="Attach files" i], form[data-chatgpt-composer] input[type="file"][aria-label*="Upload files" i], [data-composer-body] input[type="file"][aria-label*="Upload files" i], form[data-chatgpt-composer] input[type="file"][aria-label="Files"], [data-composer-body] input[type="file"][aria-label="Files"]');
     if(await labels.count().catch(()=>0))input=labels;
    if(!(await input.count())){
      const plus=await firstVisible(this.page.locator('button[aria-label*="Add files" i],button[aria-label*="Attach" i],#composer-plus-btn'));if(plus)await plus.click().catch(()=>{});
       input=this.page.locator('form[data-chatgpt-composer] input[type="file"], [data-composer-body] input[type="file"]');
    }
     if(await input.count()){await input.first().setInputFiles(filePath);}
    else{
      const up=await firstVisible(this.page.locator('[role="menuitem"],button').filter({hasText:/upload|add files|computer/i}));if(!up)throw new Error('FILE_INPUT_OR_UPLOAD_CONTROL_NOT_FOUND');
      const fc=this.page.waitForEvent('filechooser',{timeout:this.timeouts.action});await up.click();const chooser=await fc;await chooser.setFiles(filePath);
    }
      const proof=await this.waitUntil(async()=>{const s=await this.resolveActiveComposer();const a=(s.attachments||[]).filter(x=>attachmentNameRe.test(x.name));return s.root_selector_kind!=='unproven'&&a.length===1&&a[0].name_control&&a[0].remove_control&&!a[0].uploading&&!a[0].error?s:null;},this.timeouts.settle,'attachment_proof');
      const actualName=proof.attachments.find(x=>attachmentNameRe.test(x.name)).name;
      const ledger={delivery_id:String(meta.deliveryId||''),filename:actualName,source_path:filePath,sha256:expectedSha,bytes:expectedBytes,ui_status:'ATTACHED',attached_at:now(),broker_epoch:this.epoch};
      await this.page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:ledgerKey,v:ledger});
      return {status:'ATTACHED',filename:actualName,sha256:expectedSha,bytes:expectedBytes,proof,ledger};
  }
  async fillComposer(message){
    const c=await this.composer();
    if(!c) throw new Error('COMPOSER_NOT_FOUND');
    if((await c.getAttribute('contenteditable').catch(()=>''))==='true'){
      await c.fill(message).catch(async()=>{
        await c.click();
        await this.page.keyboard.press('Control+A');
        await this.page.keyboard.type(message);
      });
    } else {
      await c.fill(message);
    }
    await this.waitUntil(async()=>{
      const cp=await this.composer();
      if(!cp) return false;
      let txt='';
      try{ txt=await cp.innerText(); }catch(_){ try{ txt=await cp.inputValue(); }catch(__){ txt=''; } }
      return norm(txt)===norm(message);
    },this.timeouts.settle,'composer_exact_text');
  }
  async sendAtomic(args){
    const marker='[AI_LOOP_DELIVERY id='+args.deliveryId+']';
    // The broker owns the final side-effect boundary: re-prove Chat/Sol/High
    // after composer preparation and immediately before inspecting/clicking Send.
    const policy=await this.ensurePolicy({...args,hydrationTimeoutMs:args.hardGateTimeoutMs||this.timeouts.hydration});
    if(!policy.chat||!policy.model||!policy.high)throw new Error('HARD_POLICY_GATE_FAILED');
    const before=await this.observeContext(args.projectUrl,args.projectId,args.projectName);if(before.projectContext!=='TARGET')throw new Error('SEND_WRONG_PROJECT');
    const users=before.userTexts||[];if(users.some(t=>t.includes(marker)))return {status:'ALREADY_SENT',clicked:false,url:before.url,project:true,delivery_present:true};
    const send=await firstVisible(this.page.locator('[data-testid="send-button"],button[aria-label*="Send" i],button[type="submit"]'));if(!send)throw new Error('SEND_BUTTON_NOT_FOUND');if(!(await send.isEnabled().catch(()=>false)))throw new Error('SEND_BUTTON_DISABLED');
    const key='ai_loop_bootstrap_'+args.deliveryId;await this.page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:key,v:{delivery_id:args.deliveryId,send_status:'SENDING',clicked_at:now()}});
    await send.click();
     const after=await this.waitUntil(async()=>{const q=await this.observeContext(args.projectUrl,args.projectId,args.projectName);return q.userTexts.some(t=>t.includes(marker))&&q.projectContext==='TARGET'?q:null;},30000,'delivery_marker_after_send').catch(()=>null);
     if(!after){
       const current=await this.observeContext(args.projectUrl,args.projectId,args.projectName).catch(()=>null);
       const markerSeen=!!(current&&((current.userTexts||[]).some(t=>t.includes(marker))||(current.url||'').includes('/c/')));
       if(markerSeen&&current.projectContext==='TARGET')return {status:'PASS',clicked:true,safeToRetry:false,url:current.url,ledger:{delivery_id:args.deliveryId,send_status:'SENT',sent:true,url:current.url,sent_at:now()},project:true,delivery_present:true};
     }
    if(!after){const ledger={delivery_id:args.deliveryId,send_status:'AMBIGUOUS',sent:false,url:this.page.url()};await this.page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:key,v:ledger});return {status:'AMBIGUOUS_SEND',clicked:true,safeToRetry:false,url:this.page.url(),ledger,error:'DELIVERY_MARKER_NOT_PROVEN_AFTER_CLICK'};}
    const ledger={delivery_id:args.deliveryId,send_status:'SENT',sent:true,url:after.url,sent_at:now()};await this.page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:key,v:ledger});return {status:'PASS',clicked:true,safeToRetry:false,url:after.url,ledger,project:true,delivery_present:true};
  }

  async observeDelivery(args){
    const marker='[AI_LOOP_DELIVERY id='+args.deliveryId+']';
    const visited=[];
    const candidates=[];
    const add=u=>{u=String(u||'');if(!u||candidates.includes(u))return;candidates.push(u);};
    const current=this.page.url();if(current&&current!=='about:blank')add(current); for(const u of (args.candidateUrls||[])) add(u);
    const links=await this.page.locator('a[href*="/c/"]').evaluateAll(els=>els.map(e=>e.href)).catch(()=>[]);
    for(const u of links) add(u);
    let found=false,foundUrl='',navigationErrors=[];
    for(const u of candidates.slice(0,Number(args.maxChats||16))){
      try{if(u!==this.page.url()) await this.page.goto(u,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});}catch(e){navigationErrors.push({url:u,error:String(e&&e.message||e)});continue;}
      visited.push(this.page.url());
      const st=await this.observeContext(args.projectUrl,args.projectId,args.projectName).catch(()=>null);
      if(st&&st.projectContext==='TARGET'&&(st.userTexts||[]).some(t=>t.includes(marker))){found=true;foundUrl=st.url;break;}
    }
    let ledger={};try{ledger=await this.page.evaluate(k=>JSON.parse(localStorage.getItem(k)||'{}')||{},'ai_loop_bootstrap_'+args.deliveryId);}catch(_){ }
    const scanComplete=visited.length+navigationErrors.length>=Math.min(candidates.length,Number(args.maxChats||16));
    return {status:found?'PASS':(navigationErrors.length?'RECONCILIATION_REQUIRED':'PASS'),found,url:found?foundUrl:this.page.url(),project:found,visited,candidateCount:candidates.length,navigationErrors,scanComplete,ledger,error:found?'':(navigationErrors.length?'DELIVERY_RECONCILIATION_NAVIGATION_FAILED':'DELIVERY_MARKER_NOT_FOUND')};
  }
  async observeResponse(args){
    const state=await this.observeContext(args.projectUrl,args.projectId,args.projectName);
     const inventory=normalizeTurnInventory(state);
     Object.assign(state,inventory);
    const selectors=['[data-message-author-role="assistant"]','[data-testid*="conversation-turn" i]','[data-testid*="message-turn" i]'];
    let assistants=null,n=0,selector='';
    for(const candidate of selectors){const loc=this.page.locator(candidate);const count=typeof loc.count==='function'?await loc.count().catch(()=>0):0;if(count){assistants=loc;n=count;selector=candidate;break;}}
    const stop=await this.page.locator('[data-testid*="stop" i],button[aria-label*="Stop" i],button').filter({hasText:/^Stop$|Stop answering|Stop generating/i}).count().catch(()=>0)>0;
    const busyStatus=await this.page.locator('[role="status"], [aria-live="polite"], [data-testid*="status" i]').filter({hasText:/thinking|generating|working|researching|searching|running/i}).count().catch(()=>0)>0;
    const positiveGeneration=stop||busyStatus;
     const reconciled=(state.deliveryMatches||[]).find(x=>x.following_assistant);
    if(!n && reconciled){
       const record=(state.orderedTurns||[]).find(x=>x.id===reconciled.following_assistant.id)||reconciled.following_assistant;
      return {...state,generation_state:'SETTLED',generation_signal:{stop,busy_status:busyStatus},assistant_selector:'reconciled-turn-record',assistant_message_id:record.id,assistant_text:record.text,assistant_text_normalized:norm(record.text),assistant_turn_records:state.turnRecords||[]};
    }
    if(!n){
      const key=String(args.deliveryId||''); this._missingByDelivery=this._missingByDelivery||{}; this._missingByDelivery[key]=(this._missingByDelivery[key]||0)+1;
      const breaker=this._missingByDelivery[key]>=3;
      return {generation_state:positiveGeneration?'GENERATING':(breaker?'TURN_RECONCILIATION_AMBIGUOUS':'RESPONSE_MISSING'),generation_signal:{stop,busy_status:busyStatus},observer_breaker_open:breaker,missing_observations:this._missingByDelivery[key],...state};
    }
    const last=assistants.nth(n-1);const text=await last.innerText().catch(()=>''),normalized=norm(text);const id=(await last.getAttribute('data-message-id').catch(()=>''))||(await last.getAttribute('data-testid').catch(()=>''))||('assistant-'+(n-1));
    const gen=positiveGeneration;
    const rate=/too many requests|rate limit|try again later/i.test(await this.page.locator('body').innerText().catch(()=>''));
    const dir=path.join(this.cfg.runDir||'/tmp','browser','responses');fs.mkdirSync(dir,{recursive:true});const p=path.join(dir,id.replace(/[^A-Za-z0-9_.-]/g,'_')+'.txt');fs.writeFileSync(p,text,'utf8');
    const blocks=await last.locator('pre').evaluateAll(els=>els.map((e,i)=>{const code=e.querySelector('code');return {block_index:i,language:(code?.className||e.className||'').match(/language-([^\s]+)/)?.[1]||'',text:(code||e).textContent||'',context_before:'',context_after:''};})).catch(()=>[]);
    const meta=blocks.map(b=>({block_index:b.block_index,language:b.language,sha256:sha(b.text),bytes:Buffer.byteLength(b.text,'utf8')}));
    return {...state,generation_state:rate?'RATE_LIMIT':gen?'GENERATING':'SETTLED',generation_signal:{stop,busy_status:busyStatus},assistant_selector:selector,assistant_message_id:id,assistant_text_path:p,assistant_text_sha256:sha(text),assistant_text:text,assistant_text_normalized:normalized,turn_structure:{assistant_count:n,code_blocks:meta},assistant_turn_records:state.turnRecords||state.turns?.records||[]};
  }
  async semaphoreReadonly(args){
    let page=this.context.pages().find(p=>/semaphoreci\.com/.test(p.url()))||await this.context.newPage();
    await page.goto(args.url||'https://me.semaphoreci.com',{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});
    let authAttempts=0;
    for(;authAttempts<3;authAttempts++){
      const body=low(await page.locator('body').innerText().catch(()=>''));
      if(!/login|log in|sign in|continue with github/.test(body)) break;
      const b=await firstVisible(page.locator('button,a').filter({hasText:/login with github|log in with github|sign in with github|continue with github/i}));
      if(!b) break; await b.click().catch(()=>{}); await page.waitForLoadState('domcontentloaded').catch(()=>{});
      if(/github\.com/.test(page.url()) && /password|otp|two-factor|device|authorize/i.test(low(await page.locator('body').innerText().catch(()=>'')))) return {status:'AUTH_REQUIRED_HUMAN',auth_recovery_attempted:true,auth_recovery_succeeded:false,auth_recovery_attempts:authAttempts+1,error:'SEMAPHORE_AUTH_REQUIRED_HUMAN'};
    }
    const anchors=[args.runId,args.pipelineId,args.sha].filter(Boolean);
    for(const a of anchors){
      const link=await firstVisible(page.locator('a').filter({hasText:String(a)}));
      if(link) await link.click().catch(()=>{});
    }
    const body=await page.locator('body').innerText().catch(()=>'');
    const lowb=low(body); const missing=anchors.filter(a=>!lowb.includes(String(a).toLowerCase()));
    if(missing.length) return {status:'NOT_FOUND',error:'SEMAPHORE_EXACT_ANCHORS_NOT_FOUND:'+missing.join(','),summary:body.slice(-12000),auth_recovery_attempted:authAttempts>0,auth_recovery_succeeded:authAttempts>0,auth_recovery_attempts:authAttempts};
    const failed=/\bfailed\b/i.test(body); const success=/\b(success|passed)\b/i.test(body);
    return {status:'PASS',repo:args.repo||'',branch:args.branch||'',candidate_sha:args.sha||'',verified_candidate_sha:args.sha||'',run_id:args.runId||'',pipeline_id:args.pipelineId||'',pipeline_status:failed||success?'done':'running',pipeline_result:failed?'failed':success?'success':'',auth_recovery_attempted:authAttempts>0,auth_recovery_succeeded:authAttempts>0,auth_recovery_attempts:authAttempts,failed_jobs:[],summary:body.slice(-20000),error:''};
  }
  async downloadArtifact(args){
    if(args.chatUrl && this.page.url()!==args.chatUrl) await this.page.goto(args.chatUrl,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});
    const assistants=this.page.locator('[data-message-author-role="assistant"]');
    const n=await assistants.count(); if(!n) throw new Error('NO_ASSISTANT');
    const turn=assistants.nth(n-1);
    const dest=args.destination; fs.mkdirSync(path.dirname(dest),{recursive:true});
    let candidates=turn.locator('a[href],button'); const c=await candidates.count();
    for(let i=0;i<c;i++){
      const x=candidates.nth(i); if(!(await x.isVisible().catch(()=>false))) continue;
      const txt=norm((await x.innerText().catch(()=>''))+' '+(await x.getAttribute('aria-label').catch(()=>''))+' '+(await x.getAttribute('title').catch(()=>'')));
      const href=await x.getAttribute('href').catch(()=>null);
      if(!/\.md|markdown|download/i.test(txt+' '+String(href||''))) continue;
      try{
        if(href && href.startsWith('data:')){
          const m=href.match(/^data:([^,]*?),(.*)$/s); if(m){const raw=/;base64/i.test(m[1])?Buffer.from(m[2],'base64'):Buffer.from(decodeURIComponent(m[2]),'utf8');fs.writeFileSync(dest,raw);return {path:dest,bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex'),method:'data-url'};}
        }
        if(href && href.startsWith('blob:')){
          const b64=await this.page.evaluate(async u=>{const r=await fetch(u);const a=new Uint8Array(await r.arrayBuffer());let s='';for(const b of a)s+=String.fromCharCode(b);return btoa(s);},href);const raw=Buffer.from(b64,'base64');fs.writeFileSync(dest,raw);return {path:dest,bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex'),method:'blob-url'};
        }
        if(href){const resp=await this.context.request.get(new URL(href,this.page.url()).toString());if(resp.ok()){const raw=Buffer.from(await resp.body());if(raw.length){fs.writeFileSync(dest,raw);return {path:dest,bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex'),method:'href'};}}}
        const dlP=this.page.waitForEvent('download',{timeout:this.timeouts.action}); await x.click(); const dl=await dlP; await dl.saveAs(dest); const raw=fs.readFileSync(dest);return {path:dest,bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex'),method:'download'};
      }catch(_){ }
    }
    throw new Error('DOWNLOADABLE_MD_NOT_FOUND');
  }
  async materializeCodeBlock(args){
    const assistants=this.page.locator('[data-message-author-role="assistant"]');const n=await assistants.count();if(!n)throw new Error('NO_ASSISTANT');const last=assistants.nth(n-1);const blocks=last.locator('pre code, pre');const cnt=await blocks.count();if(args.blockIndex<0||args.blockIndex>=cnt)throw new Error('BLOCK_INDEX_OUT_OF_RANGE');const text=await blocks.nth(args.blockIndex).textContent();const s=sha(text),bytes=Buffer.byteLength(text,'utf8');if(args.expectedSha&&s!==args.expectedSha)throw new Error('BLOCK_SHA_MISMATCH');if(args.expectedBytes&&bytes!==Number(args.expectedBytes))throw new Error('BLOCK_LENGTH_MISMATCH');fs.mkdirSync(path.dirname(args.outputPath),{recursive:true});fs.writeFileSync(args.outputPath,text,'utf8');return {path:args.outputPath,sha256:s,bytes};
  }
  async handle(req){
    const op=req.operation,args=req.arguments||{};
    if(op==='HEALTH')return {status:'PASS',epoch:this.epoch,url:this.page.url()};
    if(op==='NAVIGATE_PROJECT')return {status:'PASS',state_after:await this.navigateProject(args.projectUrl,args.projectId,args.projectName)};
    if(op==='NAVIGATE_URL'){await this.page.goto(args.url,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});return {status:'PASS',url:this.page.url()};}
    if(op==='OBSERVE_CONTEXT')return {status:'PASS',state_after:await this.observeContext(args.projectUrl,args.projectId,args.projectName)};
    if(op==='ENSURE_FRESH_PROJECT_DRAFT')return {status:'PASS',state_after:await this.ensureFreshProjectDraft(args)};
    if(op==='ENSURE_CHAT_POLICY')return {status:'PASS',evidence:await this.ensurePolicy(args)};
     if(op==='ATTACH_FILE')return {status:'PASS',evidence:{attached:await this.attachFile(args.path,args.name,args)}};
    if(op==='FILL_COMPOSER'){await this.fillComposer(args.message);return {status:'PASS'};}
    if(op==='SEND_ATOMIC')return await this.sendAtomic(args);
    if(op==='OBSERVE_RESPONSE')return {status:'PASS',evidence:await this.observeResponse(args)};
     if(op==='OBSERVE_DELIVERY')return {status:'PASS',evidence:await this.observeDelivery(args)};
     if(op==='RECONCILE_HISTORICAL_DELIVERY')return {status:'PASS',evidence:reconcileHistoricalDelivery(args)};
     if(op==='PROVE_LIVE_CONVERSATION')return {status:'PASS',evidence:proveLiveConversation(args)};
     if(op==='OUTBOUND_GUARD')return {status:'PASS',evidence:outboundGuard(args)};
     if(op==='OPERATOR_ACTION_TERMINAL')return {status:'PASS',evidence:terminalOperatorAction(args)};
    if(op==='MATERIALIZE_CODE_BLOCK')return {status:'PASS',evidence:await this.materializeCodeBlock(args)};
    if(op==='DOWNLOAD_ARTIFACT')return {status:'PASS',evidence:await this.downloadArtifact(args)};
    if(op==='SEMAPHORE_READONLY')return {status:'PASS',evidence:await this.semaphoreReadonly(args)};
    if(op==='CAPTURE_DIAGNOSTICS')return {status:'PASS',evidence:await this.diag(args.label||'manual',new Error('manual capture'),args)};
    if(op==='CLOSE'){await this.close();return {status:'PASS'};}
    throw new Error('UNKNOWN_OPERATION:'+op);
  }
}

 module.exports={Broker,projectIdFrom,projectNameFrom,normProjectName,sameProjectName,norm,low,sha,classifySurfaceIdentity,verifySurfaceTransition,extractTurnProvenance,compareTurnProvenance,normalizeTurnInventory,reconcileHistoricalDelivery,historicalImmutableProvenance,renderedWitnessProof,rangeWitnessProof,dedupeRangeWitnesses,crossSourceProvenance,proveLiveConversation,outboundGuard,terminalOperatorAction,STANDARD_CHAT_SOL_MODEL,STANDARD_CHAT_HIGH_CONTRACT};

if(require.main===module)(async()=>{
  const cfgPath=process.argv[2];if(!cfgPath)throw new Error('CONFIG_PATH_REQUIRED');const cfg=JSON.parse(fs.readFileSync(cfgPath,'utf8'));const b=new Broker(cfg);await b.start();
  process.stdout.write(JSON.stringify({broker_ready:true,epoch:b.epoch})+'\n');
  const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
  for await (const line of rl){if(!line.trim())continue;let req;try{req=JSON.parse(line);}catch(e){process.stdout.write(JSON.stringify({request_id:'',status:'ERROR',error:'INVALID_JSON:'+e.message})+'\n');continue;}
    const base={request_id:req.request_id||'',epoch:b.epoch};try{const out=await b.handle(req);process.stdout.write(JSON.stringify({...base,...out})+'\n');if(req.operation==='CLOSE')break;}catch(e){const d=await b.diag(req.operation||'unknown',e,req.arguments||{}).catch(()=>({}));process.stdout.write(JSON.stringify({...base,status:'ERROR',error:String(e&&e.message||e),evidence:{diagnostics:d}})+'\n');}
  }
  await b.close().catch(()=>{});
})().catch(e=>{process.stderr.write('BROKER_FATAL '+String(e&&e.stack||e)+'\n');process.exit(1);});
