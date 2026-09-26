#!/usr/bin/env node
'use strict';
const assert=require('assert');
const {normalizeTurnInventory,reconcileHistoricalDelivery,proveLiveConversation,outboundGuard,terminalOperatorAction,renderedWitnessProof,crossSourceProvenance}=require('../browser-broker-v1.cjs');

function evidence({url='https://chatgpt.com/g/g-p-target-bot-trading/c/conversation',projectContext='TARGET',following=true}={}){
  return {url,projectContext,deliveryReconciliation:[{delivery_id:'d-1',next_turn_role:following?'assistant':'user',following_assistant:following?{id:'id-1',turn_id:'turn-1',message_id:'message-1',testid:'conversation-turn-1',role:'assistant',text:'answer'}:null}]};
}

const url='https://chatgpt.com/g/g-p-target-bot-trading/c/conversation';
let r=reconcileHistoricalDelivery({deliveryId:'d-1',ledgerStatus:'SENDING',authoritativeUrl:url,projectName:'bot_trading',evidence:evidence()});
assert.equal(r.delivery_status,'RECONCILED_SENT'); assert.equal(r.resend_allowed,false);
const normalized=normalizeTurnInventory({turnRecords:[{role:'user',id:'u-1',text:'[AI_LOOP_DELIVERY id=d-1]'},{role:'assistant',id:'id-1',turn_id:'turn-1',message_id:'message-1',testid:'conversation-turn-1',text:'answer'}]});
assert.equal(normalized.deliveryMatches[0].following_assistant.role,'assistant');
r=reconcileHistoricalDelivery({deliveryId:'d-1',ledgerStatus:'SENDING',authoritativeUrl:url,projectName:'bot_trading',evidence:evidence({following:false})});
assert.equal(r.delivery_status,'DELIVERY_AMBIGUOUS'); assert.equal(r.outbound_send_blocked,true);
r=reconcileHistoricalDelivery({deliveryId:'d-1',ledgerStatus:'SENDING',authoritativeUrl:url+'/wrong',projectName:'bot_trading',evidence:evidence()});
assert.ok(r.reasons.includes('HISTORICAL_URL_MISMATCH'));

let p=proveLiveConversation({authoritativeUrl:url,conversationId:'conversation',observed:{activeAuthenticatedPage:true,url,conversationId:'conversation',projectContext:'TARGET',surface:'chat',generationActive:false,composerAddressable:true}});
assert.equal(p.live_conversation_proof,'FAIL');
p=proveLiveConversation({authoritativeUrl:url,conversationId:'conversation',observed:{activeAuthenticatedPage:true,url,conversationId:'conversation',projectContext:'TARGET',surface:'chat',generationActive:false,composerAddressable:true,immutableLiveTurnProvenance:'PASS',immutableFingerprint:{type:'delivery_marker',value:'[AI_LOOP_DELIVERY id=d-1]'}}});
assert.equal(p.live_conversation_proof,'PASS');
assert.equal(proveLiveConversation({authoritativeUrl:url,conversationId:'conversation',observed:{activeAuthenticatedPage:true,url,conversationId:'conversation',projectContext:'TARGET',surface:'chat',generationActive:false,composerAddressable:true}}).proof,false);

assert.equal(outboundGuard({staleLedgerReconciliation:'PASS',liveConversationProof:'FAIL',chatSurface:'PASS',modelGuard:'PASS',outboundIdempotency:'PASS'}).outbound_send,'BLOCKED');
assert.equal(outboundGuard({staleLedgerReconciliation:'PASS',liveConversationProof:'PASS',chatSurface:'PASS',modelGuard:'PASS',outboundIdempotency:'PASS'}).outbound_send,'BLOCKED');
let w=renderedWitnessProof({markers:['failure-evidence-x','diagnosis-x'],candidates:[{marker:'failure-evidence-x',renderedMain:true,visible:true,inConversationRoot:true,path:'a'},{marker:'diagnosis-x',renderedMain:true,visible:true,inConversationRoot:true,path:'b'}]});
assert.equal(w.live_rendered_witness,'PASS');
assert.equal(crossSourceProvenance({markers:['failure-evidence-x','diagnosis-x'],historical:{historical_immutable_provenance:'PASS',markers:[{marker:'failure-evidence-x'},{marker:'diagnosis-x'}]},live:w,historicalConversationId:'c',liveConversationId:'c'}).cross_source_provenance,'PASS');
assert.equal(proveLiveConversation({authoritativeUrl:url,conversationId:'conversation',observed:{activeAuthenticatedPage:true,url,conversationId:'conversation',projectContext:'TARGET',surface:'chat',generationActive:false,composerAddressable:true,historicalImmutableProvenance:'PASS',liveRenderedWitness:'PASS',crossSourceProvenance:'PASS'}}).provenance_mode,'HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS');
assert.equal(terminalOperatorAction({state:'FAILED_TERMINAL'}).rerun_allowed,false);
console.log('RECONCILIATION_V4_7_8_REGRESSION=PASS');
