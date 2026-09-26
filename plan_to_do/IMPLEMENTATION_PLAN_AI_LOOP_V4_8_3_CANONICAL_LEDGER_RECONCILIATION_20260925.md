# IMPLEMENTATION PLAN — ai-loop v4.8.3
## Canonical delivery-ledger reconciliation + read-only model-policy proof refresh

**Authoritative run:** `R20260923T012014`  
**Current disposition:** `BLOCKED`  
**Outbound authorization:** NONE  
**Purpose:** Resolve contradictory `PENDING` vs `SENT_AND_RECONCILED` delivery state without resending, then re-evaluate the live proof lease.

---

## 1. Current confirmed facts

Fresh live read-only inspection has already proven:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
LIVE_RANGE_WITNESS=PASS
RANGE_ORDER=PASS
```

Visible unique Range witnesses exist exactly once for:

```text
failure-evidence-025d7f19b1dd83b26733
diagnosis-0c11a13e0c6c
operator-result-delivery-b677dccd08404429a20721413bfdc9ed
```

and ordering is:

```text
failure-evidence
<
diagnosis
<
operator-result-delivery
```

The historical canonical operator action remains:

```text
FAILED_TERMINAL
BLOCKER=MISSING_COMMAND:jq
retry_allowed=false
```

Two blockers remain:

1. Contradictory persisted delivery-ledger state (`PENDING` vs `SENT_AND_RECONCILED`).
2. Current model control exposes only ambiguous “Thinking effort” UI text, so the exact `GPT-5.6 Sol + High` policy state is not yet freshly proven.

No send is authorized in this plan.

---

## 2. Safety invariants

Do NOT:

- send or type any ChatGPT message;
- create a new delivery intent;
- resend the operator-result delivery;
- rerun any operator action;
- rerun the Semaphore Python collection;
- mutate historical evidence files in-place;
- delete stale evidence;
- navigate or switch chats;
- click model/reasoning controls;
- kill/replace/start browsers;
- mutate Git/GitHub/Semaphore/VPS/bot_trading/production;
- create commits or push;
- declare `FINAL_GO`;
- declare `AI_LOOP_COMPLETE=GO`.

This plan is read-only except for writing new reconciliation evidence files.

---

## 3. Canonical ledger reconciliation

Create a new overlay evidence directory:

```text
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v483-ledger/
```

Do not overwrite prior evidence.

### 3.1 Inventory all relevant ledger/evidence sources

Read and hash at minimum:

```text
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/delivery-intent.json
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/payload.txt
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/payload.sha256
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/physical-send-result.json
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/delivery-reconciliation.json
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/assistant-response.txt
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/assistant-response.json
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/semantic-classification.json
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/outbound-ledger.json
/var/lib/ai-loop/runs/R20260923T012014/operator-result-delivery/evidence.json
```

Also search the authoritative run evidence/state for every occurrence of:

```text
operator-result-delivery-b677dccd08404429a20721413bfdc9ed
PENDING
SENDING
SENT
RECONCILED_SENT
SENT_AND_RECONCILED
```

Persist a source inventory with path, mtime, SHA256, and relevant fields.

### 3.2 Evidence precedence

Do not choose the newest file merely by timestamp.

Use semantic precedence:

**Tier 0 — intent only**
```text
PENDING
SENDING
delivery intent created
```
This proves authorization/intention only, not delivery.

**Tier 1 — physical-send evidence**
```text
physical_send=CONFIRMED_BY_PLAYWRIGHT_CLICK
sent_at=<timestamp>
payload_sha256=<expected>
```
This proves one physical send attempt occurred.

**Tier 2 — live delivery reconciliation**
```text
unique visible delivery marker == 1
same authoritative conversation
same payload/delivery id
```
This proves the message is present live.

**Tier 3 — following settled assistant response**
A settled assistant response captured after that delivery, with persisted response hash/classification, proves the delivered message was consumed by the conversation.

Canonical delivery state is:

```text
SENT_AND_RECONCILED
```

only if Tier 1 + Tier 2 are both PASS.

If Tier 3 also passes, persist:

```text
FOLLOWING_ASSISTANT_RESPONSE=SETTLED
```

A stale Tier-0 `PENDING` record MUST NOT override Tier-1/Tier-2 evidence.

Do not edit or delete the stale record. Mark it:

```text
SUPERSEDED_BY_CANONICAL_RECONCILIATION=true
```

in the new overlay only.

### 3.3 Exactly-once consistency

Require:

```text
delivery_id=operator-result-delivery-b677dccd08404429a20721413bfdc9ed
physical_send_count=1
live_visible_marker_count=1
successful_delivery_count=1
retry_count=0
```

If evidence suggests more than one physical send or more than one live marker, stop:

```text
CANONICAL_LEDGER_RECONCILIATION=AMBIGUOUS
OUTBOUND_SEND=BLOCKED
```

### 3.4 Canonical output

Persist:

```text
canonical-delivery-ledger.json
ledger-source-inventory.json
ledger-conflicts.json
ledger-reconciliation.json
```

Expected:

```text
CANONICAL_LEDGER_RECONCILIATION=PASS
CANONICAL_OPERATOR_RESULT_DELIVERY_STATE=SENT_AND_RECONCILED
STALE_PENDING_RECORD=SUPERSEDED
OPERATOR_RESULT_DELIVERY_COUNT=1
```

---

## 4. Read-only model/reasoning policy proof

Do not click or open model controls.

Read currently exposed DOM/accessibility attributes only.

For the model control persist:

```text
visible_text
aria-label
aria-expanded
aria-selected
aria-pressed
title
data-* attributes
nearest selected-option metadata
```

For the reasoning control persist the same.

### 4.1 Model requirement

Require direct evidence for:

```text
MODEL=GPT-5.6 Sol
```

### 4.2 Reasoning requirement

Require direct evidence for:

```text
REASONING=High
```

The generic label:

```text
Thinking effort
```

alone is NOT proof of `High`.

If the DOM/accessibility tree exposes a selected value of High without interaction, accept it.

If no selected value is available read-only:

```text
MODEL_POLICY_PROOF=AMBIGUOUS
```

and stop BLOCKED.

Do not click the control merely to inspect the menu.

Persist:

```text
model-policy-proof.json
```

---

## 5. Cross-source provenance refresh

After ledger reconciliation, re-evaluate historical/live consistency.

Require:

```text
historical delivery state == canonical overlay state
live visible operator-result marker count == 1
historical conversation id == live conversation id
historical project == live project
range ordering unchanged
```

If all pass:

```text
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
CROSS_SOURCE_PROVENANCE=PASS
```

The old contradictory `PENDING` artifact is retained but treated as superseded evidence, not as an active contradiction.

---

## 6. Combined live identity proof

Require:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
LIVE_RANGE_WITNESS=PASS
RANGE_ORDER=PASS
CANONICAL_LEDGER_RECONCILIATION=PASS
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
CROSS_SOURCE_PROVENANCE=PASS
STALE_LEDGER_RECONCILIATION=PASS
OUTBOUND_IDEMPOTENCY=PASS
MODEL_POLICY_PROOF=PASS
```

