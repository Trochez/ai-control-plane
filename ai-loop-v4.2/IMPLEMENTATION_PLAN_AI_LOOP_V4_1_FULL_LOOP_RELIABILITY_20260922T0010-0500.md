# IMPLEMENTATION PLAN — ai-loop v4.1 Full-Loop Reliability, Deterministic Browser Ownership & End-to-End GO

**Generated:** 2026-09-22T00:10-05:00  
**Current baseline:** ai-loop `v4.0.0`  
**Target release:** ai-loop `v4.1.0`  
**Control-plane repository:** `/mnt/d/works/ai-control-plane`  
**Primary daemon:** `/opt/ai-loop/ai-loopd-v3.py` (name retained for compatibility; target runtime version `4.1.0`)  
**Target ChatGPT Project:** `bot_trading`  
**Target branch:** `feature/GRU`  
**Current observed baseline SHA:** `44505ddbfa5062dc1c712fc90db72cb0c54de924`  
**Primary acceptance plan:** `IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_20260918T050921Z.md`

---

## 0. Mandatory objective

The implementation is complete only when a **brand-new loop can run end-to-end, unattended, from `start-loop-v3` to final `GO/COMPLETE_GO`**, using the real integrations required by the workflow and without an uncaught traceback.

The production acceptance path must prove all of the following in one coherent run:

1. create a **new empty chat inside the `bot_trading` project**;
2. prove the active surface is normal **Chat**, never Work/Codex;
3. prove the selected model policy is **GPT-5.6 Sol + High**;
4. attach the exact requested `.md` plan;
5. send it **exactly once**;
6. observe the assistant response without model-controlled browser navigation;
7. classify the response semantically;
8. extract any requested operator action without passing command bytes through LLM output;
9. execute the correct target adapter (`local`, `github-readonly`, `vps`, `semaphore`);
10. return literal evidence to the same chat exactly once;
11. survive generating states, network delays, browser restarts and controller restarts without duplicate sends/actions;
12. download/validate any generated `.md` remediation artifact when the workflow requests one;
13. monitor CI/Semaphore and production evidence as required;
14. continue the state machine until an independently validated `FINAL_GO`;
15. persist a complete evidence bundle proving the run.

A release candidate is **not releasable** merely because unit tests pass. A live full-loop acceptance run is mandatory.

---

# 1. Evidence and diagnosis

## 1.1 Observed production failure

The v4.0 run reached the direct deterministic browser worker quickly but failed twice before sending:

```text
DETERMINISTIC_BOOTSTRAP RETRY_SAFE_NO_SEND attempt=1 error=FRESH_PROJECT_WRONG_PROJECT
DETERMINISTIC_BOOTSTRAP RETRY_SAFE_NO_SEND attempt=2 error=FRESH_PROJECT_WRONG_PROJECT
CHATGPT_DETERMINISTIC_BOOTSTRAP_FAILED_NO_SEND:FRESH_PROJECT_WRONG_PROJECT
```

The accompanying browser screenshot shows an empty composer whose UI says:

```text
New chat in Bot_trading
```

while the address bar is effectively the generic ChatGPT root rather than a URL containing the project id.

This is the key contradiction: **the UI has project-scoped draft context even when `location.href` does not contain the project id**.

## 1.2 Confirmed root cause in v4.0

`playwright-bootstrap-worker.cjs` currently defines project identity primarily as:

```javascript
location.href.includes(cfg.projectId)
```

and `ensureFreshProjectDraft()` ultimately rejects with:

```javascript
if(!page.url().includes(cfg.projectId))
    throw new Error('FRESH_PROJECT_WRONG_PROJECT');
```

That assumption is invalid for the current ChatGPT Projects UI.

### Consequence A — false negative

A legitimate project-scoped draft can be rejected because the browser URL is generic while the composer/sidebar still clearly belongs to `bot_trading`.

### Consequence B — opposite safety bug

`ensureFreshProjectDraft()` also contains an early success path:

```javascript
if(turns===0 && c) return;
```

before proving project membership. Therefore a generic empty ChatGPT draft can potentially be treated as fresh before target-project identity is established.

Both paths must be replaced by one authoritative project-context verifier.

## 1.3 Project proof is duplicated inconsistently

The same URL-centric assumption is present in `currentState()` and is reused by bootstrap/policy logic.

Post-send Python acceptance verifies `/c/` plus delivery ledger but does not currently require a strong, independently computed target-project identity. Therefore project correctness is both too strict before Send and not strict enough after Send.

## 1.4 Model/reasoning policy still has weak proof paths

`ensureModelSolHigh()` can set:

```javascript
modelOk=true
highOk=true
```

immediately after clicking a matching option. It does not always reopen/re-read the selected state to prove persistence.

`visibleTextPresent()` can also see an available option without proving that it is selected.

The final policy must use **positive selected-state evidence**, not “option exists” evidence.

## 1.5 Attachment proof is too broad

The current worker can accept a filename discovered in the entire page body. The attachment must instead be proven inside the active composer/attachment region or via the actual file input/file-chip associated with that composer.

## 1.6 Fixed sleeps add latency and race conditions

The browser worker contains many fixed waits (`1800 ms`, `1300 ms`, `700 ms`, etc.). These make fast cases slower and slow cases still unreliable.

