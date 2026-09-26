# IMPLEMENTATION PLAN — ai-loop v4.8.6
## Bootstrap the current rendered settled-response witness for successor-preflight delivery

**Authoritative run:** `R20260923T012014`  
**Current state:** `BLOCKED_NO_SEND`  
**Purpose:** resolve the v4.8.5 hash-mismatch blocker without sending, navigating, rerunning the preflight, or relying on an unrelated earlier persisted assistant-response hash.

---

## 1. Current facts

The authoritative two-successor preflight is already complete:

```text
TARGET_SHA=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
SUCCESSOR_1_SHA=cd43645e4e38c574bc728e6f383745e160ae766d
SUCCESSOR_2_SHA=2d429e66d185241e0efda9f3385f5aea55b65f5d
TWO_SUCCESSOR_COMMITS_PREFLIGHT=COMPLETED
SHA256_MANIFEST_VALIDATION=PASS
```

The currently rendered assistant response is the successor-preflight response.

Its fresh rendered SHA-256 is:

```text
1cfdd85f5b5db6a021ab1f9da576e76cc2d1666b1cfd6b3887a4d6bbc9118d13
```

The older persisted assistant-response SHA:

```text
1bdc930f1b97480eec56b619d48085d401f6a12fe5ee63619319f50dfb84e2f2
```

belongs to an earlier delivery and MUST NOT be used as the expected hash for this response.

No lease or delivery intent currently exists for the successor-preflight result delivery.

---

## 2. Objective

Persist the currently rendered successor-preflight response as a new immutable read-only witness, bind it to the exact conversation and authoritative preflight artifacts, then create one fresh READY/unconsumed proof lease.

This plan performs NO SEND.

---

## 3. Hard prohibitions

Do NOT:

- send or type any ChatGPT message;
- click Send;
- navigate or switch chats;
- create a delivery intent;
- consume a proof lease;
- rerun the two-successor preflight;
- run tests/CI;
- query Semaphore;
- query VPS;
- use SSH;
- query GitHub;
- clone/fetch Git;
- mutate repositories;
- deploy/sync;
- declare FINAL_GO;
- declare AI_LOOP_COMPLETE=GO.

---

## 4. Authoritative conversation

Require exact current URL:

```text
https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589
```

Require read-only proof:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
PROJECT=Bot_trading
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
MODEL=GPT-5.6 Sol
REASONING=High
```

Do not open/click model controls if current visible state already proves them.

---

## 5. Bootstrap the current response witness

Capture only the currently rendered settled assistant response that corresponds to the completed two-successor preflight.

Persist its exact normalized visible text as:

```text
current-settled-response.txt
```

Persist metadata:

```text
source=LIVE_RENDERED_ASSISTANT_RESPONSE
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
captured_at=<timestamp>
rendered_response_sha256=1cfdd85f5b5db6a021ab1f9da576e76cc2d1666b1cfd6b3887a4d6bbc9118d13
response_settled=true
```

Recompute the hash from the captured bytes/text.

Require:

```text
CAPTURED_RESPONSE_SHA256=
1cfdd85f5b5db6a021ab1f9da576e76cc2d1666b1cfd6b3887a4d6bbc9118d13
```

If the freshly recomputed hash differs, stop BLOCKED.

Do not compare this response to the unrelated earlier persisted response hash.

---

## 6. Bind the live response to the authoritative preflight

Read only:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight/
```

Require manifest PASS.

Extract from persisted artifacts the exact authoritative anchors:

```text
TARGET_SHA=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
SUCCESSOR_1_SHA=cd43645e4e38c574bc728e6f383745e160ae766d
SUCCESSOR_2_SHA=2d429e66d185241e0efda9f3385f5aea55b65f5d
TWO_SUCCESSOR_COMMITS_PREFLIGHT=COMPLETED
```

Require the current rendered response to contain/semantically reference the same preflight result and commit chain.

Persist:

```text
CURRENT_RESPONSE_MATCHES_PREFLIGHT=PASS
TARGET_ANCHOR_MATCH=PASS
SUCCESSOR_1_ANCHOR_MATCH=PASS
SUCCESSOR_2_ANCHOR_MATCH=PASS
```

If the current response cannot be unambiguously tied to this preflight, stop BLOCKED.

Do not infer missing commit identities.

---

## 7. New witness semantics

Set:

```text
PROVENANCE_MODE=LIVE_BOOTSTRAPPED_SETTLED_RESPONSE_WITNESS
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
```

This witness is authoritative because it is captured fresh from:
- the exact authoritative conversation;
- the current settled response;
- the current Bot_trading project context;
- a response whose commit anchors match the already-validated preflight evidence.

The older unrelated response hash remains historical evidence only.

Persist that mismatch explicitly:

```text
OLDER_PERSISTED_RESPONSE_HASH_APPLICABLE=false
OLDER_PERSISTED_RESPONSE_HASH=
1bdc930f1b97480eec56b619d48085d401f6a12fe5ee63619319f50dfb84e2f2
CURRENT_RENDERED_RESPONSE_HASH=
1cfdd85f5b5db6a021ab1f9da576e76cc2d1666b1cfd6b3887a4d6bbc9118d13
HASH_MISMATCH_CLASSIFICATION=EXPECTED_DIFFERENT_RESPONSE
```

