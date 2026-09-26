# Upgrade ai-loop v3.1 -> v3.2

v3. 2 fixes observed v3. 1 deadlock:

```text
BOOTSTRAP_OBSERVER PASS ... found=False ... visited=0
CHATGPT_AMBIGUOUS_PREVIOUS_DELIVERY_UNRESOLVED
```

root cause was not new browser failure. v3. 1 could only recover ambiguous prior delivery from links visible in current project DOM. When ChatGPT exposed no project chat links, read-only observer had zero candidates and controller permanently fenced new run.

## v3.2 remediation

v3. 2 separates **new-loop bootstrap** from **same-run ambiguous-send recovery**. new `start-loop-v3` never adopts or reopens previous run's chat. Prior ambiguous delivery IDs are quarantined as metadata, while same-run ambiguity can still use read-only recovery to avoid duplicate sends.

For diagnostics and same-run recovery, v3. 2 can build candidates from four independent evidence sources:

1. exact chat URLs persisted in previous v3 state;
2. exact chat URLs recovered from browser diagnostic/transcript artifacts;
3. recent project chat URLs from persistent Chrome profile `History` SQLite database (copied read-only before query);
4. live project DOM/model-guided read-only navigation.

Every recovered URL is passed to deterministic Playwright worker and scanned for exact `[AI_LOOP_DELIVERY id=...]` user marker. worker now reports candidate count, visited URLs, scan completion, and browser-local send ledger.

For **new loop**, prior ambiguous deliveries are always persisted as `AMBIGUITY_QUARANTINED` and controller creates fresh project chat. It does not navigate to or adopt those historical chats. new delivery carries **re-entry-safe** instruction requiring reconciliation of current branch/remote/CI state and explicitly forbidding duplicate/amend/revert/cherry-pick/push when plan's implementation/final commit already exists.

For ambiguity created **inside currently running loop**, read-only marker recovery is still allowed so same atomic delivery is not resent.

Resolved/quarantined prior states are terminal and are ignored by later starts, so stale diagnostic text cannot re-trigger same fence forever.

## Safety retained

- normal Chat only;
- GPT-5. 6 Sol + High required before authoritative sends;
- Work/Codex forbidden;
- one atomic browser Send transaction;
- exact delivery marker and browser ledger;
- no blind retry after possible Send;
- SHA-256 command/artifact integrity;
- strict local/VPS routing;
- existing Semaphore/CI/action architecture retained.

## Install

First stop all loop/browser transports:

```bash
pkill -TERM -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true
pkill -TERM -f 'opencode run' || true
pkill -TERM -f '@playwright/mcp' || true
pkill -TERM -f 'ai-loop-chatgpt-profile' || true
sleep 2
pkill -KILL -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true
pgrep -af 'ai-loopd-v2|ai-loopd-v3|opencode run|@playwright/mcp|ai-loop-chatgpt-profile' || true
```

Then:

```bash
cd /mnt/d/works/ai-control-plane
rm -rf ai-loop-v3.2
tar -xzf ai-loop-v3.2.tar.gz
cd ai-loop-v3.2
./install.sh
```

Expected key tests:

```text
SELFTEST_V3=PASS version=3.2.0
SELFTEST_V3_NEGATIVE_DELIVERY_RECONCILIATION=PASS
SELFTEST_V3_CHROME_HISTORY_CHAT_DISCOVERY=PASS
SELFTEST_V3_PRIOR_STATE_CHAT_URL_RECOVERY=PASS
SELFTEST_V3_NEW_LOOP_NEVER_ADOPTS_OLD_CHAT=PASS
SELFTEST_V3_ATOMIC_SEND_TRANSACTION=PASS
INSTALL_V3=PASS version=3.2.0
```

Before starting new run, repeat stop block above. Then:

```bash
/opt/ai-loop/bin/start-loop-v3 \
  "/mnt/d/works/ai-control-plane/IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_20260918T050921Z.md"
```

Monitor:

```bash
tail -F "$(ls -1t /var/lib/ai-loop/logs/*.v3.log | head -1)"
```

For exact v3. 1 incident, **new loop** should now log:

```text
ADAPTIVE_NEW_LOOP prior_ambiguous=... historical chat adoption disabled; quarantining prior deliveries
ADAPTIVE_NEW_LOOP QUARANTINE ... old chat will NOT be opened/adopted
```

and then continue into normal fresh-chat adaptive bootstrap rather than terminating.