All important transitions should be condition-driven with bounded, configurable budgets.

## 1.7 Browser ownership remains split after bootstrap

v4.0 correctly removes OpenCode from initial create/attach/send, but later phases still use OpenCode + Playwright for:

- semantic response inspection;
- response identity inspection;
- explicit operator-action extraction;
- exact DOM action handoff;
- some Semaphore evidence collection.

That means the same dedicated profile continues to alternate between:

```text
direct Node/Playwright
and
OpenCode → Playwright MCP
```

The controller repeatedly kills/relaunches profile-bound Chrome/MCP processes to arbitrate ownership. This is a continuing source of latency, contention, recovery complexity and hard-to-reproduce browser state.

## 1.8 Current tests validate source structure more than complete behavior

Existing v4 self-tests prove important invariants, but the latest failure passed those tests. The missing class is a realistic UI/state-machine test in which:

```text
URL = https://chatgpt.com/
composer = "New chat in Bot_trading"
target project selected in UI
turn count = 0
```

The test suite must move from source-token assertions toward executable browser fixtures and a mandatory live full-loop canary.

---

# 2. RALPLAN-DR summary

## Principles

1. **One physical browser authority:** one controller-owned browser transport owns all ChatGPT UI reads/writes for the entire run.
2. **Semantic context over URL assumptions:** project identity is proven from multiple live UI signals; URL is only one signal.
3. **No model-controlled side effects:** an LLM may classify text or propose navigation, but cannot be the authority for Send, file bytes, action bytes, project identity, CI identity or GO.
4. **Idempotency before retry:** after any potentially side-effecting operation, reconcile before retrying.
5. **Release by end-to-end evidence:** no release until a real full loop reaches validated GO.

## Top decision drivers

1. Eliminate recurrent browser/UI proof failures rather than patching each selector.
2. Reduce startup/turn latency by eliminating repeated browser ownership handoffs and fixed sleeps.
3. Guarantee no wrong-project delivery, duplicate send, duplicate action or duplicate commit.

## Viable options

### Option A — Patch only `FRESH_PROJECT_WRONG_PROJECT`

Change URL proof to accept the composer label and add a regression test.

**Pros:** smallest diff, fast implementation.  
**Cons:** leaves split browser ownership, weak model proof, broad attachment proof, fixed sleeps and later OpenCode/Playwright fragility intact.

**Disposition:** rejected. It treats the newest symptom, not the recurrent architecture class.

### Option B — Single persistent deterministic ChatGPT browser broker + text-only OpenCode reasoning

A long-lived Node/Playwright broker owns ChatGPT browser state for the full run. Python communicates with it over a bounded JSONL/RPC contract. OpenCode receives normalized response text/metadata only and never owns the ChatGPT browser.

**Pros:** one browser owner, lower latency, deterministic UI proofs, exact DOM/file transport, easier restart/idempotency testing.  
**Cons:** larger migration, requires explicit broker lifecycle/reconnect logic.

**Disposition:** **chosen**.

### Option C — Keep direct one-shot workers but remove all OpenCode Playwright use

Each browser operation launches a fresh direct Playwright context; OpenCode becomes text-only.

**Pros:** simpler than a broker, removes profile contention.  
**Cons:** repeated Chrome startup remains expensive; state transitions across workers are harder to prove atomically.

**Disposition:** viable fallback if the persistent broker cannot meet crash-recovery acceptance, but not the preferred target.

---

# 3. Target architecture

## 3.1 Browser Transport Broker

Introduce:

```text
/opt/ai-loop/browser-broker-v1.cjs
```

One process owns the dedicated ChatGPT Chrome persistent profile for the lifetime of the run.

Python communicates over:

```text
stdin/stdout JSONL
```

or a run-scoped Unix socket:

```text
/var/lib/ai-loop/runs/<RUN_ID>/browser/broker.sock
```

Every request has:

```json
{
  "request_id": "...",
  "run_id": "...",
  "operation": "...",
  "arguments": {},
  "deadline_epoch_ms": 0
}
```

Every result has:

```json
{
  "request_id": "...",
  "status": "PASS|RETRYABLE|AMBIGUOUS|BLOCKED|ERROR",
  "side_effect": false,
  "state_before": {},
  "state_after": {},
  "evidence": {},
  "error": ""
}
```

The broker must never output command/file payload bytes when a filesystem handoff is available.

## 3.2 Browser operations

The broker must support at minimum:

```text
HEALTH
NAVIGATE_PROJECT
OBSERVE_CONTEXT
ENSURE_FRESH_PROJECT_DRAFT
ENSURE_CHAT_POLICY
ATTACH_FILE
FILL_COMPOSER
SEND_ATOMIC
OBSERVE_DELIVERY
OBSERVE_RESPONSE
EXTRACT_TURN_STRUCTURE
MATERIALIZE_CODE_BLOCK
DOWNLOAD_ARTIFACT
CAPTURE_DIAGNOSTICS
CLOSE
```

## 3.3 Canonical project-context verifier

Create one function used everywhere:

```text
resolveProjectContext(targetProjectId, expectedProjectName) →
    TARGET | OTHER | UNKNOWN
```

Evidence signals:

### Strong positive signals

