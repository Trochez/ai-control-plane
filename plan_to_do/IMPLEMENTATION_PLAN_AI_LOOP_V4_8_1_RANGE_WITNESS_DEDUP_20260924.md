# IMPLEMENTATION PLAN — ai-loop v4.8.1
## Range-based rendered witness deduplication for authoritative live conversation proof

**Authoritative run:** `R20260923T012014`  
**Repo:** `/mnt/d/works/ai-control-plane`  
**Branch:** `main`  
**Baseline HEAD:** `6e6d377dae2a9400357d0cd03c6836a17f05c41b`  
**Current disposition:** `BLOCKED`  
**Outbound authorization:** NONE

## 1. Confirmed current facts

The current v4.8.0 acceptance attempt established:

- Browser is on the required authenticated ChatGPT conversation.
- Historical operator action is terminal with `exit_code=91` (`MISSING_COMMAND:jq`), no observed side effects, no retry allowed.
- Authoritative historical assistant provenance and canonical artifact hash are known.
- Fresh read-only DOM scan found 46 raw DOM matches per required marker.
- Current rendered classifier counted 34 rendered matches per marker because matching ancestor elements inherit descendant `textContent`.
- Therefore `LIVE_RENDERED_WITNESS` is not proven.
- No authoritative v4.8.0 acceptance artifacts were committed to the run directory.
- No outbound action occurred.

The defect is witness cardinality, not URL/project identity.

## 2. Root cause

The v4.8.0 witness counter treats every matching element whose aggregated `textContent` contains the marker as an independent rendered witness.

That is incorrect for nested DOM:

```text
ancestor A
  ancestor B
    content C
      text node containing marker
```

All A/B/C inherit the same descendant text, producing multiple synthetic matches for one visual occurrence.

A rendered witness must represent a unique visible text occurrence, not every ancestor whose `textContent` contains it.

## 3. Required model change

Replace element-cardinality witness counting with **Range-based visible text occurrence counting**.

The canonical identity of a live witness is:

```text
start_text_node
start_offset
end_text_node
end_offset
```

represented in persisted evidence by stable DOM paths plus offsets and hashes.

Ancestor elements may be attached as metadata, but MUST NOT increase witness cardinality.

## 4. Range witness algorithm

### 4.1 Establish main conversation root

Use the already-proven main conversation content root.

Reject any subtree belonging to:

- `script`
- `style`
- `template`
- `noscript`
- `head`
- `textarea`
- `input`
- composer
- sidebar
- search/filter controls
- hidden application state

### 4.2 Build visible text-node stream

Walk only `Node.TEXT_NODE` descendants of the main conversation root.

For each text node:

- reject excluded ancestors;
- reject if nearest rendered element is hidden;
- reject if computed `display:none`;
- reject if computed `visibility:hidden|collapse`;
- reject if effective opacity is zero;
- reject if `aria-hidden=true`;
- reject if hidden attribute applies;
- reject if no visible client rect can be produced.

Build a logical visible text stream while preserving a mapping:

```text
stream_start
stream_end
text_node_dom_path
node_value_sha256
```

Do not use ancestor `textContent` as an occurrence source.

### 4.3 Find exact marker occurrences

Search the visible text stream for the exact immutable marker strings:

```text
failure-evidence-025d7f19b1dd83b26733
diagnosis-0c11a13e0c6c
```

For each occurrence, map the stream offsets back to the start/end text nodes and offsets.

Create a DOM `Range` spanning exactly the marker.

### 4.4 Prove visual rendering

For each exact Range require:

- `Range.getClientRects().length > 0`
- at least one rect has positive width and height;
- range belongs to main conversation root;
- range is not inside excluded UI;
- owning rendered element passes visibility checks.

Persist all rects and a union bounding box.

### 4.5 Deduplicate

Deduplicate only by exact Range identity:

```text
start DOM path + start offset + end DOM path + end offset
```

Do not count parent or grandparent elements or duplicate selector matches resolving to the same Range.

The old values such as `raw_dom_matches=46` remain diagnostics only and MUST NOT be used as rendered witness cardinality.

## 5. Split-node marker support

If a marker is split across adjacent text nodes, the visible stream mapping must still produce one Range spanning those nodes.

Do not require the entire marker to reside in one text node.

## 6. Context binding

For each unique Range, persist a bounded visible-text context window:

```text
128 visible characters before marker
marker
128 visible characters after marker
```

Store hashes for the complete context and the before/after windows.

Where historical evidence permits, compare the live bounded context with the historical rendered/user-message context.

If historical context extraction is unavailable or structurally incompatible, record that limitation instead of fabricating a match.

## 7. Required cardinality

For each required marker require:

```text
unique_visible_ranges == 1
```

Expected acceptance shape:

```text
failure-evidence:
  raw_dom_matches=46   # diagnostic only
  unique_visible_ranges=1

diagnosis:
  raw_dom_matches=46   # diagnostic only
  unique_visible_ranges=1
```

The exact raw count may change and is not a gate.

Zero visible ranges => FAIL.  
More than one visible range => AMBIGUOUS/BLOCK.

## 8. Relative-order proof

Require the two unique visible ranges to have deterministic document order consistent with historical conversation order:

```text
failure-evidence range
<
diagnosis range
```

Persist the ordering proof.

Do not infer author roles or immutable live turn ids from it.

## 9. Historical/live cross-source proof

Retain v4.8.0 Mode B:

```text
PROVENANCE_MODE=HISTORICAL_IMMUTABLE_PLUS_RENDERED_WITNESS
```

Require:

```text
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
LIVE_RANGE_WITNESS=PASS
CROSS_SOURCE_PROVENANCE=PASS
```

`LIVE_TURN_PROVENANCE` may remain:

