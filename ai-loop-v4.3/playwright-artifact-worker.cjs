#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function die(code, error, extra={}) {
  emit({status:'ERROR', error, ...extra});
  process.exit(code);
}

function loadPlaywright(moduleRoot) {
  const tries = [];
  if (moduleRoot) {
    tries.push(path.join(moduleRoot, 'playwright'));
    tries.push(path.join(moduleRoot, 'playwright-core'));
  }
  tries.push('playwright');
  tries.push('playwright-core');
  let last;
  for (const name of tries) {
    try {
      const mod = require(name);
      if (mod && mod.chromium) return mod;
    } catch (e) { last = e; }
  }
  throw new Error('PLAYWRIGHT_NODE_MODULE_UNAVAILABLE:' + String(last && last.message || last || 'unknown'));
}

const {TextDecoder} = require('util');

const MIN_PLAN_BYTES = 1500;
const MAX_PLAN_BYTES = 1000000;
const NETWORK_CAPTURE_MS = 3200;
const MAX_NETWORK_CANDIDATES = 80;
const MAX_UI_CLICKS = 1;
const MAX_DOM_CANDIDATES = 80;
const MAX_RESOURCE_URLS = 160;

function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function normalizeHeaders(headers={}) {
  const out={};
  for (const [k,v] of Object.entries(headers||{})) out[String(k).toLowerCase()]=String(v||'');
  return out;
}