- current URL contains the exact project id;
- selected/current sidebar project anchor has an `href` containing the exact project id;
- a project-scoped composer explicitly identifies the project, e.g. `aria-label="New chat in Bot_trading"`, and the project anchor mapping proves that visible name belongs to the target project;
- a project header/breadcrumb/control is linked to the target project id.

### Strong negative signals

- another project is positively selected;
- composer explicitly names a different project;
- project-specific URL identifies a different project.

### Insufficient by itself

- arbitrary body text containing `Bot_trading`;
- page title;
- generic `chatgpt.com` URL;
- a project name in historical conversation text.

### Decision rule

```text
TARGET:
  >=1 project-id-linked signal
  OR
  >=2 independent semantic project signals with no negative signal

OTHER:
  any strong negative signal

UNKNOWN:
  otherwise
```

A generic `https://chatgpt.com/` URL is therefore neutral, not failure.

## 3.4 Fresh-chat verifier

A draft is fresh only if all are true:

```text
project_context == TARGET
user_turn_count == 0
assistant_turn_count == 0
composer visible
composer editable
no delivery marker from current run
not positively identified as historical conversation
```

URL shape is not required before first Send.

## 3.5 Post-send project verifier

After Send, success requires:

```text
delivery marker exists as a user turn
project_context == TARGET
new conversation identity is stable
ledger.delivery_id matches
ledger.send_status == SENT
```

Do not assume `/g/<project>/c/<id>` is the only valid URL form. Store:

```text
chat_url
conversation_id if discoverable
project_context_evidence
```

separately.

## 3.6 Chat + Sol + High verifier

Policy PASS requires **positive proof**:

```text
surface = CHAT selected
model = GPT-5.6 Sol selected
reasoning = High selected
```

After changing model/reasoning, reopen/re-read controls and prove persistence.

Do not convert a successful click into proof.

## 3.7 Exact attachment verifier

Attachment PASS requires one of:

- file input belonging to the active composer contains the exact file;
- attachment chip/card inside the active composer region contains the exact filename;
- deterministic upload state tied to the active composer proves the same file.

Whole-page body text alone is forbidden as proof.

## 3.8 Event-driven waits

Replace fixed sleeps with bounded conditions:

```text
waitForComposer()
waitForProjectContext()
waitForMenuOpen()
waitForSelectionPersisted()
waitForAttachment()
waitForSendEnabled()
waitForUserTurnMarker()
waitForAssistantStarted()
waitForAssistantSettled()
```

Budgets must come from environment/config, not scattered constants.

Recommended configurable classes:

```text
AI_LOOP_BROWSER_ACTION_TIMEOUT_MS
AI_LOOP_BROWSER_NAVIGATION_TIMEOUT_MS
AI_LOOP_BROWSER_SETTLE_TIMEOUT_MS
AI_LOOP_ASSISTANT_RESPONSE_TIMEOUT_MS
AI_LOOP_CI_POLL_INTERVAL_SECONDS
AI_LOOP_CI_TOTAL_TIMEOUT_SECONDS
```

## 3.9 OpenCode becomes browser-free

Remove ChatGPT Playwright ownership from OpenCode.

The broker returns:

```json
{
  "assistant_message_id": "...",
  "assistant_text_path": "...",
  "assistant_text_sha256": "...",
  "generation_state": "GENERATING|SETTLED|RATE_LIMIT",
  "turn_structure_path": "..."
}
```

Python sends the normalized assistant text plus bounded metadata to OpenCode for semantic classification.

OpenCode may return a semantic proposal, but Python remains transition authority.

## 3.10 Action extraction without browser-controlled LLM

The broker deterministically enumerates fenced blocks in the controller-approved assistant turn:

```json
[
  {
    "block_index": 0,
    "language": "bash",
    "sha256": "...",
    "bytes": 1234,
    "context_before": "...",
    "context_after": "..."
  }
]
```

OpenCode sees assistant text + block metadata and may propose:

```json
{
  "action": true,
  "block_index": 0,
  "target": "local|vps|github-readonly|semaphore"
}
```

The controller then asks the broker to materialize that exact block by:

```text
message identity + block index + expected SHA + expected length
```

No command bytes pass through model output.

## 3.11 Deterministic tool adapters

### Local

Controller-owned subprocess execution with existing safety policy and evidence capture.

### GitHub

Use `gh` directly with exact repo/branch/SHA verification and bounded transient retry.

### VPS

Only:

```text
/opt/ai-loop/bin/vps-ssh
```

No raw SSH from action payloads.

### Semaphore

Primary path should be deterministic:

1. Semaphore API/CLI when credentials are available;
2. direct dedicated browser adapter when web auth is required;
3. OpenCode may interpret human-readable evidence but does not own navigation or identity proof.

CI identity must always be:

```text
provider + exact candidate SHA + workflow/run id + pipeline id
```

## 3.12 State persistence and restart

Persist after every meaningful transition:

```text
browser broker pid/session epoch
project context evidence
chat identity
delivery ledger
latest assistant identity
semantic fingerprint
pending actions
action receipts
GitHub SHA
CI identity/status
VPS evidence identities
phase/failure_stage
```

On restart, reconcile state before any side effect.

---

# 4. Non-negotiable invariants

