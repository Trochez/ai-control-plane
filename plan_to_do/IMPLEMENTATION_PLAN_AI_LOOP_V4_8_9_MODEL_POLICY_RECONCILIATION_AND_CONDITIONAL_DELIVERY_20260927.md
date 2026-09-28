# IMPLEMENTATION PLAN — ai-loop v4.8.9
## Model-policy reconciliation and conditional exactly-once delivery

**Authoritative run:** `R20260923T012014`  
**Purpose:** reconcile the remaining exact-model safety gate for the already-prepared v4.8.8 proof lease, then conditionally perform exactly one delivery of the completed two-successor preflight result.

## 1. Current authoritative state

Use the existing v4.8.8 proof package:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v488/
```

Require:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS
PROVENANCE_MODE=ARTIFACT_BOUND_OUTBOUND_PROOF
ARTIFACT_BINDING=PASS
OUTBOUND_IDEMPOTENCY=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
CROSS_SOURCE_PROVENANCE=PASS
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
```

The only unresolved delivery gate is exact model-policy reconciliation.

Current read-only evidence establishes:

```text
REASONING=High
MODEL=UNAVAILABLE_FROM_READ_ONLY_GENERIC_UI
```

Do NOT reinterpret `UNAVAILABLE` as GPT-5.6 Sol.

## 2. Authoritative conversation

Require current page:

```text
https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589
```

Require before model inspection:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
REASONING=High
```

## 3. Controlled model-selector inspection

Authorize exactly ONE non-selecting inspection of the current model selector/menu.

Allowed:
1. Open the current model selector/menu.
2. Read which model is currently selected.
3. Do NOT click/select/change a model.
4. Close the selector without changing selection.
5. Revalidate exact URL, conversation ID, project, normal Chat, empty composer, and reasoning High.

Persist:

```text
MODEL_SELECTOR_OPEN_COUNT=1
MODEL_SELECTION_CHANGE=NO
```

If the selector directly proves:

```text
MODEL=GPT-5.6 Sol
REASONING=High
```

persist:

```text
MODEL_POLICY_PROOF=PASS
MODEL_POLICY_PROOF_MODE=DIRECT_SELECTOR_INSPECTION
```

Then continue to lease revalidation.

If the selector does not expose the exact selected model:

```text
MODEL_SELECTOR_EXACT_MODEL=UNAVAILABLE
```

close it without selection and continue to the immutable prior-bound fallback.

If any different model is explicitly shown as selected:

```text
MODEL_POLICY_PROOF=FAIL
reason=MODEL_CONTRADICTION
```

Do NOT send. Do NOT consume the lease. Stop.

## 4. Immutable prior-bound fallback

This fallback is authorized only when direct selector inspection cannot establish the exact model.

Search read-only through persisted local artifacts for the most recent immutable successful model-policy proof satisfying all:

```text
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
project=Bot_trading
MODEL=GPT-5.6 Sol
REASONING=High
proof/result state=PASS
```

Use local run evidence only.

Do NOT query ChatGPT remotely, GitHub, Semaphore, VPS, SSH, network APIs, or other remote systems for this fallback.

Inspect local browser/delivery/proof ledgers between that prior proof and now.

Require:

```text
PRIOR_EXACT_MODEL_PROOF_FOUND=true
PRIOR_MODEL=GPT-5.6 Sol
PRIOR_REASONING=High
PRIOR_CONVERSATION_ID_MATCH=PASS
CURRENT_CONVERSATION_ID_MATCH=PASS
CURRENT_REASONING_HIGH=PASS
CURRENT_UI_MODEL_CONTRADICTION=false
MODEL_CHANGE_EVENT_SINCE_PRIOR_PROOF=false
CHAT_SWITCH_SINCE_CURRENT_IDENTITY_PROOF=false
```

If all pass:

```text
MODEL_POLICY_PROOF=BOUND_PRIOR_PASS
MODEL_POLICY_PROOF_MODE=IMMUTABLE_PRIOR_SAME_CONVERSATION
MODEL=GPT-5.6 Sol
REASONING=High
```

Do not use prior proof from another conversation. Do not infer exact model from `High` alone.

If conditions cannot all be proven:

```text
MODEL_POLICY_PROOF=BLOCKED
reason=EXACT_MODEL_POLICY_NOT_PROVABLE
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
```

Stop.

## 5. Model-policy reconciliation evidence

Persist separately under:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-model-policy-reconciliation/
```

