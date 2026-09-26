# IMPLEMENTATION PLAN — ai-loop v4.8.2
## Fresh live-proof refresh and one-shot proof lease

**Authoritative run:** `R20260923T012014`  
**Current runtime baseline:** `4.8.1`  
**Current disposition:** `BLOCKED`  
**Outbound authorization in this plan:** NONE

## 1. Current facts

The latest Semaphore evidence delivery attempt stopped before send because the mandatory live gates were not currently accepted:

```text
LIVE_CONVERSATION_IDENTITY_PROOF
LIVE_RANGE_WITNESS
CROSS_SOURCE_PROVENANCE
```

Existing proof artifacts are stale/failed and MUST NOT authorize a send.

No delivery intent exists for the Semaphore read-only evidence delivery.

No outbound message was sent.

The canonical historical operator action remains terminal-failed and non-rerunnable.

## 2. Objective

Produce a fresh, read-only, authoritative live-proof package from the existing authenticated Playwright MCP session.

If all gates pass, create a one-shot proof lease that may be consumed by a later, separately authorized outbound delivery.

This plan itself performs NO send.

## 3. Hard prohibitions

Do NOT:
- type into the ChatGPT composer;
- click Send;
- create a delivery intent;
- navigate to another conversation;
- create a new chat;
- switch project;
- restart/replace/kill Playwright MCP;
- launch another browser;
- start ai-loopd-v3 or browser-broker-v1.cjs;
- rerun the historical canonical operator action;
- rerun the Python Semaphore collection;
- mutate Semaphore, GitHub, Git, VPS, bot_trading, production, or repository state;
- install jq;
- create commits or push;
- declare FINAL_GO;
- declare AI_LOOP_COMPLETE=GO.

## 4. Authoritative live page

Require exact URL:

```text
https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589
```

Require:

```text
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
project=Bot_trading
surface=normal Chat
model=GPT-5.6 Sol
reasoning=High
```

Model/reasoning are policy observations and do not substitute for identity proof.

## 5. Fresh proof directory

Create:

```text
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v482-live-refresh/
```

Persist at minimum:

```text
page-identity.json
page-snapshot.html
page-snapshot.png
range-witness-failure-evidence.json
range-witness-diagnosis.json
range-witness-operator-result.json
historical-immutable-provenance.json
cross-source-provenance.json
live-conversation-identity-proof.json
proof-lease.json
outbound-gate.json
RESULT.md
evidence.json
sha256-manifest.txt
```

## 6. Gate A — fresh live range witness

Using v4.8.1 Range semantics and the existing authenticated page, scan only the visible main conversation.

Required visible markers:

```text
failure-evidence-025d7f19b1dd83b26733
diagnosis-0c11a13e0c6c
operator-result-delivery-b677dccd08404429a20721413bfdc9ed
```

For each marker:

1. Build the visible text-node stream under the main conversation root.
2. Exclude script/style/template/application-state/sidebar/composer/search/filter/hidden nodes.
3. Locate exact visible marker occurrence.
4. Map it to an exact DOM Range.
5. Require positive Range client rects.
6. Deduplicate by exact Range identity.
7. Persist context hashes and document position.

Require:

```text
failure-evidence unique_visible_ranges=1
diagnosis unique_visible_ranges=1
operator-result-delivery unique_visible_ranges=1
```

If any marker has zero or more than one unique visible Range:

```text
LIVE_RANGE_WITNESS=FAIL or AMBIGUOUS
OUTBOUND_SEND=BLOCKED
```

Stop.

Otherwise:

```text
LIVE_RANGE_WITNESS=PASS
```

## 7. Gate B — historical immutable provenance

Re-validate authoritative historical evidence without mutating it.

Require:
- failure-evidence historical provenance;
- diagnosis historical provenance;
- operator-result delivery ledger/provenance;
- canonical assistant historical provenance internally consistent;
- no contradictory duplicate successful delivery;
- old jq-based operator action remains terminal and non-rerunnable.

Persist:

```text
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
```

Do not invent live message/turn identifiers.

## 8. Gate C — cross-source provenance

Cross-check:

```text
historical conversation id == live conversation id
historical project == live Bot_trading
historical marker strings == live rendered marker strings
historical delivery ordering == live Range ordering
```

Require ordering:

```text
failure-evidence
<
diagnosis
<
operator-result-delivery-b677dccd08404429a20721413bfdc9ed
```

Persist:

```text
CROSS_SOURCE_PROVENANCE=PASS
```

