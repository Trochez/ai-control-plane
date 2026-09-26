# Upgrade ai-loop v2.40 -> v3.0

v3. 0 is architectural change to ChatGPT-Web transport. It preserves mature v2 action/CI/VPS/artifact logic but replaces fragile multi-turn browser proof protocols used by v2. 32-v2. 40.

## 1. Kill every live loop/browser transport first

Run this before installing **and again before starting new loop**:

```bash
pkill -TERM -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true
pkill -TERM -f 'opencode run' || true
pkill -TERM -f '@playwright/mcp' || true
pkill -TERM -f 'ai-loop-chatgpt-profile' || true
sleep 2
pkill -KILL -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true
pgrep -af 'ai-loopd-v2|ai-loopd-v3|opencode run|@playwright/mcp|ai-loop-chatgpt-profile' || true
```

final `pgrep` should print nothing belonging to ai-loop.

## 2. Install v3.0

```bash
cd /mnt/d/works/ai-control-plane
rm -rf ai-loop-v3.0
tar -xzf ai-loop-v3.0.tar.gz
cd ai-loop-v3.0
./install.sh
```

Required final markers include:

```text
SELFTEST_V3=PASS version=3.0.0
SELFTEST_V3_NONCE_BOUND_PLAYWRIGHT_PROOF=PASS
SELFTEST_V3_MODEL_PROSE_NOT_AUTHORITY=PASS
SELFTEST_V3_V240_UNVERIFIED_REGRESSION_RETIRED=PASS
SELFTEST_V3_PRE_SEND_LEDGER_GATES=PASS
SELFTEST_V3_BOOTSTRAP_STATE_MACHINE=PASS
SELFTEST_V3_BROWSER_DIAGNOSTIC_ARTIFACT=PASS
SELFTEST_V3_V2_CORE_PRESERVED=PASS
INSTALL_V3=PASS version=3.0.0
```

## 3. Kill residuals again before the new run

Use exact block from step 1 again. v3 intentionally refuses to start if any v2/v3 controller, `opencode run`, Playwright MCP, or dedicated-profile Chrome survives.

## 4. Start a completely new loop and new project chat

For current plan:

```bash
/opt/ai-loop/bin/start-loop-v3 \
  "/mnt/d/works/ai-control-plane/IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_20260918T050921Z.md"
```

Do **not** use `restart-loop-v3` for this run. `start-loop-v3` creates new state and bootstraps brand-new chat in configured `bot_trading` project.

## 5. Monitor

Use `LOG=` path printed by `start-loop-v3`, or:

```bash
tail -F "$(ls -1t /var/lib/ai-loop/logs/*.v3.log | head -1)"
```

Expected bootstrap markers:

```text
ai-loopd-v3 version=3.0.0 ...
PLAYWRIGHT_CLI_CAPABILITY=PASS ...
ADAPTIVE_BOOTSTRAP PASS chat=.../c/... delivery_id=... verifier=dom-ledger-v1
CHAT_SURFACE PASS surface=chat work=false codex=false purpose=start-plan-post-send verifier=adaptive-dom-v1
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high purpose=start-plan-post-send verifier=adaptive-dom-v1
```

If adaptive navigation cannot converge, it fails closed and records diagnostics such as:

```text
/var/lib/ai-loop/runs/<RUN_ID>/browser/adaptive/<timestamp>-<purpose>.json
```

Those files contain deterministic observation, selected/relevant controls, compact HTML-like evidence, and tail of transport transcript. This is first artifact to inspect on future UI failure.

## 6. What changed

browser model no longer has to generate controller JSON such as `AI_LOOP_CHAT_POLICY_EVENT_*` or `AI_LOOP_FRESH_PROJECT_PROOF_*` to prove navigation. It now receives UI goal, inspects live DOM/ARIA/HTML, and acts. Controller authority comes only from nonce-bound `playwright_browser_run_code` verifier output.

new bootstrap runs in one browser turn: fresh empty project draft -> Sol High -> deterministic preflight ledger -> attach/type -> deterministic pre-send gate -> one Send click -> deterministic final proof. This avoids losing unsent draft between separate `opencode run` processes.