| ID | Invariant |
|---|---|
| INV-01 | A new loop never sends into a historical chat. |
| INV-02 | A generic `chatgpt.com` URL must not be treated as wrong project when live project UI proves `bot_trading`. |
| INV-03 | A generic empty ChatGPT composer without target-project proof must never be accepted as `bot_trading`. |
| INV-04 | Only one process owns the ChatGPT browser profile at a time. |
| INV-05 | OpenCode never clicks Send, attaches files, switches projects/models, or materializes browser bytes. |
| INV-06 | Every outbound message has one deterministic delivery id and one persistent ledger. |
| INV-07 | Any possible Send side effect forbids blind resend until reconciliation. |
| INV-08 | Surface/model/reasoning are positively proven selected, not merely visible. |
| INV-09 | Exact plan attachment is proven in the active composer before Send. |
| INV-10 | Action command bytes never traverse LLM JSON/text. |
| INV-11 | Every action is SHA/length verified immediately before execution. |
| INV-12 | `local` actions remain local; `vps` uses only controller-owned `vps-ssh`. |
| INV-13 | GitHub/CI/VPS evidence is bound to exact SHA/identity. |
| INV-14 | Controller restart cannot duplicate Send, action, pipeline launch, deployment or commit. |
| INV-15 | No release candidate is promoted until the live full-loop acceptance reaches validated FINAL_GO. |
| INV-16 | No uncaught Python/Node traceback is accepted in the full acceptance run. |
| INV-17 | All browser failures persist JSON + HTML + screenshot + state transition trace. |
| INV-18 | Timeouts/backoff are configurable and condition-driven; no multi-minute blind sleep is used for normal browser steps. |

---

# 5. Team

**Team size: 8**

| Role | Code | Responsibility |
|---|---|---|
| Technical Lead / Planner | TL | Architecture, invariants, merge authority, release gates |
| Browser Transport Engineer | BTE | Persistent Playwright broker, project/model/file/send proofs |
| Controller/FSM Engineer | CFE | Python state machine, idempotency, restart/recovery |
| Semantic Integration Engineer | SIE | Browser-free OpenCode semantic classification and action referencing |
| Tool Adapter Engineer | TAE | local/GitHub/VPS/Semaphore deterministic adapters |
| Test & Chaos Engineer | TCE | executable fixtures, failure injection, restart/idempotency tests |
| SRE / Performance Engineer | SRE | latency, process ownership, diagnostics, soak tests |
| Independent Reviewer / Release Auditor | IRA | acceptance evidence, invariant audit, final release approval |

### Reasoning guidance

- TL, BTE, CFE, IRA: **High**
- SIE, TAE, TCE: **High** for failure-path design; **Medium** for mechanical test implementation
- SRE: **Medium/High** depending on incident complexity

---

# 6. Atomic implementation backlog

## WS0 — Freeze evidence and create context snapshot

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B01 | TL | — | Create `.omx/context/ai-loop-full-cycle-reliability-<UTC>.md` with v4.0 source baseline, current log, screenshot facts, constraints and acceptance goal. |
| B02 | IRA | B01 | Record SHA-256 of all v4.0 source files before modification. |
| B03 | TCE | B01 | Add the observed `FRESH_PROJECT_WRONG_PROJECT` log as an immutable regression fixture. |
| B04 | TCE | B01 | Add a UI fixture representing generic URL + `New chat in Bot_trading` + target project selection + zero turns. |
| B05 | TCE | B01 | Add opposite fixture: generic URL + generic composer + zero turns + no target-project evidence. |

## WS1 — Canonical project identity

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B06 | BTE | B04,B05 | Implement `resolveProjectContext()` returning TARGET/OTHER/UNKNOWN with structured evidence. |
| B07 | BTE | B06 | Detect project-id-linked sidebar anchor and selected/current state. |
| B08 | BTE | B06 | Detect project-scoped composer label and correlate project display name to target project anchor. |
| B09 | BTE | B06 | Detect strong negative evidence for a different selected project. |
| B10 | CFE | B06 | Replace all URL-only project checks in bootstrap/policy/send/observer with canonical project-context result. |
| B11 | TCE | B06-B10 | Unit-test every TARGET/OTHER/UNKNOWN truth-table case. |
| B12 | IRA | B11 | Audit for remaining `url.includes(projectId)` uses that can independently authorize/reject a send. |

## WS2 — Fresh project chat state machine

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B13 | BTE | B06 | Refactor fresh-chat acquisition into explicit states: NAVIGATE_PROJECT → PROJECT_READY → FRESH_DRAFT → POLICY_READY. |
| B14 | BTE | B13 | Remove early success on `turns===0 && composer` unless project context is TARGET. |
| B15 | BTE | B13 | Allow generic root URL when project context is TARGET. |
| B16 | BTE | B13 | If current page is historical, navigate via target project anchor/control without selecting a history entry. |
| B17 | TCE | B13-B16 | Browser-fixture tests for generic root, project root, historical chat, wrong project and already-fresh draft. |

## WS3 — Persistent Browser Transport Broker

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B18 | BTE | B13 | Implement `browser-broker-v1.cjs` with one persistent Chrome context per run. |
| B19 | CFE | B18 | Implement Python broker client with request ids, deadlines and typed status contract. |
| B20 | SRE | B18 | Implement broker heartbeat, process epoch and clean shutdown/restart. |
| B21 | CFE | B18-B20 | Persist broker epoch/state and reconcile after controller restart. |
| B22 | SRE | B18 | Remove per-operation profile killing/relaunch from normal success path. |
| B23 | TCE | B18-B22 | Kill broker mid-observation and mid-pre-send; prove restart without duplicate side effects. |

