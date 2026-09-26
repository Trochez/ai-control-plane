'use strict';

const crypto = require('crypto');

const VERSION = '4.3.0';
const DEFAULT_POLICY = Object.freeze({
  schema_version: 1,
  surface: 'chat',
  selection_mode: 'strict',
  preferred: { model_key: 'GPT-5.6 Sol', reasoning_key: 'High' },
  allowed_pairs: [{ model_key: 'GPT-5.6 Sol', reasoning_key: 'High' }],
  aliases: {
    model: { 'GPT-5.6 Sol': ['GPT-5.6 Sol', 'GPT-5.6 Sol'] },
    reasoning: { High: ['High'] }
  },
  budget: { max_attempts: 3, deadline_ms: 15000 }
});

const FAILURE_CODES = Object.freeze([
  'POLICY_CONFIG_INVALID', 'CHAT_SURFACE_NOT_FOUND', 'MENU_NOT_OPEN',
  'CATALOG_INCOMPLETE', 'MODEL_SOL_OPTION_NOT_FOUND', 'MODEL_UNAVAILABLE',
  'AMBIGUOUS_MODEL_MATCH', 'MODEL_DISABLED', 'REASONING_HIGH_OPTION_NOT_FOUND',
  'UI_CONTRACT_CHANGED', 'POLICY_PROOF_INVALID'
]);

class PolicyFailure extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'PolicyFailure';
    this.code = code;
    this.stage = details.stage || 'policy';
    this.details = details;
  }
  toJSON() {
    return { error_type: 'POLICY_FAILURE', code: this.code, stage: this.stage, message: this.message, details: this.details };
  }
}

function canonical(value) { return String(value == null ? '' : value).replace(/\s+/g, ' ').trim(); }
function exact(value, aliases) { return aliases.some(alias => canonical(value) === canonical(alias)); }
function clone(value) { return JSON.parse(JSON.stringify(value)); }

function validatePolicy(input) {
  let policy = input;
  if (typeof input === 'string') {
    try { policy = JSON.parse(input); } catch (error) {
      throw new PolicyFailure('POLICY_CONFIG_INVALID', 'policy must be valid JSON', { cause: error.message });
    }
  }
  if (!policy || typeof policy !== 'object' || Array.isArray(policy)) {
    throw new PolicyFailure('POLICY_CONFIG_INVALID', 'policy must be an object');
  }
  const p = clone(policy);
  if (p.schema_version !== 1 || p.surface !== 'chat' || !['strict', 'ordered_allowlist'].includes(p.selection_mode)) {
    throw new PolicyFailure('POLICY_CONFIG_INVALID', 'unsupported policy schema, surface, or selection mode');
  }
  if (!p.preferred || typeof p.preferred.model_key !== 'string' || typeof p.preferred.reasoning_key !== 'string') {
    throw new PolicyFailure('POLICY_CONFIG_INVALID', 'preferred model and reasoning are required');
  }
  if (!Array.isArray(p.allowed_pairs) || p.allowed_pairs.length === 0) {
    throw new PolicyFailure('POLICY_CONFIG_INVALID', 'allowed_pairs must not be empty');
  }
  for (const pair of p.allowed_pairs) {
    if (!pair || typeof pair.model_key !== 'string' || typeof pair.reasoning_key !== 'string') {
      throw new PolicyFailure('POLICY_CONFIG_INVALID', 'allowed_pairs contains an invalid pair');
    }
  }
  return p;
}

function effectivePolicy(input = DEFAULT_POLICY) {
  const p = validatePolicy(input);
  return { policy: p, policy_sha256: crypto.createHash('sha256').update(JSON.stringify(p)).digest('hex') };
}

