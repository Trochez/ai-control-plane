#!/usr/bin/env node
'use strict';
const assert=require('assert');
const {Broker}=require('../browser-broker-v1.cjs');

function fakeBroker(initialMode='historical',rootMode='fresh'){
  const b=Object.create(Broker.prototype);
  let mode=initialMode;
  let gotos=0;
  let clicks=0;
  const urlFor=()=>mode==='historical'?'https://chatgpt.com/g/g-p-test-bot-trading/c/old':'https://chatgpt.com/';
  b.timeouts={nav:100,settle:100,action:100,response:100};
  b.page={
    url:()=>urlFor(),
    goto:async()=>{gotos++;mode=rootMode;},
  };
  b.observeContext=async()=>{
    if(mode==='historical')return {url:urlFor(),projectContext:'TARGET',turns:{user:1,assistant:1,total:2},userTexts:['old'],assistantTexts:['old']};
    if(mode==='fresh')return {url:urlFor(),projectContext:'TARGET',turns:{user:0,assistant:0,total:0},userTexts:[],assistantTexts:[]};
    if(mode==='target-not-fresh')return {url:urlFor(),projectContext:'TARGET',turns:{user:1,assistant:0,total:1},userTexts:['old'],assistantTexts:[]};
    return {url:urlFor(),projectContext:'UNKNOWN',turns:{user:0,assistant:0,total:0},userTexts:[],assistantTexts:[]};
  };
  b.composer=async()=>mode==='fresh'?{}:null;
  b.resolveActiveComposer=async()=>mode==='fresh'?{present:true,root_selector_kind:'data-chatgpt-composer',composer_text:'',attachments:[]}:({present:false,root_selector_kind:'none',attachments:[]});
  b.waitUntil=async(fn,_timeout,label)=>{for(let i=0;i<5;i++){const v=await fn();if(v)return v;}throw new Error('WAIT_TIMEOUT:'+label);};
  b.navigateProject=Broker.prototype.navigateProject.bind(b);
  b._freshTargetState=Broker.prototype._freshTargetState.bind(b);
  b._waitFreshTarget=Broker.prototype._waitFreshTarget.bind(b);
  b._clickFreshChatCandidate=async()=>{clicks++;mode='fresh';return {clicked:true,label:'mock'};};
  b.ensureFreshProjectDraft=Broker.prototype.ensureFreshProjectDraft.bind(b);
  return {b,get mode(){return mode},get gotos(){return gotos},get clicks(){return clicks}};
}

(async()=>{
  // Exact production regression: correct target project but historical /c/ chat loaded.
  // v4.1 returned early from project navigation and timed out; v4.2 MUST force project root.
  let f=fakeBroker('historical','fresh');
  let out=await f.b.ensureFreshProjectDraft({projectUrl:'https://chatgpt.com/g/g-p-test-bot-trading',projectId:'g-p-test-bot-trading',projectName:'bot_trading'});
  assert.equal(out.projectContext,'TARGET'); assert.equal(out.turns.total,0); assert.equal(f.gotos,1); assert.equal(f.clicks,0);
  console.log('BROKER_TEST_V4_2_HISTORICAL_TARGET_FORCES_ROOT=PASS');

  // Already-fresh target draft must be zero-navigation fast path.
  f=fakeBroker('fresh','fresh');
  out=await f.b.ensureFreshProjectDraft({projectUrl:'https://chatgpt.com/g/g-p-test-bot-trading',projectId:'g-p-test-bot-trading',projectName:'bot_trading'});
  assert.equal(out.turns.total,0); assert.equal(f.gotos,0);
  console.log('BROKER_TEST_V4_2_ALREADY_FRESH_FAST_PATH=PASS');

  // If root does not itself become fresh, bounded safe Chat/New-chat candidate path is used.
  f=fakeBroker('historical','target-not-fresh');
  out=await f.b.ensureFreshProjectDraft({projectUrl:'https://chatgpt.com/g/g-p-test-bot-trading',projectId:'g-p-test-bot-trading',projectName:'bot_trading'});
  assert.equal(out.turns.total,0); assert.ok(f.gotos>=1); assert.equal(f.clicks,1);
  console.log('BROKER_TEST_V4_2_BOUNDED_FRESH_CONTROL_FALLBACK=PASS');

  console.log('BROKER_TEST_V4_2=PASS');
})().catch(e=>{console.error(e.stack||e);process.exit(1);});