function inspectArtifactBody(buf, headers={}, url='') {
  const h=normalizeHeaders(headers);
  const ct=String(h['content-type']||'').toLowerCase();
  const cd=String(h['content-disposition']||'').toLowerCase();
  const result={
    valid:false, score:0, reason:'UNKNOWN', bytes:buf ? buf.length : 0,
    sha256:buf ? sha256(buf) : '', contentType:ct, contentDisposition:cd, url:String(url||''),
    pointerUrls:[]
  };
  if (!buf || !Buffer.isBuffer(buf)) { result.reason='BODY_MISSING'; return result; }
  if (buf.length < MIN_PLAN_BYTES) result.reason='TOO_SHORT';
  else if (buf.length > MAX_PLAN_BYTES) result.reason='TOO_LARGE';
  if (/text\/html|application\/xhtml/.test(ct)) { result.reason='HTML_RESPONSE'; return result; }
  let text='';
  try { text=new TextDecoder('utf-8',{fatal:true}).decode(buf); }
  catch (_) { result.reason='UTF8_INVALID'; return result; }
  if (/^\s*<!doctype html/i.test(text) || /^\s*<html[\s>]/i.test(text)) { result.reason='HTML_RESPONSE'; return result; }

  // Small JSON/metadata responses are not artifacts, but may point at the real file.
  const maybeJson=/application\/(?:json|problem\+json)|text\/json/.test(ct) || /^[\s\r\n]*[\[{]/.test(text);
  if (maybeJson) {
    const found=new Set();
    const add=(v)=>{
      if (typeof v!=='string') return;
      const t=v.trim();
      if (/^https?:\/\//i.test(t) || /^\//.test(t)) found.add(t);
    };
    try {
      const obj=JSON.parse(text);
      const walk=(v,depth=0)=>{
        if (depth>8 || v==null) return;
        if (typeof v==='string') { add(v); return; }
        if (Array.isArray(v)) { for (const x of v.slice(0,100)) walk(x,depth+1); return; }
        if (typeof v==='object') for (const [k,x] of Object.entries(v)) {
          if (/url|href|download|file|attachment|content/i.test(k)) add(x);
          walk(x,depth+1);
        }
      };
      walk(obj);
    } catch (_) {}
    for (const m of text.matchAll(/https?:\\?\/\\?\/[^"'\\s<>]+/g)) {
      add(String(m[0]).replace(/\\\//g,'/'));
    }
    result.pointerUrls=[...found].slice(0,20);
  }

  const low=text.toLowerCase();
  const lines=text.split(/\r?\n/).filter(x=>x.trim()).length;
  const missing=[];
  if (!low.includes('plan')) missing.push('plan');
  if (!low.includes('semaphore')) missing.push('semaphore');
  const impl=/(implementation|implementacion|implementación|backlog|team|equipo|complete_go|release|remediation|remediacion|remediación)/i.test(text);
  const backlog=/(backlog|task|tarea)/i.test(text);
  const roles=/(role|roles|team|equipo)/i.test(text);
  if (result.reason==='TOO_SHORT' || result.reason==='TOO_LARGE') return result;
  if (missing.length) { result.reason='MISSING_ANCHORS:'+missing.join(','); return result; }
  if (!impl) { result.reason='NOT_IMPLEMENTATION_PLAN'; return result; }
  if (!backlog) { result.reason='MISSING_BACKLOG'; return result; }
  if (!roles) { result.reason='MISSING_ROLES'; return result; }
  if (lines < 15) { result.reason='INSUFFICIENT_STRUCTURE'; return result; }

  result.valid=true;
  result.reason='VALID';
  result.score=100;
  if (/filename\*?=.*\.md/i.test(cd)) result.score+=80;
  if (/attachment/i.test(cd)) result.score+=35;
  if (/text\/markdown|text\/plain/.test(ct)) result.score+=45;
  if (/\.md(?:$|[?#])/i.test(String(url||''))) result.score+=60;
  if (/download|attachment|file/i.test(String(url||''))) result.score+=15;
  return result;
}

function safeUrlForLog(raw) {
  const u=String(raw||'');
  if (!u) return '';
  if (/^data:/i.test(u)) return 'data:[redacted]';
  if (/^blob:/i.test(u)) return 'blob:[redacted]';
  if (/^sandbox:/i.test(u)) return u.split(/[?#]/,1)[0].slice(0,500);
  try {
    const x=new URL(u);
    return `${x.protocol}//${x.host}${x.pathname}`.slice(0,700) + (x.search ? '?[redacted]' : '');
  } catch (_) {
    return u.split('#',1)[0].split('?',1)[0].slice(0,700);
  }
}

function newCandidateJournal() {
  return {
    entries:[], rejectedHashes:new Set(), visitedUrls:new Set(), clickedKeys:new Set(), uiClicks:0,
    domCandidates:[], resourceUrls:new Set(), rawPreviewCandidates:0,
    zeroClick:{started:false,domUrlsTried:0,performanceUrlsTried:0,rawPreviewTried:0,accepted:false},
  };
}

function addJournalEntry(journal, entry) {
  const compact={
    source:String(entry.source||''), url:safeUrlForLog(entry.url||''),
    status:Number(entry.status||0), bytes:Number(entry.bytes||0), sha256:String(entry.sha256||''),
    contentType:String(entry.contentType||'').slice(0,180), contentDisposition:String(entry.contentDisposition||'').slice(0,240),
    decision:String(entry.decision||''), reason:String(entry.reason||''), score:Number(entry.score||0)
  };
  journal.entries.push(compact);
  if (journal.entries.length>120) journal.entries.splice(0,journal.entries.length-120);
}

function recordDomCandidate(journal, c, scope='') {
  const attrs={};
  for (const [k,v] of Object.entries(c.attrs||{})) attrs[k]=String(v||'').slice(0,240);
  journal.domCandidates.push({
    scope:String(scope||''), tag:String(c.tag||''), text:String(c.text||'').slice(0,220),
    aria:String(c.aria||'').slice(0,180), title:String(c.title||'').slice(0,180),
    urls:(c.urls||[]).map(safeUrlForLog).slice(0,12), attrs
  });
  if (journal.domCandidates.length>MAX_DOM_CANDIDATES) journal.domCandidates.splice(0,journal.domCandidates.length-MAX_DOM_CANDIDATES);
}

function candidateSummary(journal) {
  const accepted=journal.entries.filter(x=>x.decision==='ACCEPT').length;
  const rejected=journal.entries.filter(x=>x.decision.startsWith('REJECT')).length;
  const dupes=journal.entries.filter(x=>x.decision==='REJECT_DUPLICATE_HASH').length;
  return {
    accepted,rejected,duplicates:dupes,uiClicks:journal.uiClicks,
    rejectedHashes:[...journal.rejectedHashes].slice(-20), candidates:journal.entries.slice(-30),
    domCandidateCount:journal.domCandidates.length, domCandidates:journal.domCandidates.slice(-20),
    resourceUrlCount:journal.resourceUrls.size, resourceUrls:[...journal.resourceUrls].slice(-30).map(safeUrlForLog),
    rawPreviewCandidates:journal.rawPreviewCandidates, zeroClick:{...journal.zeroClick}
  };
}

function resolveMaybeRelativeUrl(raw, base) {
  if (!raw) return '';
  const text=String(raw).trim();
  if (/^(?:blob:|data:|sandbox:)/i.test(text)) return text;
  try { return new URL(text,base).href; } catch (_) { return ''; }
}

function decodeDataUrl(raw) {
  const text=String(raw||'');
  const m=text.match(/^data:([^,]*?),(.*)$/s);
  if (!m) return null;
  const meta=m[1]||'';
  const payload=m[2]||'';
  const base64=/(?:^|;)base64(?:;|$)/i.test(meta);
  const contentType=(meta.split(';')[0] || 'text/plain').trim() || 'text/plain';
  try {
    const body=base64 ? Buffer.from(payload,'base64') : Buffer.from(decodeURIComponent(payload),'utf8');
    return {body,headers:{'content-type':contentType},url:'data:'};
  } catch (_) { return null; }
}

async function browserFetchResource(page, url) {
  try {
    const obj=await page.evaluate(async (u,maxBytes) => {
      const r=await fetch(u,{credentials:'include'});
      const ab=await r.arrayBuffer();
      if (ab.byteLength > maxBytes) return {ok:false,error:'RESOURCE_TOO_LARGE',status:r.status,bytes:ab.byteLength};
      const bytes=new Uint8Array(ab);
      let binary='';
      for (let i=0;i<bytes.length;i+=0x8000) binary += String.fromCharCode(...bytes.subarray(i,i+0x8000));
      const headers={}; r.headers.forEach((v,k)=>{headers[k]=v;});
      return {ok:true,status:r.status,url:r.url||u,headers,base64:btoa(binary)};
    }, url, MAX_PLAN_BYTES*2);
    if (!obj || !obj.ok) return null;
    return {body:Buffer.from(obj.base64||'','base64'),headers:obj.headers||{},url:obj.url||url,status:Number(obj.status||200)};
  } catch (_) { return null; }
}

async function tryResourceUrl(page, context, rawUrl, dest, reason, baseUrl, journal, depth=0) {
  journal=journal || newCandidateJournal();
  if (depth>2) return null;
  const abs=resolveMaybeRelativeUrl(rawUrl,baseUrl||page.url());
  if (!abs) return null;
  journal.resourceUrls.add(abs);
  if (journal.visitedUrls.has(abs)) return null;
  journal.visitedUrls.add(abs);

  let payload=null;
  if (/^https?:/i.test(abs)) {
    try {
      const opts={timeout:18000,failOnStatusCode:false,maxRedirects:8};
      if (baseUrl) opts.headers={referer:baseUrl};
      const resp=await context.request.get(abs,opts);
      payload={body:await resp.body(),headers:resp.headers(),url:resp.url(),status:resp.status()};
    } catch (_) { return null; }
  } else if (/^data:/i.test(abs)) {
    const d=decodeDataUrl(abs); if (!d) return null;
    payload={...d,status:200};
  } else if (/^(?:blob:|sandbox:)/i.test(abs)) {
    payload=await browserFetchResource(page,abs);
    if (!payload) {
      addJournalEntry(journal,{source:reason,url:abs,status:0,bytes:0,sha256:'',contentType:'',contentDisposition:'',decision:'REJECT_TRANSPORT_UNRESOLVED',reason:/^sandbox:/i.test(abs)?'SANDBOX_RESOURCE_UNRESOLVED':'BLOB_RESOURCE_UNRESOLVED'});
      return null;
    }
  } else return null;

  const inspected=inspectArtifactBody(payload.body,payload.headers,payload.url);
  const duplicate=journal.rejectedHashes.has(inspected.sha256);
  if (!inspected.valid && inspected.sha256) journal.rejectedHashes.add(inspected.sha256);
  addJournalEntry(journal,{source:reason,url:payload.url,status:payload.status,...inspected,decision:inspected.valid?'CANDIDATE_VALID':(duplicate?'REJECT_DUPLICATE_HASH':'REJECT'),reason:inspected.reason});
  const candidate={...payload,...inspected,duplicate};
  if (candidate.valid) return writeAcceptedCandidate(candidate,dest,reason,journal);
  for (const ptr of inspected.pointerUrls || []) {
    const got=await tryResourceUrl(page,context,ptr,dest,reason+':metadata-pointer',payload.url||baseUrl,journal,depth+1);
    if (got) return got;
  }
  return null;
}

function shouldObserveResponse(resp) {
  try {
    const u=String(resp.url()||'');
    // Ignore high-volume resources that cannot be the Markdown plan body. Keep
    // document/xhr/fetch/other responses because ChatGPT file transports may use
    // any of them and v2.29/v2.30 showed that URL heuristics alone are insufficient.
    if (/google-analytics|doubleclick|sentry|telemetry|metrics|statsig|segment\.io|intercom/i.test(u)) return false;
    const req=resp.request && resp.request();
    const rt=req && req.resourceType ? String(req.resourceType()||'') : '';
    if (['image','font','stylesheet','media','script'].includes(rt)) return false;
    return true;
  } catch (_) { return false; }
}

async function responseCandidate(resp, source, journal) {
  try {
    if (!shouldObserveResponse(resp)) return null;
    const headers=await resp.allHeaders().catch(()=>({}));
    const h=normalizeHeaders(headers);
    const cl=Number(h['content-length']||0);
    if (cl > MAX_PLAN_BYTES*2) return null;
    const body=await resp.body();
    const inspected=inspectArtifactBody(body,headers,resp.url());
    const duplicate=journal.rejectedHashes.has(inspected.sha256);
    if (!inspected.valid) journal.rejectedHashes.add(inspected.sha256);
    addJournalEntry(journal,{source,url:resp.url(),status:resp.status(),...inspected,decision:inspected.valid?'CANDIDATE_VALID':(duplicate?'REJECT_DUPLICATE_HASH':'REJECT'),reason:inspected.reason});
    return {body,headers,url:resp.url(),status:resp.status(),...inspected,duplicate};
  } catch (_) { return null; }
}

function writeAcceptedCandidate(candidate, dest, method, journal) {
  if (!candidate || !candidate.valid) return null;
  fs.mkdirSync(path.dirname(dest), {recursive:true, mode:0o700});
  fs.writeFileSync(dest,candidate.body,{mode:0o600});
  addJournalEntry(journal,{source:method,url:candidate.url,status:candidate.status,bytes:candidate.body.length,sha256:candidate.sha256,contentType:candidate.contentType,contentDisposition:candidate.contentDisposition,decision:'ACCEPT',reason:'VALID',score:candidate.score});
  return {method,url:candidate.url,bytes:candidate.body.length,sha256:candidate.sha256};
}

async function requestUrl(context, url, dest, reason, referer='', journal=null, depth=0) {
  journal=journal || newCandidateJournal();
  const abs=resolveMaybeRelativeUrl(url,referer||url);
  if (!abs || !/^https?:/i.test(abs) || depth>2) return null;
  if (journal.visitedUrls.has(abs)) return null;
  journal.visitedUrls.add(abs);
  try {
    const opts={timeout:18000, failOnStatusCode:false, maxRedirects:8};
    if (referer) opts.headers={referer};
    const resp=await context.request.get(abs,opts);
    const headers=resp.headers();
    const body=await resp.body();
    const inspected=inspectArtifactBody(body,headers,resp.url());
    const duplicate=journal.rejectedHashes.has(inspected.sha256);
    if (!inspected.valid) journal.rejectedHashes.add(inspected.sha256);
    addJournalEntry(journal,{source:reason,url:resp.url(),status:resp.status(),...inspected,decision:inspected.valid?'CANDIDATE_VALID':(duplicate?'REJECT_DUPLICATE_HASH':'REJECT'),reason:inspected.reason});
    const candidate={body,headers,url:resp.url(),status:resp.status(),...inspected,duplicate};
    if (resp.ok() && candidate.valid) return writeAcceptedCandidate(candidate,dest,reason,journal);
    // Metadata often contains the signed file URL. Follow it deterministically instead
    // of misclassifying the metadata body itself as the Markdown artifact.
    for (const ptr of inspected.pointerUrls || []) {
      const purl=resolveMaybeRelativeUrl(ptr,resp.url());
      const got=await requestUrl(context,purl,dest,reason+':metadata-pointer',resp.url(),journal,depth+1);
      if (got) return got;
    }
  } catch (_) {}
  return null;
}

async function validateDownloadedFile(tempPath, source, url, journal) {
  try {
    if (!fs.existsSync(tempPath)) return null;
    const body=fs.readFileSync(tempPath);
    const inspected=inspectArtifactBody(body,{'content-disposition':'attachment'},url||'');
    const duplicate=journal.rejectedHashes.has(inspected.sha256);
    if (!inspected.valid) journal.rejectedHashes.add(inspected.sha256);
    addJournalEntry(journal,{source,url,status:200,...inspected,decision:inspected.valid?'CANDIDATE_VALID':(duplicate?'REJECT_DUPLICATE_HASH':'REJECT'),reason:inspected.reason});
    return {body,headers:{},url:url||'',status:200,...inspected,duplicate};
  } catch (_) { return null; }
}

async function clickAndCapture(page, locator, context, dest, label, journal) {
  journal=journal || newCandidateJournal();
  const clickKey=String(label||'control');
  if (journal.clickedKeys.has(clickKey)) return {result:null,popup:null,error:'CONTROL_ALREADY_CLICKED'};
  journal.clickedKeys.add(clickKey);
  if (journal.uiClicks>=MAX_UI_CLICKS) return {result:null,popup:null,error:'UI_CLICK_BUDGET_EXHAUSTED'};
  journal.uiClicks += 1;

  const responsePromises=[];
  const handler=(resp)=>{
    if (responsePromises.length>=MAX_NETWORK_CANDIDATES || !shouldObserveResponse(resp)) return;
    responsePromises.push(responseCandidate(resp,'network-response:'+label,journal));
  };
  page.on('response',handler);
  const popupPromise=page.waitForEvent('popup',{timeout:5000}).catch(()=>null);
  const downloadPromise=page.waitForEvent('download',{timeout:5000}).catch(()=>null);
  try {
    await locator.scrollIntoViewIfNeeded().catch(()=>{});
    await locator.click({timeout:7000});
  } catch (e) {
    page.off('response',handler);
    return {result:null,popup:null,error:'CLICK_FAILED:'+String(e.message||e).slice(0,300)};
  }

  const download=await downloadPromise;
  if (download) {
    const temp=dest+'.native-download.tmp';
    try {
      await download.saveAs(temp);
      const cand=await validateDownloadedFile(temp,'download-event:'+label,download.url(),journal);
      try { fs.unlinkSync(temp); } catch (_) {}
      if (cand && cand.valid) return {result:writeAcceptedCandidate(cand,dest,'download-event:'+label,journal),popup:null};
    } catch (_) { try { fs.unlinkSync(temp); } catch (_) {} }
  }

  const popup=await popupPromise;
  await page.waitForTimeout(NETWORK_CAPTURE_MS).catch(()=>{});
  page.off('response',handler);
  const settled=await Promise.allSettled(responsePromises);
  const candidates=settled.filter(x=>x.status==='fulfilled' && x.value).map(x=>x.value);
  const valid=candidates.filter(x=>x.valid).sort((a,b)=>b.score-a.score || b.bytes-a.bytes);
  if (valid.length) return {result:writeAcceptedCandidate(valid[0],dest,'network-response:'+label,journal),popup};

  // Rejected metadata responses may contain a signed artifact URL. Follow every
  // unique pointer before interacting with the UI again.
  for (const c of candidates) {
    for (const ptr of c.pointerUrls || []) {
      const got=await requestUrl(context,resolveMaybeRelativeUrl(ptr,c.url),dest,'network-metadata-pointer:'+label,c.url,journal,1);
      if (got) return {result:got,popup};
    }
  }
  return {result:null,popup};
}

async function collectCandidateMetadata(root) {
  return await root.evaluate((node) => {
    const out=[];
    const seen=new Set();
    const selectors=['a','button','[role="button"]','[role="link"]','[data-testid]','[aria-label]','[title]','[download]','[src]','[data-file-id]','[data-attachment-id]'];
    const elems=[];
    if (node.matches && node.matches(selectors.join(','))) elems.push(node);
    elems.push(...node.querySelectorAll(selectors.join(',')));
    const signalRe=/\.md(?:\b|$)|download(?:\s+the)?(?:\s+approved)?\s+plan|attachment|file\s*card|download\s*file|blob:|sandbox:|data:/i;
    const urlish=/^(?:https?:|blob:|data:|sandbox:|\/)/i;
    for (const el of elems) {
      const text=String(el.innerText||el.textContent||'').trim().replace(/\s+/g,' ').slice(0,500);
      const attrs={}; const urls=[];
      for (const a of [...(el.attributes||[])]) {
        const name=String(a.name||''); const value=String(a.value||'');
        if (/^(?:href|src|download|title|aria-|data-|value|type)/i.test(name)) attrs[name]=value.slice(0,500);
        if (urlish.test(value.trim())) urls.push(value.trim());
      }
      const href=el.getAttribute&&el.getAttribute('href')||'';
      const src=el.getAttribute&&el.getAttribute('src')||'';
      const aria=el.getAttribute&&(el.getAttribute('aria-label')||'')||'';
      const title=el.getAttribute&&(el.getAttribute('title')||'')||'';
      if (href && !urls.includes(href)) urls.push(href);
      if (src && !urls.includes(src)) urls.push(src);
      const joined=[text,href,src,aria,title,...Object.values(attrs)].filter(Boolean).join(' ');
      if (!signalRe.test(joined)) continue;
      const key=[el.tagName,href,src,text,aria,title].join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      const id='ai-loop-artifact-'+out.length;
      el.setAttribute('data-ai-loop-artifact-candidate',id);
      out.push({id,tag:el.tagName,text,href,src,aria,title,attrs,urls:[...new Set(urls)].slice(0,30)});
    }
    return out;
  });
}

async function inspectExistingRawPreview(page, scopedRoot, dest, journal, label='zero-click-preview') {
  const rows=await page.locator('pre,textarea').evaluateAll((els)=>els.slice(0,40).map((el,i)=>{
    const text=String(el.value!==undefined && el.tagName==='TEXTAREA' ? el.value : (el.textContent||''));
    let cur=el; let signal='';
    for (let d=0;cur&&d<7;d++,cur=cur.parentElement) {
      signal += ' ' + String(cur.getAttribute&&cur.getAttribute('data-testid')||'') + ' ' + String(cur.getAttribute&&cur.getAttribute('aria-label')||'') + ' ' + String(cur.getAttribute&&cur.getAttribute('title')||'') + ' ' + String(cur.className&&typeof cur.className==='string'?cur.className:'');
      const own=String(cur.innerText||'').slice(0,1000); if (/\.md\b|download(?:\s+the)?(?:\s+approved)?\s+plan|attachment|file\s*card/i.test(own)) signal += ' '+own;
    }
    return {i,tag:el.tagName,text:text.slice(0,1000000),signal:signal.slice(0,5000),insideTurn:Boolean(el.closest('[data-ai-loop-turn-candidate]'))};
  }));
  for (const row of rows) {
    if (row.insideTurn) continue; // never reconstruct the plan from inline assistant prose/code.
    if (!/\.md\b|download(?:\s+the)?(?:\s+approved)?\s+plan|attachment|file|preview/i.test(row.signal||'')) continue;
    if (!row.text || row.text.length<MIN_PLAN_BYTES) continue;
    journal.rawPreviewCandidates += 1;
    const body=Buffer.from(row.text,'utf8');
    const inspected=inspectArtifactBody(body,{'content-type':'text/markdown'},`dom-preview://${row.tag.toLowerCase()}/${row.i}`);
    const duplicate=journal.rejectedHashes.has(inspected.sha256);
    if (!inspected.valid && inspected.sha256) journal.rejectedHashes.add(inspected.sha256);
    addJournalEntry(journal,{source:label,url:`dom-preview://${row.tag.toLowerCase()}/${row.i}`,status:200,...inspected,decision:inspected.valid?'CANDIDATE_VALID':(duplicate?'REJECT_DUPLICATE_HASH':'REJECT'),reason:inspected.reason});
    journal.zeroClick.rawPreviewTried += 1;
    if (inspected.valid) {
      const candidate={body,headers:{'content-type':'text/markdown'},url:`dom-preview://${row.tag.toLowerCase()}/${row.i}`,status:200,...inspected,duplicate};
      journal.zeroClick.accepted=true;
      return writeAcceptedCandidate(candidate,dest,label,journal);
    }
  }
  return null;
}

async function performanceArtifactUrls(page) {
  try {
    return await page.evaluate(()=>{
      const re=/\.md(?:$|[?#])|download|attachment|file|blob:|sandbox:/i;
      return [...new Set(performance.getEntriesByType('resource').map(e=>String(e.name||'')).filter(u=>re.test(u)))].slice(-160);
    });
  } catch (_) { return []; }
}

function normalizedTurnText(text) {
  return String(text || '').replace(/\s+/g, ' ').trim();
}

function textSha256(text) {
  return crypto.createHash('sha256').update(Buffer.from(normalizedTurnText(text), 'utf8')).digest('hex');
}

async function discoverPhysicalTurns(page, sourceMessageId='') {
  return await page.evaluate(({sourceMessageId}) => {
    const diagnostics = {
      pageUrl: location.href,
      title: document.title || '',
      conversationTurnCount: document.querySelectorAll('[data-testid^="conversation-turn-"]').length,
      articleCount: document.querySelectorAll('article').length,
      roleAttrCount: document.querySelectorAll('[data-message-author-role]').length,
      assistantRoleAttrCount: document.querySelectorAll('[data-message-author-role="assistant"]').length,
      userRoleAttrCount: document.querySelectorAll('[data-message-author-role="user"]').length,
      mainCount: document.querySelectorAll('main').length,
      artifactControlCount: 0,
      strongArtifactControlCount: 0,
      candidateCount: 0,
      assistantLikelyCount: 0,
      artifactTurnCount: 0,
      strongArtifactTurnCount: 0,
    };

    const strongArtifactRe = /download(?:\s+the)?(?:\s+approved)?\s+plan|\.md(?:\b|$)|attachment|file\s*card|download\s*file/i;
    const weakArtifactRe = /\.md\b|download(?:\s+the)?(?:\s+approved)?\s+plan/i;
    const roots = [];
    const seen = new Set();

    function elementText(el) {
      return String((el && (el.innerText || el.textContent)) || '');
    }
    function joinedMeta(el) {
      if (!el) return '';
      return [
        elementText(el),
        el.getAttribute && el.getAttribute('href') || '',
        el.getAttribute && el.getAttribute('aria-label') || '',
        el.getAttribute && el.getAttribute('title') || '',
        el.getAttribute && el.getAttribute('data-testid') || '',
        el.getAttribute && el.getAttribute('data-message-author-role') || '',
        el.id || '',
        el.className && typeof el.className === 'string' ? el.className : ''
      ].join(' ');
    }
    function nearestCanonical(el) {
      if (!el || !(el instanceof Element)) return null;
      const exact = el.closest('[data-testid^="conversation-turn-"]') || el.closest('article') || el.closest('[data-message-id]');
      if (exact) return exact;
      // ChatGPT DOM schemas change. For a visible plan/file control, prefer the
      // smallest non-trivial section/div ancestor that still contains the signal.
      let cur = el;
      for (let depth=0; cur && depth<9; depth++, cur=cur.parentElement) {
        if (!cur || ['HTML','BODY'].includes(cur.tagName) || cur.tagName === 'MAIN') continue;
        const txt = elementText(cur);
        if (txt.length >= 16 && txt.length <= 160000 && weakArtifactRe.test(joinedMeta(cur))) return cur;
      }
      return el.parentElement || el;
    }
    function addRoot(el, source) {
      const root = nearestCanonical(el);
      if (!root || !(root instanceof Element) || seen.has(root)) return;
      seen.add(root);
      roots.push({root, sources:[source]});
    }

    // DOM-schema independent discovery. Start with stable-ish conversation/semantic
    // containers, then role nodes, then artifact controls themselves.
    document.querySelectorAll('[data-testid^="conversation-turn-"]').forEach(el => addRoot(el,'conversation-turn'));
    document.querySelectorAll('article').forEach(el => addRoot(el,'article'));
    document.querySelectorAll('[data-message-id]').forEach(el => addRoot(el,'data-message-id'));
    document.querySelectorAll('[data-message-author-role]').forEach(el => addRoot(el,'message-author-role'));

    const artifactUniverse = [...document.querySelectorAll('a[href],button,[role="button"],[role="link"],[data-testid],[aria-label],[title]')];
    for (const el of artifactUniverse) {
      const meta = joinedMeta(el);
      if (!weakArtifactRe.test(meta) && !/attachment|file\s*card/i.test(meta)) continue;
      diagnostics.artifactControlCount += 1;
      if (strongArtifactRe.test(meta)) diagnostics.strongArtifactControlCount += 1;
      addRoot(el,'artifact-control');
    }

    // If the page uses none of the known containers but contains the visible plan
    // filename as raw text, promote its nearest useful ancestor as a physical turn.
    if (!roots.length) {
      const all = [...document.querySelectorAll('div,section,li')];
      for (const el of all) {
        const txt = elementText(el);
        if (txt.length < 16 || txt.length > 120000) continue;
        if (!weakArtifactRe.test(txt)) continue;
        addRoot(el,'artifact-text-fallback');
      }
    }

    roots.sort((a,b) => {
      if (a.root === b.root) return 0;
      const pos = a.root.compareDocumentPosition(b.root);
      if (pos & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
      if (pos & Node.DOCUMENT_POSITION_PRECEDING) return 1;
      return 0;
    });

    const out=[];
    for (const item of roots) {
      const root=item.root;
      const text=elementText(root);
      const testid=root.getAttribute('data-testid') || '';
      const attrs=[...(root.attributes || [])].map(x=>`${x.name}=${x.value}`).join(' ');
      const html=String(root.outerHTML || '');
      const roleNodes=[root, ...root.querySelectorAll('[data-message-author-role]')];
      const roles=roleNodes.map(el=>String(el.getAttribute && el.getAttribute('data-message-author-role') || '').toLowerCase()).filter(Boolean);
      const explicitAssistant=roles.includes('assistant');
      const explicitUser=roles.includes('user');
      const controls=[...root.querySelectorAll('a[href],button,[role="button"],[role="link"],[data-testid],[aria-label],[title]')];
      let strongArtifactSignal=false;
      let artifactSignal=weakArtifactRe.test(text);
      for (const el of controls) {
        const meta=joinedMeta(el);
        if (weakArtifactRe.test(meta) || /attachment|file\s*card/i.test(meta)) artifactSignal=true;
        if (strongArtifactRe.test(meta)) strongArtifactSignal=true;
      }
      const rootMeta=joinedMeta(root);
      if (strongArtifactRe.test(rootMeta)) strongArtifactSignal=true;
      const roleMeta=[testid,root.getAttribute('aria-label')||'',root.id||'',typeof root.className==='string'?root.className:''].join(' ').toLowerCase();
      const assistantLikely=explicitAssistant || (!explicitUser && (strongArtifactSignal || /assistant|response|answer/.test(roleMeta)));
      const userLikely=explicitUser || (!explicitAssistant && /user|prompt/.test(roleMeta));
      const id='ai-loop-physical-turn-'+out.length;
      root.setAttribute('data-ai-loop-turn-candidate',id);
      out.push({
        id,index:out.length,testid,text,
        sources:item.sources,
        explicitAssistant,explicitUser,assistantLikely,userLikely,
        hasArtifactSignal:Boolean(artifactSignal),
        hasStrongArtifactSignal:Boolean(strongArtifactSignal),
        containsSourceMessageId:Boolean(sourceMessageId && (attrs.includes(sourceMessageId) || html.includes(sourceMessageId)))
      });
    }
    diagnostics.candidateCount=out.length;
    diagnostics.assistantLikelyCount=out.filter(x=>x.assistantLikely).length;
    diagnostics.artifactTurnCount=out.filter(x=>x.hasArtifactSignal).length;
    diagnostics.strongArtifactTurnCount=out.filter(x=>x.hasStrongArtifactSignal).length;
    return {turns:out, diagnostics};
  }, {sourceMessageId});
}

async function findScopedRoot(page, cfg) {
  const sourceMessageId = String(cfg.sourceMessageId || '').replace(/^msg:/,'').trim();
  const sourceTurnTestId = String(cfg.sourceTurnTestId || '').trim();
  const sourceTextSha256 = String(cfg.sourceTextSha256 || '').trim().toLowerCase();
  const rawIndex = cfg.sourceTurnIndex;
  const sourceTurnIndex = Number.isInteger(rawIndex) ? rawIndex : (String(rawIndex ?? '').match(/^-?\d+$/) ? Number(rawIndex) : -1);
  const allowLatestArtifactFallback = cfg.allowLatestArtifactFallback !== false;

  // Give the dynamic ChatGPT thread a bounded chance to hydrate. This is internal
  // worker waiting, not an external controller retry and never invokes a model.
  let discovered={turns:[],diagnostics:{}};
  for (let i=0;i<4;i++) {
    discovered=await discoverPhysicalTurns(page,sourceMessageId);
    if ((discovered.turns||[]).length || Number((discovered.diagnostics||{}).artifactControlCount||0)>0) break;
    await page.waitForTimeout(1200 + i*600).catch(()=>{});
  }

  const turns=discovered.turns || [];
  const diagnostics=discovered.diagnostics || {};
  const enriched = turns.map(t => ({...t, textSha256: textSha256(t.text)}));
  let chosen = null;
  let locatorMethod = '';

  if (sourceTurnTestId) {
    chosen = enriched.find(t => t.testid === sourceTurnTestId) || null;
    if (chosen) locatorMethod = 'source-turn-testid';
  }
  if (!chosen && sourceMessageId && /^conversation-turn-/i.test(sourceMessageId)) {
    chosen = enriched.find(t => t.testid === sourceMessageId) || null;
    if (chosen) locatorMethod = 'source-message-as-turn-testid';
  }
  if (!chosen && sourceMessageId) {
    chosen = enriched.find(t => t.containsSourceMessageId) || null;
    if (chosen) locatorMethod = 'source-message-dom-occurrence';
  }
  if (!chosen && /^[0-9a-f]{64}$/i.test(sourceTextSha256)) {
    const matches = enriched.filter(t => t.textSha256 === sourceTextSha256);
    if (matches.length === 1) {
      chosen = matches[0]; locatorMethod = 'source-text-sha256';
    } else if (matches.length > 1) {
      return {root:null, error:'AMBIGUOUS_PLAN_TURN', detail:'source-text-sha256 matched multiple physical turn candidates', diagnostics, turns:enriched.map(({text,...r})=>r)};
    }
  }
  if (!chosen && sourceTurnIndex >= 0) {
    // Prefer an assistant-likely index because older semantic inspectors indexed
    // assistant messages, not arbitrary DOM containers. Fall back to all candidates.
    const assistantCandidates=enriched.filter(t=>t.assistantLikely && !t.userLikely);
    if (sourceTurnIndex < assistantCandidates.length) {
      chosen=assistantCandidates[sourceTurnIndex]; locatorMethod='source-turn-index-assistant';
    } else if (sourceTurnIndex < enriched.length) {
      chosen=enriched[sourceTurnIndex]; locatorMethod='source-turn-index-physical';
    }
  }
  if (!chosen && allowLatestArtifactFallback) {
    // Strong controls (actual .md link/card/download button) are superior to prose
    // that merely mentions a filename. Under PLAN_READY recovery the newest strong
    // artifact-bearing non-user turn is the deterministic physical target.
    let artifactTurns=enriched.filter(t=>t.hasStrongArtifactSignal && !t.explicitUser);
    if (!artifactTurns.length) artifactTurns=enriched.filter(t=>t.hasArtifactSignal && !t.explicitUser);
    if (!artifactTurns.length) artifactTurns=enriched.filter(t=>t.hasStrongArtifactSignal || t.hasArtifactSignal);
    if (artifactTurns.length) {
      chosen=artifactTurns[artifactTurns.length-1];
      locatorMethod=chosen.hasStrongArtifactSignal?'latest-strong-artifact-turn':'latest-artifact-turn';
    }
  }

  if (!chosen) {
    return {
      root:null,
      error:'ASSISTANT_TURN_LOCATOR_FAILED',
      detail:'no physical turn matched source identity and no artifact-bearing fallback turn was discoverable',
      diagnostics,
      turns:enriched.slice(-20).map(({text,...r})=>r)
    };
  }
  const root = page.locator(`[data-ai-loop-turn-candidate="${chosen.id}"]`).first();
  if (!await root.count()) {
    return {root:null,error:'ASSISTANT_TURN_LOCATOR_FAILED',detail:'chosen physical turn locator disappeared',diagnostics,turns:enriched.slice(-20).map(({text,...r})=>r)};
  }
  return {
    root, locatorMethod, turnTestId:chosen.testid || '', turnIndex:chosen.index,
    textSha256:chosen.textSha256, hasArtifactSignal:Boolean(chosen.hasArtifactSignal),
    hasStrongArtifactSignal:Boolean(chosen.hasStrongArtifactSignal), diagnostics
  };
}

async function scanHrefCandidates(page, root, context, dest, chatUrl, journal) {
  journal=journal || newCandidateJournal();
  journal.zeroClick.started=true;
  const rootMeta=await collectCandidateMetadata(root);
  const body=page.locator('body').first();
  const pageMeta=await collectCandidateMetadata(body);
  const merged=[]; const seen=new Set();
  for (const [scope,list] of [['turn',rootMeta],['page',pageMeta]]) {
    for (const c of list) {
      recordDomCandidate(journal,c,scope);
      const key=[c.tag,c.text,c.href,c.src,JSON.stringify(c.urls||[])].join('|');
      if (seen.has(key)) continue; seen.add(key); merged.push(c);
    }
  }
  merged.sort((a,b)=>{
    const score=x=>(/download(?: the)? (?:approved )?plan/i.test(x.text)?0:/\.md\b/i.test([x.href,x.src,...(x.urls||[])].join(' '))?1:/\.md\b/i.test(x.text)?2:3);
    return score(a)-score(b);
  });

  // ZERO-CLICK lane: consume every discoverable transport URL before changing UI.
  for (const c of merged) {
    for (const raw of c.urls || []) {
      journal.zeroClick.domUrlsTried += 1;
      const got=await tryResourceUrl(page,context,raw,dest,'zero-click-dom-url',page.url(),journal,0);
      if (got) { journal.zeroClick.accepted=true; return got; }
    }
  }

  // If an existing side preview exposes the raw Markdown in a PRE/TEXTAREA outside
  // the conversation turn, it is a byte source, not a reconstruction from rendered prose.
  const rawPreview=await inspectExistingRawPreview(page,root,dest,journal,'zero-click-existing-preview');
  if (rawPreview) return rawPreview;

  // Resource entries may already contain a signed file endpoint because an earlier
  // v2.28/v2.29 run opened the preview. Consume them without any new click.
  const preResources=await performanceArtifactUrls(page);
  for (const u of preResources.reverse()) {
    journal.zeroClick.performanceUrlsTried += 1;
    const got=await tryResourceUrl(page,context,u,dest,'zero-click-performance-resource',page.url(),journal,0);
    if (got) { journal.zeroClick.accepted=true; return got; }
  }

  // SINGLE-INTERACTION fallback. One visible control may be activated once. The
  // worker then re-inspects DOM/network/blob/data/sandbox/raw-preview state, but never
  // clicks a second preview/download control in this run.
  // `collectCandidateMetadata(body)` is the last pass that stamped DOM candidate IDs,
  // so choose the click target from that pool to avoid stale/colliding IDs from the
  // earlier turn-scoped enumeration.
  const openerPool=pageMeta.length ? pageMeta : rootMeta;
  const opener=openerPool.find(c=>/download(?: the)? (?:approved )?plan/i.test(c.text)) || openerPool.find(c=>/\.md\b/i.test(c.text)) || openerPool[0];
  let popup=null;
  if (opener) {
    const loc=page.locator(`[data-ai-loop-artifact-candidate="${opener.id}"]`).first();
    if (await loc.count()) {
      const click=await clickAndCapture(page,loc,context,dest,'single-artifact-interaction:'+opener.id,journal);
      if (click.result && fs.existsSync(dest)) return click.result;
      popup=click.popup;
    }
  }

  const postBodyMeta=await collectCandidateMetadata(page.locator('body').first());
  for (const c of postBodyMeta) {
    recordDomCandidate(journal,c,'post-click-page');
    for (const raw of c.urls || []) {
      const got=await tryResourceUrl(page,context,raw,dest,'post-click-dom-url',page.url(),journal,0);
      if (got) return got;
    }
  }
  const postPreview=await inspectExistingRawPreview(page,root,dest,journal,'post-click-existing-preview');
  if (postPreview) return postPreview;
  const postResources=await performanceArtifactUrls(page);
  for (const u of postResources.reverse()) {
    const got=await tryResourceUrl(page,context,u,dest,'post-click-performance-resource',page.url(),journal,0);
    if (got) return got;
  }

  if (popup) {
    try {
      await popup.waitForLoadState('domcontentloaded',{timeout:7000}).catch(()=>{});
      const popupMeta=await collectCandidateMetadata(popup.locator('body').first());
      for (const c of popupMeta) {
        recordDomCandidate(journal,c,'popup');
        for (const raw of c.urls || []) {
          const got=await tryResourceUrl(popup,popup.context(),raw,dest,'popup-dom-url',popup.url(),journal,0);
          if (got) return got;
        }
      }
      const popupPreview=await inspectExistingRawPreview(popup,null,dest,journal,'popup-existing-preview');
      if (popupPreview) return popupPreview;
      const popupResources=await performanceArtifactUrls(popup);
      for (const u of popupResources.reverse()) {
        const got=await tryResourceUrl(popup,popup.context(),u,dest,'popup-performance-resource',popup.url(),journal,0);
        if (got) return got;
      }
    } catch (_) {}
  }
  return null;
}

async function main() {
  const cfgPath = process.argv[2];
  if (!cfgPath) die(2,'CONFIG_PATH_REQUIRED');
  let cfg;
  try { cfg = JSON.parse(fs.readFileSync(cfgPath,'utf8')); }
  catch (e) { die(2,'CONFIG_INVALID:'+String(e.message||e)); }

  const playwright = loadPlaywright(cfg.moduleRoot || process.env.AI_LOOP_PLAYWRIGHT_MODULE_ROOT || '');
  const chromeExe = cfg.chromeExecutable || process.env.AI_LOOP_CHROME_EXECUTABLE || '/opt/google/chrome/chrome';
  const profile = cfg.browserProfile;
  const dest = cfg.destination;
  if (!profile || !dest || !cfg.chatUrl) die(2,'CONFIG_MISSING_REQUIRED_FIELDS');

  let context;
  try {
    context = await playwright.chromium.launchPersistentContext(profile, {
      headless:false,
      executablePath: fs.existsSync(chromeExe) ? chromeExe : undefined,
      acceptDownloads:true,
      viewport:null,
      args:[
        '--disable-blink-features=AutomationControlled',
        '--disable-session-crashed-bubble',
        '--hide-crash-restore-bubble',
        '--no-first-run', '--disable-infobars', '--disable-sync'
      ]
    });
    let page = context.pages().find(p => p.url().includes('chatgpt.com')) || context.pages()[0] || await context.newPage();
    if (!page.url().startsWith(cfg.chatUrl)) {
      await page.goto(cfg.chatUrl, {waitUntil:'domcontentloaded', timeout:45000});
    }
    await page.waitForTimeout(2500);
    const journal = newCandidateJournal();
    const scoped = await findScopedRoot(page, cfg);
    if (!scoped.root) die(4,scoped.error || 'ASSISTANT_TURN_LOCATOR_FAILED',{sourceMessageId:cfg.sourceMessageId||'',detail:scoped.detail||'',diagnostics:scoped.diagnostics||{},turns:scoped.turns||[]});
    const result = await scanHrefCandidates(page, scoped.root, context, dest, cfg.chatUrl, journal);
    if (!result || !fs.existsSync(dest)) die(5,'PLAN_ARTIFACT_NO_VALID_CANDIDATE',{sourceMessageId:cfg.sourceMessageId||'',candidateSummary:candidateSummary(journal)});
    const bytes = fs.readFileSync(dest);
    const sha = crypto.createHash('sha256').update(bytes).digest('hex');
    emit({status:'PASS', method:result.method||'deterministic-browser', bytes:bytes.length, sha256:sha, sourceMessageId:cfg.sourceMessageId||'', locatorMethod:scoped.locatorMethod||'', turnTestId:scoped.turnTestId||'', turnIndex:scoped.turnIndex, textSha256:scoped.textSha256||'', hasStrongArtifactSignal:Boolean(scoped.hasStrongArtifactSignal), diagnostics:scoped.diagnostics||{}, candidateSummary:candidateSummary(journal), url:result.url||''});
    await context.close();
    process.exit(0);
  } catch (e) {
    try { if (context) await context.close(); } catch (_) {}
    die(6,'WORKER_EXCEPTION:'+String(e && e.message || e).slice(0,1000));
  }
}

if (require.main === module) {
  main();
}

module.exports = {inspectArtifactBody, candidateSummary, newCandidateJournal, decodeDataUrl, safeUrlForLog, shouldObserveResponse, responseCandidate};
