# IMPLEMENTATION PLAN — ai-loop v4.8.7
## Controlled navigation bootstrap for successor-preflight delivery proof

**Authoritative run:** `R20260923T012014`
**Current state:** `BLOCKED_NO_SEND`
**Reason for prior block:** browser was at `about:blank`, while v4.8.6 prohibited navigation.
**Purpose:** allow exactly one controlled read-only navigation to the authoritative ChatGPT conversation, then rebuild the no-send delivery proof for the already-completed two-successor preflight.

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

Read all relevance/change classifications from persisted artifacts only.

## 2. New authorization delta

This plan changes only one previous constraint:

```text
ONE_CONTROLLED_NAVIGATION=AUTHORIZED
```

If the existing authenticated ChatGPT browser page is at `about:blank` or another non-target inert page, exactly ONE navigation is authorized to:

```text
https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589
```

This does NOT authorize sending, typing, opening another conversation, creating a new chat, changing model/reasoning, repeated refreshes, creating delivery intent, or consuming a proof lease.

Use only the existing authenticated browser/session. Do NOT start, replace, kill, or race another browser.

## 3. Navigation safety

Before navigation persist:

```text
pre_navigation_url
pre_navigation_page_count
browser_session_identity if available
navigation_reason=BOOTSTRAP_FROM_ABOUT_BLANK
```

Then perform exactly one navigation to the authoritative URL.

After navigation require:

```text
CONTROLLED_NAVIGATION=PASS
POST_NAVIGATION_URL_EXACT=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
PROJECT=Bot_trading
NORMAL_CHAT_SURFACE=PASS
```

If redirected to login, another conversation, project home without the target conversation, Work/Codex, or any unexpected surface: stop BLOCKED. Do not perform a second navigation.

## 4. Read-only page settling

After navigation:
- wait for the page to settle;
- do not type;
- do not click Send;
- do not open model selectors;
- do not change reasoning;
- do not interact with sidebars.

Require:

```text
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
```

## 5. Model / reasoning proof

Read-only verify:

```text
MODEL=GPT-5.6 Sol
REASONING=High
MODEL_POLICY_PROOF=PASS
```

If the current UI exposes insufficient generic labels, prior-bound-policy fallback is allowed only if exact conversation ID matches, no model/reasoning change is evidenced, and current UI does not contradict the prior bound state:

```text
MODEL_POLICY_PROOF=BOUND_PRIOR_PASS
```

Do not click model/reasoning controls.

## 6. Bootstrap current settled-response witness

Capture only the currently rendered settled assistant response corresponding to the successor-preflight discussion.

Persist:

```text
current-settled-response.txt
current-settled-response-witness.json
```

Compute a NEW hash from the freshly captured response. Do NOT require it to equal any stale v4.8.6 expected hash.

Require the rendered response to unambiguously reference:

```text
TARGET_SHA=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
SUCCESSOR_1_SHA=cd43645e4e38c574bc728e6f383745e160ae766d
SUCCESSOR_2_SHA=2d429e66d185241e0efda9f3385f5aea55b65f5d
```

and the completed successor-preflight result.

Then persist:

```text
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CURRENT_RESPONSE_MATCHES_PREFLIGHT=PASS
```

If the current response cannot be unambiguously tied to this preflight, stop BLOCKED.

## 7. Cross-source provenance

Require:

```text
live conversation id == authoritative conversation id
live project == Bot_trading
preflight manifest == PASS
current response anchors == persisted preflight commit chain
current response hash == freshly captured witness hash
```

Then:

```text
CROSS_SOURCE_PROVENANCE=PASS
PROVENANCE_MODE=CONTROLLED_NAVIGATION_PLUS_LIVE_BOOTSTRAPPED_RESPONSE
```

No live turn/message IDs are required or fabricated.

## 8. Outbound idempotency

For:

```text
delivery_purpose=TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
```

search authoritative local ledgers/evidence.

Require:

```text
EXISTING_DELIVERY_INTENT=false
EXISTING_PHYSICAL_SEND=false
EXISTING_RECONCILED_DELIVERY=false
OUTBOUND_IDEMPOTENCY=PASS
```

Do not create a delivery intent in this plan.

## 9. Combined proof

Require:

