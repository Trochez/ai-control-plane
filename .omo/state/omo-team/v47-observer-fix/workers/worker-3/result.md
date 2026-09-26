# Worker: worker-3
## Task: Read-only observer regression-test design for R20260923T012014

### Scope and repository state

- Repository: `/mnt/d/works/ai-control-plane`; branch `main`; HEAD `6e6d377dae2a9400357d0cd03c6836a17f05c41b`.
- Existing user changes and untracked files were preserved. No production files were modified.
- No live browser, controller daemon, or install operation was run.
- Existing verification is standalone: `ai-loop-v4.3/bin/verify-v4.3-local` has no package test runner and currently does not include observer-specific coverage.

### Anchored implementation findings

- `ai-loop-v4.3/browser-broker-v1.cjs:373-381` currently emits `NO_ASSISTANT`, `GENERATING`, `RATE_LIMIT`, or `SETTLED`. It uses assistant selectors and a visible Stop control; a latest-user/no-assistant relationship is not represented.
- `ai-loop-v4.3/ai-loopd-v3.py:1293-1305` normalizes `NO_ASSISTANT` to `GENERATING`, and `:1357-1373` rejects/does not map `RESPONSE_MISSING`. The requested missing-response regression therefore requires a schema/translation change before the test can pass.
- `ai-loop-v4.3/ai-loopd-v3.py:1394-1404` already provides a settled-message ledger keyed by source identity; reuse it for exactly-once post-reload handling instead of adding a second ledger.
- `ai-loop-v4.3/ai-loopd-v3.py:3826-3833` has bounded delay values but `:5615-5618` retries generating indefinitely. A regression should assert a persisted streak/deadline/circuit transition once the implementation adds that bound.
- `ai-loop-v4.3/ai-loopd-v3.py:5806-5825` treats `EVIDENCE_DELIVERED` as a resumable evidence stage. Resume tests must prove that already-delivered evidence does not reattach or resend merely because the process restarted.
- `ai-loop-v4.3/browser-broker-v1.cjs:333-351` and `ai-loop-v4.3/ai-loopd-v3.py:3153-3217` already provide delivery markers and conservative reconciliation; tests must preserve the rule that a missing assistant response is not proof that the user delivery failed.

### Recommended regression file

Add `ai-loop-v4.3/tests/test-observer-response-v4.7.py` as a pure import/fixture test. Mock `broker_observe_response`, browser observations, clock/sleep, and send/attachment functions; do not launch Playwright or touch a live run. If the broker-level implementation is changed first, add a companion `test-browser-broker-v4.7.cjs` with mocked page/locator fixtures.

Required cases and assertions:

1. **Response-state classification**
   - Latest user turn, no completed assistant after it, no active Stop/Thinking/Working/Researching/tool signal => `RESPONSE_MISSING`.
   - Same no-assistant shape with a real active Stop control => `GENERATING`.
   - Assistant turn with streaming/generation signal => `GENERATING`.
   - Assistant turn with stable identity/content and no active signal => `SETTLED`.
   - Older conversation with no pending latest user request must not be classified as missing.
   - Parser accepts `RESPONSE_MISSING` and rejects unknown observations; semantic inspection must not call the text classifier for `RESPONSE_MISSING` or `GENERATING`.

2. **Evidence-delivery resume idempotency**
   - Fixture state: `phase=FAILURE_ANALYSIS`, `failure_stage=EVIDENCE_DELIVERED`, evidence delivery id/ledger already recorded.
   - Resume/re-entry performs zero attachment calls and zero `guarded_send`/send calls.
   - Repeated resume remains idempotent and preserves the delivered ledger.
   - An ambiguous or missing response must not authorize a blind resend; only positive marker proof or the existing strict reconciliation path may change delivery state.

3. **Bounded generating recovery / circuit breaker**
   - Repeated `GENERATING` observations persist the same response identity, increment the observer streak, and use delays no greater than `POLL_GENERATING_MAX`.
   - After the configured threshold/deadline, exactly one deterministic reconciliation runs; no semantic model call and no message send occurs during the generating lane.
   - Failed reconciliation opens a persisted observer circuit/error state with the last error/evidence reference; subsequent iterations suppress repeated broker calls until the defined cooldown/recovery probe.
   - A settled observation or successful recovery resets only the consecutive generating/transport streak that it is supposed to reset.

4. **Post-reload exactly-once response handling**
   - First settled observation records identity (`source_message_id`, fallback content hash, turn index/chat URL) and emits/handles it once.
   - Reloading state and observing the same identity does not rerun semantic handling or send a duplicate follow-up.
   - A genuinely new settled identity is handled once after reload; the old identity remains terminal in `settled_message_ledger`.

### Suggested verification commands

After implementation and test-file addition, run:

```bash
python3 -m py_compile ai-loop-v4.3/ai-loopd-v3.py
python3 ai-loop-v4.3/tests/test-observer-response-v4.7.py
python3 ai-loop-v4.3/tests/test-semaphore-evidence-v4.7.py
./ai-loop-v4.3/bin/verify-v4.3-local
bash -n ai-loop-v4.3/install.sh
```

Add the observer test to `ai-loop-v4.3/bin/verify-v4.3-local` so future local verification cannot omit these regressions. Do not run `install.sh` as part of this read-only investigation: it checks live processes and writes under `/opt/ai-loop` and system/user state. A later install smoke test should be isolated and explicitly capture its logs.

### Current conclusion

The existing code has useful identity, settled-message, delivery-marker, and semaphore circuit-breaker primitives, but it does not yet implement the requested `RESPONSE_MISSING` distinction or an observer-specific bounded recovery circuit. The test file should therefore be added alongside the corresponding implementation change; writing only a test against the current `NO_ASSISTANT -> GENERATING` behavior would encode the defect rather than prevent its return.

### Files modified

- `.omo/state/omo-team/v47-observer-fix/workers/worker-3/result.md` only.
