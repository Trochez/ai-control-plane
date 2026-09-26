#!/usr/bin/env node
'use strict';
const assert=require('assert');
const fs=require('fs');
const path=require('path');
const {
  Broker,projectNameFrom,normProjectName,sameProjectName,
  STANDARD_CHAT_SOL_MODEL,STANDARD_CHAT_HIGH_CONTRACT
}=require('../browser-broker-v1.cjs');

const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'R20260922T040029-policy-state.json'),'utf8'));

// Exact production URL regression: v4.2 incorrectly returned only "trading".
assert.equal(projectNameFrom(fixture.projectUrl),'bot_trading');
assert.equal(normProjectName('Bot_trading'),'bot trading');
assert.equal(normProjectName('bot-trading'),'bot trading');
assert.ok(sameProjectName('Bot_trading','bot-trading'));
console.log('BROKER_TEST_V4_3_PROJECT_NAME_PARSE=PASS');

// Exact live UI regression: current standard Chat exposes High in a reasoning slider
// and no literal visible GPT-5.6 Sol option. High on standard paid Chat is the Sol policy.
const b=Object.create(Broker.prototype);
b.observeContext=async()=>({
  url:fixture.url,
  projectContext:'TARGET',
  controls:fixture.controls,
  turns:{user:0,assistant:0,total:0},
  userTexts:[],assistantTexts:[]
});
b.page={url:()=>fixture.url,goto:async()=>{throw new Error('unexpected goto');},locator:()=>{throw new Error('unexpected locator');}};
b.timeouts={settle:100,nav:100,action:100,response:100};
b.waitUntil=Broker.prototype.waitUntil.bind(b);
b.policyState=Broker.prototype.policyState.bind(b);
b.ensurePolicy=Broker.prototype.ensurePolicy.bind(b);
b.clickMatching=async()=>{throw new Error('unexpected click: already High');};

(async()=>{
  let st=await b.policyState();
  assert.equal(st.chat,true);
  assert.equal(st.high,true);
  assert.equal(st.model,true);
  assert.equal(st.modelName,STANDARD_CHAT_SOL_MODEL);
  assert.equal(st.modelProof,STANDARD_CHAT_HIGH_CONTRACT);
  assert.equal(st.reasoningProof,'data-selected-reasoning-effort');
  console.log('BROKER_TEST_V4_3_REAL_DOM_HIGH_IMPLIES_SOL=PASS');

  const out=await b.ensurePolicy({});
  assert.equal(out.chat,true);
  assert.equal(out.model,true);
  assert.equal(out.high,true);
  console.log('BROKER_TEST_V4_3_NO_LITERAL_SOL_MENU_REQUIRED=PASS');

  // Medium is Sol-capable but does not satisfy the loop's mandatory High policy.
  const med=Object.create(Broker.prototype);
  med.observeContext=async()=>({controls:fixture.controls.map(x=>x.navTarget==='reasoning'?{...x,text:'Medium',reasoningEffort:'medium'}:x)});
  med.policyState=Broker.prototype.policyState.bind(med);
  st=await med.policyState();
  assert.equal(st.model,true);
  assert.equal(st.high,false);
  assert.equal(st.reasoning,'medium');
  console.log('BROKER_TEST_V4_3_MEDIUM_SOL_BUT_NOT_HIGH=PASS');

  console.log('BROKER_TEST_V4_3=PASS');
})().catch(e=>{console.error(e.stack||e);process.exit(1);});