function resolveSelection(policyInput, observation) {
  const { policy, policy_sha256 } = effectivePolicy(policyInput);
  const obs = observation || {};
  if (String(obs.surface || '').toLowerCase() !== 'chat') throw new PolicyFailure('CHAT_SURFACE_NOT_FOUND', 'normal Chat surface was not proven', { stage: 'surface' });
  const modelCandidates = Array.isArray(obs.models) ? obs.models : null;
  const reasoningCandidates = Array.isArray(obs.reasoning) ? obs.reasoning : null;
  if (!modelCandidates || !reasoningCandidates) throw new PolicyFailure('CATALOG_INCOMPLETE', 'model and reasoning catalogs were not observed', { stage: 'catalog' });
  const pair = policy.allowed_pairs.find(candidate => candidate.model_key === policy.preferred.model_key && candidate.reasoning_key === policy.preferred.reasoning_key);
  if (!pair) throw new PolicyFailure('POLICY_CONFIG_INVALID', 'preferred pair is not allowed');
  const modelMatches = modelCandidates.filter(item => exact(item.label, (policy.aliases && policy.aliases.model && policy.aliases.model[pair.model_key]) || [pair.model_key]));
  if (modelMatches.length === 0) throw new PolicyFailure('MODEL_SOL_OPTION_NOT_FOUND', 'exact GPT-5.6 Sol option was not observed', { stage: 'model' });
  if (modelMatches.length > 1) throw new PolicyFailure('AMBIGUOUS_MODEL_MATCH', 'multiple exact model options were observed', { stage: 'model', count: modelMatches.length });
  if (modelMatches[0].disabled) throw new PolicyFailure('MODEL_DISABLED', 'required model option is disabled', { stage: 'model' });
  const reasoningMatches = reasoningCandidates.filter(item => exact(item.label, (policy.aliases && policy.aliases.reasoning && policy.aliases.reasoning[pair.reasoning_key]) || [pair.reasoning_key]));
  if (reasoningMatches.length === 0) throw new PolicyFailure('REASONING_HIGH_OPTION_NOT_FOUND', 'exact High reasoning option was not observed', { stage: 'reasoning' });
  if (reasoningMatches.length > 1) throw new PolicyFailure('UI_CONTRACT_CHANGED', 'multiple exact reasoning options were observed', { stage: 'reasoning', count: reasoningMatches.length });
  if (reasoningMatches[0].disabled) throw new PolicyFailure('UI_CONTRACT_CHANGED', 'required reasoning option is disabled', { stage: 'reasoning' });
  return { status: 'PASS', policy_sha256, surface: 'chat', model_key: pair.model_key, reasoning_key: pair.reasoning_key, selected_evidence: [modelMatches[0], reasoningMatches[0]] };
}

function validateProof(proof, expected = {}) {
  const required = ['schema_version', 'status', 'run_id', 'iteration', 'broker_epoch', 'page_binding', 'project_id', 'surface', 'model_key', 'reasoning_key', 'policy_sha256', 'observed_at', 'selected_evidence'];
  if (!proof || required.some(key => proof[key] === undefined || proof[key] === '')) throw new PolicyFailure('POLICY_PROOF_INVALID', 'policy proof is missing required fields', { stage: 'proof' });
  if (proof.schema_version !== 1 || proof.status !== 'PASS' || proof.surface !== 'chat' || proof.model_key !== 'GPT-5.6 Sol' || proof.reasoning_key !== 'High' || !Array.isArray(proof.selected_evidence) || proof.selected_evidence.length < 2) throw new PolicyFailure('POLICY_PROOF_INVALID', 'policy proof does not satisfy the strict Chat policy', { stage: 'proof' });
  for (const key of ['run_id', 'iteration', 'broker_epoch', 'page_binding', 'project_id', 'policy_sha256']) if (expected[key] !== undefined && proof[key] !== expected[key]) throw new PolicyFailure('POLICY_PROOF_INVALID', `policy proof binding mismatch: ${key}`, { stage: 'proof', expected: expected[key], actual: proof[key] });
  return true;
}

module.exports = { VERSION, DEFAULT_POLICY, FAILURE_CODES, PolicyFailure, effectivePolicy, resolveSelection, validatePolicy, validateProof };