## WS4 — Positive Chat / Sol / High proof

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B24 | BTE | B18 | Implement positive Chat-surface selected-state verifier. |
| B25 | BTE | B24 | Implement selected GPT-5.6 Sol proof from live control state. |
| B26 | BTE | B24 | Implement selected High proof from live control state. |
| B27 | BTE | B25,B26 | After any selection click, reopen/re-read and prove persisted selected state. |
| B28 | TCE | B24-B27 | Fixtures: Chat/Work/Codex, Sol Light/Medium/High, unreadable picker, changed DOM roles. |

## WS5 — Exact attachment and atomic send

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B29 | BTE | B18 | Bind upload proof to active composer/file input/attachment chip only. |
| B30 | BTE | B29 | Remove whole-body filename as sufficient attachment proof. |
| B31 | CFE | B18 | Preserve READY → SENDING → SENT durable delivery ledger with controller-side mirror. |
| B32 | BTE | B31 | Implement `SEND_ATOMIC`: final project/policy/attachment/text proof + exactly one Send click. |
| B33 | BTE | B32 | Post-click prove user delivery marker + target project + stable chat identity. |
| B34 | CFE | B32 | If click may have happened, prohibit sender re-entry until reconciliation. |
| B35 | TCE | B29-B34 | Failure injection before click, during click, after click, before DOM update and after DOM update. |

## WS6 — Condition-driven performance

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B36 | SRE | B18 | Replace fixed browser sleeps with condition waits. |
| B37 | SRE | B36 | Centralize browser/navigation/settle/response budgets in environment configuration. |
| B38 | SRE | B36 | Add per-step duration telemetry and slow-step threshold logging. |
| B39 | TCE | B36-B38 | Test fast UI, delayed hydration, delayed menu, delayed upload and delayed post-send navigation. |
| B40 | SRE | B39 | Establish normal-condition startup target: plan sent in ≤60 s, with stretch target ≤30 s. |

## WS7 — Model-free response observation

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B41 | BTE | B18 | Broker operation `OBSERVE_RESPONSE` returns generation state, latest assistant identity and exact normalized text file/hash. |
| B42 | CFE | B41 | Replace OpenCode Playwright response-identity probe with broker observation. |
| B43 | SIE | B41 | Feed response text/metadata to OpenCode as text-only semantic classification. |
| B44 | SIE | B43 | Harden classifier parser to recover newest valid object and safely retry classification because it has no side effect. |
| B45 | TCE | B41-B44 | Tests for generating, settled, rate limit, malformed classifier output, duplicate semantic inspection and changed rationale. |

## WS8 — Secure action extraction without model browser access

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B46 | BTE | B41 | Broker enumerates fenced blocks with index/SHA/bytes/context metadata for approved assistant turn. |
| B47 | SIE | B46 | Semantic classifier references block index/SHA and target only; never command bytes. |
| B48 | BTE | B47 | Broker `MATERIALIZE_CODE_BLOCK` writes exact textContent bytes to run-scoped file. |
| B49 | CFE | B48 | Reuse existing SHA/length pre-execution verification immediately before execution. |
| B50 | TCE | B46-B49 | Tests for multiple code blocks, quoted historical commands, plan backlog snippets, UTF-8, 12KB+ commands, tampered block/hash. |

## WS9 — Deterministic tool adapters

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B51 | TAE | — | Define typed adapter result schema shared by local/GitHub/VPS/Semaphore. |
| B52 | TAE | B51 | Local adapter returns exit code/stdout/stderr/evidence path with policy validation. |
| B53 | TAE | B51 | GitHub adapter validates exact repo/branch/SHA and transient retry classification. |
| B54 | TAE | B51 | VPS adapter enforces `/opt/ai-loop/bin/vps-ssh` and captures remote exit/evidence. |
| B55 | TAE | B51 | Implement deterministic Semaphore API/CLI collector when credentials are available. |
| B56 | BTE,TAE | B55 | Implement direct browser Semaphore fallback for authenticated web-only evidence; no OpenCode navigation. |
| B57 | TCE | B52-B56 | Contract tests for successful and failed local/GitHub/VPS/Semaphore operations. |

## WS10 — Artifact download / replanning lane

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B58 | BTE | B18 | Move existing deterministic plan-artifact worker behind broker ownership so it reuses the same ChatGPT session. |
| B59 | CFE | B58 | Preserve exact bytes/SHA validator and controller promotion path. |
| B60 | TCE | B58,B59 | Test DOM href, blob, data URL, sandbox URL, existing preview, network response capture and invalid candidate rejection. |

## WS11 — Controller restart, idempotency and state migration

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B61 | CFE | B31,B41,B49 | Define v4.1 state schema/version and migration from v4.0. |
| B62 | CFE | B61 | Reconcile pending delivery/action/CI identities before any resumed side effect. |
| B63 | CFE | B61 | Ensure new-loop mode never adopts historical chat; resume mode restores only its own run/chat identity. |
| B64 | TCE | B61-B63 | Crash/restart matrix at every state transition. |
| B65 | IRA | B64 | Prove zero duplicate sends/actions/pipelines/commits across restart matrix. |

