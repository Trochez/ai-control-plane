#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TS="$(date +%Y%m%dT%H%M%S)"

LIVE_PATTERN='/opt/ai-loop/ai-loopd\.py|/opt/ai-loop/ai-loopd-v2\.py|/opt/ai-loop/ai-loopd-v3\.py|opencode run|@playwright/mcp|ai-loop-chatgpt-profile|browser-broker-v1\.cjs'
if pgrep -af "$LIVE_PATTERN" | grep -vE 'pgrep|grep' >/dev/null 2>&1; then
  echo "ERROR: old/new ai-loop or browser transport is still alive. Stop it before installing v4.8.1:" >&2
  echo "  pkill -TERM -f '/opt/ai-loop/ai-loopd-v2.py|/opt/ai-loop/ai-loopd-v3.py' || true" >&2
  echo "  pkill -TERM -f 'opencode run' || true" >&2
  echo "  pkill -TERM -f '@playwright/mcp' || true" >&2
  echo "  pkill -TERM -f 'ai-loop-chatgpt-profile' || true" >&2
  pgrep -af "$LIVE_PATTERN" | grep -vE 'pgrep|grep' >&2 || true
  exit 20
fi

mkdir -p /opt/ai-loop/bin /opt/ai-loop/prompts /var/lib/ai-loop/{state,logs,runs}
mkdir -p "$HOME/.config/opencode/agents" "$HOME/.playwright-mcp/uploads" "$HOME/.playwright-mcp/handoff"
chmod 0755 "$HOME/.playwright-mcp" "$HOME/.playwright-mcp/uploads" 2>/dev/null || true
chmod 0700 "$HOME/.playwright-mcp/handoff" 2>/dev/null || true

for f in \
  /opt/ai-loop/ai-loopd-v3.py \
  /opt/ai-loop/bin/start-loop-v3 /opt/ai-loop/bin/stop-loop-v3 /opt/ai-loop/bin/status-loop-v3 \
  /opt/ai-loop/bin/restart-loop-v3 /opt/ai-loop/bin/resume-current-v3 /opt/ai-loop/bin/kill-all-loop-v3 /opt/ai-loop/bin/preflight-v4.1 /opt/ai-loop/bin/verify-v4.1-local /opt/ai-loop/bin/preflight-v4.2 /opt/ai-loop/bin/verify-v4.2-local /opt/ai-loop/bin/preflight-v4.3 /opt/ai-loop/bin/verify-v4.3-local \
  /opt/ai-loop/OPERATOR_POLICY_V3.md /opt/ai-loop/semaphore_evidence.py /opt/ai-loop/playwright-artifact-worker.cjs /opt/ai-loop/playwright-bootstrap-observer.cjs /opt/ai-loop/playwright-bootstrap-worker.cjs /opt/ai-loop/browser-broker-v1.cjs; do
  [[ -f "$f" ]] && cp -a "$f" "$f.bak.$TS" || true
done

install -m 0755 "$SRC/ai-loopd-v3.py" /opt/ai-loop/ai-loopd-v3.py
install -m 0755 "$SRC/semaphore_evidence.py" /opt/ai-loop/semaphore_evidence.py
install -m 0755 "$SRC/bin/vps-ssh" /opt/ai-loop/bin/vps-ssh
install -m 0755 "$SRC/bin/ci-status" /opt/ai-loop/bin/ci-status
install -m 0755 "$SRC/playwright-artifact-worker.cjs" /opt/ai-loop/playwright-artifact-worker.cjs
install -m 0755 "$SRC/playwright-bootstrap-observer.cjs" /opt/ai-loop/playwright-bootstrap-observer.cjs
install -m 0755 "$SRC/playwright-bootstrap-worker.cjs" /opt/ai-loop/playwright-bootstrap-worker.cjs
install -m 0755 "$SRC/browser-broker-v1.cjs" /opt/ai-loop/browser-broker-v1.cjs
install -m 0755 "$SRC/selftest-v4.3.py" /opt/ai-loop/selftest-v4.3.py
mkdir -p /opt/ai-loop/tests
install -m 0755 "$SRC/tests/test-browser-broker-v4.2.cjs" /opt/ai-loop/tests/test-browser-broker-v4.2.cjs
install -m 0755 "$SRC/tests/test-browser-broker-v4.3.cjs" /opt/ai-loop/tests/test-browser-broker-v4.3.cjs
  install -m 0755 "$SRC/tests/test-browser-broker-v4.5.cjs" /opt/ai-loop/tests/test-browser-broker-v4.5.cjs
  install -m 0755 "$SRC/tests/test-attachments-v4.7.cjs" /opt/ai-loop/tests/test-attachments-v4.7.cjs
  install -m 0755 "$SRC/tests/test-observer-v4.7.3.cjs" /opt/ai-loop/tests/test-observer-v4.7.3.cjs
  install -m 0644 "$SRC/tests/attachment-regressions-v4.7.json" /opt/ai-loop/tests/attachment-regressions-v4.7.json
