# Upgrade ai-loop v4.1 -> v4.2

## Why

The live v4.1 run failed with `WAIT_TIMEOUT:fresh_project_draft`. The root cause is control flow, not project recognition alone: if the persistent profile starts in a historical chat that already belongs to `bot_trading`, `navigateProject()` considers the target project reached and returns without leaving the historical `/c/` conversation. The next generic `Chat` click may not create a fresh project draft.

## Remediation

- historical `/c/` or nonzero-turn state forces navigation to the exact project root;
- fresh draft is checked immediately after root navigation;
- only then are bounded non-sending Chat/New-chat candidates tried;
- every candidate must result in target-project + zero-turn + editable composer;
- target project anchor mapping includes collapsed/non-visible DOM anchors;
- policy waits require Chat + Sol + High simultaneously.

## Install

1. Kill all loop/browser processes.
2. Extract `ai-loop-v4.2.tar.gz`.
3. Run `./bin/verify-v4.2-local`.
4. Run `./install.sh`.
5. Run `/opt/ai-loop/bin/preflight-v4.2 <PLAN>`.
6. Start a new loop with `/opt/ai-loop/bin/start-loop-v3 <PLAN>`.
