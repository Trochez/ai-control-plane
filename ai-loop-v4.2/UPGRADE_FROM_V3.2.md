# Upgrade ai-loop v3.2 → v4.0

## 1. Kill every existing controller/browser transport

```bash
/opt/ai-loop/bin/kill-all-loop-v3 || true
pkill -TERM -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true
pkill -TERM -f 'opencode run|@playwright/mcp|ai-loop-chatgpt-profile' || true
sleep 2
pgrep -af 'ai-loopd-v2|ai-loopd-v3|opencode run|@playwright/mcp|ai-loop-chatgpt-profile' || true
```

The final `pgrep` must be empty.

## 2. Extract and install

```bash
cd /mnt/d/works/ai-control-plane
rm -rf ai-loop-v4.0
tar -xzf ai-loop-v4.0.tar.gz
cd ai-loop-v4.0
./install.sh
```

Required terminal markers include:

```text
SELFTEST_V4=PASS version=4.0.0
SELFTEST_V4_BOOTSTRAP_MODEL_FREE=PASS
SELFTEST_V4_POLICY_MODEL_FREE=PASS
SELFTEST_V4_FAST_BOOTSTRAP_BEFORE_OPENCODE=PASS
SELFTEST_V4_DIRECT_NODE_PLAYWRIGHT_WORKER=PASS
SELFTEST_V4_NO_BLIND_RESEND_AFTER_CLICK=PASS
SELFTEST_V4_ALL_SENDS_MODEL_FREE=PASS
INSTALL_V4=PASS version=4.0.0
```

## 3. Kill residuals again immediately before start

```bash
/opt/ai-loop/bin/kill-all-loop-v3 || true
pgrep -af 'ai-loopd-v2|ai-loopd-v3|opencode run|@playwright/mcp|ai-loop-chatgpt-profile' || true
```

## 4. Start a NEW loop from the plan

```bash
/opt/ai-loop/bin/start-loop-v3 \
  '/mnt/d/works/ai-control-plane/IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_20260918T050921Z.md'
```

The command name remains `start-loop-v3` for compatibility; the controller reports `version=4.0.0`.

## 5. Monitor

```bash
tail -F "$(ls -1t /var/lib/ai-loop/logs/*.v3.log | head -1)"
```

Expected early sequence:

```text
v4.0 migration: model-free direct Node/Playwright bootstrap ...
ai-loopd-v3 version=4.0.0 ...
DETERMINISTIC_BOOTSTRAP PASS chat=https://chatgpt.com/g/...bot-trading/c/... transport=direct-node-playwright-v4
PLAYWRIGHT_CLI_CAPABILITY=PASS ...
CHAT_SURFACE PASS ... verifier=direct-playwright-worker-v4
MODEL_GUARD PASS ... verifier=direct-playwright-worker-v4
```

The important difference is that `DETERMINISTIC_BOOTSTRAP PASS` should occur *before* the OpenCode capability turn. There must be no `ADAPTIVE_PLAYWRIGHT_PROOF_MISSING` in bootstrap or controller sends.

## 6. If it fails before Send

Do not guess selectors from a truncated log. Inspect the generated artifacts:

```bash
find /var/lib/ai-loop/runs/<RUN_ID>/browser/deterministic-bootstrap -maxdepth 1 -type f -ls
```

A pre-send failure is safe to rerun because no click occurred.

## 7. If it reports AMBIGUOUS_SEND

Do not restart/send manually. v4.0 automatically invokes the model-free read-only observer. If that observer cannot prove the marker, the controller fails closed without a second Send.
