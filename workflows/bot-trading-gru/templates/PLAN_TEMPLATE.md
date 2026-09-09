---
schema: agent-handoff/v1
workflow_id: bot-trading-gru
plan_id: P000000
parent_run_id: null
status: READY

target_repository: bot_trading
target_branch: feature/GRU
expected_base_sha: REPLACE_ME

execution_mode: local_opencode
---

# Objective

Describe exactly what must be achieved.

# Verified Current State

Record only facts supported by evidence.

# Scope

## In scope

- ...

## Out of scope

- ...

# Preconditions

- Repository must be available.
- Target branch must match.
- Current HEAD must match `expected_base_sha`.
- Existing unrelated modifications must not be destroyed.

# Required Work

1. ...
2. ...
3. ...

# Acceptance Criteria

- [ ] ...
- [ ] ...
- [ ] ...

# Required Tests

- ...

# Required Evidence

The operator must provide at minimum:

- base SHA
- resulting SHA
- git status before/after
- test results
- implementation summary
- commit/push status when applicable
- deployment state when applicable
- rollback readiness

# Rollback Requirements

Describe the required rollback mechanism.

# Deliverables

- implementation
- tests
- RESULT.md
- evidence.json
- supporting evidence

# Completion Contract

After completing execution:

1. publish the evidence bundle;
2. mark the run REVIEW_READY;
3. do not invent the next authoritative plan;
4. hand control back to the ChatGPT Planner.
