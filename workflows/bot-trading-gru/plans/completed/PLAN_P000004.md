---
schema: agent-handoff/v1
workflow_id: bot-trading-gru
plan_id: P000004
parent_run_id: R000003
status: READY

target_repository: bot_trading
target_branch: feature/GRU
expected_base_sha: 1afb326bead32e2f928530e33850b5651e46b9b1

execution_mode: local_opencode
---

# Objective

Remediate the control-plane defects exposed by R000003 so the next smoke test can execute end-to-end without human intervention.

This PLAN authorizes changes only in `/mnt/d/works/ai-control-plane`. The target repository `/mnt/d/works/bot_trad/bot_trading` is read-only for this run and must remain unchanged.

# Mandatory Preconditions

1. Read this complete PLAN, `WORKFLOW.md`, `reviews/R000003.md`, and the current implementations of:
   - `bin/spawn-opencode`
   - `bin/run-opencode-session`
   - `bin/complete-run`
   - `bin/handoff-to-planner`
   - `bin/publish-run`
2. Verify `/mnt/d/works/bot_trad/bot_trading` is on `feature/GRU` at SHA `1afb326bead32e2f928530e33850b5651e46b9b1` with a clean working tree.
3. Verify `/mnt/d/works/ai-control-plane` is on `main` and inspect its working tree. Preserve existing workflow artifacts for R000004; do not discard or reset them.
4. Confirm the configured OpenCode model remains `omniroute/openrouter/openrouter/free`.

If any mandatory precondition affecting safety fails, produce BLOCKED evidence and do not mutate either repository.

# Required Remediation

## 1. `bin/spawn-opencode`

Make `OPENCODE_MODE=run` fully non-interactive.

Required behavior:

- Never call `tmux attach-session` in `run` mode.
- Never require the caller to have a terminal in `run` mode.
- Launch `run-opencode-session` in detached tmux so it survives terminal closure.
- If `$TMUX_SESSION` exists, create a detached window named with the run id.
- If it does not exist, create a detached session/window.
- Print a durable diagnostic such as `OPENCODE_SPAWNED_DETACHED=<run_id>` and return success after the detached worker starts.
- Preserve the existing interactive tmux behavior only for `OPENCODE_MODE=interactive`.

## 2. `bin/run-opencode-session`

Make completion contract-aware instead of trusting only the OpenCode process exit code.

Required behavior:

- Preserve `--agent "$OPENCODE_AGENT"` and explicit `--model "$OPENCODE_MODEL"` support.
- Preserve `OPENCODE_MODE=run` as the default automated mode.
- Execute a bounded maximum of 2 OpenCode attempts for one run by default. A configurable environment variable may override this, but the default must be 2.
- Attempt 1 uses the normal authoritative PLAN bootstrap prompt.
- After any attempt that exits 0, validate at minimum that these core artifacts exist:
  - `RESULT.md`
  - `evidence.json`
  - `git-status-after.txt`
  - `head-sha-after.txt`
- Validate `evidence.json` with `python3 -m json.tool`.
- If process exit is 0 but the evidence contract is incomplete/invalid, automatically run exactly one recovery attempt for the same run with a prompt that explicitly instructs the operator to read the PLAN and prior attempt log and physically create/validate the missing evidence.
- The retry must remain part of the same `RUN_ID`; do not create a new PLAN or run.
- Persist attempt-specific logs and exit codes so the history is auditable, e.g. `operator-attempt-1.log`, `operator-attempt-1-exit-code.txt`, `operator-attempt-2.log`, `operator-attempt-2-exit-code.txt`.
- Preserve or generate `operator.log` as the canonical first-attempt log for compatibility if practical.
- Only call `complete-run` after the core evidence contract is satisfied.
- If attempts are exhausted and evidence remains incomplete/invalid, return non-zero, leave lifecycle `RUNNING`, and do not call `publish-run`.
- After successful `complete-run`, call `publish-run` automatically.