At minimum:

```text
pre-inspection-identity.json
model-selector-inspection.json
prior-model-proof.json
model-change-history.json
model-policy-reconciliation.json
RESULT.md
evidence.json
sha256-manifest.txt
```

Do not modify or regenerate the v4.8.8 proof package. Validate the reconciliation manifest.

## 6. Revalidate existing lease

Only after `MODEL_POLICY_PROOF=PASS` or `MODEL_POLICY_PROOF=BOUND_PRIOR_PASS`, read the exact existing lease from:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v488/proof-lease.json
```

Require:

```text
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
```

Revalidate:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
ARTIFACT_BINDING=PASS
OUTBOUND_IDEMPOTENCY=PASS
CROSS_SOURCE_PROVENANCE=PASS
```

Verify persisted payload SHA-256. If any fails: do not consume lease, do not send, stop.

## 7. Git publication reconciliation

Read:

```text
/var/lib/ai-loop/runs/R20260923T012014/control-plane-main-publication/
```

Accept:

```text
FINAL_GIT_PUBLICATION=BLOCKED
reason=NO_COMMITTABLE_REPOSITORY_CHANGES
```

as a non-fatal no-op only if persisted evidence proves:
- repository clean;
- branch `main`;
- local HEAD `2c1e168002576f1f08f1564ff3c2629273e6fc38`;
- local main matched origin/main before publication;
- `git add -A` produced no committable changes;
- no empty commit was created;
- no push was performed.

Persist for the delivery phase:

```text
GIT_PUBLICATION_DISPOSITION=NO_ACTION_REQUIRED
GIT_PUBLICATION_REASON=NO_COMMITTABLE_REPOSITORY_CHANGES
```

Do NOT rerun Git publication.

## 8. Exactly-once delivery

Use exact persisted payload:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v488/payload.txt
```

Verify its SHA-256 against `payload.sha256`. Do not reconstruct payload from memory.

Add exactly ONE new immutable delivery marker.

Generate exactly ONE delivery ID for:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_DELIVERY
```

Before physical send, atomically:
1. persist delivery intent;
2. consume the existing proof lease.

Persist:

```text
delivery_id
delivery_kind=TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_DELIVERY
authoritative_run=R20260923T012014
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
proof_lease_id=<exact existing lease id>
payload_sha256
state=SENDING
created_at
```

Consume:

```text
PROOF_LEASE=CONSUMED
PROOF_LEASE_CONSUMED=true
consumed_by_delivery_id=<delivery_id>
consumed_at=<timestamp>
```

If either durable operation fails: DO NOT SEND.

Perform exactly ONE physical Send. Persist:

```text
physical_send_attempt_count=1
sent_at
physical_send_disposition
```

No second send is authorized. If send disposition is uncertain: DO NOT RESEND. Proceed only to reconciliation.

## 9. Reconciliation

Locate the new immutable marker in the live conversation. Require exactly one visible occurrence.

