# RESULT — P000004 / R000004

## Outcome

R000004 completed the control-plane remediation required after R000003.

R000004 is a remediation run and is NOT the final unattended proof.

## Execution history

The initial spawn successfully claimed P000004/R000004 but failed before
OpenCode started because the tmux command invocation was malformed.

The first remediation commit was:

926768f14b0982e871610729be0c57b382084062
fix: harden unattended OpenCode lifecycle

Subsequent bootstrap OpenCode executions returned exit code 0 without producing
the mandatory R000004 evidence, demonstrating again that process exit 0 alone
cannot be trusted as completion.

The final corrective remediation commit is:

242eb4dc818999494d0851956207db974ba24c3f
fix: complete unattended lifecycle hardening

## Final remediation

The resulting control-plane now provides:

- detached OPENCODE_MODE=run spawning without terminal attachment;
- shell-safe tmux argv serialization;
- bounded evidence-aware OpenCode retry with default maximum 2 attempts;
- recovery access to operator-attempt-1.log;
- evidence JSON validation before completion;
- last_completed_run_id update by complete-run;
- normal REVIEW_READY planner handoff;
- idempotent PLAN_READY already-reviewed handoff.

## Validation

All affected scripts passed bash -n.

Static contract checks passed for detached execution, safe tmux command
serialization, bounded retry, recovery logging, evidence validation,
last_completed_run_id and handoff idempotency.

See control-plane-remediation-tests.txt.

## Target repository

/mnt/d/works/bot_trad/bot_trading remained:

branch: feature/GRU
HEAD: 1afb326bead32e2f928530e33850b5651e46b9b1
working tree: clean

No target repository files were modified, committed or pushed.

## Ownership

The local orchestrator owns lifecycle completion.
ChatGPT owns review and the next authoritative PLAN.
