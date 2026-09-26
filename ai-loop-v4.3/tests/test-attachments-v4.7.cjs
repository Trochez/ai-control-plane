#!/usr/bin/env node
'use strict';
const assert=require('assert');
const fs=require('fs');
const path=require('path');
const {Broker}=require('../browser-broker-v1.cjs');
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'attachment-regressions-v4.7.json'),'utf8'));
const source=fs.readFileSync(path.join(__dirname,'..','browser-broker-v1.cjs'),'utf8');
assert.deepEqual(fixture.empty_historical_composer.expected_attachments,[]);
assert.match(source,/Never use the whole composer as an attachment region/);
assert.match(source,/const regions=\[\.\.\.root\.querySelectorAll\('\[data-composer-attachments\],\[data-visible-attachments\],\.composer-attachment-surface'\)/);
assert.match(source,/CURRENT_COMPOSER_ATTACHMENT_UNREMOVABLE/);
assert.equal(fixture.positive_current_attachment.expected.remove_control,true);
assert.equal(fixture.stale_then_new_failure_evidence.expected_retry,'ATTACHED');
const b=Object.create(Broker.prototype); b.resolveActiveComposer=async()=>({attachments:[]}); b.composer=async()=>null;
(async()=>{
  await assert.rejects(()=>b.attachFile(__filename,'failure-evidence.json'),/COMPOSER_NOT_FOUND/);
  const guarded=Object.create(Broker.prototype); guarded.resolveActiveComposer=async()=>({attachments:[{name:'old-failure-evidence.json',name_control:true,remove_control:false}]});
  await assert.rejects(()=>guarded.attachFile(__filename,'failure-evidence.json'),/CURRENT_COMPOSER_ATTACHMENT_UNREMOVABLE/);
  console.log('BROKER_TEST_V4_7_ATTACHMENT_REGRESSIONS=PASS');
})().catch(e=>{console.error(e.stack||e);process.exit(1);});
