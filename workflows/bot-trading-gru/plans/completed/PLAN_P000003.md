---
schema: agent-handoff/v1
workflow_id: bot-trading-gru
plan_id: P000003
parent_run_id: R000002
status: READY

target_repository: bot_trading
target_branch: feature/GRU
expected_base_sha: 1afb326bead32e2f928530e33850b5651e46b9b1

execution_mode: local_opencode
---

# Objective

Validate the final unattended local execution chain using `opencode run` with automatic completion and publication.

This is a read-only smoke test. The target repository must not be modified.

# Required Work

1. Read this complete PLAN and the workflow contract.
2. Verify this is P000003 with parent run R000002.
3. Verify the target repository is `/mnt/d/works/bot_trad/bot_trading`.
4. Verify the active branch is `feature/GRU`.
5. Verify current HEAD equals `expected_base_sha`.
6. Inspect the target working tree before execution.
7. Perform no modifications to the target repository.
8. Create the required run evidence in the assigned R000003 directory.
9. Inspect the target working tree again before returning control.
10. Do not change lifecycle state and do not publish the next PLAN; those responsibilities belong to the orchestrator and Planner.

# Acceptance Criteria

- [ ] P000003 identified as the authoritative plan.
- [ ] `parent_run_id` is R000002.
- [ ] Correct target repository verified.
- [ ] Branch is `feature/GRU`.
- [ ] HEAD equals `1afb326bead32e2f928530e33850b5651e46b9b1`.
- [ ] Working tree is clean before execution.
- [ ] Working tree is clean after execution.
- [ ] No target-repository files are modified.
- [ ] `RESULT.md` is created.
- [ ] `evidence.json` is created.
- [ ] `git-status-after.txt` is created.
- [ ] `head-sha-after.txt` is created.
- [ ] `branch-after.txt` is created.

# Required Evidence

Create in the assigned run directory:

- `RESULT.md`
- `evidence.json`
- `git-status-after.txt`
- `head-sha-after.txt`
- `branch-after.txt`

`RESULT.md` must state that this run was intended to validate the non-interactive unattended execution path and must clearly state whether any target-repository modifications occurred.

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
- acceptance_criteria_met
- blocked

# Forbidden Operations

Do not:

- edit target-repository files;
- commit or push in `bot_trading`;
- deploy;
- reset;
- checkout another branch;
- clean the repository;
- modify credentials or secrets;
- create P000004.

# Completion Contract

When evidence generation is complete, return normally to the local orchestrator.

The local orchestrator must own the subsequent lifecycle transition, evidence commit, and push. The ChatGPT Planner owns the review decision and any next PLAN.
