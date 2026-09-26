'use strict';
const assert = require('assert');
const { DEFAULT_POLICY, FAILURE_CODES, PolicyFailure, effectivePolicy, resolveSelection, validateProof } = require('../chat-policy-v4.3.cjs');

function fails(fn, code) { assert.throws(fn, error => error instanceof PolicyFailure && error.code === code); }
const observed = { surface: 'chat', models: [{ label: 'GPT-5.6 Sol', selected: true }], reasoning: [{ label: 'High', selected: true }] };
const resolved = resolveSelection(DEFAULT_POLICY, observed);
assert.equal(resolved.status, 'PASS');
assert.equal(resolved.model_key, 'GPT-5.6 Sol');
assert.equal(resolved.reasoning_key, 'High');
console.log('POLICY_V4_3_EXACT_SELECTION=PASS');

fails(() => resolveSelection(DEFAULT_POLICY, { ...observed, models: [{ label: 'GPT-5.6', selected: true }] }), 'MODEL_SOL_OPTION_NOT_FOUND');
console.log('POLICY_V4_3_MODEL_SOL_OPTION_NOT_FOUND=PASS');
fails(() => resolveSelection(DEFAULT_POLICY, { ...observed, models: [{ label: 'GPT-5.6 Sol' }, { label: 'GPT-5.6 Sol' }] }), 'AMBIGUOUS_MODEL_MATCH');
fails(() => resolveSelection(DEFAULT_POLICY, { ...observed, surface: 'work' }), 'CHAT_SURFACE_NOT_FOUND');
fails(() => resolveSelection(DEFAULT_POLICY, { ...observed, reasoning: [] }), 'REASONING_HIGH_OPTION_NOT_FOUND');
console.log('POLICY_V4_3_NEGATIVE_CASES=PASS');

const { policy_sha256 } = effectivePolicy(DEFAULT_POLICY);
const proof = { schema_version: 1, status: 'PASS', run_id: 'RTEST', iteration: 0, broker_epoch: 'E1', page_binding: 'P1', project_id: 'g-p-test-bot-trading', surface: 'chat', model_key: 'GPT-5.6 Sol', reasoning_key: 'High', policy_sha256, observed_at: '2026-09-22T00:00:00Z', selected_evidence: [{ label: 'GPT-5.6 Sol' }, { label: 'High' }] };
assert.equal(validateProof(proof, { run_id: 'RTEST', broker_epoch: 'E1', page_binding: 'P1', project_id: 'g-p-test-bot-trading', policy_sha256 }), true);
fails(() => validateProof({ ...proof, model_key: 'GPT-5.5' }), 'POLICY_PROOF_INVALID');
console.log('POLICY_V4_3_PROOF_BINDING=PASS');
assert.ok(FAILURE_CODES.includes('MODEL_SOL_OPTION_NOT_FOUND'));
console.log('POLICY_V4_3=PASS');
