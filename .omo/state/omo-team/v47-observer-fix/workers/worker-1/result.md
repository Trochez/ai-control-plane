# Worker: worker-1
## Task: Read-only observer investigation for R20260923T012014

### Summary
OPENCODE context verified: `OPENCODE=1`; repository `/mnt/d/works/ai-control-plane`; branch `main`; HEAD `6e6d377dae2a9400357d0cd03c6836a17f05c41b`. Investigation was read-only apart from this required result file; no browser/runtime actions were launched.

### Findings
- Persisted current diagnostics repeatedly report no conversation turns: `turns.user=0`, `turns.assistant=0`, `turns.total=0`, with empty `assistantTexts`. Exact evidence: `/var/lib/ai-loop/runs/R20260923T012014/browser/broker-diagnostics/2026-09-23T214949739Z-ATTACH_FILE.json:1123-1129` (same shape also appears in the 21:47:32 and 21:43:57 ATTACH_FILE snapshots).
- The broker's proven assistant-turn candidate selector is `[data-message-author-role="assistant"]`. The supported fallback is `article[data-testid^="conversation-turn"]`, combined with `[data-message-author-role="user"]` and visibility filtering. Exact implementation: `ai-loop-v4.3/ai-loopd-v3.py:2972-2978`, repeated for presend/send at `:3042` and `:3066-3067`.
- For assistant identity, the intended proven identity fields are the closest latest assistant turn's DOM `data-testid`/message id plus normalized assistant-turn `innerText` SHA-256. Contract: `ai-loop-v4.3/ai-loopd-v3.py:1330-1342`; controller mapping consumes `assistant_message_id`, `assistant_text_sha256`, and assistant count at `:1369-1373`. The persisted diagnostic schema does not expose an assistant id/hash because there are zero assistant turns.
- Positive generation signal proven by the real artifact: visible control `{aria:"Stop"}`. Exact persisted evidence: `/var/lib/ai-loop/runs/R20260923T012014/browser/broker-diagnostics/2026-09-23T062107605Z-ENSURE_CHAT_POLICY.json:1578-1590`. The same snapshot still reports zero assistant turns (`:1592-1598`), so `Stop` is a stronger busy/generation signal than attempting to select an older assistant response.
- Broker policy explicitly gives current-response indicators precedence: visible `Stop`/`Stop answering`/`Stop generating`, Thinking/Working/Researching, active tool activity, or streaming means `GENERATING`; only unchanged identity across two observations is `SETTLED`. Exact policy: `ai-loop-v4.3/ai-loopd-v3.py:3401-3406`. Response identity states and required fields are defined at `:1330-1342`.
- Current later ATTACH_FILE artifact has `High` with `aria:"Select ChatGPT model"`, `navTarget:"reasoning"`, `reasoningEffort:"high"`, and `codexIntelligenceTrigger:"true"` at `/var/lib/ai-loop/runs/R20260923T012014/browser/broker-diagnostics/2026-09-23T214949739Z-ATTACH_FILE.json:1084-1094`; this is a positive reasoning control signal, not assistant-generation proof.

### Uncertainties
- No persisted HTML artifact contains a proven assistant element in the inspected snapshots; HTML grep found no `data-message-author-role` occurrence. Therefore the selector is broker/code-proven, while actual run evidence only proves the empty-state behavior.
- The `Stop` snapshot is from 06:21, not the latest 21:49 snapshot. It proves the UI's positive generation signal existed during this run, but does not establish that the later 21:49 state was still generating. The later snapshot's `WAIT_TIMEOUT:stale_attachment_removal` and zero turns are not sufficient to classify generation without a contemporaneous `Stop`/streaming indicator.
- `source_turn_testid` is currently always blank in the controller mapping (`ai-loop-v4.3/ai-loopd-v3.py:1373`), despite the identity prompt requiring a DOM turn testid (`:1336-1342`); message id/hash are the available persisted identity channels.

### Files Modified
- `.omo/state/omo-team/v47-observer-fix/workers/worker-1/result.md` only.

### Recommendations
- Treat `[data-message-author-role="assistant"]` as the primary assistant selector and `article[data-testid^="conversation-turn"]` only as a fallback candidate, then visibility-filter and choose the latest node.
- Before classifying any latest answer, check visible `button`/control accessible name matching `Stop`, `Stop answering`, or `Stop generating` and equivalent Thinking/Working/Researching indicators; return `GENERATING` immediately when present.
- Do not infer a positive assistant generation or settled answer from these ATTACH_FILE artifacts alone: they contain zero assistant turns and later evidence lacks a contemporaneous generation marker.
