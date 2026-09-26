# AI LOOP FULL ACCEPTANCE — READ ONLY

Goal: validate ai-loop controller end-to-end without repository, CI, deployment, trading, or production mutation.

Non-negotiable safety rules:
- Do not commit, push, amend, merge, revert, cherry-pick, tag, deploy, launch/rerun/cancel CI, modify Semaphore, change VPS files/services, place trades, or modify databases.
- Every requested operator action must be read-only and must be issued as one unambiguous fenced shell block with action id, target and timeout stated outside block.
- Use `target=github-readonly` for GitHub inspection, `target=local` for local controller inspection, and `target=vps` only for read-only VPS inspection.

Acceptance sequence:
1. Request local read-only action that prints current branch and HEAD of `/mnt/d/works/bot_trad/bot_trading` and no other mutation.
2. After literal evidence returns, request GitHub read-only action that prints remote `feature/GRU` SHA using `gh api` or `git ls-remote`, without mutation.
3. After literal evidence returns, request VPS read-only action that prints hostname/date and current production checkout SHA via controller-owned VPS route; do not change files or services.
4. Request current Semaphore evidence only through controller's read-only CI evidence path. Do not click Run/Rerun/Retry/Cancel/Edit/Promote/Schedule.
5. Require at least two separate controller evidence round-trips after initial bootstrap.
6. If every requested evidence item is verified and there was no unsafe mutation, duplicate action, duplicate delivery, or integrity error, reply exactly with clear `FINAL_GO` / `COMPLETE_GO` statement.
7. If human-only login/MFA/credential choice is required, state `HUMAN_BLOCKED` and exact requirement; do not ask controller to bypass it.
