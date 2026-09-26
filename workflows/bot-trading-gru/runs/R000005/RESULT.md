# Run R000005 — BLOCKED Evidence

## Verified facts
- PLAN: `P000005`; parent: `R000004`; workflow: `bot-trading-gru`.
- Target path exists: `/mnt/d/works/bot_trad/bot_trading`.
- Target branch is `feature/GRU`.
- Target working tree is clean.
- Actual target HEAD is `d4960be98cee3edef96413ee77f200ce744d3461`.
- Control-plane HEAD is `6e6d377dae2a9400357d0cd03c6836a17f05c41b`; required baseline `75bdef421ac50ff9f49c679d1daed69371fc05a7` is an ancestor.

## Blocking precondition
The PLAN requires target HEAD `1afb326bead32e2f928530e33850b5651e46b9b1`, but the verified target HEAD is `d4960be98cee3edef96413ee77f200ce744d3461`. Because the target repository is strictly read-only under this PLAN, no reset, checkout, branch change, or other remediation was attempted.

## Consequence
No authorized preflight or lifecycle operation was performed. No target files were modified. OpenCode did not invoke `complete-run` or `publish-run`, alter lifecycle state, create a new PLAN, or make a Planner decision.