install -m 0755 "$SRC/tests/test-semaphore-evidence-v4.7.py" /opt/ai-loop/tests/test-semaphore-evidence-v4.7.py
install -m 0755 "$SRC/tests/test-reconciliation-v4.8.1.cjs" /opt/ai-loop/tests/test-reconciliation-v4.8.1.cjs
install -m 0644 "$SRC/tests/R20260922T040029-policy-state.json" /opt/ai-loop/tests/R20260922T040029-policy-state.json
install -m 0644 "$SRC/tests/ui-drift-fixtures.json" /opt/ai-loop/tests/ui-drift-fixtures.json
for x in start-loop-v3 stop-loop-v3 status-loop-v3 restart-loop-v3 resume-current-v3 kill-all-loop-v3 preflight-v4.1 verify-v4.1-local preflight-v4.2 verify-v4.2-local preflight-v4.3 verify-v4.3-local preflight-v4.5 doctor-v4.5 acceptance-v4.5 verify-acceptance-v4.5; do
  install -m 0755 "$SRC/bin/$x" "/opt/ai-loop/bin/$x"
done
install -m 0755 "$SRC/bin/verify-v4.5-local" /opt/ai-loop/bin/verify-v4.5-local

python3 - <<'PY'
import importlib.util
import sys
sys.path.insert(0, '/opt/ai-loop')
p='/opt/ai-loop/ai-loopd-v3.py'
s=importlib.util.spec_from_file_location('ai_loop',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
if m.VERSION != '4.8.1':
    raise SystemExit('ERROR: installed controller is not v4.8.1')
PY
install -m 0644 "$SRC/OPERATOR_POLICY_V3.md" /opt/ai-loop/OPERATOR_POLICY_V3.md
for prompt in operator_capabilities.txt implement.txt read_only_probe.txt diagnosis.txt no_commit_followup.txt replan.txt plan_artifact_followup.txt; do
  install -m 0644 "$SRC/prompts/$prompt" "/opt/ai-loop/prompts/$prompt"
done
install -m 0644 "$SRC/operator-transport.md" "$HOME/.config/opencode/agents/operator-transport.md"

# Preserve the established environment while normalizing v3 browser/controller settings.
touch /opt/ai-loop/ai-loop.env
sed -i \
  -e '/^OPENCODE_TRANSPORT_AGENT=/d' \
  -e '/^AI_LOOP_PLAYWRIGHT_UPLOAD_ROOT=/d' \
  -e '/^AI_LOOP_BROWSER_PROFILE=/d' \
  -e '/^AI_LOOP_OPENCODE_CLI_DIR=/d' \
  -e '/^AI_LOOP_DOM_HANDOFF_ROOT=/d' \
  -e '/^AI_LOOP_ARTIFACT_WORKER=/d' \
  -e '/^AI_LOOP_BOOTSTRAP_OBSERVER_WORKER=/d' \
  -e '/^AI_LOOP_BOOTSTRAP_WORKER=/d' \
  -e '/^AI_LOOP_CHROME_EXECUTABLE=/d' \
  -e '/^AI_LOOP_BROWSER_BROKER=/d' \
  -e '/^AI_LOOP_BROWSER_ACTION_TIMEOUT_MS=/d' \
  -e '/^AI_LOOP_BROWSER_NAVIGATION_TIMEOUT_MS=/d' \
  -e '/^AI_LOOP_BROWSER_SETTLE_TIMEOUT_MS=/d' \
  -e '/^AI_LOOP_ASSISTANT_RESPONSE_TIMEOUT_MS=/d' \
  -e '/^AI_LOOP_MIN_SEND_INTERVAL_SECONDS=/d' \
  -e '/^AI_LOOP_STARTUP_QUIET_SECONDS=/d' \
  -e '/^AI_LOOP_GENERATING_POLL_BASE_SECONDS=/d' \
  -e '/^AI_LOOP_GENERATING_POLL_MAX_SECONDS=/d' \
  /opt/ai-loop/ai-loop.env 2>/dev/null || true
{
  echo 'OPENCODE_TRANSPORT_AGENT=operator'
  echo "AI_LOOP_PLAYWRIGHT_UPLOAD_ROOT=$HOME/.playwright-mcp/uploads"
  echo "AI_LOOP_BROWSER_PROFILE=$HOME/.cache/ai-loop-chatgpt-profile"
  echo "AI_LOOP_OPENCODE_CLI_DIR=${AI_LOOP_OPENCODE_CLI_DIR:-$SRC}"
  echo "AI_LOOP_DOM_HANDOFF_ROOT=$HOME/.playwright-mcp/handoff"
  echo 'AI_LOOP_ARTIFACT_WORKER=/opt/ai-loop/playwright-artifact-worker.cjs'
  echo 'AI_LOOP_BOOTSTRAP_OBSERVER_WORKER=/opt/ai-loop/playwright-bootstrap-observer.cjs'
  echo 'AI_LOOP_BOOTSTRAP_WORKER=/opt/ai-loop/playwright-bootstrap-worker.cjs'
  echo 'AI_LOOP_CHROME_EXECUTABLE=/opt/google/chrome/chrome'
  echo 'AI_LOOP_BROWSER_BROKER=/opt/ai-loop/browser-broker-v1.cjs'
  echo 'AI_LOOP_BROWSER_ACTION_TIMEOUT_MS=8000'
  echo 'AI_LOOP_BROWSER_NAVIGATION_TIMEOUT_MS=30000'
  echo 'AI_LOOP_BROWSER_SETTLE_TIMEOUT_MS=12000'
  echo 'AI_LOOP_BROWSER_HYDRATION_TIMEOUT_MS=12000'
  echo 'AI_LOOP_ASSISTANT_RESPONSE_TIMEOUT_MS=900000'
  echo 'AI_LOOP_MIN_SEND_INTERVAL_SECONDS=5'
  echo 'AI_LOOP_STARTUP_QUIET_SECONDS=0'
  echo 'AI_LOOP_GENERATING_POLL_BASE_SECONDS=5'
  echo 'AI_LOOP_GENERATING_POLL_MAX_SECONDS=30'
} >> /opt/ai-loop/ai-loop.env
for kv in \
  'AI_LOOP_MIN_SEND_INTERVAL_SECONDS=5' \
  'AI_LOOP_RATE_LIMIT_BASE_SECONDS=300' \
  'AI_LOOP_RATE_LIMIT_STEP_SECONDS=120' \
  'AI_LOOP_STARTUP_QUIET_SECONDS=0' \
  'AI_LOOP_GENERATING_POLL_BASE_SECONDS=5' \
  'AI_LOOP_GENERATING_POLL_MAX_SECONDS=30' \
  'AI_LOOP_RESPONSE_SETTLE_SECONDS=12' \
  'AI_LOOP_OPENCODE_TURN_TIMEOUT_SECONDS=2700' \
  'AI_LOOP_PLAN_ARTIFACT_MAX_ATTEMPTS=3' \
  'AI_LOOP_PLAN_ARTIFACT_BLOCKED_RECHECK_SECONDS=900' \
  'AI_LOOP_PLAN_ARTIFACT_MAX_REQUESTS=1' \
  'AI_LOOP_SEMANTIC_MIN_CONFIDENCE=0.55' \
  'AI_LOOP_SEMANTIC_UNCLASSIFIED_RECHECK_SECONDS=300' \
  'AI_LOOP_NEW_MESSAGE_POLL_BASE_SECONDS=30' \
  'AI_LOOP_NEW_MESSAGE_POLL_MAX_SECONDS=300'; do
  key="${kv%%=*}"
  grep -q "^${key}=" /opt/ai-loop/ai-loop.env 2>/dev/null || echo "$kv" >> /opt/ai-loop/ai-loop.env
done

python3 -m py_compile /opt/ai-loop/ai-loopd-v3.py
command -v node >/dev/null || { echo 'ERROR: node is required' >&2; exit 23; }
node --check /opt/ai-loop/playwright-artifact-worker.cjs
node --check /opt/ai-loop/playwright-bootstrap-observer.cjs
node --check /opt/ai-loop/playwright-bootstrap-worker.cjs
node --check /opt/ai-loop/browser-broker-v1.cjs
node /opt/ai-loop/tests/test-browser-broker-v4.2.cjs
node /opt/ai-loop/tests/test-browser-broker-v4.3.cjs
node /opt/ai-loop/tests/test-attachments-v4.7.cjs
node /opt/ai-loop/tests/test-observer-v4.7.3.cjs
node /opt/ai-loop/tests/test-reconciliation-v4.8.1.cjs
python3 /opt/ai-loop/selftest-v4.3.py
python3 /opt/ai-loop/tests/test-semaphore-evidence-v4.7.py
command -v opencode >/dev/null || { echo 'ERROR: opencode not found' >&2; exit 24; }
command -v python3 >/dev/null || exit 25

echo 'INSTALL_V4_8_1=PASS version=4.8.1'