## WS12 — Diagnostics and observability

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B66 | SRE | B18 | On every browser failure save JSON state, HTML, screenshot, URL, project evidence and transition trace. |
| B67 | SRE | B66 | Add one concise failure code plus evidence directory to controller log. |
| B68 | SRE | B38 | Add phase timers: startup, fresh-chat, policy, attachment, send, response, action, CI, GO. |
| B69 | IRA | B66-B68 | Verify diagnostics contain no secrets/tokens/cookies. |

## WS13 — Executable test harness

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B70 | TCE | B06-B69 | Build local fake ChatGPT Projects application with configurable DOM variants and response state machine. |
| B71 | TCE | B70 | Execute complete bootstrap→response→action→evidence→GO against fake app. |
| B72 | TCE | B70 | Add ≥20 UI drift fixtures including current screenshot-equivalent generic URL/project composer state. |
| B73 | TCE | B70 | Add chaos injection for browser crash, navigation timeout, upload delay, lost DOM update and duplicate event. |
| B74 | TCE | B70 | Add fake GitHub/VPS/Semaphore adapters for deterministic full-cycle tests. |
| B75 | TCE | B70-B74 | Run 100 consecutive synthetic full loops; require 100/100 GO and zero duplicates. |

## WS14 — Real integration preflight

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B76 | SRE | B75 | Preflight real ChatGPT login/session, target project visibility, Node/Playwright, plan readability and broker startup. |
| B77 | TAE | B75 | Preflight `git`, `gh`, local repo/branch, VPS wrapper, Semaphore access and required credentials. |
| B78 | TL | B76,B77 | Fail before creating/sending a ChatGPT message if any required capability is unavailable. |

## WS15 — Safe live full-loop canary

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B79 | TL,SIE | B78 | Create a dedicated `AI_LOOP_FULL_ACCEPTANCE_<timestamp>.md` that requests only safe/read-only actions across local, GitHub, VPS and Semaphore, then asks for FINAL_GO. |
| B80 | IRA | B79 | Review canary plan to guarantee it cannot commit, push, deploy or trade. |
| B81 | SRE,TCE | B80 | Launch one brand-new loop in `bot_trading` with the acceptance plan. |
| B82 | IRA | B81 | Require new chat + Chat/Sol/High + attachment + exact one Send. |
| B83 | IRA | B81 | Require at least one successful local adapter action and evidence round-trip. |
| B84 | IRA | B81 | Require at least one successful GitHub read-only adapter action and evidence round-trip. |
| B85 | IRA | B81 | Require at least one successful VPS read-only adapter action and evidence round-trip. |
| B86 | IRA | B81 | Require successful Semaphore status/evidence collection and round-trip. |
| B87 | IRA | B81 | Require at least two controller outbound messages after bootstrap, proving subsequent deterministic Send. |
| B88 | IRA | B81 | Require assistant FINAL_GO and controller independent GO validation. |
| B89 | SRE | B81-B88 | Capture complete performance/evidence bundle and verify no uncaught traceback. |

## WS16 — Actual remediation-plan acceptance

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B90 | TL | B89 | Run preflight against current `feature/GRU` state and the real `IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_20260918T050921Z.md`. |
| B91 | TL,IRA | B90 | Confirm re-entry guard prevents duplicate mutations if plan work already exists. |
| B92 | SRE | B90 | Launch a new production loop with the real plan only after safe canary passes. |
| B93 | IRA | B92 | Observe through required actions/CI/VPS/evidence until FINAL_GO or a genuinely external/human-only blocker. |
| B94 | IRA | B93 | Approve release only if final acceptance matrix is fully green. |

## WS17 — Packaging and release

| Task | Owner | Depends on | Atomic deliverable |
|---|---|---|---|
| B95 | TL | B94 | Bump runtime/version to `4.1.0`; update migration notes and README. |
| B96 | TCE | B95 | Run complete unit/integration/browser/chaos/selftest suite from clean extraction. |
| B97 | SRE | B96 | Verify `install.sh` on clean target and upgrade-from-v4.0 path. |
| B98 | IRA | B97 | Generate SHA-256 manifest and release evidence index. |
| B99 | TL | B98 | Produce `ai-loop-v4.1.tar.gz`; no release if any gate is waived. |

---

# 7. Mandatory test matrix

## 7.1 Unit tests

Must cover:

- project context TARGET/OTHER/UNKNOWN;
- generic URL + target project composer;
- generic URL + no project evidence;
- target URL + wrong selected project;
- fresh draft definition;
- historical chat rejection;
- Chat/Work/Codex selection;
- Sol selected vs merely visible;
- High selected vs merely visible;
- exact attachment proof;
- delivery ledger transitions;
- restart reconciliation;
- action metadata/SHA/length;
- adapter route ownership;
- state migration.

## 7.2 Browser fixture integration

At minimum:

