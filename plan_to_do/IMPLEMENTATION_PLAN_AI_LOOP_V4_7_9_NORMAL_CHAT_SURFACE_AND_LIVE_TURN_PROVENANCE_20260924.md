# IMPLEMENTATION PLAN — ai-loop v4.7.9
## Normalize Existing Conversation to Normal Chat + Prove Live Turn Provenance

**Authoritative run:** `R20260923T012014`
**Authoritative state:** `/var/lib/ai-loop/state/R20260923T012014.v3.json`
**Target release:** `4.7.9`
**Current disposition:** `BLOCKED`
**No outbound send is authorized by this plan.**

## 1. Current proven facts

Read-only live verification already established:

- Exact authoritative ChatGPT conversation URL: PASS.
- Project context `Bot_trading` / `TARGET`: PASS.
- Conversation-specific fingerprints are present in live DOM: PASS.
- Current surface is NOT acceptable:
  - `work=true`
  - `codex=true`
- Immutable live message-turn provenance is not yet sufficiently proven.
- No message was sent.
- No operator action was rerun.
- No navigation to a different conversation occurred.
- `FINAL_GO` and `AI_LOOP_COMPLETE=GO` remain unverified.

Therefore the remaining blockers are:

```text
NORMAL_CHAT_SURFACE_PROOF
LIVE_IMMUTABLE_TURN_PROVENANCE
```

## 2. Hard safety invariants

This plan MUST NOT:

- send any ChatGPT message;
- type into the composer;
- create a new chat;
- switch to a different conversation;
- kill or replace the authenticated Playwright MCP process;
- race the existing browser profile;
- rerun the canonical operator action;
- resend `failure-evidence-025d7f19b1dd83b26733`;
- resend `diagnosis-0c11a13e0c6c`;
- mutate `bot_trading`, Semaphore, VPS, or production;
- set `OUTBOUND_SEND_UNLOCKED=true`.

Any ambiguity leaves the run `BLOCKED`.

## 3. Surface normalization objective

The exact same authoritative conversation must be placed into normal Chat surface:

```text
surface=chat
work=false
codex=false
```

without creating or switching conversations.

The URL and conversation id MUST remain exactly unchanged before and after surface normalization.

### 3.1 Inspect before acting

Persist the current surface state, including:

- exact URL;
- conversation id;
- project context;
- work/codex indicators;
- visible mode controls;
- DOM markers that caused `work=true` and `codex=true`;
- screenshot;
- HTML snapshot.

Do not assume which UI control changes the mode.

### 3.2 Determine the minimal reversible UI action

Using the existing authenticated page, identify the actual UI control that returns the current conversation to normal Chat.

Allowed only if all are true:

- action changes mode/surface only;
- it does not create a new conversation;
- it does not send a message;
- it does not alter project membership;
- it does not navigate to a different conversation id.

Do not guess selectors or click an ambiguous control.

### 3.3 Post-action proof

Immediately after the surface-only action, require:

```text
current_url == authoritative_url
current_conversation_id == authoritative_conversation_id
project_context == TARGET
surface == chat
work == false
codex == false
```

If any identity changes:

```text
SURFACE_NORMALIZATION=FAIL
OUTBOUND_SEND=BLOCKED
```

and stop.

## 4. Prove immutable live turn provenance

Conversation-specific text fingerprints alone are insufficient.

For each target historical item, prove its owning live message/turn DOM identity.

Targets:

```text
failure-evidence-025d7f19b1dd83b26733
diagnosis-0c11a13e0c6c
```

Also use known assistant provenance where available:

```text
assistant message_id=1e649da7-f024-44e9-aa37-8d48ed6a70bf
assistant turn_id=59ee4348-f877-4c79-9494-5f54cebda141
testid=conversation-turn-4
role=assistant
```

### 4.1 Required extraction for each live marker

Locate the exact fingerprint text in the main conversation DOM.

Walk to the nearest owning message/turn ancestors and persist:

```text
marker
role
message_id
turn_id
testid
DOM order/index
text SHA256
outerHTML SHA256
```

The provenance extractor MUST distinguish:

```text
turn_id
message_id
testid
role
```

and MUST NOT conflate them.

### 4.2 Required proof for each immutable delivery

For each delivery marker:

1. marker exists in a live `role=user` message;
2. owning `message_id` is present if the live DOM exposes it;
3. owning `turn_id` is present if exposed;
4. owning `testid` is present if exposed;
5. record belongs to main conversation, not sidebar/composer/preview;
6. a following assistant turn exists before the next user delivery;
7. following assistant provenance is persisted;
8. DOM order is deterministic.

### 4.3 Historical/live cross-check

Compare live provenance against:

```text
/var/lib/ai-loop/runs/R20260923T012014/browser/broker-diagnostics/2026-09-24T064145688Z-ENSURE_CHAT_POLICY.html
```

At minimum, the known assistant message must reconcile to:

```text
message_id=1e649da7-f024-44e9-aa37-8d48ed6a70bf
turn_id=59ee4348-f877-4c79-9494-5f54cebda141
testid=conversation-turn-4
role=assistant
```

If live and historical provenance conflict:

```text
LIVE_TURN_PROVENANCE=AMBIGUOUS
OUTBOUND_SEND=BLOCKED
```