Do not use `--auto`.

## 3. `bin/complete-run`

When a run completes successfully and transitions to `REVIEW_READY`, also set:

```json
"last_completed_run_id": "<current RUN_ID>"
```

Do not set `last_review_decision`; that remains Planner-owned.

## 4. `bin/handoff-to-planner`

Make it idempotent for the race already observed.

Required behavior:

- Existing `REVIEW_READY` behavior remains valid.
- If called for run `Rxxxxxx` after the Planner has already reviewed it and durable state is `PLAN_READY` with `last_completed_run_id` equal to the supplied run id, do not fail. Skip the obsolete handoff prompt and directly start `wait-next-plan <RUN_ID>`.
- Reject genuinely inconsistent states.

# Validation

At minimum run:

```bash
bash -n bin/spawn-opencode
bash -n bin/run-opencode-session
bash -n bin/complete-run
bash -n bin/handoff-to-planner
bash -n bin/publish-run
```

Also perform non-destructive contract checks proving:

1. `spawn-opencode` contains a detached `run` path and no attach is reachable from that path.
2. `run-opencode-session` contains bounded evidence validation/retry logic and does not treat exit 0 alone as completion.
3. `complete-run` updates `last_completed_run_id`.
4. `handoff-to-planner` accepts the already-reviewed `PLAN_READY` case.
5. The target `bot_trading` repository is still clean, on `feature/GRU`, and at the expected SHA after all work.

# Control-Plane Commit / Push

The workflow run itself makes the control-plane working tree dirty. Therefore stage and commit only the remediation files you intentionally changed; do not stage lifecycle/run artifacts at this point.

Commit the remediation to `main` with a message equivalent to:

```text
fix: harden unattended OpenCode lifecycle
```

Push that remediation commit to `origin/main` before finalizing R000004 evidence.

Do not commit or push anything in `bot_trading`.

# Required Run Evidence

Create in the assigned R000004 run directory:

- `RESULT.md`
- `evidence.json`
- `git-status-after.txt`
- `head-sha-after.txt`
- `branch-after.txt`
- a concise remediation test log, e.g. `control-plane-remediation-tests.txt`

`RESULT.md` must include:

- files changed in the control-plane;
- exact validation commands and outcomes;
- remediation commit SHA;
- confirmation that the target repository was not modified;
- explicit statement that R000004 is a remediation run, not the final unattended proof.

`evidence.json` must include at minimum:

- workflow_id
- plan_id
- run_id
- parent_run_id
- repository_path
- current_branch
- expected_branch
- branch_matches_expected
- head_sha
- expected_base_sha
- head_matches_expected
- working_tree_clean_before
- working_tree_clean_after
- no_target_repo_modifications
- control_plane_remediation_commit
- spawn_detached_run_mode_fixed
- bounded_evidence_retry_fixed
- last_completed_run_id_fixed
- handoff_idempotency_fixed
- validation_passed
- acceptance_criteria_met
- blocked

# Forbidden Operations

Do not:

- modify files in `bot_trading`;
- commit or push in `bot_trading`;
- deploy;
- change branches in `bot_trading`;
- reset or clean either repository;
- modify credentials or secrets;
- use `opencode --auto`;
- create P000005;
- make Planner/review decisions.

# Acceptance Criteria

- [ ] All four control-plane defects from R000003 are remediated.
- [ ] Shell syntax validation passes for all affected scripts.
- [ ] Remediation is committed and pushed to `ai-control-plane/main` without staging workflow lifecycle artifacts into the remediation commit.
- [ ] `bot_trading` remains clean, on `feature/GRU`, at the expected SHA.
- [ ] All required R000004 evidence is produced.
- [ ] Lifecycle ownership remains with the orchestrator and review ownership remains with ChatGPT.

# Completion Contract

After the required evidence exists, return normally to the local orchestrator. The orchestrator owns `complete-run` and `publish-run`. ChatGPT owns review and any next PLAN.
