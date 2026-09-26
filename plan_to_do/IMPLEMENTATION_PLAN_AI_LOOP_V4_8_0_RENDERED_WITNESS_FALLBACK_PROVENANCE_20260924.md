# IMPLEMENTATION PLAN — ai-loop v4.8.0
## Rendered-Witness Fallback for Live Conversation Identity When Immutable Turn IDs Are Not Exposed

**Authoritative run:** `R20260923T012014`
**Authoritative state:** `/var/lib/ai-loop/state/R20260923T012014.v3.json`
**Target release:** `4.8.0`
**Current disposition:** `BLOCKED`
**Outbound send authorization:** NONE in this plan.

## 1. Problem statement

The live authenticated ChatGPT conversation is proven to have the exact authoritative URL, exact authoritative conversation id, expected `Bot_trading` project context, and no active Work/Codex surface.

However, the current live UI does not expose deterministic message-turn provenance for:

```text
failure-evidence-025d7f19b1dd83b26733
diagnosis-0c11a13e0c6c
```

The markers are visibly rendered in conversation content, but their current owning DOM containers expose no stable `data-testid`, `message_id`, `turn_id`, or author role. The same strings also occur in hidden application/script content, so raw string presence is insufficient.

Historical broker evidence from the same authoritative run DOES contain immutable provenance and proves those historical deliveries existed in the authoritative conversation.

Therefore introduce a two-source fallback proof:

```text
historical immutable provenance
+
live rendered conversation witness
```

## 2. Safety invariants

This plan MUST NOT send a message, type into the composer, rerun the canonical operator action, resend historical deliveries, create/switch chats, navigate away, kill/replace the authenticated Playwright MCP, launch a competing browser profile, mutate Semaphore/VPS/bot_trading/production, or declare FINAL_GO / AI_LOOP_COMPLETE=GO.

Any ambiguity leaves:

```text
OUTBOUND_SEND=BLOCKED
```

## 3. Provenance modes

### Mode A — IMMUTABLE_LIVE

Keep v4.7.9 behavior when live DOM exposes:

```text
message_id
turn_id
testid
role
```

### Mode B — HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS

Allow only when Mode A is impossible because current UI does not expose immutable live turn metadata.

Require:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
STALE_LEDGER_RECONCILIATION=PASS
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
LIVE_RENDERED_WITNESS=PASS
CROSS_SOURCE_PROVENANCE=PASS
```

Do not fabricate live immutable ids. Historical provenance stays historical; live proof stays live-rendered-witness proof.

## 4. Historical immutable provenance gate

For each historical delivery marker, require authoritative run evidence proving:

1. exact marker in authoritative conversation;
2. owning historical user turn/message;
3. following historical assistant turn;
4. exact authoritative conversation URL/id;
5. artifact SHA256;
6. no contradictory duplicate evidence.

Persist:

```text
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
```

Known assistant provenance remains:

```text
message_id=1e649da7-f024-44e9-aa37-8d48ed6a70bf
turn_id=59ee4348-f877-4c79-9494-5f54cebda141
testid=conversation-turn-4
role=assistant
```

Never conflate `message_id` and `turn_id`.

## 5. Live rendered-witness proof

Raw HTML/string matches are NOT sufficient.

For each required marker, prove at least one occurrence is truly rendered in the main conversation.

### 5.1 Reject non-conversation candidates

Reject if candidate or ancestor is:

```text
script
style
template
noscript
head
textarea
input
composer
sidebar/search/filter UI
hidden application state
```

or outside the main conversation root.

### 5.2 Visibility requirements

Persist for each accepted candidate:

```text
marker
DOM path
tag
nearest conversation/content ancestor
innerText SHA256
outerHTML SHA256
bounding rectangle
computed display
computed visibility
computed opacity
aria-hidden
hidden attribute
offsetParent status
checkVisibility result if available
screenshot clip path if available
```

Require visible dimensions, visible display/visibility, opacity > 0, no hidden/aria-hidden, and `checkVisibility(...) == true` when available.

### 5.3 Visible uniqueness

For each marker persist:

```text
raw_dom_matches
hidden_or_script_matches
rendered_main_matches
```

Require:

```text
rendered_main_matches == 1
```

Hidden duplicates are allowed only when explicitly classified and excluded. More than one rendered main match is ambiguous and blocks.

### 5.4 Independent witnesses

Require both markers independently:

```text
failure-evidence-... -> rendered witness PASS
diagnosis-...        -> rendered witness PASS
```

They must resolve to distinct rendered content positions consistent with conversation order.

### 5.5 Bind witnesses to conversation identity

Both rendered witnesses must be inside the main conversation root on the page already proving exact URL, exact conversation id, TARGET project, and normal Chat surface.

## 6. Cross-source reconciliation

Require:

```text
historical marker identity == live rendered marker identity
historical conversation id == live conversation id
historical project target == live TARGET
historical deliveries == RECONCILED_SENT
```

Persist historical artifact path/hash, historical provenance, live witness path/hash, marker equality, conversation-id equality, project equality, and result.

Result:

```text
CROSS_SOURCE_PROVENANCE=PASS
```

or BLOCKED if ambiguous.

## 7. Revised live conversation proof gate

Do NOT set `LIVE_TURN_PROVENANCE=PASS` when immutable live turn metadata is unavailable.

Instead introduce:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROVENANCE_MODE=HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS
```

Combined proof may pass via either:

```text
Mode A:
IMMUTABLE_LIVE_TURN_PROVENANCE=PASS
```

or:

```text
Mode B:
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
LIVE_RENDERED_WITNESS=PASS
CROSS_SOURCE_PROVENANCE=PASS
```

