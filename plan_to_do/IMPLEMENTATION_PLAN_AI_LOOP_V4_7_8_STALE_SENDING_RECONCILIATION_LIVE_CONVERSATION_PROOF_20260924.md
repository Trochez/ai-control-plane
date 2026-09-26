# IMPLEMENTATION PLAN — ai-loop v4.7.8
## Stale `SENDING` Reconciliation + Live Conversation Proof Before Any Further Send

**Authoritative run:** `R20260923T012014`  
**Authoritative state:** `/var/lib/ai-loop/state/R20260923T012014.v3.json`  
**Target release:** `4.7.8`  
**Default disposition:** `BLOCKED` until every send-safety precondition below is proven.

## 1. Current authoritative facts

1. The authenticated Playwright MCP browser is active and owns `/home/trocha/.cache/ai-loop-chatgpt-profile`.
2. That process/profile MUST NOT be terminated, replaced, or raced.
3. The target ChatGPT conversation is open.
4. The current live DOM does not expose a usable message-turn inventory.
5. Persisted delivery ledgers are ambiguous/stale:
   - `failure-evidence-025d7f19b1dd83b26733` → `SENDING`
   - `diagnosis-0c11a13e0c6c` → `SENDING`
6. Historical broker diagnostics from this same run contain evidence that both immutable deliveries existed in the target conversation and each had a following assistant response.
7. The canonical historical operator action was attempted and terminated with `MISSING_COMMAND:jq`.
8. That operator action MUST NOT be rerun.
9. No additional message may be sent until stale `SENDING` ledgers are reconciled deterministically and the live browser is proven to be on the exact authoritative conversation.
10. `FINAL_GO` and `AI_LOOP_COMPLETE=GO` remain unverified.

## 2. Safety invariants

- Never resend an immutable delivery merely because its ledger says `SENDING`.
- Never infer `SENT` from elapsed time.
- Never infer `NOT_SENT` from a missing live DOM turn.
- Never rerun the canonical operator action.
- Never kill or replace the currently authenticated Playwright MCP/browser profile.
- Never create a new ChatGPT chat for this run.
- Never send any operator-result/reconciliation message until live conversation proof passes.
- Never mutate `bot_trading`, Semaphore, VPS, or production as part of ledger reconciliation.
- Reconciliation is read-only until an outbound send is explicitly unlocked.
- Any ambiguity results in `BLOCKED`, not retry/resend.

## 3. Delivery state model

Use:

```text
PENDING
SENDING
RECONCILED_SENT
SENT
DELIVERY_AMBIGUOUS
DELIVERY_BLOCKED
```

`RECONCILED_SENT` is terminal for duplicate-prevention purposes and MUST be treated like `SENT` by resend guards.

## 4. Reconcile stale `SENDING` ledgers from historical evidence

Use only evidence under:

```text
/var/lib/ai-loop/runs/R20260923T012014/
```

Preferred source:

```text
browser/broker-diagnostics/2026-09-24T064145688Z-ENSURE_CHAT_POLICY.html
browser/broker-diagnostics/2026-09-24T064145688Z-ENSURE_CHAT_POLICY.json
```

Before consuming them:

- verify files exist;
- compute SHA256;
- record hashes in reconciliation evidence;
- verify diagnostic URL equals the authoritative conversation URL;
- verify project context is `TARGET` where available.

For each immutable delivery:

```text
failure-evidence-025d7f19b1dd83b26733
diagnosis-0c11a13e0c6c
```

require:

1. Exact immutable marker exists in a user message.
2. User message belongs to the authoritative conversation URL.
3. A following assistant turn exists before the next user delivery.
4. Assistant provenance is persisted:
   - turn_id
   - message_id
   - testid
   - role
5. Evidence files and hashes are recorded.
6. No contradictory evidence shows another conversation or duplicate delivery.

On PASS:

```text
delivery_status=RECONCILED_SENT
reconciliation_source=HISTORICAL_BROKER_DIAGNOSTIC
resend_allowed=false
```

If proof fails:

```text
delivery_status=DELIVERY_AMBIGUOUS
outbound_send_blocked=true
```

and stop.

## 5. Operator action terminal reconciliation

The canonical operator action MUST NOT be rerun.

Persist:

```text
OPERATOR_ACTION_EXECUTION=FAILED_TERMINAL
retry_allowed=false
failure_reason=MISSING_COMMAND:jq
```

Record:

- canonical source message id;
- canonical block index;
- canonical SHA256;
- byte length;
- attempt id;
- exit code;
- stdout SHA256;
- stderr SHA256;
- evidence directory;
- verified side-effect classification.

