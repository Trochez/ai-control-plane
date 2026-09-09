# bot-trading-gru workflow

## Purpose

This repository is the durable coordination layer between:

1. ChatGPT Planner / Reviewer
2. Local OpenCode Operator
3. The target application repository

## Authority model

ChatGPT owns:
- planning
- evidence review
- GO / NO_GO / BLOCKED decisions
- creation of the next PLAN

OpenCode owns:
- local inspection
- source-code modifications
- tests
- Git operations
- CI operations
- SSH / deployment operations when authorized
- evidence collection

OpenCode MUST NOT create the authoritative next implementation plan.

ChatGPT MUST NOT claim operational success without evidence produced by the operator.

## Lifecycle

PLAN_READY
-> CLAIMED
-> RUNNING
-> REVIEW_READY
-> REVIEWING
-> GO | NO_GO | BLOCKED
-> NEXT_PLAN | CLOSEOUT

## Durable artifacts

Every execution must have:

- immutable plan
- unique plan_id
- unique run_id
- RESULT.md
- evidence.json
- relevant tests/logs
- base SHA
- resulting SHA
- review decision

## Fresh-session rule

A new authoritative plan MUST be executed in a fresh OpenCode session.

Previous OpenCode conversation state is not authoritative.

The new PLAN and repository state are authoritative.

## Safety

Secrets MUST NOT be committed to this repository.

Missing evidence MUST NOT be interpreted as success.

GO MUST NOT be emitted unless acceptance criteria are evidenced.
