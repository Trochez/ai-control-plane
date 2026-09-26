#!/usr/bin/env node
'use strict';
const assert=require('assert');
const {Broker}=require('../browser-broker-v1.cjs');

function state(overrides={}){return {chat:false,model:false,high:false,reasoning:'',trigger:null,...overrides};}

(async()=>{
  const b=Object.create(Broker.prototype);
  b.timeouts={hydration:400,nav:100}; b.pollMs=20; b.page={url:()=> 'https://chatgpt.com/g/g-p-test'};
  let reads=0, clicks=0;
  b.policyState=async()=>{reads++; return reads<4?state():state({chat:true,model:true,high:true,reasoning:'high',modelProof:'standard-chat-high=>gpt-5.6-sol-v1'});};
  b.clickMatching=async()=>{clicks++;return false;};
  const out=await b.ensurePolicy({});
  assert.equal(out.chat,true); assert.ok(reads>=4); assert.equal(clicks,0);
  assert.ok(out.hydration_timeline.length>=4);
  console.log('BROKER_TEST_V4_5_DELAYED_HYDRATION=PASS observations='+reads);

  const failed=Object.create(Broker.prototype);
  failed.timeouts={hydration:90,nav:100}; failed.pollMs=15; failed.page={url:()=> 'https://chatgpt.com/g/g-p-test'};
  failed.policyState=async()=>state(); failed.clickMatching=async()=>false;
  await assert.rejects(()=>failed.ensurePolicy({}),/WAIT_TIMEOUT:chat_policy_hydration_ready/);
  try { await failed.ensurePolicy({}); } catch(e) {
    assert.ok(Array.isArray(e.timeline)); assert.ok(e.timeline.length>0);
    assert.equal(e.hydration_budget_ms,90); assert.ok(e.hydration_elapsed_ms>=0);
  }
  console.log('BROKER_TEST_V4_5_TIMEOUT_TIMELINE=PASS');
})();
