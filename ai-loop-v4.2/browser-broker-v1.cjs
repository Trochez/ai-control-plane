#!/usr/bin/env node
'use strict';
const fs=require('fs');
const path=require('path');
const readline=require('readline');
const crypto=require('crypto');

function norm(s){return String(s||'').replace(/\s+/g,' ').trim();}
function low(s){return norm(s).toLowerCase();}
function sha(s){return crypto.createHash('sha256').update(Buffer.from(String(s||''),'utf8')).digest('hex');}
function projectIdFrom(url){const m=String(url||'').match(/\/g\/(g-p-[^/]+)/);return m?m[1]:'';}
function projectNameFrom(url){const m=String(url||'').match(/\/g\/g-p-[^-\/]+-(.+?)(?:\/|$)/);return m?m[1].replace(/-/g,'_'):'';}
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
      response:Number(cfg.responseTimeoutMs||process.env.AI_LOOP_ASSISTANT_RESPONSE_TIMEOUT_MS||900000),
    };
  }
  async start(){
    this.context=await this.pw.chromium.launchPersistentContext(this.cfg.browserProfile,{headless:false,executablePath:this.cfg.chromeExecutable||undefined,args:['--disable-blink-features=AutomationControlled']});
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
    fs.writeFileSync(j,JSON.stringify({at:now(),op,error:String(err&&err.message||err),state:st,extra},null,2));
    try{fs.writeFileSync(h,await this.page.content());}catch(_){ }
    try{await this.page.screenshot({path:p,fullPage:true});}catch(_){ }
    return {json:j,html:h,screenshot:p};
  }
  async waitUntil(fn,timeoutMs,label){const end=Date.now()+timeoutMs;let last;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch(e){last=e;}await sleep(150);}throw new Error('WAIT_TIMEOUT:'+label+(last?':'+last.message:''));}
  async composer(){const sels=['div[contenteditable="true"][aria-label*="New chat" i]','div[contenteditable="true"][aria-label*="message" i]','div[contenteditable="true"]','textarea[placeholder*="message" i]','textarea'];for(const s of sels){const x=await firstVisible(this.page.locator(s));if(x)return x;}return null;}
  async turns(){const u=await this.page.locator('[data-message-author-role="user"]').count().catch(()=>0);const a=await this.page.locator('[data-message-author-role="assistant"]').count().catch(()=>0);return {user:u,assistant:a,total:u+a};}
  async observeContext(projectUrl='',projectId='',projectName=''){
    projectId=projectId||projectIdFrom(projectUrl);projectName=projectName||this.cfg.projectName||'bot_trading';
    return await this.page.evaluate(({projectId,projectName})=>{
      const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
      const vis=e=>{try{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';}catch(_){return false;}};
      const attr=(e,n)=>e.getAttribute(n)||'';
      const selected=e=>attr(e,'aria-current')==='page'||attr(e,'aria-selected')==='true'||attr(e,'aria-checked')==='true'||attr(e,'aria-pressed')==='true'||['checked','selected','active','on'].includes(attr(e,'data-state'));
      const esc=s=>String(s||'').replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
      const allLinks=[...document.querySelectorAll('a[href]')].map(e=>({href:e.href,text:norm(e.innerText||e.textContent),aria:norm(attr(e,'aria-label')),selected:selected(e),visible:vis(e)}));
      const links=allLinks.filter(x=>x.visible);
      const comps=[...document.querySelectorAll('div[contenteditable="true"],textarea')].filter(vis).map(e=>({aria:norm(attr(e,'aria-label')),placeholder:norm(attr(e,'placeholder')),text:norm(e.innerText||e.value||e.textContent)}));
      const controls=[...document.querySelectorAll('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="option"],[aria-selected],[aria-checked],[data-state]')].filter(vis).map(e=>({text:norm(e.innerText||e.textContent),aria:norm(attr(e,'aria-label')),title:norm(attr(e,'title')),role:attr(e,'role'),selected:selected(e),checked:attr(e,'aria-checked'),state:attr(e,'data-state')}));
      const targetLinksAll=allLinks.filter(x=>projectId&&x.href.includes(projectId));
      const targetLinks=targetLinksAll.filter(x=>x.visible);
      const selectedTarget=targetLinksAll.some(x=>x.visible&&x.selected);
      const nameRe=projectName?new RegExp('(^|\\b)'+esc(projectName).replace(/[_-]+/g,'[_\\s-]+')+'(\\b|$)','i'):null;
      const composerTarget=comps.some(c=>projectName&&new RegExp('new chat in\\s+'+esc(projectName).replace(/[_-]+/g,'[_\\s-]+'),'i').test(c.aria+' '+c.placeholder));
      const headerTarget=[...document.querySelectorAll('h1,h2,h3,[aria-label],[data-testid]')].filter(vis).some(e=>{const t=norm((e.innerText||e.textContent)+' '+attr(e,'aria-label'));return !!nameRe&&nameRe.test(t)&&!e.closest('[data-message-author-role]');});
      const otherSelected=allLinks.some(x=>x.visible&&x.selected&&/\/g\/g-p-/.test(x.href)&&projectId&&!x.href.includes(projectId));
      const composerOther=comps.some(c=>/new chat in\s+/i.test(c.aria+' '+c.placeholder)&&projectName&&!new RegExp(esc(projectName).replace(/[_-]+/g,'[_\\s-]+'),'i').test(c.aria+' '+c.placeholder));
      const urlTarget=!!projectId&&location.href.includes(projectId);
      const positive=[];
      if(urlTarget)positive.push('url_project_id');
      if(targetLinksAll.length)positive.push('project_anchor_mapped');
      if(targetLinks.length)positive.push('sidebar_target_link_present');
      if(selectedTarget)positive.push('selected_sidebar_project_id');
      if(composerTarget)positive.push('project_scoped_composer');
      if(headerTarget)positive.push('project_header');
      const negative=[];if(otherSelected)negative.push('other_selected_project');if(composerOther)negative.push('other_project_composer');
      let projectContext='UNKNOWN';
      if(negative.length)projectContext='OTHER';
      else if(urlTarget||selectedTarget||(composerTarget&&targetLinksAll.length)||positive.filter(x=>x!=='sidebar_target_link_present').length>=2)projectContext='TARGET';
      const user=[...document.querySelectorAll('[data-message-author-role="user"]')].filter(vis).map(e=>norm(e.innerText||e.textContent));
      const assistant=[...document.querySelectorAll('[data-message-author-role="assistant"]')].filter(vis).map(e=>norm(e.innerText||e.textContent));
      return {url:location.href,projectContext,projectEvidence:{positive,negative,targetLinks:targetLinks.slice(0,8),targetLinksAll:targetLinksAll.slice(0,8),selectedTarget,composerTarget,headerTarget},composers:comps,controls:controls.slice(0,200),turns:{user:user.length,assistant:assistant.length,total:user.length+assistant.length},userTexts:user,assistantTexts:assistant};
    },{projectId,projectName});
  }
  async _freshTargetState(projectUrl,projectId,projectName){
    const q=await this.observeContext(projectUrl,projectId,projectName);
    const cp=await this.composer();
    return q.projectContext==='TARGET'&&q.turns.total===0&&!!cp?q:null;
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
  async clickMatching(re){const loc=this.page.locator('button,[role="button"],[role="tab"],[role="radio"],[role="menuitemradio"],[role="menuitem"],[role="option"],a');const n=await loc.count().catch(()=>0);for(let i=0;i<n;i++){const x=loc.nth(i);if(!(await x.isVisible().catch(()=>false)))continue;const s=norm((await x.innerText().catch(()=>''))+' '+(await x.getAttribute('aria-label').catch(()=>''))+' '+(await x.getAttribute('title').catch(()=>'')));if(re.test(s)){await x.click();return true;}}return false;}
  async ensurePolicy(args){
    if(args.targetUrl && this.page.url()!==args.targetUrl){ await this.page.goto(args.targetUrl,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav}); }
    // Chat surface
    if(await this.selectedText(/\b(work|codex)\b/i)){if(!(await this.clickMatching(/^chat$/i)))throw new Error('CHAT_SURFACE_CONTROL_NOT_FOUND');}
    // model: open selector if not already positively selected
    if(!(await this.selectedText(/GPT[- ]?5\.6\s+Sol/i))){const b=await firstVisible(this.page.locator('button[aria-label*="model" i],button[aria-label*="ChatGPT model" i]'));if(b)await b.click();if(!(await this.clickMatching(/GPT[- ]?5\.6\s+Sol/i)))throw new Error('MODEL_SOL_OPTION_NOT_FOUND');}
    // reasoning
    if(!(await this.selectedText(/^High$/i))){const r=await firstVisible(this.page.locator('button[aria-label*="reason" i],button[aria-label*="thinking" i],button').filter({hasText:/^(Light|Medium|High|Instant)$/i}));if(r)await r.click().catch(()=>{});if(!(await this.clickMatching(/^High$/i)))throw new Error('REASONING_HIGH_OPTION_NOT_FOUND');}
    // re-read selected state; clicks are not proof
    const ok=await this.waitUntil(async()=>{const v={chat:!(await this.selectedText(/\b(work|codex)\b/i)),model:await this.selectedText(/GPT[- ]?5\.6\s+Sol/i),high:await this.selectedText(/^High$/i)};return v.chat&&v.model&&v.high?v:null;},this.timeouts.settle,'policy_selected').catch(()=>null);
    const final={chat:!(await this.selectedText(/\b(work|codex)\b/i)),model:await this.selectedText(/GPT[- ]?5\.6\s+Sol/i),high:await this.selectedText(/^High$/i)};
    if(!final.chat||!final.model||!final.high)throw new Error('MODEL_POLICY_NOT_PROVEN_SELECTED_STATE');
    return final;
  }
  async attachFile(filePath,fileName){
    const c=await this.composer();if(!c)throw new Error('COMPOSER_NOT_FOUND');
    let input=this.page.locator('input[type="file"]');
    if(!(await input.count())){
      const plus=await firstVisible(this.page.locator('button[aria-label*="Add files" i],button[aria-label*="Attach" i],#composer-plus-btn'));if(plus)await plus.click().catch(()=>{});
      input=this.page.locator('input[type="file"]');
    }
    if(await input.count()){await input.first().setInputFiles(filePath);}
    else{
      const up=await firstVisible(this.page.locator('[role="menuitem"],button').filter({hasText:/upload|add files|computer/i}));if(!up)throw new Error('FILE_INPUT_OR_UPLOAD_CONTROL_NOT_FOUND');
      const fc=this.page.waitForEvent('filechooser',{timeout:this.timeouts.action});await up.click();const chooser=await fc;await chooser.setFiles(filePath);
    }
    await this.waitUntil(async()=>{const near=await this.page.locator('input[type="file"]').evaluateAll((els,n)=>els.some(e=>[...e.files].some(f=>f.name===n)),fileName).catch(()=>false);if(near)return true;const cp=await this.composer();if(!cp)return false;const root=cp.locator('xpath=ancestor::*[self::form or @data-testid="composer" or contains(@class,"composer")][1]');const r=(await root.count())?root:this.page.locator('main');return await r.getByText(fileName,{exact:false}).count().catch(()=>0)>0;},this.timeouts.settle,'attachment_proof');
    return true;
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
    const before=await this.observeContext(args.projectUrl,args.projectId,args.projectName);if(before.projectContext!=='TARGET')throw new Error('SEND_WRONG_PROJECT');
    const users=before.userTexts||[];if(users.some(t=>t.includes(marker)))return {status:'ALREADY_SENT',clicked:false,url:before.url,project:true,delivery_present:true};
    const send=await firstVisible(this.page.locator('[data-testid="send-button"],button[aria-label*="Send" i],button[type="submit"]'));if(!send)throw new Error('SEND_BUTTON_NOT_FOUND');if(!(await send.isEnabled().catch(()=>false)))throw new Error('SEND_BUTTON_DISABLED');
    const key='ai_loop_bootstrap_'+args.deliveryId;await this.page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:key,v:{delivery_id:args.deliveryId,send_status:'SENDING',clicked_at:now()}});
    await send.click();
    const after=await this.waitUntil(async()=>{const q=await this.observeContext(args.projectUrl,args.projectId,args.projectName);return q.userTexts.some(t=>t.includes(marker))&&q.projectContext==='TARGET'?q:null;},30000,'delivery_marker_after_send').catch(()=>null);
    if(!after){const ledger={delivery_id:args.deliveryId,send_status:'AMBIGUOUS',sent:false,url:this.page.url()};await this.page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:key,v:ledger});return {status:'AMBIGUOUS_SEND',clicked:true,safeToRetry:false,url:this.page.url(),ledger,error:'DELIVERY_MARKER_NOT_PROVEN_AFTER_CLICK'};}
    const ledger={delivery_id:args.deliveryId,send_status:'SENT',sent:true,url:after.url,sent_at:now()};await this.page.evaluate(({k,v})=>localStorage.setItem(k,JSON.stringify(v)),{k:key,v:ledger});return {status:'PASS',clicked:true,safeToRetry:false,url:after.url,ledger,project:true,delivery_present:true};
  }

  async observeDelivery(args){
    const marker='[AI_LOOP_DELIVERY id='+args.deliveryId+']';
    const visited=[];
    const candidates=[];
    const add=u=>{u=String(u||'');if(!u||candidates.includes(u))return;candidates.push(u);};
    add(this.page.url()); for(const u of (args.candidateUrls||[])) add(u);
    const links=await this.page.locator('a[href*="/c/"]').evaluateAll(els=>els.map(e=>e.href)).catch(()=>[]);
    for(const u of links) add(u);
    let found=false,foundUrl='';
    for(const u of candidates.slice(0,Number(args.maxChats||16))){
      try{if(u!==this.page.url()) await this.page.goto(u,{waitUntil:'domcontentloaded',timeout:this.timeouts.nav});}catch(_){continue;}
      visited.push(this.page.url());
      const st=await this.observeContext(args.projectUrl,args.projectId,args.projectName).catch(()=>null);
      if(st&&st.projectContext==='TARGET'&&(st.userTexts||[]).some(t=>t.includes(marker))){found=true;foundUrl=st.url;break;}
    }
    let ledger={};try{ledger=await this.page.evaluate(k=>JSON.parse(localStorage.getItem(k)||'{}')||{},'ai_loop_bootstrap_'+args.deliveryId);}catch(_){ }
    return {status:'PASS',found,url:found?foundUrl:this.page.url(),project:found,visited,candidateCount:candidates.length,scanComplete:visited.length>=Math.min(candidates.length,Number(args.maxChats||16)),ledger};
  }
  async observeResponse(args){
    const state=await this.observeContext(args.projectUrl,args.projectId,args.projectName);const assistants=this.page.locator('[data-message-author-role="assistant"]');const n=await assistants.count().catch(()=>0);if(!n)return {generation_state:'NO_ASSISTANT',...state};
    const last=assistants.nth(n-1);const text=norm(await last.innerText().catch(()=>''));const id=(await last.getAttribute('data-message-id').catch(()=>''))||(await last.getAttribute('data-testid').catch(()=>''))||('assistant-'+(n-1));
    const gen=await this.page.locator('[data-testid*="stop" i],button[aria-label*="Stop" i]').count().catch(()=>0)>0;
    const rate=/too many requests|rate limit|try again later/i.test(await this.page.locator('body').innerText().catch(()=>''));
    const dir=path.join(this.cfg.runDir||'/tmp','browser','responses');fs.mkdirSync(dir,{recursive:true});const p=path.join(dir,id.replace(/[^A-Za-z0-9_.-]/g,'_')+'.txt');fs.writeFileSync(p,text,'utf8');
    const blocks=await last.locator('pre code, pre').evaluateAll(els=>els.map((e,i)=>({block_index:i,language:(e.className||'').match(/language-([^\s]+)/)?.[1]||'',text:e.textContent||'',context_before:'',context_after:''}))).catch(()=>[]);
    const meta=blocks.map(b=>({block_index:b.block_index,language:b.language,sha256:sha(b.text),bytes:Buffer.byteLength(b.text,'utf8')}));
    return {...state,generation_state:rate?'RATE_LIMIT':gen?'GENERATING':'SETTLED',assistant_message_id:id,assistant_text_path:p,assistant_text_sha256:sha(text),assistant_text:text,turn_structure:{assistant_count:n,code_blocks:meta}};
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
    if(op==='ATTACH_FILE')return {status:'PASS',evidence:{attached:await this.attachFile(args.path,args.name)}};
    if(op==='FILL_COMPOSER'){await this.fillComposer(args.message);return {status:'PASS'};}
    if(op==='SEND_ATOMIC')return await this.sendAtomic(args);
    if(op==='OBSERVE_RESPONSE')return {status:'PASS',evidence:await this.observeResponse(args)};
    if(op==='OBSERVE_DELIVERY')return {status:'PASS',evidence:await this.observeDelivery(args)};
    if(op==='MATERIALIZE_CODE_BLOCK')return {status:'PASS',evidence:await this.materializeCodeBlock(args)};
    if(op==='DOWNLOAD_ARTIFACT')return {status:'PASS',evidence:await this.downloadArtifact(args)};
    if(op==='SEMAPHORE_READONLY')return {status:'PASS',evidence:await this.semaphoreReadonly(args)};
    if(op==='CAPTURE_DIAGNOSTICS')return {status:'PASS',evidence:await this.diag(args.label||'manual',new Error('manual capture'),args)};
    if(op==='CLOSE'){await this.close();return {status:'PASS'};}
    throw new Error('UNKNOWN_OPERATION:'+op);
  }
}