| Scenario | Required result |
|---|---|
| `chatgpt.com/` + `New chat in Bot_trading` + selected target project | TARGET + fresh draft accepted |
| `chatgpt.com/` + generic composer | UNKNOWN; no Send |
| project root restores historical chat | navigate to fresh draft; no historical Send |
| wrong project selected | OTHER; correct project before Send |
| Work selected | switch to Chat and re-prove |
| Sol Light selected | switch to Sol High and re-prove |
| Sol option visible but not selected | must not pass |
| upload input hidden | direct file input/chooser succeeds |
| filename elsewhere in page only | attachment proof fails |
| send click succeeds but URL update delayed | reconcile; no second click |
| browser crashes after click | recover delivery marker; no resend |

## 7.3 Controller integration

A full fake-app cycle must include:

```text
BOOTSTRAP
→ assistant GENERATING
→ assistant OPERATOR_ACTION_REQUESTED
→ exact command materialization
→ local/VPS/GitHub/Semaphore adapter
→ evidence send
→ assistant PLAN_READY or CONTINUE
→ artifact acquisition if requested
→ additional evidence
→ FINAL_GO
```

## 7.4 Chaos tests

Inject:

- browser process kill at every browser state;
- controller SIGTERM at every persisted state;
- network delay/temporary failure;
- GitHub unexpected EOF;
- VPS wrapper timeout;
- Semaphore temporary auth/session expiry;
- malformed OpenCode semantic JSON;
- OpenCode timeout;
- DOM mutation between observation and action;
- duplicate assistant message;
- stale assistant response;
- wrong file hash;
- command tamper;
- rate limit;
- long assistant generation.

Expected:

```text
no duplicate financial/repository/CI side effect
no wrong-project Send
no uncaught traceback
bounded recovery or explicit external blocker
```

## 7.5 Soak

Run:

```text
100 synthetic full loops
```

Required:

```text
100/100 reach GO
0 duplicate sends
0 duplicate actions
0 wrong-project sends
0 lost action payloads
0 uncaught exceptions
```

## 7.6 Live safe canary

One real loop in `bot_trading` must exercise:

```text
ChatGPT browser
OpenCode text-only semantic classifier
local executor
GitHub
VPS wrapper
Semaphore
multiple evidence sends
FINAL_GO
```

No production mutation is allowed in this canary.

## 7.7 Live real-plan acceptance

Only after safe canary GO:

```text
start-loop-v3 IMPLEMENTATION_PLAN_SEMAPHORE_REMEDIATION_20260918T050921Z.md
```

The run must finish at independently validated GO or a clearly external/human-only blocker. A controller/parser/browser defect is not an acceptable blocker.

---

# 8. Performance acceptance

Normal healthy-session targets:

| Metric | Target |
|---|---:|
| controller start → broker healthy | ≤5 s |
| broker healthy → target fresh draft proven | ≤15 s |
| fresh draft → Chat/Sol/High proven | ≤10 s |
| policy ready → attachment/text ready | ≤10 s |
| ready → Send click | ≤5 s |
| total healthy startup → plan sent | ≤60 s, stretch ≤30 s |
| redundant Chrome launches during one normal turn | 0 |
| OpenCode browser/MCP launches for ChatGPT UI | 0 |
| blind fixed sleeps >1 s in browser normal path | 0 |

Timing failures do not permit unsafe shortcuts.

---

# 9. Release gates

| Gate | Requirement |
|---|---|
| G0 | Context/evidence frozen |
| G1 | Canonical project identity tests green |
| G2 | Single browser-owner broker green |
| G3 | Fresh-chat + Chat/Sol/High green |
| G4 | Attachment + atomic Send green |
| G5 | Model-free response observation green |
| G6 | Secure action extraction/materialization green |
| G7 | local/GitHub/VPS/Semaphore adapter contracts green |
| G8 | restart/idempotency/chaos matrix green |
| G9 | 100/100 synthetic full-loop soak green |
| G10 | real safe full-loop canary reaches FINAL_GO |
| G11 | actual remediation-plan run reaches validated GO or only an external human blocker |
| G12 | independent release audit approves evidence bundle |

No gate may be skipped because prior unit tests passed.

---

# 10. Acceptance log contract

A successful healthy bootstrap should look conceptually like:

```text
ai-loopd-v3 version=4.1.0 run=...
BROWSER_BROKER=PASS epoch=...
PROJECT_CONTEXT PASS project=bot_trading evidence=...
FRESH_PROJECT_DRAFT PASS turns=0
CHAT_SURFACE PASS surface=chat
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high
ATTACHMENT_GUARD PASS filename=...
DELIVERY_READY id=...
DELIVERY_SENT id=... chat=...
DELIVERY_PROOF PASS id=...
```

Later turns should include:

```text
ASSISTANT_OBSERVER SETTLED message_id=... sha=...
SEMANTIC_EVENT ...
ACTION_MATERIALIZED id=... bytes=... sha=...
ACTION_EXECUTED id=... target=...
EVIDENCE_SENT id=...
CI_EVIDENCE ...
FINAL_GO_VALIDATED sha=...
AI_LOOP_COMPLETE=GO
```

The following must not recur:

```text
FRESH_PROJECT_WRONG_PROJECT
ADAPTIVE_PLAYWRIGHT_PROOF_MISSING
FRESH_PROJECT_CHAT ... UNVERIFIED
CHATGPT_AMBIGUOUS_SEND_UNRESOLVED
ACTION_PAYLOAD_BASE64_INVALID
ACTION_PAYLOAD_UTF8_INVALID
ACTION_PAYLOAD_SHA256_MISMATCH
implicit local->vps
duplicate delivery
uncaught traceback
```