If conflict or ambiguity exists, block.

## 9. Combined live identity proof

Require simultaneously:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
MODEL_POLICY=GPT-5.6-Sol+High
LIVE_RANGE_WITNESS=PASS
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
CROSS_SOURCE_PROVENANCE=PASS
STALE_LEDGER_RECONCILIATION=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

Then persist:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROVENANCE_MODE=HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS
LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI
```

`LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI` is acceptable and MUST NOT be fabricated as PASS.

## 10. One-shot proof lease

Generate an immutable `proof_lease_id`.

Persist:

```text
proof_lease_id
authoritative_run
conversation_id
project
url
created_at
page_identity_sha256
range_witness_sha256
historical_provenance_sha256
cross_source_sha256
live_identity_proof_sha256
state=READY
consumed=false
```

The lease remains valid only while all are true:

```text
same browser session
same conversation URL/id
same project
no navigation
no chat switch
no identity-changing page reload
no composer typing
no outbound send
no new delivery intent
no contradictory ledger mutation
```

A later outbound delivery MUST perform just-in-time read-only verification and atomically consume the lease when its delivery intent is durably persisted:

```text
state=CONSUMED
consumed=true
```

A consumed lease can never authorize another send.

If any identity condition changes before consumption:

```text
state=STALE
OUTBOUND_SEND=BLOCKED
```

and a new proof lease is required.

## 11. Important: no delivery intent yet

This plan MUST NOT create a Semaphore evidence delivery id or `state=SENDING`.

Those belong to a later separately authorized operation.

Successful completion stops at:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_SEMAPHORE_EVIDENCE_DELIVERY_AUTHORIZATION
```

## 12. Successful terminal state

```text
LIVE_RANGE_WITNESS=PASS
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
CROSS_SOURCE_PROVENANCE=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS

PROVENANCE_MODE=HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS
LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI

PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false

OLD_OPERATOR_ACTION_RETRY_ALLOWED=false

OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_SEMAPHORE_EVIDENCE_DELIVERY_AUTHORIZATION

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

No outbound message occurs.

## 13. Stop conditions

Stop BLOCKED if:
- exact URL/id/project cannot be proven;
- normal Chat surface cannot be proven;
- any required marker does not have exactly one visible Range;
- historical/live ordering conflicts;
- cross-source provenance fails;
- stale-ledger reconciliation fails;
- outbound idempotency fails;
- browser mutation would be required;
- another browser would need to start;
- a send/delivery intent is proposed during this plan.

## 14. /omo-team prompt

```text
/omo-team execute authoritative live-proof refresh only for run R20260923T012014 according to IMPLEMENTATION_PLAN_AI_LOOP_V4_8_2_LIVE_PROOF_REFRESH_LEASE_20260925.md.

This is NO-SEND and NO-DELIVERY-INTENT.

Use ONLY the existing authenticated Playwright MCP session.

Freshly prove:
- LIVE_RANGE_WITNESS
- HISTORICAL_IMMUTABLE_PROVENANCE
- CROSS_SOURCE_PROVENANCE
- LIVE_CONVERSATION_IDENTITY_PROOF

Use v4.8.1 Range witness semantics.

Required visible markers:
- failure-evidence-025d7f19b1dd83b26733
- diagnosis-0c11a13e0c6c
- operator-result-delivery-b677dccd08404429a20721413bfdc9ed

Require exactly one unique visible Range for each.

Require ordering:
failure-evidence < diagnosis < operator-result-delivery.

Require exact current URL:
https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589

Require:
project=Bot_trading
surface=normal Chat
model=GPT-5.6 Sol
reasoning=High

Do not fabricate live message_id/turn_id/testid/role.

Persist fresh evidence under:
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v482-live-refresh/

If and only if all identity/provenance gates pass, create a one-shot proof lease with state=READY and consumed=false.

Do NOT:
- send a message;
- type into composer;
- create delivery intent;
- click Send;
- navigate;
- switch chats;
- restart/replace browser;
- rerun any operator action;
- rerun the Semaphore Python evidence collection;
- mutate Git/Semaphore/GitHub/VPS/bot_trading/production;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

Successful terminal state:
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_SEMAPHORE_EVIDENCE_DELIVERY_AUTHORIZATION

Stop there.
```

## 15. Definition of done

PASS if fresh evidence proves all mandatory live gates and creates a READY/unconsumed one-shot proof lease.

SAFE BLOCK if any gate cannot be freshly established.

This plan never sends a message.