module.exports={Broker,projectIdFrom,projectNameFrom,norm,low,sha};

if(require.main===module)(async()=>{
  const cfgPath=process.argv[2];if(!cfgPath)throw new Error('CONFIG_PATH_REQUIRED');const cfg=JSON.parse(fs.readFileSync(cfgPath,'utf8'));const b=new Broker(cfg);await b.start();
  process.stdout.write(JSON.stringify({broker_ready:true,epoch:b.epoch})+'\n');
  const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
  for await (const line of rl){if(!line.trim())continue;let req;try{req=JSON.parse(line);}catch(e){process.stdout.write(JSON.stringify({request_id:'',status:'ERROR',error:'INVALID_JSON:'+e.message})+'\n');continue;}
    const base={request_id:req.request_id||'',epoch:b.epoch};try{const out=await b.handle(req);process.stdout.write(JSON.stringify({...base,...out})+'\n');if(req.operation==='CLOSE')break;}catch(e){const d=await b.diag(req.operation||'unknown',e,req.arguments||{}).catch(()=>({}));process.stdout.write(JSON.stringify({...base,status:'ERROR',error:String(e&&e.message||e),evidence:{diagnostics:d}})+'\n');}
  }
  await b.close().catch(()=>{});
})().catch(e=>{process.stderr.write('BROKER_FATAL '+String(e&&e.stack||e)+'\n');process.exit(1);});
