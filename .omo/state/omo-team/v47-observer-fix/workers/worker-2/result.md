# Observer/recovery investigation

## Scope and repository state

- Investigated `ai-loop-v4.3/ai-loopd-v3.py`, `browser-broker-v1.cjs`, `playwright-bootstrap-observer.cjs`, and the existing browser/semaphore tests.
- Branch is `main`, HEAD is `6e6d377dae2a9400357d0cd03c6836a17f05c41b`.
- No production files were modified. No live browser operation was run.

## Current behavior

### Response classification

- `browser-broker-v1.cjs:373-381` returns only `NO_ASSISTANT`, `GENERATING`, `RATE_LIMIT`, or `SETTLED` from `observeResponse()`.
- The broker determines `GENERATING` from a visible stop button and otherwise treats the latest assistant turn as settled. It does not distinguish “no assistant response after the latest user message” from a settled assistant response.
- `ai-loopd-v3.py:1293-1305` maps `NO_ASSISTANT` to `GENERATING`, so there is no explicit missing-response terminal/provisional state.
- `ai-loopd-v3.py:1330-1342` and `:1357-1366` hard-code the same four identity observations. `SEMANTIC_EVENTS` at `:1134-1146` has no `RESPONSE_MISSING` event.
- The semantic text prompt at `:1162-1184` is only called after the deterministic browser observation is considered settled.

### Generating polling

- `generating_delay()` at `ai-loopd-v3.py:3826-3833` increments persistent `generating_streak` and applies delays of base/90/120/180/240/max seconds.
- The main loop at `:5608-5619` retries forever while the event is `GENERATING`; there is no maximum streak, deadline, or transition after repeated observations.
- The plan-artifact wait lane at `:5296-5303` similarly retries `GENERATING`/`NO_ASSISTANT` without a bounded terminal outcome.
- `reset_generating()` is called after any non-generating event and after successful sends (`:3883`, `:5619`).

### Delivery and reconciliation

- `sendAtomic()` at `browser-broker-v1.cjs:333-351` re-proves policy/project, checks the exact user marker before sending, and waits up to 30 seconds for marker evidence after clicking.
- A clicked send without proof is returned as `AMBIGUOUS_SEND`; the controller forbids blind resend and invokes the deterministic observer (`ai-loopd-v3.py:3902-3910`).
- `_recover_delivery_via_browser()` at `ai-loopd-v3.py:3153-3217` provides positive marker recovery and optional negative proof. Negative proof is deliberately conservative: complete candidate/history scan, intact history evidence, and no sent ledger; `_negative_delivery_reconciliation()` is the existing gate.
- `mark_settled_message_terminal()` and `wait_new_assistant_message` protect immutable settled responses and prevent repeated semantic interpretation of the same response (`:1394+`, `:5273-5311`). These mechanisms should be reused rather than adding a parallel response ledger.

### Circuit breaker

- Semaphore evidence has a generic reference implementation in `semaphore_evidence.py:68-79`: increment attempts, persist a fingerprint/error code, open at a configured maximum, and record a terminal error.
- A semaphore retry/circuit-breaker test exists in `tests/test-semaphore-evidence-v4.7.py:24-27`.
- No observer-specific failure counter, persisted observer circuit state, or observer circuit-breaker test was found.

## Minimal implementation recommendation

1. Add `RESPONSE_MISSING` to the broker/identity schema and to the semantic event vocabulary. Define it narrowly as: latest user turn exists, no completed assistant turn follows it, and the UI is not actively generating. Preserve `NO_ASSISTANT` internally if needed, but normalize it to `RESPONSE_MISSING` only when the latest-turn relationship proves a response is expected.
2. Return the latest user identity alongside assistant identity from `observeResponse()`. This is necessary to avoid classifying a conversation with no pending request as missing. Add parser validation and prompt output documentation in `response_identity_prompt()`/`parse_response_identity()`.
3. In `semantic_inspect()`, map `RESPONSE_MISSING` to a deterministic event with no semantic model call. Do not infer a semantic event from missing text. In the main loop, record it and enter a bounded wait/reconciliation path rather than sending or repeating a request.
4. Bound generating/missing polling with a persisted per-response streak/deadline. Reuse `generating_streak` for compatibility or introduce a clearly versioned `response_observer` record containing `identity_key`, `generating_attempts`, `missing_attempts`, `started_at`, `last_observed_at`, and `status`. After the limit, run one deterministic reconciliation; if it cannot prove a new settled response, transition to an explicit blocked/error state and preserve evidence.
5. Reuse `_recover_delivery_via_browser()` and `_negative_delivery_reconciliation()` for positive/negative delivery reconciliation. Do not treat a missing response as proof that the user message was not sent, and never resend solely because the assistant response is missing.
6. Add an observer circuit breaker around `broker_observe_response()`/`inspect_response_identity()`: persist consecutive transport/parse failures keyed by chat/operation, open after a small configured threshold, record the last error and evidence path, and require a later cooldown/recovery probe before closing. Keep semantic classification errors separate from browser transport failures.

## Tests to add

- Broker fixture: latest user turn with no assistant answer yields `RESPONSE_MISSING`; settled assistant after an older user turn remains `SETTLED`; active stop control remains `GENERATING`.
- Python parser/identity tests: accept the new observation, reject unknown values, and verify `semantic_inspect()` does not invoke the text classifier for missing/generating states.
- Polling tests: bounded generating and missing streaks persist across loop iterations, perform one reconciliation, and reach a stable blocked/error result without sending.
- Reconciliation tests: exact marker gives positive proof; complete history/observer scan with no marker can give negative proof only under existing strict preconditions; navigation failure cannot produce negative proof.
- Circuit-breaker tests: failures increment and persist, threshold opens the breaker, open state suppresses repeated broker calls, cooldown probe can close it, and success resets consecutive failures.

## Files/symbols for implementation

- `ai-loop-v4.3/browser-broker-v1.cjs:373-381` — response observation payload.
- `ai-loop-v4.3/ai-loopd-v3.py:1134-1159` — event set and broker observation wrapper.
- `ai-loop-v4.3/ai-loopd-v3.py:1162-1184` — semantic prompt contract.
- `ai-loop-v4.3/ai-loopd-v3.py:1323-1373` — identity prompt, parser, and normalization.
- `ai-loop-v4.3/ai-loopd-v3.py:3826-3833` — generating backoff.
- `ai-loop-v4.3/ai-loopd-v3.py:5296-5311` and `:5608-5625` — unbounded polling paths.
- `ai-loop-v4.3/ai-loopd-v3.py:3153-3217` — existing delivery reconciliation.
- `ai-loop-v4.3/semaphore_evidence.py:68-79` — circuit-breaker design reference.
