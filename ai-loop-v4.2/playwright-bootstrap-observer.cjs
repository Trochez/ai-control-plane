#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function emit(obj){ process.stdout.write(JSON.stringify(obj)+'\n'); }
function die(code,error,extra={}){ emit({status:'ERROR',error,...extra}); process.exit(code); }
function loadPlaywright(moduleRoot){
  const tries=[];
  if(moduleRoot){ tries.push(path.join(moduleRoot,'playwright')); tries.push(path.join(moduleRoot,'playwright-core')); }
  tries.push('playwright'); tries.push('playwright-core');
  let last;
  for(const name of tries){ try{ const mod=require(name); if(mod&&mod.chromium) return mod; } catch(e){ last=e; } }
  throw new Error('PLAYWRIGHT_NODE_MODULE_UNAVAILABLE:'+String(last&&last.message||last||'unknown'));
}
function norm(s){ return String(s||'').replace(/\s+/g,' ').trim(); }
function projectIdFrom(url){ const m=String(url||'').match(/\/g\/(g-p-[^/]+)/); return m?m[1]:''; }
function absUrl(href,base){ try{return new URL(href,base).toString();}catch(_){return '';} }

async function inspect(page,cfg){
  return await page.evaluate(cfg=>{
    const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
    const vis=el=>{try{const r=el.getBoundingClientRect(),st=getComputedStyle(el);return r.width>0&&r.height>0&&st.display!=='none'&&st.visibility!=='hidden';}catch(e){return false;}};
    const users=[...document.querySelectorAll('[data-message-author-role="user"]')].filter(vis).map(e=>norm(e.innerText||e.textContent)).filter(Boolean);
    const marker='[AI_LOOP_DELIVERY id='+cfg.deliveryId+']';
    const found=users.some(t=>t.includes(marker)||t.includes(cfg.deliveryId));
    const links=[...document.querySelectorAll('a[href]')].filter(vis).map(a=>({href:a.getAttribute('href')||'',text:norm(a.innerText||a.textContent).slice(0,180)}));
    const key='ai_loop_bootstrap_'+cfg.deliveryId; let ledger={}; try{ledger=JSON.parse(localStorage.getItem(key)||'{}')||{};}catch(_){}
    return {url:location.href,project:!!cfg.projectId&&location.href.includes(cfg.projectId),found,userTexts:users.slice(-12),links,ledger};
  },cfg);
}

async function main(){
  const cfgPath=process.argv[2];
  if(!cfgPath) die(2,'CONFIG_PATH_MISSING');
  let cfg; try{cfg=JSON.parse(fs.readFileSync(cfgPath,'utf8'));}catch(e){die(2,'CONFIG_INVALID:'+String(e.message||e));}
  if(!cfg.projectUrl||!cfg.deliveryId||!cfg.browserProfile) die(2,'CONFIG_MISSING_REQUIRED_FIELDS');
  cfg.projectId=cfg.projectId||projectIdFrom(cfg.projectUrl);
  cfg.maxChats=Math.max(1,Math.min(160,Number(cfg.maxChats||16)));
  cfg.candidateUrls=Array.isArray(cfg.candidateUrls)?cfg.candidateUrls:[];
  const playwright=loadPlaywright(cfg.moduleRoot||'');
  const chromeExe=cfg.chromeExecutable||'/opt/google/chrome/chrome';
  let context;
  try{
    context=await playwright.chromium.launchPersistentContext(cfg.browserProfile,{
      headless:false,
      executablePath:fs.existsSync(chromeExe)?chromeExe:undefined,
      viewport:null,
      args:['--disable-blink-features=AutomationControlled','--disable-session-crashed-bubble','--hide-crash-restore-bubble','--no-first-run','--disable-infobars','--disable-sync']
    });
    let page=context.pages().find(p=>p.url().includes('chatgpt.com'))||context.pages()[0]||await context.newPage();
    if(!page.url().includes(cfg.projectId)){
      await page.goto(cfg.projectUrl,{waitUntil:'domcontentloaded',timeout:45000});
      await page.waitForTimeout(2200);
    }
    let obs=await inspect(page,cfg);
    const visited=[];
    if(obs.found && obs.project && /\/c\//.test(obs.url)){
      emit({status:'PASS',found:true,url:obs.url,project:true,deliveryId:cfg.deliveryId,visited,userTexts:obs.userTexts,ledger:obs.ledger||{},candidateCount:0,scanComplete:true});
      await context.close(); return;
    }
    if(!obs.project){
      await page.goto(cfg.projectUrl,{waitUntil:'domcontentloaded',timeout:45000});
      await page.waitForTimeout(2200);
      obs=await inspect(page,cfg);
    }
    const seen=new Set();
    const candidates=[];
    for(const raw of cfg.candidateUrls){
      const u=absUrl(raw,cfg.projectUrl);
      if(!u||!u.includes('/g/'+cfg.projectId+'/c/')||seen.has(u)) continue;
      seen.add(u); candidates.push({url:u,text:'explicit'});
    }
    for(const l of obs.links||[]){
      const u=absUrl(l.href,obs.url||cfg.projectUrl);
      if(!u||!u.includes('/g/'+cfg.projectId+'/c/')) continue;
      if(seen.has(u)) continue; seen.add(u); candidates.push({url:u,text:l.text||''});
    }
    // Current URL is checked first if it is already a project chat.
    if(obs.url&&obs.url.includes('/g/'+cfg.projectId+'/c/')&&!seen.has(obs.url)) candidates.unshift({url:obs.url,text:'current'});
    for(const c of candidates.slice(0,cfg.maxChats)){
      visited.push(c.url);
      if(page.url()!==c.url){
        try{ await page.goto(c.url,{waitUntil:'domcontentloaded',timeout:35000}); await page.waitForTimeout(1300); }
        catch(_){ continue; }
      }
      const cur=await inspect(page,cfg);
      if(cur.found&&cur.project&&/\/c\//.test(cur.url)){
        emit({status:'PASS',found:true,url:cur.url,project:true,deliveryId:cfg.deliveryId,visited,userTexts:cur.userTexts,ledger:cur.ledger||{},candidateCount:candidates.length,scanComplete:true});
        await context.close(); return;
      }
    }
    const fin=await inspect(page,cfg);
    emit({status:'PASS',found:false,url:page.url(),project:page.url().includes(cfg.projectId),deliveryId:cfg.deliveryId,visited,candidateCount:candidates.length,scanComplete:true,ledger:fin.ledger||{}});
    await context.close();
  }catch(e){ try{if(context)await context.close();}catch(_){} die(6,'WORKER_EXCEPTION:'+String(e&&e.message||e).slice(0,1200)); }
}

main();