and stop.

## 5. Combined proof gate

Only report:

```text
LIVE_CONVERSATION_PROOF=PASS
```

when ALL are simultaneously true:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
work=false
codex=false
IMMUTABLE_LIVE_TURN_PROVENANCE=PASS
```

This plan still MUST NOT send anything even after PASS.

Persist:

```text
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION
```

## 6. Required evidence artifacts

Create/update under:

```text
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v479/
```

At minimum:

```text
pre-surface-proof.json
pre-surface-proof.html
pre-surface-proof.png
surface-normalization.json
post-surface-proof.json
post-surface-proof.html
post-surface-proof.png
live-turn-provenance.json
historical-live-provenance-diff.json
outbound-gate.json
RESULT.md
evidence.json
```

Every evidence artifact should have SHA256 recorded.

## 7. Controller/broker behavior

If code changes are required, add pure helpers for:

```text
surface identity classification
same-conversation surface transition verification
nearest owning message/turn provenance extraction
historical/live provenance comparison
combined live proof gate
```

Do not weaken existing outbound guards.

The guarded send path must continue to reject all sends during this plan.

## 8. Regression coverage

Add tests for:

1. Same URL/project but `work=true` → blocked.
2. Same URL/project but `codex=true` → blocked.
3. Surface transition changes conversation id → fail.
4. Surface transition keeps exact URL/id and produces Chat/work=false/codex=false → pass.
5. Fingerprint text without owning message provenance → fail.
6. Marker inside sidebar/preview → fail.
7. Marker in main user message with role/message_id/turn_id/testid → pass.
8. Following assistant provenance extraction.
9. `turn_id` and `message_id` remain distinct.
10. Historical/live provenance mismatch → blocked.
11. Full combined gate PASS does not itself send anything.
12. Resume does not repeat a completed surface-only normalization unnecessarily.

## 9. Live acceptance

Required final state for this plan:

```text
SURFACE_NORMALIZATION=PASS
current_url=<authoritative URL>
current_conversation_id=<authoritative id>
project_context=TARGET
surface=chat
work=false
codex=false

LIVE_TURN_PROVENANCE=PASS

failure-evidence-025d7f19b1dd83b26733:
  role=user
  owning provenance proven
  following assistant proven

diagnosis-0c11a13e0c6c:
  role=user
  owning provenance proven
  following assistant proven

known assistant:
  message_id=1e649da7-f024-44e9-aa37-8d48ed6a70bf
  turn_id=59ee4348-f877-4c79-9494-5f54cebda141
  testid=conversation-turn-4
  role=assistant

LIVE_CONVERSATION_PROOF=PASS

OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION
```

No send occurs in this plan.

## 10. Stop conditions

Stop `BLOCKED` immediately if:

- no unambiguous normal-Chat surface control exists;
- switching mode would create or switch conversation;
- exact URL/id changes;
- work/codex remains true;
- fingerprint cannot be tied to immutable owning message/turn provenance;
- historical/live provenance conflicts;
- browser ownership would need to be killed/replaced;
- any send would be required to prove the conversation.

## 11. `/omo-team` prompt

```text
/omo-team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_7_9_NORMAL_CHAT_SURFACE_AND_LIVE_TURN_PROVENANCE_20260924.md for authoritative run R20260923T012014.

This is a NO-SEND verification/reconciliation task.

Current live evidence already proves:
- exact authoritative conversation URL
- TARGET/Bot_trading project
- conversation-specific fingerprints in DOM

But current surface is invalid:
work=true
codex=true

and immutable live message-turn provenance is still insufficient.

Requirements:

1. Keep the existing authenticated Playwright MCP/browser/profile alive.
2. Do not launch a competing browser.
3. Do not send or type anything.
4. Inspect the real current UI and identify an unambiguous mode/surface-only action that returns the SAME conversation to normal Chat.
5. Perform that action only if it cannot create/switch conversation and cannot send anything.
6. Prove exact URL and conversation id are unchanged afterward.
7. Require:
   surface=chat
   work=false
   codex=false
   project=TARGET
8. Then prove immutable live turn provenance for:
   failure-evidence-025d7f19b1dd83b26733
   diagnosis-0c11a13e0c6c
9. Persist nearest owning role/message_id/turn_id/testid and following assistant provenance.
10. Cross-check live provenance against authoritative historical diagnostics.
11. Preserve message_id and turn_id as distinct fields.
12. If any ambiguity remains, stop BLOCKED.
13. Even if LIVE_CONVERSATION_PROOF=PASS, DO NOT SEND.
14. Persist:
   OUTBOUND_SEND=BLOCKED
   reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION
15. Do not rerun the canonical operator action.
16. Do not resend any historical immutable delivery.
17. Do not declare FINAL_GO or AI_LOOP_COMPLETE=GO.
```

## 12. Definition of done

This plan succeeds when the SAME existing conversation is proven as:

```text
TARGET project
normal Chat
work=false
codex=false
immutable live turn provenance proven
LIVE_CONVERSATION_PROOF=PASS
```

while:

```text
OUTBOUND_SEND=BLOCKED
```

remains enforced pending the next explicit result-delivery plan.