Then:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
```

`LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI` remains acceptable.

---

## 7. Fresh one-shot proof lease

Only if every gate above passes, create a new proof lease:

```text
proof_lease_id
state=READY
consumed=false
authoritative_run=R20260923T012014
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
project=Bot_trading
canonical_ledger_sha256
model_policy_sha256
range_witness_sha256
cross_source_sha256
identity_proof_sha256
created_at
```

Any subsequent browser navigation, chat switch, composer mutation, outbound send, or contradictory ledger mutation invalidates the lease.

This plan does NOT consume the lease.

---

## 8. Evidence artifacts

Under:

```text
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v483-ledger/
```

persist at minimum:

```text
ledger-source-inventory.json
ledger-conflicts.json
canonical-delivery-ledger.json
ledger-reconciliation.json
model-policy-proof.json
historical-immutable-provenance.json
cross-source-provenance.json
live-conversation-identity-proof.json
proof-lease.json
outbound-gate.json
RESULT.md
evidence.json
sha256-manifest.txt
```

---

## 9. Successful terminal state

```text
CANONICAL_LEDGER_RECONCILIATION=PASS
CANONICAL_OPERATOR_RESULT_DELIVERY_STATE=SENT_AND_RECONCILED
STALE_PENDING_RECORD=SUPERSEDED
OPERATOR_RESULT_DELIVERY_COUNT=1