```text
UNAVAILABLE_IN_CURRENT_UI
```

No live immutable ids may be invented.

## 10. Combined conversation identity gate

Allow:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
```

only when all are true:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
STALE_LEDGER_RECONCILIATION=PASS
HISTORICAL_IMMUTABLE_PROVENANCE=PASS
LIVE_RANGE_WITNESS=PASS
CROSS_SOURCE_PROVENANCE=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

Even after PASS:

```text
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION
```

## 11. Regression tests

Add deterministic tests covering:

1. One leaf text occurrence nested under 20 matching ancestors => one visible Range.
2. Two selectors resolving to same Range => one witness.
3. Marker split across two text nodes => one Range.
4. Hidden text-node occurrence => excluded.
5. Script/application-state occurrence => excluded.
6. Sidebar occurrence => excluded.
7. One visible + many hidden duplicates => one witness.
8. Two genuinely visible marker occurrences => ambiguous/block.
9. Zero visible occurrences => fail.
10. Positive Range rect requirement.
11. Main-conversation-root binding.
12. Relative order `failure-evidence < diagnosis`.
13. Historical/live marker equality.
14. Mode B PASS with `LIVE_TURN_PROVENANCE=UNAVAILABLE_IN_CURRENT_UI`.
15. No send after proof PASS.
16. Terminal operator action remains non-rerunnable.
17. Existing stale ledgers remain reconciled and are never reset.

## 12. Versioning

Version runtime and collector as:

```text
4.8.1
```

Do not alter the historical run's operator terminal state.

## 13. Safe installation

Use the already-established safe manual installation procedure that:

- backs up installed runtime;
- copies only validated runtime/test files;
- does not execute legacy lifecycle actions;
- does not kill Playwright MCP;
- does not start ai-loopd/browser-broker;
- preserves `/var/lib/ai-loop/state` and run evidence.

Verify source/destination hashes after install.

## 14. NO-SEND live acceptance

Use only the already authenticated Playwright MCP.

Do not click, type, navigate, send, start another browser, rerun operator action, or mutate production.

Perform only the Range-based read-only scan.

Create:

```text
/var/lib/ai-loop/runs/R20260923T012014/reconciliation-v481/
```

with at minimum:

```text
range-witness-failure-evidence.json
range-witness-diagnosis.json
visible-text-stream-summary.json
historical-immutable-provenance.json
cross-source-provenance.json
conversation-identity-proof.json
outbound-gate.json
RESULT.md
evidence.json
sha256-manifest.txt
```

Do not overwrite v4.8.0 local scan artifacts; preserve them as diagnostic history.

## 15. Successful acceptance checkpoint

Expected:

```text
HISTORICAL_IMMUTABLE_PROVENANCE=PASS

failure-evidence:
  unique_visible_ranges=1

diagnosis:
  unique_visible_ranges=1

LIVE_RANGE_WITNESS=PASS
RANGE_ORDER=PASS
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

No send occurs.

## 16. Stop conditions

Stop safely if:

- either marker yields zero unique visible Ranges;
- either marker yields >1 unique visible Range;
- Range cannot be bound to the main conversation root;
- historical/live marker identity conflicts;
- relative ordering conflicts;
- any browser mutation is needed;
- another browser would need to start;
- operator rerun is proposed.

## 17. `/omo-team` prompt

```text
/omo-team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_8_1_RANGE_WITNESS_DEDUP_20260924.md for authoritative run R20260923T012014.

Current v4.8.0 live scan found 46 raw DOM matches and 34 rendered element matches per marker because ancestor elements inherit descendant textContent.

This is a witness-cardinality defect.

Implement v4.8.1 so rendered witness counting is based on unique visible text Ranges, NOT matching ancestor elements.

Hard requirements:
- Build a visible TEXT_NODE stream under the main conversation root.
- Exclude script/style/template/hidden/sidebar/composer/search/filter/application-state content.
- Preserve stream-to-text-node offset mapping.
- Find exact marker occurrences in that visible stream.
- Map each occurrence to an exact DOM Range.
- Support markers split across multiple text nodes.
- Require positive Range client rects.
- Deduplicate by start-node/path+offset and end-node/path+offset.
- Ancestors containing the same descendant marker must never increase witness cardinality.
- Persist raw DOM match counts only as diagnostics.
- Require exactly one unique visible Range for each required marker.
- Persist bounded visible-context hashes around each Range.
- Require deterministic document order: failure-evidence before diagnosis.
- Retain Mode B historical immutable provenance and cross-source reconciliation.
- Do not fabricate live turn/message ids.
- LIVE_TURN_PROVENANCE may remain UNAVAILABLE_IN_CURRENT_UI.
- Add deterministic regressions for nested ancestors, split text nodes, hidden duplicates, and true duplicate visible ranges.
- Version runtime/collector as 4.8.1.
- Install using the proven safe manual process without killing/replacing Playwright MCP and without starting ai-loopd/browser-broker.
- Perform NO-SEND live acceptance using only the existing authenticated Playwright MCP.
- Write new acceptance evidence under reconciliation-v481/.
- Do not send any message.
- Do not rerun the terminal operator action.
- Do not mutate Semaphore/VPS/bot_trading/production.
- Even if LIVE_CONVERSATION_IDENTITY_PROOF=PASS, persist OUTBOUND_SEND=BLOCKED with reason AWAITING_EXPLICIT_RESULT_DELIVERY_CONTINUATION.
- Do not declare FINAL_GO or AI_LOOP_COMPLETE=GO.
```

## 18. Definition of done

This plan succeeds when the ancestor-derived rendered matches collapse to unique visible Range witnesses and the Mode B identity proof either passes deterministically with exactly one visible Range per required marker, or remains safely blocked with a precise reason.

No outbound send is part of v4.8.1.