If physical send evidence and live marker agree:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_DELIVERY=SENT_AND_RECONCILED
DELIVERY_COUNT=1
RETRY_COUNT=0
```

Never resend because later response observation fails.

## 10. Capture and classify

Capture only the immediately following settled assistant response.

Persist:

```text
assistant-response.txt
assistant-response.json
response_sha256
response metadata
observation disposition
fenced/artifact metadata if present
```

If delivery is reconciled but response observation fails, keep delivery `SENT_AND_RECONCILED`, do not resend, and stop for observation recovery.

Classify exact next action as exactly one:

```text
ADDITIONAL_READONLY_EVIDENCE_REQUIRED
REPLAN_REQUIRED
IMPLEMENTATION_PLAN_READY
IMPLEMENTATION_REQUIRED
CI_VALIDATION_REQUIRED
VPS_VALIDATION_REQUIRED
DEPLOYMENT_PLAN_REQUIRED
BLOCKED
NO_FURTHER_ACTION
```

Persist:

```text
NEXT_ACTION_CLASSIFICATION
EXACT_NEXT_ACTION
TARGET_REPOSITORY if applicable
TARGET_BRANCH if applicable
TARGET_VPS_PATH if applicable
EXPECTED_SIDE_EFFECTS
NEW_OUTBOUND_DELIVERY_REQUIRED=true/false
```

Do NOT execute the classified action.

## 11. Delivery evidence

Persist under:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-result-delivery/
```

At minimum:

```text
pre-send-identity-proof.json
git-publication-reconciliation.json
model-policy-reconciliation-reference.json
proof-lease-consumption.json
delivery-intent.json
payload.txt
payload.sha256
physical-send-result.json
delivery-reconciliation.json
assistant-response.txt
assistant-response.json
semantic-classification.json
outbound-ledger.json
RESULT.md
evidence.json
sha256-manifest.txt
```

Validate final manifest.

## 12. Hard prohibitions

Do NOT:
- select/change model;
- change reasoning;
- navigate to another conversation;
- create a new proof lease;
- recreate the v4.8.8 proof package;
- rerun successor preflight;
- rerun Git publication;
- create empty commits;
- commit/push/fetch;
- query GitHub;
- query Semaphore;
- query VPS;
- use SSH;
- run CI/tests;
- deploy/sync;
- send more than once;
- resend on uncertainty;
- execute the classified next action;
- declare FINAL_GO;
- declare AI_LOOP_COMPLETE=GO.

## 13. Success terminal state

```text
MODEL_POLICY_PROOF=<PASS|BOUND_PRIOR_PASS>
MODEL=GPT-5.6 Sol
REASONING=High
MODEL_SELECTION_CHANGE=NO

GIT_PUBLICATION_DISPOSITION=NO_ACTION_REQUIRED

PROOF_LEASE=CONSUMED
PROOF_LEASE_CONSUMED=true

TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_DELIVERY=SENT_AND_RECONCILED
DELIVERY_COUNT=1
RETRY_COUNT=0

ASSISTANT_RESPONSE=SETTLED
RESPONSE_SHA256=<sha256>

NEXT_ACTION_CLASSIFICATION=<allowed value>
EXACT_NEXT_ACTION=<persisted exact instruction>
NEW_OUTBOUND_DELIVERY_REQUIRED=<true|false>

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

If exact model policy cannot be established:

```text
MODEL_POLICY_PROOF=BLOCKED
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

Stop.

## 14. `/omo-team` invocation

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_9_MODEL_POLICY_RECONCILIATION_AND_CONDITIONAL_DELIVERY_20260927.md for authoritative run R20260923T012014.

Use IMPLEMENTATION_PLAN_AI_LOOP_V4_8_8_ARTIFACT_BOUND_SUCCESSOR_PREFLIGHT_DELIVERY_PROOF_WITH_MAIN_PUSH_20260926.md as the authoritative predecessor contract for the existing v4.8.8 proof package and READY lease.

Do not rerun the two-successor preflight or Git publication.
Do not create a new proof lease.
First reconcile the model policy exactly as specified in v4.8.9.
Only if MODEL_POLICY_PROOF becomes PASS or BOUND_PRIOR_PASS may the existing lease be consumed and the exactly-once delivery proceed.
Stop immediately after capturing and classifying the settled response.
```