MODEL_POLICY_PROOF=PASS
MODEL=GPT-5.6 Sol
REASONING=High

LIVE_RANGE_WITNESS=PASS
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
CROSS_SOURCE_PROVENANCE=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS

PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false

OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_SEMAPHORE_EVIDENCE_DELIVERY_AUTHORIZATION

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

No message is sent.

---

## 10. Stop conditions

Stop BLOCKED if:

- more than one physical send is evidenced;
- more than one live operator-result marker exists;
- physical send evidence and payload hash conflict;
- settled assistant response cannot be linked after the delivered result;
- model is not directly proven as GPT-5.6 Sol;
- reasoning is not directly proven as High;
- only generic `Thinking effort` text is available;
- cross-source provenance remains contradictory after canonical overlay;
- any click/navigation/send would be needed.

---

## 11. `/omo-team` prompt

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_3_CANONICAL_LEDGER_RECONCILIATION_20260925.md for authoritative run R20260923T012014.

This is READ-ONLY / NO-SEND.

Primary objective:
resolve contradictory operator-result delivery ledger state by semantic evidence precedence, without modifying or deleting historical artifacts.

Expected canonical delivery id:
operator-result-delivery-b677dccd08404429a20721413bfdc9ed

Rules:
- Intent/PENDING is lower precedence than confirmed physical send.
- Confirmed physical send + exactly one live visible delivery marker establishes SENT_AND_RECONCILED.
- A settled assistant response following the delivered result strengthens reconciliation.
- Preserve stale PENDING evidence but mark it superseded in a new overlay.
- Require exactly one physical send and one live marker.
- Do not resend.

Also refresh model/reasoning policy read-only:
- prove GPT-5.6 Sol from current DOM/accessibility metadata;
- prove High reasoning from current DOM/accessibility metadata;
- generic “Thinking effort” text alone is not sufficient;
- do not click or open controls.

Then refresh:
HISTORICAL_IMMUTABLE_PROVENANCE
CROSS_SOURCE_PROVENANCE
LIVE_CONVERSATION_IDENTITY_PROOF

If all gates pass, create a fresh one-shot proof lease READY/unconsumed.

Write new evidence only under:
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v483-ledger/

Do NOT:
- type/send;
- create delivery intent;
- navigate;
- switch chats;
- click model controls;
- rerun operator actions;
- rerun Semaphore queries;
- mutate repo/Git/GitHub/Semaphore/VPS/production;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

Successful terminal state:
CANONICAL_LEDGER_RECONCILIATION=PASS
CANONICAL_OPERATOR_RESULT_DELIVERY_STATE=SENT_AND_RECONCILED
MODEL_POLICY_PROOF=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_SEMAPHORE_EVIDENCE_DELIVERY_AUTHORIZATION

Stop there.
```

## 12. Definition of done

PASS if the stale `PENDING` record is deterministically superseded by stronger send/reconciliation evidence, model/reasoning policy is freshly proven read-only, and a new one-shot proof lease is created.

Otherwise remain safely BLOCKED with the exact unresolved contradiction.
