#!/usr/bin/env node
'use strict';
const assert=require('assert');
const {classifySurfaceIdentity,verifySurfaceTransition,extractTurnProvenance,compareTurnProvenance,proveLiveConversation}=require('../browser-broker-v1.cjs');

assert.deepEqual(classifySurfaceIdentity({surface:'chat',work:false,codex:false}),{surface:'chat',work:false,codex:false,normalChat:true});
assert.equal(classifySurfaceIdentity({surface:'work',work:true,codex:true}).normalChat,false);
const url='https://chatgpt.com/g/g-p-target-bot-trading/c/conversation';
assert.equal(verifySurfaceTransition({surface:'work',work:true,codex:true},{surface:'chat',work:false,codex:false,url,conversationId:'conversation',projectContext:'TARGET'},{url,conversationId:'conversation',projectContext:'TARGET'}).pass,true);
const records=[
  {role:'user',message_id:'u-message',turn_id:'u-turn',testid:'conversation-turn-1',text:'[AI_LOOP_DELIVERY id=failure-evidence-025d7f19b1dd83b26733]',index:0},
  {role:'assistant',message_id:'a-message',turn_id:'a-turn',testid:'conversation-turn-2',text:'answer',index:1},
  {role:'user',message_id:'u2-message',turn_id:'u2-turn',testid:'conversation-turn-3',text:'[AI_LOOP_DELIVERY id=diagnosis-0c11a13e0c6c]',index:2},
  {role:'assistant',message_id:'1e649da7-f024-44e9-aa37-8d48ed6a70bf',turn_id:'59ee4348-f877-4c79-9494-5f54cebda141',testid:'conversation-turn-4',text:'diagnosis',index:3},
];
const live=extractTurnProvenance(records,['failure-evidence-025d7f19b1dd83b26733','diagnosis-0c11a13e0c6c']);
assert.equal(live.proof,true);
assert.equal(live.markers[1].following_assistant.message_id,'1e649da7-f024-44e9-aa37-8d48ed6a70bf');
assert.equal(compareTurnProvenance(live,live).pass,true);
assert.equal(extractTurnProvenance(records.map(x=>({...x,mainConversation:false})),['diagnosis-0c11a13e0c6c']).proof,false);
const proof=proveLiveConversation({authoritativeUrl:url,conversationId:'conversation',observed:{activeAuthenticatedPage:true,url,conversationId:'conversation',projectContext:'TARGET',surface:'chat',work:false,codex:false,generationActive:false,composerAddressable:true,immutableLiveTurnProvenance:'PASS',immutableFingerprint:{type:'turn_inventory',value:'inventory-sha'}}});
assert.equal(proof.live_conversation_proof,'PASS');
console.log('RECONCILIATION_V4_7_9_PROVENANCE_REGRESSION=PASS');