plus all common URL/project/surface gates.

Mode B may persist:

```text
LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI
```

without treating it as failure.

## 8. Outbound guard behavior

Change the guard from requiring only immutable live turn provenance to requiring `conversationIdentityProof == PASS`, where:

```text
conversationIdentityProof =
  immutableLiveTurnProvenance == PASS
  OR
  (
    historicalImmutableProvenance == PASS
    AND liveRenderedWitness == PASS
    AND crossSourceProvenance == PASS
  )
```

Common requirements remain mandatory:

```text
STALE_LEDGER_RECONCILIATION=PASS
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

This plan MUST still force:

```text
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION
```

even after proof passes.

## 9. Regression tests

Add tests for:

1. Mode A unchanged.
2. URL-only proof fails.
3. Marker only in `<script>` fails.
4. Marker only in hidden DOM fails.
5. Marker in sidebar/filter fails.
6. Exactly one rendered main-conversation match passes.
7. Hidden duplicate + one rendered match passes.
8. Two rendered matches blocks.
9. Both markers must independently pass.
10. Witnesses must bind to the authoritative conversation root.
11. Historical conversation id must equal live id.
12. Historical/live marker mismatch blocks.
13. `message_id` and `turn_id` remain distinct.
14. Mode B can pass identity proof with `LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI`.
15. Proof PASS does not send.
16. Existing stale deliveries cannot reset to PENDING.
17. FAILED_TERMINAL operator action cannot rerun.
18. Resume does not repeat proof side effects.

## 10. Evidence artifacts

Create under:

```text
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v480/
```

At minimum:

```text
historical-immutable-provenance.json
rendered-witness-failure-evidence.json
rendered-witness-diagnosis.json
rendered-witness-page.html
rendered-witness-page.png
cross-source-provenance.json
conversation-identity-proof.json
outbound-gate.json
RESULT.md
evidence.json
sha256-manifest.txt
```

## 11. Live acceptance — NO SEND

Use the existing authenticated Playwright MCP only. Do not start another browser or ai-loop browser broker.

Required successful checkpoint:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET

NORMAL_CHAT_SURFACE=PASS
SURFACE_ACTION=NONE_REQUIRED
CLASSIFIER_FALSE_POSITIVE=RECONCILED

HISTORICAL_IMMUTABLE_PROVENANCE=PASS

LIVE_RENDERED_WITNESS=PASS
failure-evidence rendered_main_matches=1
diagnosis rendered_main_matches=1

CROSS_SOURCE_PROVENANCE=PASS

LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI

LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROVENANCE_MODE=HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS

OPERATOR_ACTION_EXECUTION=FAILED_TERMINAL
OPERATOR_ACTION_RETRY_ALLOWED=false
OPERATOR_RESULT_DELIVERY=PENDING

OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

No message is sent in this plan.

## 12. Stop conditions

Stop BLOCKED if:

- either marker has zero rendered main-conversation matches;
- either marker has more than one rendered main-conversation match;
- rendered candidate cannot be separated from hidden/script state;
- conversation root cannot be bound to exact URL/id/project;
- historical evidence and live witness disagree;
- stale-ledger reconciliation is not PASS;
- any browser mutation beyond read-only inspection would be required;
- another browser/profile would need to be started;
- operator action rerun is proposed.

## 13. /omo-team prompt

```text
/omo-team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_8_0_RENDERED_WITNESS_FALLBACK_PROVENANCE_20260924.md for authoritative run R20260923T012014.

The run remains BLOCKED and this task is NO-SEND.

The current ChatGPT UI does not expose deterministic live message_id/turn_id/testid/role for the required rendered messages.

Do not keep retrying the impossible v4.7.9 immutable-live-turn requirement.

Implement fallback provenance mode:
HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS

Requirements:
- Keep IMMUTABLE_LIVE as preferred behavior.
- Do not fabricate live immutable ids.
- Require exact URL, exact conversation id, TARGET project, normal Chat surface, stale-ledger reconciliation PASS.
- Reuse authoritative historical broker evidence for immutable historical provenance.
- Prove both required delivery markers are independently and uniquely RENDERED in the MAIN live conversation.
- Exclude script/style/template/hidden/sidebar/composer/filter matches.
- Persist visibility, bounds, DOM path, hashes, screenshot evidence, and raw-vs-rendered match counts.
- Require exactly one rendered main-conversation witness for each marker.
- Cross-check historical marker/conversation identity against live marker/conversation identity.
- Introduce LIVE_CONVERSATION_IDENTITY_PROOF, PROVENANCE_MODE, HISTORICAL_IMMUTABLE_PROVENANCE, LIVE_RENDERED_WITNESS, CROSS_SOURCE_PROVENANCE.
- Allow combined identity proof to PASS via fallback while LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI.
- Keep outbound sending blocked throughout implementation and live acceptance.
- Do not rerun canonical operator action.
- Do not resend failure-evidence or diagnosis.
- Do not start/kill/replace the authenticated Playwright browser.
- Add deterministic regression coverage.
- Version runtime as 4.8.0.
- Install safely without legacy install.sh if it still requires killing the active Playwright owner.
- Perform NO-SEND live acceptance using the existing authenticated Playwright MCP.
- Stop with OUTBOUND_SEND=BLOCKED reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION even if identity proof passes.
- Do not declare FINAL_GO or AI_LOOP_COMPLETE=GO.
```

## 14. Definition of done

PASS:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROVENANCE_MODE=HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION
```

with zero sends.

Otherwise persist a deterministic safe BLOCK with zero send/rerun/navigation/production mutation.
