#!/usr/bin/env node
'use strict';
const assert=require('assert');
const {rangeWitnessProof,dedupeRangeWitnesses,crossSourceProvenance,proveLiveConversation,outboundGuard,terminalOperatorAction}=require('../browser-broker-v1.cjs');
const base=(marker, id, extra={})=>({marker,rangeIdentity:id,visible:true,inConversationRoot:true,excluded:false,positiveRect:true,...extra});
let x=rangeWitnessProof({markers:['failure-evidence-x','diagnosis-x'],candidates:[
  ...Array.from({length:20},()=>base('failure-evidence-x','leaf|0|leaf|12',{documentOrder:10})),
  base('diagnosis-x','diag|0|diag|11',{documentOrder:20})
]});
assert.equal(x.live_range_witness,'PASS'); assert.equal(x.witnesses[0].raw_dom_matches,20); assert.equal(x.witnesses[0].unique_visible_ranges,1);
x=rangeWitnessProof({markers:['failure-evidence-x','diagnosis-x'],candidates:[
  base('failure-evidence-x','leaf|0|leaf|12',{documentOrder:10}),base('failure-evidence-x','leaf|0|leaf|12',{documentOrder:10}),base('diagnosis-x','diag|0|diag|11',{documentOrder:20})
]}); assert.equal(x.live_range_witness,'PASS');
x=rangeWitnessProof({markers:['failure-evidence-x','diagnosis-x'],candidates:[base('failure-evidence-x','a|0|b|5',{documentOrder:10}),base('diagnosis-x','c|0|d|5',{documentOrder:20})]}); assert.equal(x.range_order.failure_evidence_before_diagnosis,true);
x=rangeWitnessProof({markers:['failure-evidence-x'],candidates:[base('failure-evidence-x','a|0|b|5',{positiveRect:false})]}); assert.equal(x.live_range_witness,'FAIL');
x=rangeWitnessProof({markers:['failure-evidence-x'],candidates:[base('failure-evidence-x','a|0|b|5'),base('failure-evidence-x','c|0|d|5')]}); assert.equal(x.live_range_witness,'FAIL');
x=rangeWitnessProof({markers:['failure-evidence-x'],candidates:[]}); assert.equal(x.live_range_witness,'FAIL');
x=rangeWitnessProof({markers:['failure-evidence-x','diagnosis-x'],candidates:[base('failure-evidence-x','a|0|b|5'),base('diagnosis-x','c|0|d|5')]}); assert.equal(x.live_range_witness,'FAIL');
const hidden=base('failure-evidence-x','hidden|0|hidden|5',{visible:false,excluded:true});
x=rangeWitnessProof({markers:['failure-evidence-x'],candidates:[hidden,base('failure-evidence-x','visible|0|visible|5')]}); assert.equal(x.live_range_witness,'PASS');
assert.equal(rangeWitnessProof({markers:['failure-evidence-x'],candidates:[base('failure-evidence-x','split-a|9|split-b|3')]}).live_range_witness,'PASS');
const d=dedupeRangeWitnesses([base('failure-evidence-x','a|0|b|5'),base('failure-evidence-x','a|0|b|5',{visible:false})],['failure-evidence-x']);
assert.equal(d.witnesses[0].unique_visible_ranges,1);
const live={live_range_witness:'PASS',witnesses:[{marker:'failure-evidence-x'},{marker:'diagnosis-x'}]};
assert.equal(crossSourceProvenance({markers:['failure-evidence-x','diagnosis-x'],historical:{historical_immutable_provenance:'PASS',markers:[{marker:'failure-evidence-x'},{marker:'diagnosis-x'}]},live,historicalConversationId:'c',liveConversationId:'c'}).cross_source_provenance,'PASS');
const url='https://chatgpt.com/g/g-p-target-bot-trading/c/conversation';
assert.equal(proveLiveConversation({authoritativeUrl:url,conversationId:'conversation',observed:{activeAuthenticatedPage:true,url,conversationId:'conversation',projectContext:'TARGET',surface:'chat',generationActive:false,composerAddressable:true,historicalImmutableProvenance:'PASS',liveRangeWitness:'PASS',crossSourceProvenance:'PASS'}}).provenance_mode,'HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS');
assert.equal(outboundGuard({liveConversationProof:'PASS'}).outbound_send,'BLOCKED');
assert.equal(terminalOperatorAction({state:'FAILED_TERMINAL'}).rerun_allowed,false);
console.log('RECONCILIATION_V4_8_1_RANGE_WITNESS_REGRESSION=PASS');
