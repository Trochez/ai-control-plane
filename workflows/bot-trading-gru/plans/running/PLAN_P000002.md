---
schema: agent-handoff/v1
workflow_id: bot-trading-gru
plan_id: P000002
parent_run_id: R000001
status: READY

target_repository: bot_trading
target_branch: feature/GRU
expected_base_sha: 1afb326bead32e2f928530e33850b5651e46b9b1

execution_mode: local_opencode
---

# Objective

Validate the Planner -> GitHub -> local watcher -> fresh OpenCode session handoff.

This is a read-only target-repository smoke test. Successful execution of this PLAN demonstrates that the local watcher discovered a Planner-published READY plan linked to R000001 and launched a new OpenCode workflow session for P000002.

# Required Work

1. Read this complete authoritative PLAN.
2. Verify that `parent_run_id` is `R000001`.
3. Read the workflow contract and applicable persistent operator instructions.
4. Verify the target repository is `/mnt/d/works/bot_trad/bot_trading`.
5. Verify the active branch is `feature/GRU`.
6. Verify current HEAD equals `expected_base_sha`.
7. Inspect the target working tree.
8. Do not modify the target repository.
9. Record evidence showing P000002/R000002 executed from this handoff chain.
10. Produce all required run evidence.

# Acceptance Criteria

- [ ] P000002 is identified as the authoritative plan.
- [ ] Parent run R000001 is identified correctly.
- [ ] Correct target repository verified.
- [ ] Correct branch verified.
- [ ] Expected base SHA verified.
- [ ] Working tree inspected.
- [ ] No target repository files modified.
- [ ] RESULT.md created.
- [ ] evidence.json created.
- [ ] handoff-chain.json created.
- [ ] Required after-state evidence created.

# Required Evidence

Create in the assigned R000002 run directory:

- RESULT.md
- evidence.json
- handoff-chain.json
- git-status-after.txt
- head-sha-after.txt

`handoff-chain.json` must contain at minimum:

```json
{
  "schema": "agent-handoff/v1",
  "workflow_id": "bot-trading-gru",
  "plan_id": "P000002",
  "run_id": "R000002",
  "parent_run_id": "R000001",
  "planner_plan_received": true
}
```

# Forbidden Operations

Do not:

- edit target repository files;
- commit or push the target repository;
- deploy;
- reset;
- checkout another branch;
- clean the target repository;
- modify credentials;
- create the next authoritative PLAN.

# Completion

Return control to the ChatGPT Planner / Reviewer after evidence is complete.

Do not create P000003.
