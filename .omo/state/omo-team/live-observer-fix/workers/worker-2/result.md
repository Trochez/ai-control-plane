# Worker 2 observer audit

## Result

The repository and installed runtime are byte-identical, both at controller version `4.7.1`. No code changes were made during this audit. The current implementation already has the main reconciliation safeguards, but the release/install metadata and regression coverage are not yet at a complete 4.7.2 standard.

## Verified behavior

- `ai-loop-v4.3/browser-broker-v1.cjs:382-397` distinguishes `GENERATING`, `RATE_LIMIT`, `SETTLED`, and `RESPONSE_MISSING`. Positive stop/busy signals win over a missing assistant selector.
- The broker returns the complete ordered `turnRecords` inventory from `observeContext` and exposes it as `assistant_turn_records`, including historical turns (`browser-broker-v1.cjs:155,397`).
- `ai-loop-v4.3/ai-loopd-v3.py:1149-1177` persists the broker inventory in `last_observed_turns` and records the latest assistant identity in `last_observed_assistant`.
- `ai-loop-v4.3/ai-loopd-v3.py:1311-1329` prevents semantic inference for `RESPONSE_MISSING`; it returns deterministic `NO_CHANGE` instead.
- `ai-loop-v4.3/ai-loopd-v3.py:1397-1406` derives response identity from the broker observation and inventory, rather than trusting a separate model interpretation.
- `ai-loop-v4.3/ai-loopd-v3.py:1480-1483` rejects a missing response when a historical assistant turn was already observed, preventing an observer regression from erasing evidence.
- `ai-loop-v4.3/ai-loopd-v3.py:5317-5346` polls for a genuinely new immutable assistant identity before re-running semantic inspection after a corrective request. `GENERATING` and `RESPONSE_MISSING` do not trigger semantic inference.
- `ai-loop-v4.3/bin/restart-loop-v3:3-11` resumes an existing `.v3.json` state and refuses to start while another controller/browser transport is live. `install.sh:6-15` applies the same process safety boundary before installation.

## Gaps and minimal 4.7.2 fixes

1. Bump the controller release consistently from `4.7.1` to `4.7.2` in `ai-loop-v4.3/ai-loopd-v3.py`, `ai-loop-v4.3/install.sh`, and the relevant README/verification output. The installed copy currently matches the repository at `4.7.1`, so installation alone will not deliver a new behavior version.
2. Add a focused regression test for diagnosis reconciliation: observe a settled assistant turn, then return `RESPONSE_MISSING`, and assert that `last_observed_assistant` remains the reconciliation anchor and semantic inspection returns `NO_CHANGE` without a semantic-model call.
3. Add a test that supplies a full historical inventory and verifies that the latest assistant record, index, id, and hash are persisted. The current test only checks broker output (`tests/test-observer-v4.7.1.cjs:21-47`), not controller persistence.
4. Add an idempotency test around `PLAN_ARTIFACT_WAIT_NEW_MESSAGE`: repeated `GENERATING`/`RESPONSE_MISSING` probes must not send another corrective request or invoke semantic inspection; only a changed response identity may transition to repair.
5. Add an install/resume smoke test or documented captured evidence: install must fail with exit 20 when a controller/transport is live, and resume must fail with exit 4 when a controller/transport is already live. After a clean stop, install and resume should select one state and create one PID/log pair.

## Safe operational sequence

1. Stop old/new controller, browser transport, and OpenCode processes using the project stop/kill helpers or the exact patterns printed by `install.sh`; verify no matching process remains.
2. Run `ai-loop-v4.3/install.sh`; verify its version check reports `4.7.2` after the version bump.
3. Run the local observer/controller verification and the new reconciliation/idempotency tests.
4. Resume only the intended existing state with `/opt/ai-loop/bin/restart-loop-v3 /path/to/state.v3.json` (or `resume-current-v3`); do not start a second controller.
5. Inspect the state/log for `last_observed_turns`, `last_observed_assistant`, immutable response identity, and absence of duplicate corrective sends.

## Evidence

- Repository branch: `main`; HEAD: `6e6d377dae2a9400357d0cd03c6836a17f05c41b`.
- Worktree contains unrelated user changes and untracked artifacts; none were modified or cleaned.
- SHA-256 repository/installed equality verified:
  - `ai-loop-v4.3/ai-loopd-v3.py` = `/opt/ai-loop/ai-loopd-v3.py`: `fcb144a2e4c334f79adaeaa455951fdeb94e3d2e62ecb5ea25138cf97f25e7c1`
  - `ai-loop-v4.3/browser-broker-v1.cjs` = `/opt/ai-loop/browser-broker-v1.cjs`: `c43b23d5342334da703136b7d8d2e990c03c1df2d00fdcf96780583d7f8325f4`
- Existing observer test command is `node ai-loop-v4.3/tests/test-observer-v4.7.1.cjs`; its scope is classification and historical inventory only.
