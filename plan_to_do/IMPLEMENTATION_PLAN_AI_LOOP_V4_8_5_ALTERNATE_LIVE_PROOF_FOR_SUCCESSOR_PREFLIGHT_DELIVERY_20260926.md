# IMPLEMENTATION PLAN — ai-loop v4.8.5
## Alternate live-proof mode for delivery of the already-completed two-successor preflight

**Authoritative run:** `R20260923T012014`  
**Current state:** `BLOCKED_NO_SEND`  
**Purpose:** permit a new no-send proof package for the already-completed two-successor preflight when the legacy live gates are not all directly provable in the current UI.

## 1. Existing authoritative preflight

Do NOT rerun the preflight.

Authoritative evidence:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight/
```

Require:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT=COMPLETED
SHA256_MANIFEST_VALIDATION=PASS
TARGET_SHA=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
SUCCESSOR_1_SHA=cd43645e4e38c574bc728e6f383745e160ae766d
SUCCESSOR_2_SHA=2d429e66d185241e0efda9f3385f5aea55b65f5d
```

Read all relevance/change classifications from persisted artifacts. Do not reconstruct them from memory.

## 2. Why this plan exists

The legacy proof path is currently blocked because all of the following cannot be freshly demonstrated at the same time:

```text
MODEL=GPT-5.6 Sol
LIVE_RANGE_WITNESS
CROSS_SOURCE_PROVENANCE
OUTBOUND_IDEMPOTENCY
LIVE_CONVERSATION_IDENTITY_PROOF
```

This plan introduces an alternate proof mode for **this delivery only**:

```text
PROVENANCE_MODE=EXACT_CONVERSATION_PLUS_SETTLED_RESPONSE_WITNESS
```

It does not weaken exactly-once delivery semantics.

## 3. No-send scope

This plan creates only a new proof package and one READY/unconsumed proof lease.

It MUST NOT:
- type into the composer;
- click Send;
- create a delivery intent;
- consume a lease;
- navigate to another conversation;
- rerun the preflight;
- query Semaphore;
- query VPS;
- use SSH;
- mutate Git/GitHub/repositories;
- run tests/CI;
- deploy;
- declare FINAL_GO;
- declare AI_LOOP_COMPLETE=GO.

## 4. Authoritative conversation identity

Require exact current URL:

```text
https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589
```

Require read-only evidence for:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
PROJECT=Bot_trading
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
```

No navigation or UI mutation is allowed to obtain these.

## 5. Model / reasoning policy

Use:

```text
MODEL_POLICY_MODE=READONLY_VISIBLE_STATE_OR_PRIOR_BOUND_POLICY
```

Accept either:

### Mode A — direct visible proof

```text
MODEL=GPT-5.6 Sol
REASONING=High
MODEL_POLICY_PROOF=PASS
```

from current read-only DOM/accessibility evidence.

### Mode B — prior bound policy

If the current UI does not expose enough read-only metadata, accept:

```text
MODEL_POLICY_PROOF=BOUND_PRIOR_PASS
```

only if all of these hold:

1. the exact same conversation ID is proven;
2. the immediately preceding successful delivery proof for this conversation persisted `MODEL=GPT-5.6 Sol` and `REASONING=High`;
3. no navigation/chat switch/model change/reasoning change is evidenced after that proof;
4. current visible UI does not contradict GPT-5.6 Sol + High.

If any contradiction exists:

```text
MODEL_POLICY_PROOF=FAIL
```

and stop.

Do not click model/reasoning controls.

## 6. Alternate rendered witness

Legacy marker Range witness is not mandatory in this plan.

Instead require a fresh witness for the **current settled assistant response** that immediately preceded this preflight-delivery preparation.

Use the persisted prior settled-response artifact/hash and compare it to the currently rendered response text.

Persist:

```text
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
VISIBLE_RESPONSE_SHA256=<sha256>
PERSISTED_RESPONSE_SHA256=<sha256>
RESPONSE_HASH_MATCH=PASS
```

The witness may use visible text-node/range extraction where available, but exact historical marker Range cardinality is not required.

If the rendered response cannot be matched to the persisted response:

```text
VISIBLE_SETTLED_RESPONSE_WITNESS=FAIL
```

and stop.

## 7. Cross-source provenance in alternate mode

Require:

```text
historical/persisted conversation_id == live conversation_id
persisted project == live project
persisted settled response hash == live rendered settled response hash
authoritative preflight manifest validates
```

Then set:

```text
CROSS_SOURCE_PROVENANCE=PASS
PROVENANCE_MODE=EXACT_CONVERSATION_PLUS_SETTLED_RESPONSE_WITNESS
```

No fabricated live turn/message IDs.

## 8. Outbound idempotency

For the new delivery purpose:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
```

