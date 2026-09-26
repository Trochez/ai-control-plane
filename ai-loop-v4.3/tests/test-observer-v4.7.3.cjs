#!/usr/bin/env node
'use strict';
const assert=require('assert');
const fs=require('fs');
const {Broker,normalizeTurnInventory}=require('../browser-broker-v1.cjs');

const brokerSource=fs.readFileSync(require.resolve('../browser-broker-v1.cjs'),'utf8');
const evaluateStart=brokerSource.indexOf('this.page.evaluate(({projectId,projectName})=>{');
const evaluateEnd=brokerSource.indexOf('},{projectId,projectName});',evaluateStart);
const observeContextBody=brokerSource.slice(evaluateStart,evaluateEnd);
assert.equal(/normalizeTurnInventory/.test(observeContextBody),false,'browser realm must not reference Node normalization');

async function observe({assistant=true,stop=false,body='Ready'}){
  const b=Object.create(Broker.prototype);
  b.page={
    locator(selector){
      if(selector.includes('data-message-author-role')||selector.includes('conversation-turn')) return {count:async()=>assistant?1:0,nth:()=>({innerText:async()=> 'settled response',getAttribute:async()=> 'assistant-1',locator:()=>({evaluateAll:async()=>[]})})};
      if(selector.includes('stop')||selector.includes('Stop')) return {filter:()=>({count:async()=>stop?1:0}),count:async()=>stop?1:0};
      if(selector.includes('role="status"')||selector.includes('aria-live')||selector.includes('status')) return {filter:()=>({count:async()=>body!=='Ready'?1:0}),count:async()=>0};
      return {innerText:async()=>body};
    }
  };
  b.observeContext=async()=>({url:'https://chatgpt.com/c/test'});
  b.cfg={runDir:'/tmp/observer-v471-test'};
  return b.observeResponse({});
}

async function historicalTurns(){
  const b=Object.create(Broker.prototype);
  const records=[
    {role:'user',id:'u-1',text:'first request',index:0},
    {role:'assistant',id:'a-1',text:'first answer',index:1},
    {role:'user',id:'u-2',text:'second request',index:2},
    {role:'assistant',id:'a-2',text:'second answer',index:3},
  ];
  b.page={locator(selector){
    if(selector.includes('data-message-author-role')||selector.includes('conversation-turn')) return {count:async()=>1,nth:()=>({innerText:async()=> 'second answer',getAttribute:async()=> 'a-2',locator:()=>({evaluateAll:async()=>[]})})};
    if(selector.includes('stop')||selector.includes('Stop')) return {filter:()=>({count:async()=>0}),count:async()=>0};
    if(selector.includes('role="status"')||selector.includes('aria-live')||selector.includes('status')) return {filter:()=>({count:async()=>0}),count:async()=>0};
    return {innerText:async()=>''};
  }};
  b.observeContext=async()=>({url:'https://chatgpt.com/c/test',turnRecords:records,turns:{records}});
  b.cfg={runDir:'/tmp/observer-v471-test'};
  return b.observeResponse({});
}

async function liveDomInventory(){
  const b=Object.create(Broker.prototype);
  const domTurns=[
    {role:'user',id:'u-live-1',text:'diagnosis request',index:0},
    {role:'assistant',id:'a-live-1',text:'diagnosis response',index:1},
    {role:'user',id:'u-live-2',text:'resume request',index:2},
    {role:'assistant',id:'a-live-2',text:'settled resume response',index:3},
  ];
  b.page={locator(selector){
    if(selector.includes('data-message-author-role')||selector.includes('conversation-turn')) return {
      count:async()=>2,
      nth:(index)=>({
        innerText:async()=>domTurns.filter(x=>x.role==='assistant')[index].text,
        getAttribute:async(name)=>name==='data-message-id'?domTurns.filter(x=>x.role==='assistant')[index].id:'',
        locator:()=>({evaluateAll:async()=>[]}),
      }),
    };
    if(selector.includes('stop')||selector.includes('Stop')) return {filter:()=>({count:async()=>0}),count:async()=>0};
    if(selector.includes('role="status"')||selector.includes('aria-live')||selector.includes('status')) return {filter:()=>({count:async()=>0}),count:async()=>0};
    return {innerText:async()=>''};
  }};
  b.observeContext=async()=>({
    url:'https://chatgpt.com/g/g-p-test/c/resumed',
    turns:{user:2,assistant:2,total:4,records:domTurns},
    turnRecords:domTurns,
    userTexts:domTurns.filter(x=>x.role==='user').map(x=>x.text),
    assistantTexts:domTurns.filter(x=>x.role==='assistant').map(x=>x.text),
  });
  b.cfg={runDir:'/tmp/observer-v471-test'};
  return {b,domTurns};
}