The already-persisted failure result is the literal operator result that may later be delivered to ChatGPT.

## 6. Global outbound guard

Before ANY new send require:

```text
STALE_LEDGER_RECONCILIATION=PASS
LIVE_CONVERSATION_PROOF=PASS
CHAT_SURFACE=PASS
MODEL_GUARD=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

Otherwise:

```text
OUTBOUND_SEND=BLOCKED
```

No fallback may downgrade these requirements.

## 7. Prove the live conversation without sending

The currently authenticated Playwright MCP process/profile remains owner.

Do not launch another browser using the same profile.

A read-only observer must prove all of:

1. Active authenticated ChatGPT page exists.
2. Current URL exactly equals authoritative conversation URL.
3. Conversation id extracted from URL exactly equals authoritative conversation id.
4. Project context resolves to `TARGET` / `bot_trading`.
5. Surface is normal Chat, not Work or Codex.
6. No generation/send operation is active.
7. Composer is addressable but remains untouched.
8. At least one conversation-specific immutable fingerprint is visible after bounded read-only hydration.

Preferred fingerprint order:

```text
A. exact immutable delivery marker
B. exact historical message_id / turn_id
C. exact known diagnosis filename/hash text
D. exact existing assistant response fingerprint
```

URL alone is NOT sufficient.

### Bounded read-only hydration

Allowed:

- wait for hydration;
- inspect main conversation container;
- scroll existing conversation viewport;
- scroll top/bottom and back;
- query existing DOM;
- inspect page HTML;
- use existing session capabilities to reveal already-loaded history.

Forbidden:

- typing;
- clicking Send;
- creating a new chat;
- switching to another conversation;
- killing/replacing the authenticated profile owner.

On PASS persist:

```text
LIVE_CONVERSATION_PROOF=PASS
conversation_url=<exact URL>
conversation_id=<exact id>
project=TARGET
surface=chat
fingerprint_type=<type>
fingerprint_value=<value/hash>
proof_timestamp=<timestamp>
proof_artifact=<path>
```

If no fingerprint can be proven after bounded attempts:

```text
LIVE_CONVERSATION_PROOF=FAIL
OUTBOUND_SEND=BLOCKED
```

and stop.

## 8. Separate execution from result delivery

Current operator execution:

```text
OPERATOR_ACTION_EXECUTION=FAILED_TERMINAL
OPERATOR_ACTION_RETRY_ALLOWED=false
```

Result delivery:

```text
OPERATOR_RESULT_DELIVERY=PENDING
```

It remains `PENDING` until every outbound gate passes.

## 9. Operator result delivery

Only after:

```text
STALE_LEDGER_RECONCILIATION=PASS
LIVE_CONVERSATION_PROOF=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

may the controller deliver the already-persisted literal result.

Requirements:

- new unique delivery id dedicated to the operator result;
- persist send intent before physical send;
- identify historical action source;
- report literal exit/failure evidence;
- state explicitly that the action was not rerun;
- avoid reconstructing or altering operator output;
- reconcile the new delivery after physical send.

## 10. Existing diagnosis remains provisional

The existing diagnosis remains:

```text
provisional=true
```

until GPT Web consumes the operator-action failure result and reconciles/updates it.

Expected path:

```text
historical deliveries -> RECONCILED_SENT
operator action -> FAILED_TERMINAL
live conversation proof -> PASS
operator result -> delivered once
assistant response -> SETTLED
diagnosis -> RECONCILED
DIAGNOSIS_READY
```

Do not advance directly to replan before this sequence.

## 11. Regression tests

Add deterministic tests for:

1. `SENDING` + historical marker + following assistant → `RECONCILED_SENT`.
2. `SENDING` + no proof → `DELIVERY_AMBIGUOUS`; no resend.
3. `RECONCILED_SENT` prevents duplicate resend.
4. Historical evidence URL mismatch → reconciliation FAIL.
5. Historical project mismatch → reconciliation FAIL.
6. Live URL match alone → insufficient.
7. Live URL + project + immutable fingerprint → PASS.
8. Zero live turns after bounded hydration → BLOCKED; no send.
9. Existing authenticated profile owner is never killed/replaced.
10. Operator action `FAILED_TERMINAL` cannot rerun.
11. Installing a missing dependency does not reset consumed operator action.
12. Operator execution and result-delivery states are independent.
13. Existing stale diagnosis/failure-evidence entries reconcile without physical resend.
14. Global send guard blocks outbound while any condition is false.
15. Resume does not repeat completed reconciliation.
16. Same persisted operator result cannot be delivered twice.
17. Provenance fields remain distinct: turn_id, message_id, testid, role.