require that no prior delivery exists.

Search local authoritative ledgers/evidence for this exact delivery purpose and prospective marker namespace.

Require:

```text
EXISTING_DELIVERY_INTENT=false
EXISTING_PHYSICAL_SEND=false
EXISTING_RECONCILED_DELIVERY=false
OUTBOUND_IDEMPOTENCY=PASS
```

Historical deliveries of other purposes do not block this delivery.

Do not create an intent in this plan.

## 9. Combined alternate identity proof

Require:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
MODEL_POLICY_PROOF=PASS or BOUND_PRIOR_PASS
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

Then persist:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROVENANCE_MODE=EXACT_CONVERSATION_PLUS_SETTLED_RESPONSE_WITNESS
LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_5_ALTERNATE_MODE
```

This is valid only for preparing the preflight-result delivery proof.

## 10. Fresh proof lease

Create exactly one new proof lease only if all alternate-mode gates pass.

Persist:

```text
proof_lease_id
authoritative_run=R20260923T012014
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
project=Bot_trading
delivery_purpose=TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
provenance_mode=EXACT_CONVERSATION_PLUS_SETTLED_RESPONSE_WITNESS
state=READY
consumed=false
created_at
preflight_manifest_sha256
page_identity_sha256
visible_response_witness_sha256
cross_source_sha256
idempotency_sha256
```

Any later navigation/chat switch/composer mutation/outbound send invalidates the lease.

## 11. Evidence directory

Create:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v485/
```

Persist at minimum:

```text
page-identity.json
model-policy-proof.json
visible-settled-response-witness.json
cross-source-provenance.json
outbound-idempotency.json
live-conversation-identity-proof.json
proof-lease.json
RESULT.md
evidence.json
sha256-manifest.txt
```

Validate the manifest.

## 12. Successful terminal state

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS

PROVENANCE_MODE=EXACT_CONVERSATION_PLUS_SETTLED_RESPONSE_WITNESS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
MODEL_POLICY_PROOF=PASS or BOUND_PRIOR_PASS
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS

LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_5_ALTERNATE_MODE

PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false

OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_TWO_SUCCESSOR_PREFLIGHT_RESULT_DELIVERY_AUTHORIZATION

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

Stop there. Do not send.

## 13. Safe-block conditions

Stop without lease creation if:
- exact conversation URL/id cannot be proven;
- project context is not Bot_trading;
- composer is not empty;
- current response is not settled;
- current visible state contradicts GPT-5.6 Sol + High;
- current rendered settled response cannot be matched to persisted response evidence;
- cross-source provenance fails;
- a prior delivery for this exact purpose already exists;
- any send/navigation/UI mutation would be required.

## 14. `/omo-team` prompt

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_5_ALTERNATE_LIVE_PROOF_FOR_SUCCESSOR_PREFLIGHT_DELIVERY_20260926.md for authoritative run R20260923T012014.

This is NO-SEND.

Do NOT rerun TWO_SUCCESSOR_COMMITS_PREFLIGHT.

Use the already-completed evidence under:
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight/

Apply alternate proof mode:
PROVENANCE_MODE=EXACT_CONVERSATION_PLUS_SETTLED_RESPONSE_WITNESS

Require:
- exact authoritative URL and conversation ID;
- Bot_trading project;
- normal Chat surface;
- empty composer;
- settled response;
- model policy via direct visible proof OR prior-bound-policy mode;
- current rendered settled-response hash matching persisted settled-response evidence;
- cross-source provenance PASS;
- outbound idempotency PASS for delivery purpose TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT.

Legacy LIVE_RANGE_WITNESS is NOT required in this v4.8.5 alternate mode.

If and only if all alternate gates pass:
create one NEW proof lease READY/unconsumed.

Persist under:
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v485/

Do NOT:
- type/send;
- create delivery intent;
- consume lease;
- navigate;
- query Semaphore/VPS/GitHub;
- clone/fetch/rerun preflight;
- run tests/CI;
- mutate repositories;
- deploy;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

Successful terminal state:
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS
PROVENANCE_MODE=EXACT_CONVERSATION_PLUS_SETTLED_RESPONSE_WITNESS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS
LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_5_ALTERNATE_MODE
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED

Stop there.
```
