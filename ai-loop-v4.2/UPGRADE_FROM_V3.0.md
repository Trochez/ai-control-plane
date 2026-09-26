# Upgrade ai-loop v3.0 -> v3.1

v3.1 fixes the v3.0 bootstrap failure where OpenCode could type the delivery marker and click **Send**, yet omit the final nonce-bound verifier call. v3.0 then classified the turn as `ADAPTIVE_PLAYWRIGHT_PROOF_MISSING` and retried the entire bootstrap, creating a duplicate-delivery risk.

## What changes

- **Atomic send transaction:** generic `playwright_browser_click` is forbidden for Send. One exact `playwright_browser_run_code` transaction re-checks the empty project draft, browser ledger, attachment and exact composer text; then it alone clicks Send, waits for the user turn and `/c/` URL, persists `ledger.sent`, and returns the proof in the same tool result.
- **No blind retry after a possible send:** any transcript showing a send click/transaction or delivery-marker composer mutation becomes `AMBIGUOUS_SEND`; a second send is forbidden.
- **Prior-run recovery before new delivery:** when starting the same plan, v3.1 scans prior v3 state/diagnostics for ambiguous deliveries. It tries to recover that newly-created chat before generating another delivery id.
- **Direct deterministic recovery worker:** `playwright-bootstrap-observer.cjs` scans the project/current recent chats for the exact delivery marker without OpenCode/LLM prose and without typing/uploading/sending.
- **Read-only guided recovery fallback:** if the deterministic worker cannot locate the marker, the navigator may inspect recent project chats read-only. It still cannot type, attach, create or send.
- **Upload ordering:** the navigator must open the Add-files/attachment control before calling file upload. `browser_file_upload ... no related modal state` is repaired in-place, not by restarting the whole bootstrap.
- **Fail closed if an old ambiguous delivery cannot be resolved.** This intentionally prevents a second implementation message.

## 1. Kill every existing loop/browser transport

```bash
pkill -TERM -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true
pkill -TERM -f 'opencode run' || true
pkill -TERM -f '@playwright/mcp' || true
pkill -TERM -f 'ai-loop-chatgpt-profile' || true
sleep 2
pkill -KILL -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true
pgrep -af 'ai-loopd-v2|ai-loopd-v3|opencode run|@playwright/mcp|ai-loop-chatgpt-profile' || true
```

The final `pgrep` should return no loop-owned process.

## 2. Install

```bash
cd /mnt/d/works/ai-control-plane
rm -rf ai-loop-v3.1
tar -xzf ai-loop-v3.1.tar.gz
cd ai-loop-v3.1
./install.sh
```

Required markers include:

```text
SELFTEST_V3=PASS version=3.1.0
SELFTEST_V3_ATOMIC_SEND_TRANSACTION=PASS
SELFTEST_V3_V300_MISSING_FINAL_PROOF_NO_BLIND_RETRY=PASS
SELFTEST_V3_PRIOR_AMBIGUOUS_DELIVERY_DISCOVERY=PASS
SELFTEST_V3_DETERMINISTIC_READONLY_RECOVERY_WORKER=PASS
SELFTEST_V3_AMBIGUOUS_SEND_RECOVERY_NO_RETRY=PASS
SELFTEST_V3_PRIOR_AMBIGUOUS_FAIL_CLOSED=PASS
INSTALL_V3=PASS version=3.1.0
```

## 3. Kill residuals again immediately before launch

Run the block from step 1 again. This is intentional.

## 4. Start the same plan as a new controller run

```bash
/opt/ai-loop/bin/start-loop-v3 \
  "/mnt/d/works/ai-control-plane/IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_20260918T050921Z.md"
```

### Important for the failed v3.0 run

The previous v3.0 transcript showed the delivery marker `8e1a6222437163fe71724c9d` being typed and a Send-button click. Therefore v3.1 will **first recover that ambiguous delivery**. If that message actually created a new `bot_trading` chat, v3.1 will adopt that newly-created chat and continue the loop there. It will not create/send a duplicate.

If the marker cannot be located deterministically/read-only, v3.1 stops with `CHATGPT_AMBIGUOUS_PREVIOUS_DELIVERY_UNRESOLVED`. That is a safety fence, not a retry condition.

## 5. Monitor

```bash
tail -F "$(ls -1t /var/lib/ai-loop/logs/*.v3.log | head -1)"
```

Expected recovery path if v3.0 really sent:

```text
ai-loopd-v3 version=3.1.0 ...
ADAPTIVE_RECOVERY prior_ambiguous=1 ...
BOOTSTRAP_OBSERVER PASS delivery_id=8e1a6222437163fe71724c9d found=true ...
ADAPTIVE_RECOVERY PASS prior_run=R20260918T160851 chat=.../bot-trading/c/<id> ...
CHAT_SURFACE PASS ...
MODEL_GUARD PASS ...
```

Expected clean-new-delivery path when there is no ambiguous predecessor:

```text
ADAPTIVE_SEND_TX PASS status=SENT chat=.../bot-trading/c/<id> ...
ADAPTIVE_BOOTSTRAP PASS ... verifier=atomic-sendtx-v1
```

You must **not** see three whole-bootstrap retries after a Send click. After a possible send, only recovery is allowed.