## 12. Required evidence artifacts

Create under:

```text
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v478/
```

At minimum:

```text
historical-ledger-reconciliation.json
historical-evidence-sha256.txt
live-conversation-proof.json
live-conversation-proof.html
operator-action-terminal-state.json
outbound-gate.json
RESULT.md
evidence.json
```

## 13. Version and validation

Version as `4.7.8`.

Run:

```text
node --check
git diff --check
Python compile
broker tests
observer tests
delivery-ledger reconciliation tests
live-conversation proof tests
operator-action idempotency tests
attachment tests
policy/hydration tests
controller self-tests
resume tests
100-loop synthetic soak
```

No live send is part of local validation.

## 14. Live acceptance order

Required:

```text
ai-loopd-v3 version=4.7.8

STALE_LEDGER_RECONCILIATION
failure-evidence-... = RECONCILED_SENT
diagnosis-... = RECONCILED_SENT

OPERATOR_ACTION_EXECUTION=FAILED_TERMINAL
OPERATOR_ACTION_RETRY_ALLOWED=false
OPERATOR_RESULT_DELIVERY=PENDING

LIVE_CONVERSATION_PROOF=PASS
CHAT_SURFACE=PASS
MODEL_GUARD=PASS
OUTBOUND_IDEMPOTENCY=PASS

OUTBOUND_SEND_UNLOCKED=true

OPERATOR_RESULT_DELIVERY=SENDING
OPERATOR_RESULT_DELIVERY=SENT or RECONCILED_SENT

ASSISTANT_OBSERVER=SETTLED
DIAGNOSIS_RECONCILED
DIAGNOSIS_READY
```

Only then may normal replan/implementation/CI continue.

## 15. Stop conditions

Immediately stop and leave the run `BLOCKED` if:

- historical evidence conflicts;
- either stale delivery cannot be reconciled;
- exact live conversation cannot be proven;
- browser ownership would require killing/replacing the authenticated MCP process;
- any new delivery would be ambiguous;
- controller proposes rerunning the canonical operator action;
- a new chat would be required;
- send idempotency cannot be proven.

No emergency resend path is allowed.

## 16. `/omo-team` execution prompt

```text
/omo-team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_7_8_STALE_SENDING_RECONCILIATION_LIVE_CONVERSATION_PROOF_20260924.md for authoritative run R20260923T012014.

The current task is historical/send-state reconciliation, not new bot_trading implementation.

Hard requirements:

- Do not kill, replace, or race the authenticated Playwright MCP process that owns /home/trocha/.cache/ai-loop-chatgpt-profile.
- Do not rerun the canonical operator action. Its MISSING_COMMAND:jq attempt is terminal for exactly-once purposes.
- Do not resend failure-evidence-025d7f19b1dd83b26733.
- Do not resend diagnosis-0c11a13e0c6c.
- Reconcile those stale SENDING ledgers from immutable historical broker evidence into RECONCILED_SENT only if exact evidence proves they existed in the authoritative conversation and had following assistant responses.
- If reconciliation is not provable, mark DELIVERY_AMBIGUOUS and stop.
- Before ANY new send, prove the currently authenticated live browser is on the exact authoritative conversation using exact URL/conversation id, TARGET project, normal Chat surface, and at least one immutable conversation-specific fingerprint after bounded read-only hydration.
- URL alone is insufficient.
- If live proof fails, leave the run BLOCKED and send nothing.
- Treat operator execution state and operator-result delivery state independently.
- Persist the previous operator action as FAILED_TERMINAL / retry_allowed=false.
- Only after stale-ledger reconciliation and live-conversation proof PASS may the already-persisted literal operator failure result be delivered once using a new immutable delivery id.
- Existing diagnosis stays provisional until GPT Web reconciles it from that result.
- Preserve turn_id, message_id, testid, and role as separate provenance fields.
- Add all required regressions and evidence artifacts.
- Version as 4.7.8, install only after tests pass, and resume the SAME state.
- Do not declare completion unless live evidence reaches FINAL_GO and AI_LOOP_COMPLETE=GO.
- If any safety gate remains ambiguous, stop BLOCKED without mutation or resend.
```

## 17. Definition of done

Success requires:

```text
FINAL_GO
AI_LOOP_COMPLETE=GO
```

with no duplicate immutable delivery and no repeated operator action.

Otherwise, an acceptable safe terminal outcome for this attempt is a persisted deterministic blocker with:

```text
OUTBOUND_SEND=BLOCKED
```

and zero additional sends or mutations.
