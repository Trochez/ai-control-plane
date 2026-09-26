# ai-loop v4.4

Production hardening release over v4. 2, built from literal diagnostics of run `R20260922T040029`.

## What v4.3 fixes

v4. 2 reached valid empty `Bot_trading` draft but failed in two related proof layers:

1. project-name parser extracted `trading` instead of `bot_trading` from real project URL;
2. current standard Chat UI exposes selected reasoning effort (`High`) rather than literal `GPT-5.6 Sol` menu option, while v4. 2 still required that literal option.

v4. 3 uses actual DOM contract:

- `Change project: Bot_trading` and `New chat in Bot_trading` are positive project signals;
- `Chat` must be selected;
- `data-selected-reasoning-effort="high"` / visible `High` must be positively proven;
- in current standard paid Chat, High maps to GPT-5. 6 Sol;
- legacy explicit Sol model selection remains fallback only.

## Verify locally

```bash
./bin/verify-v4.3-local
```

Expected tail:

```text
BROKER_TEST_V4_3=PASS
SELFTEST_V4_3_R040029_PROJECT_IDENTITY=PASS
SELFTEST_V4_3_R040029_MODEL_POLICY=PASS
SELFTEST_V4_3_RELEASE_CANDIDATE_LOCAL=PASS
VERIFY_V4_7_LOCAL=PASS version=4.7.0
```

## Install

```bash
./install.sh
```

Expected:

```text
INSTALL_V4_7=PASS version=4.7.0
```

## Preflight

```bash
/opt/ai-loop/bin/preflight-v4.3 /path/to/PLAN.md
```

## Start a new run

```bash
/opt/ai-loop/bin/start-loop-v3 /path/to/PLAN.md
```

`v3` filename is retained for compatibility; daemon reports `version=4.7.0`.