---

## 8. Cross-source provenance

Require:

```text
live conversation id == authoritative conversation id
live project == Bot_trading
preflight manifest == PASS
current response anchors == persisted preflight commit chain
current rendered response hash == newly captured witness hash
```

Then:

```text
CROSS_SOURCE_PROVENANCE=PASS
```

No historical live turn/message IDs are required or fabricated.

---

## 9. Outbound idempotency

For delivery purpose:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
```

search authoritative local ledgers/evidence only.

Require:

```text
EXISTING_DELIVERY_INTENT=false
EXISTING_PHYSICAL_SEND=false
EXISTING_RECONCILED_DELIVERY=false
OUTBOUND_IDEMPOTENCY=PASS
```

Do not create a delivery intent in this plan.

---

## 10. Combined identity proof

Require:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
MODEL=GPT-5.6 Sol
REASONING=High
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CURRENT_RESPONSE_MATCHES_PREFLIGHT=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

Then persist:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROVENANCE_MODE=LIVE_BOOTSTRAPPED_SETTLED_RESPONSE_WITNESS
LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_6_BOOTSTRAP_MODE
```

---

## 11. Fresh proof lease

If and only if every gate passes, create exactly one new immutable proof lease:

```text
proof_lease_id=<new unique id>
authoritative_run=R20260923T012014
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
project=Bot_trading
delivery_purpose=TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
provenance_mode=LIVE_BOOTSTRAPPED_SETTLED_RESPONSE_WITNESS
state=READY
consumed=false
created_at=<timestamp>
preflight_manifest_sha256=<sha>
current_response_sha256=1cfdd85f5b5db6a021ab1f9da576e76cc2d1666b1cfd6b3887a4d6bbc9118d13
page_identity_sha256=<sha>
cross_source_sha256=<sha>
idempotency_sha256=<sha>
```

Any later navigation, chat switch, composer mutation, or outbound send invalidates the lease.

---

## 12. Evidence directory

Create:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v486/
```

Persist at minimum:

```text
page-identity.json
current-settled-response.txt
current-settled-response-witness.json
preflight-binding.json
model-policy-proof.json
cross-source-provenance.json
outbound-idempotency.json
live-conversation-identity-proof.json
proof-lease.json
RESULT.md
evidence.json
sha256-manifest.txt
```

Validate the manifest.

---

## 13. Successful terminal state

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS

PROVENANCE_MODE=LIVE_BOOTSTRAPPED_SETTLED_RESPONSE_WITNESS

MODEL_POLICY_PROOF=PASS
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CURRENT_RESPONSE_MATCHES_PREFLIGHT=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS

LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_6_BOOTSTRAP_MODE

PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false

OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_TWO_SUCCESSOR_PREFLIGHT_RESULT_DELIVERY_AUTHORIZATION

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

Stop there. Do not send.

---

## 14. `/omo-team` prompt

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_6_BOOTSTRAP_CURRENT_SETTLED_RESPONSE_WITNESS_20260926.md for authoritative run R20260923T012014.

This is NO-SEND.

Do NOT rerun TWO_SUCCESSOR_COMMITS_PREFLIGHT.

The v4.8.5 blocker is understood:
the current rendered successor-preflight response has SHA256
1cfdd85f5b5db6a021ab1f9da576e76cc2d1666b1cfd6b3887a4d6bbc9118d13
while the locally persisted older response hash
1bdc930f1b97480eec56b619d48085d401f6a12fe5ee63619319f50dfb84e2f2
belongs to an earlier response.

Do NOT require those two different responses to hash-match.

Instead bootstrap the CURRENT settled successor-preflight response as a fresh immutable live witness.

Require exact URL/conversation/project/normal Chat/empty composer/settled response/GPT-5.6 Sol/High.

Capture the current rendered response read-only and require its freshly recomputed SHA256 to equal:
1cfdd85f5b5db6a021ab1f9da576e76cc2d1666b1cfd6b3887a4d6bbc9118d13

Bind that current response to the already-validated preflight by requiring exact anchors:
TARGET=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
SUCCESSOR_1=cd43645e4e38c574bc728e6f383745e160ae766d
SUCCESSOR_2=2d429e66d185241e0efda9f3385f5aea55b65f5d

Require preflight manifest PASS.

Require outbound idempotency PASS for:
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT

Set:
PROVENANCE_MODE=LIVE_BOOTSTRAPPED_SETTLED_RESPONSE_WITNESS
LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_6_BOOTSTRAP_MODE

If all gates pass, create one new proof lease READY/unconsumed.

Persist under:
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v486/

Do NOT:
- type/send;
- create delivery intent;
- consume lease;
- navigate;
- rerun preflight;
- clone/fetch;
- run tests/CI;
- query Semaphore/VPS/GitHub;
- mutate repositories;
- deploy;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

Stop after creating the no-send proof package.
```