async function restartResumeSettled(){
  const first=await liveDomInventory();
  const before=await first.b.observeResponse({});
  assert.equal(before.generation_state,'SETTLED');
  assert.equal(before.assistant_message_id,'a-live-2');
  assert.deepEqual(before.assistant_turn_records,first.domTurns);

  // A broker restart has no in-memory response state; the same DOM is the
  // source of truth and must remain a settled response, not a missing one.
  const resumed=await liveDomInventory();
  const after=await resumed.b.observeResponse({});
  assert.equal(after.generation_state,'SETTLED');
  assert.equal(after.assistant_message_id,before.assistant_message_id);
  assert.equal(after.assistant_text,'settled resume response');
  assert.deepEqual(after.assistant_turn_records,resumed.domTurns);
}

(async()=>{
  const fixture={turns:{records:[
    {role:'user',id:'u0',text:'old',index:0},
    {role:'assistant',id:'a0',text:'old answer',index:1},
    {role:'user',id:'u1',text:'[AI_LOOP_DELIVERY id=failure-evidence-025d7f19b1dd83b26733]',index:2},
    {role:'user',id:'u2',text:'[AI_LOOP_DELIVERY id=diagnosis-0c11a13e0c6c]',index:3},
     {role:'assistant',id:'c724d7df-c1fe-4eac-88da-2c7795a46cb6',turn_id:'turn-4',message_id:'c724d7df-c1fe-4eac-88da-2c7795a46cb6',testid:'conversation-turn-4',text:'diagnosis',index:4},
  ]}};
  const normalized=normalizeTurnInventory(fixture);
  assert.equal(normalized.turns.total,5);
  assert.equal(normalized.turns.user,3);
  assert.equal(normalized.turns.assistant,2);
  assert.equal(normalized.deliveryMatches[0].following_assistant,null);
  assert.equal(normalized.deliveryMatches[1].assistant_index,4);
   assert.equal(normalized.latestAssistantTurn.id,'c724d7df-c1fe-4eac-88da-2c7795a46cb6');
   assert.equal(normalized.latestAssistantTurn.turn_id,'turn-4');
   assert.equal(normalized.latestAssistantTurn.message_id,'c724d7df-c1fe-4eac-88da-2c7795a46cb6');
   assert.equal(normalized.latestAssistantTurn.testid,'conversation-turn-4');
   assert.equal(normalized.deliveryMatches[1].user_turn_id,'u2');
   assert.equal(normalized.deliveryMatches[1].following_assistant.id,'c724d7df-c1fe-4eac-88da-2c7795a46cb6');
   assert.equal(normalized.deliveryMatches[1].following_assistant.turn_id,'turn-4');
   assert.equal(normalized.deliveryMatches[1].following_assistant.message_id,'c724d7df-c1fe-4eac-88da-2c7795a46cb6');
  for(const sparse of [
    {turnRecords:fixture.turns.records},
    {orderedTurns:fixture.turns.records},
    {turns:{records:fixture.turns.records},turnRecords:null,orderedTurns:null,latestAssistant:null,deliveryMatches:null},
  ]) assert.equal(normalizeTurnInventory(sparse).deliveryMatches[1].assistant_index,4);
  assert.equal((await observe({assistant:true})).generation_state,'SETTLED');
  assert.equal((await observe({assistant:true,stop:true})).generation_state,'GENERATING');
  assert.equal((await observe({assistant:false,stop:true})).generation_state,'GENERATING');
  assert.equal((await observe({assistant:false})).generation_state,'RESPONSE_MISSING');
  const historical=await historicalTurns();
  assert.deepEqual(historical.assistant_turn_records.map(x=>x.id),['u-1','a-1','u-2','a-2']);
  assert.equal(historical.assistant_message_id,'a-2');
  await restartResumeSettled();
   console.log('OBSERVER_V4_7_3_LIVE_DOM_INVENTORY_RESTART_RESUME=PASS');
   console.log('OBSERVER_V4_7_3_CLASSIFICATION=PASS');
})().catch(e=>{console.error(e);process.exit(1);});
