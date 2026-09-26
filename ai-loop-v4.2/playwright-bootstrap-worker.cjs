#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function emit(obj){ process.stdout.write(JSON.stringify(obj)+'\n'); }
function norm(s){ return String(s||'').replace(/\s+/g,' ').trim(); }
function low(s){ return norm(s).toLowerCase(); }
function projectIdFrom(url){ const m=String(url||'').match(/\/g\/(g-p-[^/]+)/); return m?m[1]:''; }
function loadPlaywright(moduleRoot){
  const tries=[];
  if(moduleRoot){ tries.push(path.join(moduleRoot,'playwright')); tries.push(path.join(moduleRoot,'playwright-core')); }
  tries.push('playwright'); tries.push('playwright-core');
  let last;
  for(const name of tries){ try{ const mod=require(name); if(mod&&mod.chromium) return mod; }catch(e){ last=e; } }
  throw new Error('PLAYWRIGHT_NODE_MODULE_UNAVAILABLE:'+String(last&&last.message||last||'unknown'));
}
async function visible(locator){ try{ return await locator.isVisible(); }catch(_){ return false; } }
async function firstVisible(loc){ const n=await loc.count().catch(()=>0); for(let i=0;i<n;i++){ const x=loc.nth(i); if(await visible(x)) return x; } return null; }
async function bodyText(page){ return low(await page.locator('body').innerText().catch(()=>'')); }
async function userTexts(page){ return await page.locator('[data-message-author-role="user"]').allInnerTexts().catch(()=>[]); }
async function turnCount(page){
  const a=await page.locator('[data-message-author-role="user"]').count().catch(()=>0);
  const b=await page.locator('[data-message-author-role="assistant"]').count().catch(()=>0);
  return a+b;
}
async function composer(page){
  const candidates=[
    page.locator('div[contenteditable="true"][aria-label*="New chat" i]'),
    page.locator('div[contenteditable="true"][aria-label*="message" i]'),
    page.locator('div[contenteditable="true"]'),
    page.locator('textarea[placeholder*="message" i]'),
    page.locator('textarea')
  ];
  for(const c of candidates){ const x=await firstVisible(c); if(x) return x; }
  return null;
}
async function currentState(page,cfg){
  return await page.evaluate(cfg=>{
    const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
    const vis=el=>{try{const r=el.getBoundingClientRect(),st=getComputedStyle(el);return r.width>0&&r.height>0&&st.display!=='none'&&st.visibility!=='hidden';}catch(_){return false;}};
    const attr=(e,n)=>e.getAttribute(n)||'';
    const selected=e=>attr(e,'aria-checked')==='true'||attr(e,'aria-selected')==='true'||attr(e,'aria-pressed')==='true'||['checked','selected','active'].includes(attr(e,'data-state'));
    const els=[...document.querySelectorAll('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="menuitem"],[role="option"],[aria-checked],[aria-selected],[data-state]')].filter(vis);
    const controls=els.map(e=>({tag:e.tagName.toLowerCase(),role:attr(e,'role'),text:norm(e.innerText||e.textContent).slice(0,180),aria:norm(attr(e,'aria-label')).slice(0,180),title:norm(attr(e,'title')).slice(0,140),checked:attr(e,'aria-checked'),selected:attr(e,'aria-selected'),pressed:attr(e,'aria-pressed'),state:attr(e,'data-state'),isSelected:selected(e)}));
    const turns=[...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"]')].filter(vis);
    const comps=[...document.querySelectorAll('div[contenteditable="true"],textarea')].filter(vis).map(e=>({aria:attr(e,'aria-label'),placeholder:attr(e,'placeholder'),text:norm(e.innerText||e.value||e.textContent).slice(0,400)}));
    const files=[...document.querySelectorAll('input[type="file"]')].map(e=>({accept:e.accept,multiple:e.multiple,files:[...e.files].map(f=>f.name)}));
    return {url:location.href,project:!!cfg.projectId&&location.href.includes(cfg.projectId),turnCount:turns.length,controls,composers:comps,files};
  },{projectId:cfg.projectId});
}
async function clickTextExact(page, regexes){
  const loc=page.locator('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="menuitem"],[role="option"],a');
  const n=await loc.count().catch(()=>0);
  for(const re of regexes){
    for(let i=0;i<n;i++){
      const x=loc.nth(i); if(!(await visible(x))) continue;
      const txt=norm(await x.innerText().catch(()=>''));
      const aria=norm(await x.getAttribute('aria-label').catch(()=>''));
      const title=norm(await x.getAttribute('title').catch(()=>''));
      const v=[txt,aria,title].join(' ');
      if(re.test(v)){ await x.click({timeout:5000}).catch(()=>{}); return true; }
    }
  }
  return false;
}
async function selectedTextPresent(page,re){
  return await page.evaluate(src=>{
    const re=new RegExp(src,'i');
    const vis=el=>{try{const r=el.getBoundingClientRect(),st=getComputedStyle(el);return r.width>0&&r.height>0&&st.display!=='none'&&st.visibility!=='hidden';}catch(_){return false;}};
    const attr=(e,n)=>e.getAttribute(n)||'';
    const selected=e=>attr(e,'aria-checked')==='true'||attr(e,'aria-selected')==='true'||attr(e,'aria-pressed')==='true'||['checked','selected','active'].includes(attr(e,'data-state'));
    return [...document.querySelectorAll('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="menuitem"],[role="option"],[aria-checked],[aria-selected],[data-state]')].filter(vis).some(e=>selected(e)&&re.test(((e.innerText||e.textContent||'')+' '+attr(e,'aria-label')+' '+attr(e,'title')).replace(/\s+/g,' ')));
  },re.source).catch(()=>false);
}
async function visibleTextPresent(page,re){
  const loc=page.locator('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="menuitem"],[role="option"]');
  const n=await loc.count().catch(()=>0);
  for(let i=0;i<n;i++){
    const x=loc.nth(i); if(!(await visible(x))) continue;
    const s=(norm(await x.innerText().catch(()=>''))+' '+norm(await x.getAttribute('aria-label').catch(()=>''))+' '+norm(await x.getAttribute('title').catch(()=>'')));
    if(re.test(s)) return true;
  }
  return false;
}
async function ensureFreshProjectDraft(page,cfg){
  if(!page.url().includes(cfg.projectId)){
    await page.goto(cfg.projectUrl,{waitUntil:'domcontentloaded',timeout:45000});
    await page.waitForTimeout(1800);
  }
  let c=await composer(page), turns=await turnCount(page);
  if(turns===0 && c) return;
  // Re-navigate to project root first. Current ChatGPT Projects often exposes a fresh composer directly there.
  await page.goto(cfg.projectUrl,{waitUntil:'domcontentloaded',timeout:45000});
  await page.waitForTimeout(1800);
  c=await composer(page); turns=await turnCount(page);
  if(turns===0 && c) return;
  // Semantic fallbacks only; never history entries.
  const clicked=await clickTextExact(page,[/^new chat$/i,/new chat in /i,/^chat$/i]);
  if(clicked){ await page.waitForTimeout(1300); }
  c=await composer(page); turns=await turnCount(page);
  if(turns!==0 || !c) throw new Error('FRESH_PROJECT_DRAFT_NOT_PROVEN');
  if(!page.url().includes(cfg.projectId)) throw new Error('FRESH_PROJECT_WRONG_PROJECT');
}
async function ensureChatSurface(page){
  // If Work/Codex is selected, switch to Chat. If no explicit selection metadata exists, a visible normal composer is sufficient.
  const workSel=await selectedTextPresent(page,/\b(work|codex)\b/i);
  if(workSel){
    const ok=await clickTextExact(page,[/^chat$/i,/\bchat\b/i]);
    if(!ok) throw new Error('CHAT_SURFACE_CONTROL_NOT_FOUND');
    await page.waitForTimeout(700);
  }
  const st=await currentState(page,{projectId:''});
  const anyWorkSelected=st.controls.some(c=>c.isSelected&&/\b(work|codex)\b/i.test((c.text+' '+c.aria+' '+c.title)));
  if(anyWorkSelected) throw new Error('CHAT_SURFACE_NOT_PROVEN');
}
async function ensureModelSolHigh(page){
  let modelOk=await visibleTextPresent(page,/GPT[- ]?5\.6\s+Sol/i) || await selectedTextPresent(page,/GPT[- ]?5\.6\s+Sol/i);
  if(!modelOk){
    const modelBtn=await firstVisible(page.locator('button[aria-label*="model" i],button[aria-label*="ChatGPT model" i]'));
    if(modelBtn){ await modelBtn.click({timeout:5000}); await page.waitForTimeout(500); }
    const picked=await clickTextExact(page,[/GPT[- ]?5\.6\s+Sol/i]);
    if(!picked) throw new Error('MODEL_SOL_OPTION_NOT_FOUND');
    await page.waitForTimeout(700);
    modelOk=true; // exact option was deterministically clicked
  }
  let highOk=await visibleTextPresent(page,/^High$/i) || await selectedTextPresent(page,/^High$/i);
  if(!highOk){
    // First try a reasoning/effort button, then direct High option.
    const reasonBtn=await firstVisible(page.locator('button[aria-label*="reason" i],button[aria-label*="thinking" i],button').filter({hasText:/^(Light|Medium|High|Instant)$/i}));
    if(reasonBtn){ await reasonBtn.click({timeout:5000}).catch(()=>{}); await page.waitForTimeout(350); }
    const picked=await clickTextExact(page,[/^High$/i,/\bHigh\b/i]);
    if(!picked) throw new Error('REASONING_HIGH_OPTION_NOT_FOUND');
    await page.waitForTimeout(600); highOk=true;
  }
  if(!modelOk || !highOk) throw new Error('MODEL_POLICY_NOT_PROVEN');
}
async function attachPlan(page,cfg){
  let input=page.locator('input[type="file"]');
  if((await input.count().catch(()=>0))>0){
    await input.first().setInputFiles(cfg.planPath,{timeout:10000});
  }else{
    const plus=await firstVisible(page.locator('button[aria-label*="Add files" i],button[aria-label*="Attach" i],#composer-plus-btn'));
    if(plus){ await plus.click({timeout:5000}).catch(()=>{}); await page.waitForTimeout(350); }
    input=page.locator('input[type="file"]');
    if((await input.count().catch(()=>0))>0){
      await input.first().setInputFiles(cfg.planPath,{timeout:10000});
    }else{
      const up=await firstVisible(page.locator('[role="menuitem"],button').filter({hasText:/upload|add files|computer/i}));
      if(!up) throw new Error('FILE_INPUT_OR_UPLOAD_CONTROL_NOT_FOUND');
      const chooserPromise=page.waitForEvent('filechooser',{timeout:4000}).catch(()=>null);
      await up.click({timeout:5000});
      const chooser=await chooserPromise;
      if(chooser) await chooser.setFiles(cfg.planPath);
      else{
        await page.waitForTimeout(250);
        input=page.locator('input[type="file"]');
        if((await input.count().catch(()=>0))===0) throw new Error('FILE_CHOOSER_NOT_OBSERVED');
        await input.first().setInputFiles(cfg.planPath,{timeout:10000});
      }
    }
  }
  await page.waitForTimeout(900);
  const bt=await bodyText(page);
  const fileByInput=await page.locator('input[type="file"]').evaluateAll((els,n)=>els.some(e=>[...e.files].some(f=>f.name===n)),cfg.planFilename).catch(()=>false);
  if(!bt.includes(low(cfg.planFilename)) && !fileByInput) throw new Error('PLAN_ATTACHMENT_NOT_PROVEN');
}
async function fillComposer(page,cfg){
  const c=await composer(page); if(!c) throw new Error('COMPOSER_NOT_FOUND');
  await c.fill(cfg.message,{timeout:10000}).catch(async()=>{ await c.click(); await page.keyboard.press('Control+A').catch(()=>{}); await page.keyboard.type(cfg.message); });
  await page.waitForTimeout(300);
  const txt=norm(await c.innerText().catch(async()=>await c.inputValue().catch(()=>'')));
  if(!txt.includes(cfg.deliveryId) || !txt.includes(norm(cfg.implementText).slice(0,40))) throw new Error('COMPOSER_TEXT_NOT_PROVEN');
}
async function setLedger(page,cfg,status,extra={}){
  return await page.evaluate(({key,deliveryId,status,extra})=>{
    let old={}; try{old=JSON.parse(localStorage.getItem(key)||'{}')||{};}catch(_){ }
    const next={...old,delivery_id:deliveryId,send_status:status,updated_at:new Date().toISOString(),...extra};
    localStorage.setItem(key,JSON.stringify(next)); return next;
  },{key:'ai_loop_bootstrap_'+cfg.deliveryId,deliveryId:cfg.deliveryId,status,extra});
}
async function verifySent(page,cfg){
  const deadline=Date.now()+22000;
  while(Date.now()<deadline){
    const users=await userTexts(page);
    if(users.some(t=>String(t).includes(cfg.deliveryId)) && /\/c\//.test(page.url())) return true;
    await page.waitForTimeout(500);
  }
  return false;
}
async function saveDiagnostics(page,cfg,label,error){
  if(!cfg.diagDir) return {};
  try{ fs.mkdirSync(cfg.diagDir,{recursive:true}); }catch(_){ }
  const stamp=new Date().toISOString().replace(/[:.]/g,'');
  const base=path.join(cfg.diagDir,stamp+'-'+label);
  let state={}; try{state=await currentState(page,cfg);}catch(_){ }
  try{fs.writeFileSync(base+'.json',JSON.stringify({error:String(error||''),state},null,2));}catch(_){ }
  try{fs.writeFileSync(base+'.html',await page.content());}catch(_){ }
  try{await page.screenshot({path:base+'.png',fullPage:true});}catch(_){ }
  return {json:base+'.json',html:base+'.html',screenshot:base+'.png'};
}
async function detectBusyOrRateLimit(page){
  const body=await bodyText(page);
  if(/too many requests|making requests too quickly|temporarily limited|rate limit/.test(body)) return {rateLimit:true,busy:false};
  const stop=await firstVisible(page.locator('[data-testid*="stop" i],button[aria-label*="Stop" i],button').filter({hasText:/^Stop$|Stop answering|Stop generating/i}));
  if(stop) return {rateLimit:false,busy:true};
  const roles=await page.locator('[data-message-author-role]').evaluateAll(els=>els.filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height}).map(e=>e.getAttribute('data-message-author-role'))).catch(()=>[]);
  if(roles.length && roles[roles.length-1]==='user') return {rateLimit:false,busy:true};
  return {rateLimit:false,busy:false};
}
async function sendExisting(page,cfg){
  if(page.url()!==cfg.targetUrl){ await page.goto(cfg.targetUrl,{waitUntil:'domcontentloaded',timeout:45000}); await page.waitForTimeout(1400); }
  await ensureChatSurface(page); await ensureModelSolHigh(page);
  const existing=(await userTexts(page)).some(t=>String(t).includes(cfg.deliveryId));
  if(existing) return {status:'ALREADY_SENT',clicked:false,safeToRetry:false,url:page.url()};
  const gate=await detectBusyOrRateLimit(page);
  if(gate.rateLimit) return {status:'NOT_SENT_RATE_LIMIT',clicked:false,safeToRetry:true,url:page.url()};
  if(gate.busy) return {status:'NOT_SENT_GENERATING',clicked:false,safeToRetry:true,url:page.url()};
  if(cfg.attachmentPath){
    cfg.planPath=cfg.attachmentPath; cfg.planFilename=cfg.attachmentName||path.basename(cfg.attachmentPath);
    await attachPlan(page,cfg);
  }
  await fillComposer(page,cfg);
  await setLedger(page,cfg,'READY',{url:page.url(),attachment:cfg.attachmentName||''});
  let send=await firstVisible(page.locator('[data-testid="send-button"],button[aria-label*="Send prompt" i],button[aria-label*="Send message" i]'));
  if(!send) throw new Error('SEND_BUTTON_NOT_FOUND');
  for(let i=0;i<10;i++){ if(await send.isEnabled().catch(()=>false)) break; await page.waitForTimeout(250); }
  if(!(await send.isEnabled().catch(()=>false))) throw new Error('SEND_BUTTON_DISABLED');
  await setLedger(page,cfg,'SENDING',{url:page.url(),clicked_at:new Date().toISOString()});
  await send.click({timeout:5000});
  const ok=await verifySent(page,cfg);
  if(!ok) return {status:'AMBIGUOUS_SEND',clicked:true,safeToRetry:false,url:page.url(),error:'DELIVERY_MARKER_NOT_PROVEN_AFTER_CLICK'};
  const ledger=await setLedger(page,cfg,'SENT',{url:page.url(),sent:true,sent_at:new Date().toISOString()});
  return {status:'SENT',clicked:true,safeToRetry:false,url:page.url(),ledger};
}
async function main(){
  const cfgPath=process.argv[2]; if(!cfgPath){emit({status:'ERROR',error:'CONFIG_PATH_MISSING'});process.exit(2);}
  let cfg; try{cfg=JSON.parse(fs.readFileSync(cfgPath,'utf8'));}catch(e){emit({status:'ERROR',error:'CONFIG_INVALID:'+String(e.message||e)});process.exit(2);}
  cfg.projectId=cfg.projectId||projectIdFrom(cfg.projectUrl||cfg.targetUrl);
  cfg.mode=String(cfg.mode||'BOOTSTRAP').toUpperCase();
  if(!cfg.browserProfile){emit({status:'ERROR',error:'CONFIG_MISSING_BROWSER_PROFILE'});process.exit(2);}
  if(cfg.mode==='POLICY_ONLY'){ if(!cfg.targetUrl||!cfg.projectId){emit({status:'ERROR',error:'CONFIG_MISSING_POLICY_FIELDS'});process.exit(2);} }
  else if(cfg.mode==='SEND_EXISTING'){ if(!cfg.targetUrl||!cfg.projectId||!cfg.message||!cfg.deliveryId){emit({status:'ERROR',error:'CONFIG_MISSING_SEND_FIELDS'});process.exit(2);} }
  else if(!cfg.projectUrl||!cfg.projectId||!cfg.planPath||!cfg.planFilename||!cfg.message||!cfg.deliveryId){emit({status:'ERROR',error:'CONFIG_MISSING_REQUIRED_FIELDS'});process.exit(2);}
  const playwright=loadPlaywright(cfg.moduleRoot||'');
  const chromeExe=cfg.chromeExecutable||'/opt/google/chrome/chrome';
  let context,page,clicked=false;
  try{
    context=await playwright.chromium.launchPersistentContext(cfg.browserProfile,{headless:false,executablePath:fs.existsSync(chromeExe)?chromeExe:undefined,viewport:null,args:['--disable-blink-features=AutomationControlled','--disable-session-crashed-bubble','--hide-crash-restore-bubble','--no-first-run','--disable-infobars','--disable-sync']});
    page=context.pages().find(p=>p.url().includes('chatgpt.com'))||context.pages()[0]||await context.newPage();
    if(cfg.mode==='POLICY_ONLY'){
      if(page.url()!==cfg.targetUrl){ await page.goto(cfg.targetUrl,{waitUntil:'domcontentloaded',timeout:45000}); await page.waitForTimeout(1600); }
      await ensureChatSurface(page);
      await ensureModelSolHigh(page);
      const st=await currentState(page,cfg);
      emit({status:'PASS',mode:'POLICY_ONLY',url:page.url(),project:st.project,model:'GPT-5.6 Sol',reasoning:'High',surface:'CHAT'});
      await context.close(); return;
    }
    if(cfg.mode==='SEND_EXISTING'){
      const r=await sendExisting(page,cfg);
      if(r.status==='AMBIGUOUS_SEND'){
        const diag=await saveDiagnostics(page,cfg,'ambiguous-send-existing',r.error); r.diagnostics=diag;
        emit(r); await context.close(); process.exit(9);
      }
      emit(r); await context.close(); return;
    }
    await ensureFreshProjectDraft(page,cfg);
    await ensureChatSurface(page);
    await ensureModelSolHigh(page);
    if(await turnCount(page)!==0) throw new Error('FRESH_DRAFT_LOST_BEFORE_ATTACH');
    await attachPlan(page,cfg);
    await fillComposer(page,cfg);
    const bt=await bodyText(page);
    if(!bt.includes(low(cfg.planFilename))) throw new Error('PLAN_ATTACHMENT_LOST_BEFORE_SEND');
    if(await turnCount(page)!==0) throw new Error('FRESH_DRAFT_LOST_BEFORE_SEND');
    await setLedger(page,cfg,'READY',{url:page.url(),plan_filename:cfg.planFilename});
    let send=await firstVisible(page.locator('[data-testid="send-button"],button[aria-label*="Send prompt" i],button[aria-label*="Send message" i]'));
    if(!send) throw new Error('SEND_BUTTON_NOT_FOUND');
    for(let i=0;i<10;i++){ if(await send.isEnabled().catch(()=>false)) break; await page.waitForTimeout(300); }
    if(!(await send.isEnabled().catch(()=>false))) throw new Error('SEND_BUTTON_DISABLED');
    await setLedger(page,cfg,'SENDING',{url:page.url(),clicked_at:new Date().toISOString()});
    clicked=true;
    await send.click({timeout:5000});
    const ok=await verifySent(page,cfg);
    if(!ok){
      const diag=await saveDiagnostics(page,cfg,'ambiguous-send','DELIVERY_MARKER_NOT_PROVEN_AFTER_CLICK');
      const ledger=await setLedger(page,cfg,'SENDING_UNVERIFIED',{url:page.url(),diagnostics:diag});
      emit({status:'AMBIGUOUS_SEND',error:'DELIVERY_MARKER_NOT_PROVEN_AFTER_CLICK',clicked:true,safeToRetry:false,url:page.url(),ledger,diagnostics:diag});
      await context.close(); process.exit(9);
    }
    const ledger=await setLedger(page,cfg,'SENT',{url:page.url(),sent:true,sent_at:new Date().toISOString()});
    const state=await currentState(page,cfg);
    emit({status:'PASS',clicked:true,safeToRetry:false,url:page.url(),project:state.project,turnCount:state.turnCount,deliveryId:cfg.deliveryId,ledger,model:'GPT-5.6 Sol',reasoning:'High',surface:'CHAT'});
    await context.close();
  }catch(e){
    let diag={}; try{ if(page) diag=await saveDiagnostics(page,cfg,clicked?'post-click-error':'pre-send-error',String(e&&e.message||e)); }catch(_){ }
    try{if(context)await context.close();}catch(_){ }
    emit({status:clicked?'AMBIGUOUS_SEND':'ERROR',error:String(e&&e.message||e).slice(0,1200),clicked,safeToRetry:!clicked,url:page?page.url():'',diagnostics:diag});
    process.exit(clicked?9:6);
  }
}
main();
