# Upgrade ai-loop v4.2 -> v4.3

v4. 3 is based on real browser diagnostics from `R20260922T040029`.

## Fixed production regressions

- `projectName=trading` is corrected to `bot_trading` for real project URL.
- generic `chatgpt.com/` + `New chat in Bot_trading` + `Change project: Bot_trading` is recognized as target-project context.
- current standard Chat `High` reasoning UI is accepted as GPT-5. 6 Sol / High policy; broker no longer requires literal visible `GPT-5.6 Sol` menu option.
- legacy explicit Sol model pickers remain supported as fallback.

## Install

1. Stop all ai-loop/browser/OpenCode processes.
2. Extract `ai-loop-v4.3.tar.gz`.
3. Run `./bin/verify-v4.3-local`.
4. Run `./install.sh`.
5. Stop residual processes again.
6. Run `/opt/ai-loop/bin/preflight-v4.3 <CANARY_PLAN>`.
7. Launch brand-new canary using `start-loop-v3`.

Do not resume failed v4. 2 run.