```text
CONTROLLED_NAVIGATION=PASS
POST_NAVIGATION_URL_EXACT=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
MODEL_POLICY_PROOF=PASS or BOUND_PRIOR_PASS
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CURRENT_RESPONSE_MATCHES_PREFLIGHT=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

Then:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_7_CONTROLLED_NAVIGATION_MODE
```

## 10. Fresh proof lease

Only if every gate passes, create exactly one new immutable proof lease:

```text
proof_lease_id=<new unique id>
authoritative_run=R20260923T012014
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
project=Bot_trading
delivery_purpose=TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
provenance_mode=CONTROLLED_NAVIGATION_PLUS_LIVE_BOOTSTRAPPED_RESPONSE
state=READY
consumed=false
created_at=<timestamp>
preflight_manifest_sha256=<sha>
current_response_sha256=<fresh sha>
page_identity_sha256=<sha>
cross_source_sha256=<sha>
idempotency_sha256=<sha>
```

Any subsequent navigation/chat switch/composer mutation/outbound send invalidates the lease.

## 11. Evidence directory

Create a NEW directory:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v487/
```

Persist at minimum:

```text
navigation-proof.json
page-identity.json
model-policy-proof.json
current-settled-response.txt
current-settled-response-witness.json
preflight-binding.json
cross-source-provenance.json
outbound-idempotency.json
live-conversation-identity-proof.json
proof-lease.json
RESULT.md
evidence.json
sha256-manifest.txt
```

Validate the manifest.

## 12. Hard prohibitions

Do NOT:
- send or type a ChatGPT message;
- click Send;
- perform more than one navigation;
- switch to another conversation;
- create a new chat;
- rerun the successor preflight;
- clone/fetch Git;
- run tests/CI;
- query Semaphore;
- query VPS;
- use SSH;
- query GitHub;
- mutate Git/repositories;
- deploy/sync;
- create delivery intent;
- consume the new proof lease;
- declare FINAL_GO;
- declare AI_LOOP_COMPLETE=GO.

## 13. Successful terminal state

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS
CONTROLLED_NAVIGATION=PASS
PROVENANCE_MODE=CONTROLLED_NAVIGATION_PLUS_LIVE_BOOTSTRAPPED_RESPONSE
MODEL_POLICY_PROOF=PASS or BOUND_PRIOR_PASS
VISIBLE_SETTLED_RESPONSE_WITNESS=PASS
CURRENT_RESPONSE_MATCHES_PREFLIGHT=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
LIVE_RANGE_WITNESS=NOT_REQUIRED_BY_V4_8_7_CONTROLLED_NAVIGATION_MODE
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_TWO_SUCCESSOR_PREFLIGHT_RESULT_DELIVERY_AUTHORIZATION
FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

Stop there.

## 14. `/omo-team` execution prompt

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_7_CONTROLLED_NAVIGATION_BOOTSTRAP_FOR_SUCCESSOR_PREFLIGHT_DELIVERY_20260926.md for authoritative run R20260923T012014.

This is NO-SEND.

The previous v4.8.6 attempt blocked because the browser was at about:blank and navigation was prohibited.

This plan explicitly authorizes EXACTLY ONE controlled navigation, only if needed, from about:blank/non-target inert state to:

https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589

Use only the existing authenticated browser/session.

Do NOT start/replace/kill another browser.

After the one navigation:
- verify exact URL/conversation/project/normal Chat;
- require empty composer and settled response;
- verify GPT-5.6 Sol + High read-only, or safe prior-bound-policy fallback;
- capture the CURRENT settled response fresh;
- compute a fresh hash;
- bind that response to the authoritative completed preflight via exact commit anchors:
  0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
  cd43645e4e38c574bc728e6f383745e160ae766d
  2d429e66d185241e0efda9f3385f5aea55b65f5d
- require cross-source provenance PASS;
- require outbound idempotency PASS for TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT.

Do NOT require stale prior response hashes to match the newly rendered response.

If all gates pass:
create one NEW proof lease READY/unconsumed.

Persist under:
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v487/

Do NOT:
- send/type;
- navigate a second time;
- create delivery intent;
- consume lease;
- rerun preflight;
- run tests/CI;
- query Semaphore/VPS/GitHub;
- mutate repositories;
- deploy;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

Stop after the no-send proof package.
```
