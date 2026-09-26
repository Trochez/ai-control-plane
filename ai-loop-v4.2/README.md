# ai-loop v4.2 / v4.3 policy increment

Production hardening release over v4.1.

The isolated v4.3 policy increment is implemented in `chat-policy-v4.3.cjs`.
It adds strict exact selection, typed policy failures, policy hashes, and
fail-closed proof validation without changing the v4.2 runtime entrypoints.

## Live regression fixed

v4.1 could remain on a historical `/c/` conversation that already belonged to `bot_trading`. Because project identity was already `TARGET`, project navigation returned early; the fresh-chat routine then clicked an ambiguous `Chat` control and timed out. v4.2 forces the exact project root whenever a historical conversation/turns are loaded, then verifies an empty target-project draft before any attachment or Send.

It also:

- maps the exact target project anchor even when the sidebar link is not currently visible;
- treats `New chat in Bot_trading` + exact project-anchor mapping as strong target-project proof;
- uses bounded safe fresh-chat candidate actions only after project-root re-entry;
- re-enters the target project if a generic New chat action escapes project scope;
- fixes the model-policy wait predicate so it waits for Chat + Sol + High simultaneously;
- keeps single broker ownership and model-free Send/action-byte transport from v4.1.

## Verify

```bash
./bin/verify-v4.2-local
```

Expected end markers:

```text
BROKER_TEST_V4_2=PASS
SELFTEST_V4_2_RELEASE_CANDIDATE_LOCAL=PASS
VERIFY_V4_2_LOCAL=PASS
```

## Verify v4.3 policy increment

```bash
./bin/verify-v4.3-local
```

This is an offline regression only; it does not claim ChatGPT, GitHub, CI,
Semaphore, VPS, or deployment availability.

## Install

```bash
./install.sh
```

Expected:

```text
INSTALL_V4_2=PASS version=4.2.0
```

## Preflight

```bash
/opt/ai-loop/bin/preflight-v4.2 /path/to/PLAN.md
```

## Start a brand-new loop

```bash
/opt/ai-loop/bin/start-loop-v3 /path/to/PLAN.md
```