---

# 11. Pre-mortem — deliberate mode

## Failure scenario 1 — ChatGPT changes project UI again

**Failure:** selectors change and project identity becomes UNKNOWN.

**Mitigation:** canonical multi-signal project resolver, versioned locator registry, HTML fixture capture, no URL-only assumption, diagnostics on UNKNOWN, model may propose selector discovery but cannot authorize Send.

**Detection:** project resolver outputs signal-by-signal evidence.

## Failure scenario 2 — browser/controller dies immediately after Send

**Failure:** delivery happens but state is not persisted; restart could duplicate.

**Mitigation:** durable READY/SENDING ledger before click, unique marker, read-only reconciliation before any retry, browser local storage + controller state + DOM marker.

**Detection:** restart test at every send transition.

## Failure scenario 3 — tool chain works individually but full loop deadlocks

**Failure:** ChatGPT response, action execution, Semaphore/VPS evidence and follow-up sends each pass alone but FSM never reaches GO.

**Mitigation:** synthetic full-loop harness + 100-run soak + mandatory real safe canary that exercises every adapter + actual remediation-plan run before release.

**Detection:** phase timer + transition trace + bounded no-progress watchdog that captures evidence rather than blindly restarting.

---

# 12. ADR

## Decision

Adopt a **single persistent deterministic Browser Transport Broker** for all ChatGPT Web interaction, while restricting OpenCode to browser-free semantic reasoning.

## Drivers

- repeated proof/parser/selector regressions across v2.32–v4.0;
- latest v4.0 false negative caused by URL-as-project assumption;
- unacceptable latency from repeated browser/model ownership handoffs;
- requirement for an unattended end-to-end loop.

## Alternatives considered

1. patch the latest project selector only;
2. keep one-shot direct Playwright workers;
3. persistent broker + text-only model reasoning.

## Chosen

Option 3.

## Consequences

Positive:

- one browser owner;
- no OpenCode/MCP profile conflict for ChatGPT;
- faster state transitions;
- stronger project and policy proof;
- simpler restart/idempotency model;
- browser bytes remain deterministic.

Costs:

- new broker lifecycle/RPC code;
- larger migration and test surface;
- requires explicit broker restart/reconciliation logic.

## Follow-ups

- consider moving Semaphore browser access to a separate deterministic broker if API/CLI is unavailable;
- version DOM locator/evidence schema independently from controller release;
- preserve fixture corpus for every future UI change.

---

# 13. Consensus review

## Planner conclusion

The latest failure is not evidence that direct Playwright is the wrong direction; it shows the remaining verifier still encodes an invalid URL invariant. A patch-only release is insufficient because browser ownership is still split later in the loop.

## Architect review

**Strongest counterargument:** a persistent broker is more code and may introduce its own lifecycle bugs. One-shot workers are easier to reason about because each process starts clean.

**Tradeoff tension:** process isolation/simplicity versus cross-turn continuity/performance.

**Synthesis:** keep operations stateless at the RPC-contract level while the broker owns only browser/session continuity. Persist all authoritative state in Python/run files, not solely inside the broker. If the broker dies, Python recreates it and reconciles from persisted state + DOM before any side effect.

**Verdict:** APPROVE with mandatory broker-crash/restart tests.

## Critic review

The plan is acceptable only if “successful” is measured by an executable end-to-end run rather than source assertions. Project identity needs both positive and negative fixtures, and the safe live canary must exercise every adapter.

**Verdict:** APPROVE after inclusion of G9/G10/G11 and the 100-run soak.

---

# 14. Execution guidance

## `/team` implementation

Recommended parallel lanes:

```text
Lane A: BTE — WS1/WS2/WS3/WS4/WS5
Lane B: CFE — WS3/WS5/WS7/WS11
Lane C: SIE — WS7/WS8
Lane D: TAE — WS9
Lane E: TCE — tests/fixtures/chaos continuously
Lane F: SRE — lifecycle/performance/diagnostics
Lane G: IRA — invariant and evidence review
TL coordinates integration and release gates
```

Suggested launch:

```text
/team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_1_FULL_LOOP_RELIABILITY_20260922T0010-0500.md
```

## `team → ralph` verification path

After the implementation team reports completion, run a separate sequential verifier:

```text
/ralph verify every invariant, release gate, executable test, safe live canary evidence and actual remediation-plan GO evidence from IMPLEMENTATION_PLAN_AI_LOOP_V4_1_FULL_LOOP_RELIABILITY_20260922T0010-0500.md; do not modify code unless a verification failure is first proven
```

The release is accepted only after the independent verification confirms G0–G12.

---

# 15. Definition of Done

`ai-loop v4.1.0` is Done only when:

```text
all deterministic unit/browser/integration tests PASS
100/100 synthetic full loops reach GO
safe real bot_trading full-loop canary reaches FINAL_GO
all required adapters were actually exercised
actual remediation-plan loop reaches validated GO or only a genuine external human-only blocker
no wrong-project message
no duplicate send
no duplicate operator action
no duplicate commit/push/pipeline/deployment
no payload integrity failure
no uncaught traceback
complete evidence bundle archived
independent release auditor approves G0–G12
```

Anything less is a release candidate, not a completed remediation.
