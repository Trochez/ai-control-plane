# IMPLEMENTATION PLAN — ai-loop v4.4 Live End-to-End Reliability, Attachment Proof, Hydration Safety & Mandatory Full-Loop GO

**Generated:** 2026-09-22T12:52-05:00  
**Current baseline:** ai-loop `v4.3.0`  
**Target release:** ai-loop `v4.4.0`  
**Control-plane repository:** `/mnt/d/works/ai-control-plane`  
**Runtime install root:** `/opt/ai-loop`  
**Primary daemon:** `/opt/ai-loop/ai-loopd-v3.py`  
**Primary browser broker:** `/opt/ai-loop/browser-broker-v1.cjs`  
**Target ChatGPT project:** `bot_trading`  
**Target repository:** `Trochez/bot_trading`  
**Target branch:** `feature/GRU`  
**Observed run:** `R20260922T042847`  
**Observed baseline SHA:** `44505ddbfa5062dc1c712fc90db72cb0c54de924`  
**Mandatory objective:** finish at least one real, unattended, end-to-end loop at independently validated `FINAL_GO`, exercising every tool/integration required by the loop.  
**Release rule:** the implementation team MUST keep diagnosing, fixing, regression-testing and re-running live acceptance until the loop succeeds. A known controller/browser/parser/tool bug is not an acceptable final blocker.

---

# 0. Execution contract

This plan is not complete when code compiles, when unit tests pass, or when bootstrap reaches Send.

The implementation is complete only after all of the following are simultaneously true:

1. a brand-new run starts successfully on the Ubuntu execution machine;
2. a new, empty, clean draft is proven inside `bot_trading`;
3. normal Chat is proven;
4. GPT-5.6 Sol + High policy is proven using the current live UI contract;
5. the exact `.md` plan is attached exactly once;
6. the exact controller message is sent exactly once;
7. the assistant response is observed to settlement;
8. semantic classification succeeds without giving the LLM browser authority;
9. requested operator actions are extracted without transcribing command bytes through the LLM;
10. local actions work;
11. GitHub evidence works;
12. VPS actions/evidence work through the controller-owned wrapper;
13. Semaphore/CI evidence works;
14. result evidence is returned to the same chat;
15. additional controller-to-chat turns work after bootstrap;
16. artifact download/replan works if exercised;
17. restart/reconciliation does not duplicate any side effect;
18. CI state is bound to the exact candidate SHA;
19. final ChatGPT `GO` is independently validated;
20. the controller ends at `AI_LOOP_COMPLETE=GO` / equivalent durable DONE state with no uncaught Python or Node traceback.

If any live test exposes a new bug, the team MUST:

```text
capture evidence
→ isolate root cause
→ add a deterministic regression reproducer
→ implement the fix
→ rerun local/unit/integration/chaos tests
→ rerun the live canary from a clean run
→ continue until FINAL_GO
```

The team must not stop at “next bug found”.

---

# 1. Grounded pre-context snapshot

## 1.1 Latest observed production/canary behavior

The latest v4.3 run reached:

```text
PROJECT_CONTEXT PASS project=bot_trading
FRESH_PROJECT_DRAFT PASS turns=0
CHAT_SURFACE PASS surface=chat
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high
```

This proves the previous project identity and Sol/High failures were successfully cleared.

The run then failed before Send:

```text
BROWSER_BROKER_ATTACH_FILE_FAILED:WAIT_TIMEOUT:attachment_proof
```

The controller exited with:

```text
CHATGPT_DETERMINISTIC_BOOTSTRAP_FAILED_NO_SEND:
BROWSER_BROKER_ATTACH_FILE_FAILED:WAIT_TIMEOUT:attachment_proof
```

Therefore the current defect is still pre-send and did not produce a ChatGPT user turn.

## 1.2 Evidence from the real ATTACH_FILE diagnostic

The actual diagnostic captured after the timeout proves that the attachment **was already visible in the live ChatGPT composer**.

The state includes controls with:

```text
aria="AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md"
aria="Remove AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md"
```

The captured HTML contains the exact live structure:

```html
<form
  data-composer-placement="home"
  data-chatgpt-composer=""
  data-thread-find-composer="true">

  ...

  <div
    class="ComposerLayoutAttachments-..."
    data-composer-attachments=""
    data-visible-attachments="">

    ...

    <span class="truncate">
      AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md
    </span>

    <button
      class="composer-attachment-surface ..."
      aria-label="AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md">
    </button>

    <button
      aria-label="Remove AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md">
    </button>
  </div>

  ...

  <div class="ComposerLayoutInput-...">
    <div
      contenteditable="true"
      aria-label="New chat in Bot_trading">
    </div>
  </div>
</form>
```

This establishes a confirmed false negative:

```text
physical upload = SUCCESS
UI attachment chip = PRESENT
attachment verifier = FALSE
result = WAIT_TIMEOUT
```

## 1.3 Confirmed root cause in v4.3 attachment proof

Current `browser-broker-v1.cjs` uses approximately:

```javascript
const cp = await this.composer();

const root = cp.locator(
  'xpath=ancestor::*[' +
  'self::form or ' +
  '@data-testid="composer" or ' +
  'contains(@class,"composer")' +
  '][1]'
);

const r = (await root.count()) ? root : this.page.locator('main');

return await r.getByText(fileName, {exact:false}).count() > 0;
```

The nearest ancestor matching `contains(@class,"composer")` is allowed to be a narrow inner element such as:

```text
ComposerLayoutInput-...
```

The real attachment region is a **sibling** of that input under the outer:

```text
form[data-chatgpt-composer]
```

Therefore the proof searches the wrong scope and cannot see the attachment chip.

The current fallback also checks:

```javascript
input[type=file].files
```

but ChatGPT may consume/clear the file input after upload, so that state is not a durable post-upload proof.

## 1.4 Additional attachment risk: ambiguous file input selection

The captured live HTML contains multiple file inputs:

```html
<input accept="image/*,video/*" aria-label="Attach photos or videos" ... type="file">
<input accept="image/*" aria-label="Attach photos" ... type="file">
<input aria-label="Attach files" ... type="file">
```

Current v4.3 code selects:

```javascript
this.page.locator('input[type="file"]').first()
```

This is not semantically safe.

The file-specific input should be preferred explicitly:

```text
aria-label = Attach files
```

or selected through a compatibility resolver.

## 1.5 Confirmed policy-hydration race

The first v4.3 attempt failed with:

```text
CHAT_SURFACE_CONTROL_NOT_FOUND
```

but the diagnostic state captured immediately afterward already contained:

```text
Chat selected=true
High
data-selected-reasoning-effort="high"
```

The next bootstrap attempt then immediately passed:

```text
CHAT_SURFACE PASS
MODEL_GUARD PASS
```

Current `ensurePolicy()` does this:

```javascript
state = await policyState();

if (!state.chat) {
    if (!(await clickMatching(/^Chat$/i)))
        throw new Error('CHAT_SURFACE_CONTROL_NOT_FOUND');
}
```

It does not wait for the Chat surface controls to hydrate before declaring failure.

This is a classic time-of-check/hydration race.

## 1.6 Newly exposed stale-draft risk

A failed run can now leave an unsent attachment in a draft.

Current fresh-draft proof is essentially:

```text
project TARGET
+ turns == 0
+ composer exists
```

That is insufficient.

A draft with:

```text
0 turns
+ stale composer text
or
+ stale attachment(s)
```

is not a clean new draft.

A new run must never inherit an unsent plan from a previous failed run.

## 1.7 Retry-idempotency risk

`start_new_chat()` retries the complete pre-send bootstrap when the broker reports a safe pre-send failure.

If `ATTACH_FILE` physically succeeded but proof falsely failed, a subsequent retry can attempt the attachment operation again.

Therefore attachment itself must be idempotent:

```text
observe exact current attachment state first
→ if exact expected attachment already exists, return ALREADY_ATTACHED
→ never attach a duplicate
```

## 1.8 Post-bootstrap scope remains mandatory

The latest run still has not exercised the complete real path after Send.

The implementation team must therefore treat these as **unproven live paths until tested in the same acceptance campaign**:

- post-send delivery proof;
- assistant settling;
- semantic classification;
- exact fenced-block extraction;
- local operator execution;
- GitHub evidence;
- VPS wrapper;
- Semaphore evidence;
- evidence delivery back to ChatGPT;
- further ChatGPT turns;
- CI polling;
- replan/artifact acquisition if invoked;
- final GO validation;
- restart recovery around side effects.

The implementation must not finish after merely clearing `ATTACH_FILE`.

---

# 2. RALPLAN-DR summary

## 2.1 Principles

1. **Evidence over inference.** Real DOM/UI evidence is authoritative for browser-state bugs.
2. **Side effects must be idempotent.** Attach, Send, operator action, CI trigger and any external mutation must reconcile before retry.
3. **Hydration is a state, not an error.** Missing transient controls must be condition-waited within bounded budgets before failure.
4. **One browser owner.** The persistent deterministic Browser Broker remains the sole physical owner of ChatGPT Web.
5. **Release requires live end-to-end GO.** No partial bootstrap milestone is a release criterion.

## 2.2 Top decision drivers

1. Eliminate the exact attachment false negative proven by the real v4.3 DOM.
2. Prevent the next class of stale-draft, duplicate-attachment and hydration-race failures.
3. Force implementation to continue through every remaining live stage until the complete loop reaches validated GO.

## 2.3 Viable options

### Option A — Patch only the attachment selector

Change attachment proof to:

```javascript
page.getByText(fileName)
```

or add:

```javascript
[aria-label="<filename>"]
```

**Pros**
- tiny change;
- likely clears the immediate timeout.

**Cons**
- can match historical/body text outside the active composer;
- leaves ambiguous file input selection;
- leaves duplicate-attachment retry risk;
- leaves stale draft acceptance;
- leaves policy hydration race;
- still does not validate post-Send paths.

**Disposition:** REJECTED.

---

### Option B — Canonical composer-state resolver + idempotent attachment transaction + hydration-safe policy + mandatory live convergence

Create one canonical representation of the active composer and use it for:

- project/draft cleanliness;
- attachment enumeration;
- upload readiness;
- text readiness;
- Send gating.

Then make attachment a proper idempotent transaction and fix policy hydration.

After local test completion, enter a mandatory live test/fix loop until the whole controller reaches GO.

**Pros**
- addresses confirmed root cause;
- prevents stale-draft inheritance;
- prevents duplicate attachments;
- reduces selector drift;
- turns current diagnostics into executable regression tests;
- directly satisfies the full-loop objective.

**Cons**
- larger change than a selector patch;
- requires careful current-run/resume semantics.

**Disposition:** **CHOSEN**.

---

### Option C — Stop attaching `.md` files and paste the plan text

**Pros**
- bypasses attachment UI.

**Cons**
- breaks the artifact/byte-integrity architecture;
- reintroduces large text transport through UI;
- weakens reproducibility and hashing;
- does not test artifact download/upload path required by the project.

**Disposition:** REJECTED.

---

### Option D — Use a separate browser automation path only for upload

**Pros**
- isolates upload logic.

**Cons**
- violates the single-browser-owner principle;
- reintroduces profile contention and synchronization problems solved in v4.1+.

**Disposition:** REJECTED.

---

# 3. Target v4.4 architecture

v4.4 keeps the persistent broker architecture and strengthens it:

```text
Python controller
      │
      ▼
Persistent Browser Broker
      │
      ├── canonical project resolver
      ├── canonical active composer resolver
      ├── clean-draft verifier
      ├── hydration-aware Chat/Sol/High policy
      ├── idempotent attachment transaction
      ├── exact composer fill
      ├── atomic Send
      ├── assistant observer
      ├── block materialization
      ├── artifact download
      └── Semaphore read-only browser fallback
      │
      ▼
ChatGPT Web

OpenCode:
  semantic reasoning only
  no ChatGPT browser ownership
  no command bytes as authority
```

---

# 4. Canonical active-composer model

Introduce a single broker method:

```text
resolveActiveComposer()
```

It must return a structured state:

```json
{
  "present": true,
  "root_selector_kind": "data-chatgpt-composer",
  "project_name": "Bot_trading",
  "editable_visible": true,
  "composer_text": "",
  "attachments": [
    {
      "name": "AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md",
      "name_control": true,
      "remove_control": true,
      "uploading": false,
      "error": false
    }
  ],
  "send_present": true,
  "send_enabled": false
}
```

## 4.1 Root selection priority

The active composer root must be resolved in this order:

1. visible:

```css
form[data-chatgpt-composer]
```

containing the selected/visible composer;

2. visible ancestor with:

```css
[data-composer-body]
```

or equivalent known outer composer container;

3. nearest visible `<form>` containing both:
   - the active editor;
   - composer footer or attachment region;

4. only if no semantic outer root exists, fail explicitly:

```text
ACTIVE_COMPOSER_ROOT_UNPROVEN
```

Do **not** use generic:

```text
contains(@class, "composer")
```

as the first/authoritative root.

## 4.2 Attachment enumeration

Inside the resolved composer root, enumerate attachments using multiple signals:

- `[data-composer-attachments]`;
- `[data-visible-attachments]`;
- `.composer-attachment-surface`;
- exact `aria-label="<filename>"`;
- exact `aria-label="Remove <filename>"`;
- visible filename text inside the attachment region.

The enumeration must not accept matching text outside the active composer root.

---

# 5. Attachment transaction contract

Add broker operation semantics:

```text
ATTACH_FILE
```

with arguments:

```json
{
  "path": "...",
  "name": "...",
  "sha256": "...",
  "bytes": 12345,
  "deliveryId": "..."
}
```

## 5.1 Pre-attachment reconciliation

Before selecting a file:

```text
resolve active composer
→ enumerate attachments
→ if exact expected file already attached:
       verify no upload error
       return ALREADY_ATTACHED
→ if stale/conflicting attachment exists:
       do not Send
       normalize according to new-run/resume rules
→ otherwise upload
```

## 5.2 Input resolver

Preferred file input order:

1. visible/hidden input whose accessible label matches:

```text
Attach files
Upload files
Files
```

and whose `accept` permits `.md` or is unrestricted;

2. unrestricted:

```css
input[type=file]:not([accept])
```

3. input whose accept list is compatible with the target MIME/extension;

4. deterministic filechooser route after clicking `Add files and more`.

Do not choose the first generic file input blindly.

## 5.3 Post-upload proof

Post-upload success requires:

```text
active composer root proven
+ exact expected attachment name in attachment region
+ exact attachment surface/control OR exact remove control
+ no upload-error signal
+ attachment count for expected filename == 1
```

A cleared `input.files` is allowed after upload.

The following are insufficient alone:

```text
filename anywhere in body
filename in history
filename in another project/chat
input file value before UI adoption
```

## 5.4 Attachment ledger

Persist a run/delivery-scoped attachment ledger:

```json
{
  "delivery_id": "...",
  "filename": "...",
  "source_path": "...",
  "source_sha256": "...",
  "source_bytes": 12345,
  "ui_status": "ATTACHED",
  "attached_at": "...",
  "broker_epoch": "..."
}
```

On retry:

```text
ledger + exact active-composer UI proof
→ ALREADY_ATTACHED
```

No second `setInputFiles()`.

---

# 6. Clean fresh-draft contract

Upgrade fresh-draft definition to require:

```text
project_context == TARGET
user_turn_count == 0
assistant_turn_count == 0
composer visible/editable
composer text == empty
attachment count == 0
no pending upload/error
no current-run or stale delivery marker in composer
```

## 6.1 New run

A new run MUST NOT adopt an unsent draft left by an earlier failed run.

If target project has:

```text
0 turns
but composer text != empty
or attachments != 0
```

the broker must:

1. classify it as:

```text
STALE_UNSENT_DRAFT
```

2. create or reset to a genuinely clean project draft;
3. prove the clean state before continuing.

## 6.2 Resume same run

A resumed run may adopt a pre-send draft only when persisted ledger and UI state agree exactly on:

```text
run_id
delivery_id
filename
attachment hash metadata
composer text/delivery marker
```

Otherwise fail closed and reconcile.

---

# 7. Hydration-safe policy contract

Replace immediate control-not-found failures with bounded semantic waits.

## 7.1 Chat surface

Current behavior:

```text
policyState()
→ no chat yet
→ clickMatching(Chat)
→ if not found, immediate error
```

Target behavior:

```text
wait for one of:
    selected Chat
    visible Chat/Work surface switcher
    explicit terminal evidence surface is unavailable

if selected Chat:
    PASS

if Work/Codex selected and Chat control exists:
    click Chat
    wait until selected Chat

if timeout:
    CHAT_SURFACE_HYDRATION_TIMEOUT
```

## 7.2 Reasoning/Sol

Likewise:

```text
wait for reasoning trigger
→ read data-selected-reasoning-effort
→ if high: PASS
→ otherwise open selector
→ select High
→ re-read persisted state
```

Do not consume a whole outer bootstrap retry merely because React had not hydrated a control for a few hundred milliseconds.

## 7.3 Diagnostic timeline

Every browser operation that waits for hydration should record a compact transition timeline:

```json
[
  {"t_ms":0, "chat_control":false, "reasoning_trigger":false},
  {"t_ms":320, "chat_control":true, "chat_selected":true},
  {"t_ms":420, "reasoning":"high"}
]
```

This lets future failures distinguish:

```text
control never existed
from
control appeared after initial check
```

---

# 8. Bootstrap should become step-resumable before Send

Current outer retry re-runs the full bootstrap.

v4.4 should persist deterministic pre-send milestones:

```text
FRESH_DRAFT_PROVEN
POLICY_PROVEN
ATTACHMENT_PROVEN
COMPOSER_TEXT_PROVEN
READY_TO_SEND
```

If a safe pre-send operation fails, the next retry should reconcile from observed browser state rather than replay all previous actions.

Example:

```text
attachment upload succeeded
proof layer crashed
→ retry
→ observe attachment already present
→ mark ATTACHMENT_PROVEN
→ continue to FILL_COMPOSER
```

Do not reattach.

---

# 9. Mandatory bootstrap invariants

Before Send:

| Invariant | Required |
|---|---|
| Project | `TARGET` |
| Historical turns | 0 |
| Draft text before fill | empty |
| Stale attachments before current attach | 0 |
| Surface | Chat selected |
| Model contract | GPT-5.6 Sol |
| Reasoning | High |
| Expected attachment count | exactly 1 |
| Expected attachment name | exact |
| Upload error | none |
| Controller message | exact |
| Delivery ID | unique |
| Send control | present and enabled |
| Side-effect ledger | `READY` |

Send is forbidden if any invariant is unknown.

---

# 10. Full-loop hardening beyond bootstrap

The team MUST audit and live-test every stage that has not yet been reached by v4.3.

## 10.1 Delivery proof

After click:

```text
delivery marker must become a user turn
project must remain TARGET
conversation identity must stabilize
delivery ledger must become SENT
```

No blind second click.

## 10.2 Assistant observer

Prove transitions:

```text
NO_ASSISTANT
→ GENERATING
→ SETTLED
```

or:

```text
RATE_LIMIT
```

with bounded polling and no partial-message authority.

## 10.3 Semantic classifier

OpenCode receives text/metadata only.

Parser must tolerate malformed first responses by safely reclassifying because classification itself has no side effect.

## 10.4 Code-block materialization

Block selection:

```text
message id
+ block index
+ expected SHA
+ expected bytes
```

Broker returns exact DOM text bytes.

Controller re-hashes immediately before execution.

## 10.5 Operator actions

Live acceptance must exercise:

- local command;
- GitHub read-only query;
- VPS wrapper command;
- Semaphore evidence query.

Every action must persist an immutable receipt.

## 10.6 Evidence return

At least two controller-originated post-bootstrap messages must successfully return to the same chat.

This proves deterministic Send is not only functional for bootstrap.

## 10.7 CI path

CI observation must bind:

```text
provider
candidate SHA
run id
pipeline id
```

No generic “green” interpretation.

## 10.8 Artifact/replan path

If the canary or real loop asks for a plan artifact, verify:

```text
download
bytes
UTF-8
SHA
plan structure
```

before opening a new implementation iteration.

## 10.9 Final GO

Accept GO only if:

```text
candidate_sha exists
remote HEAD == candidate_sha
CI(candidate_sha) == SUCCESS
assistant final event == FINAL_GO
```

---

# 11. Team

**Team size: 9**

| Role | Code | Responsibility |
|---|---|---|
| Technical Lead / Orchestrator | TL | Scope, architecture, integration order, release authority |
| Browser Broker Engineer | BBE | Playwright broker, active composer, upload, hydration, Send |
| Controller/FSM Engineer | CFE | Python state machine, milestones, restart/reconciliation |
| DOM & Attachment Verification Engineer | DAVE | real-DOM fixtures, semantic locators, attachment proof |
| Semantic/OpenCode Engineer | SOE | text-only semantic classification and block references |
| Tool Adapter Engineer | TAE | local/GitHub/VPS/Semaphore adapters |
| Test & Chaos Engineer | TCE | executable fixtures, failure injection, 100-run soak |
| SRE / Live Validation Engineer | SRE | Ubuntu live tests, performance, diagnostics, repeated canaries |
| Independent Release Auditor | IRA | invariant audit, evidence review, final GO/release gate |

## Reasoning guidance

- TL / BBE / CFE / IRA: high reasoning
- DAVE / TCE: high on failure-path design, medium on mechanical fixture implementation
- SOE / TAE: medium-high
- SRE: medium-high, high during live incident diagnosis

No task may be marked complete solely from another worker's textual claim; its acceptance evidence must be inspectable.

---

# 12. Atomic backlog

## WS0 — Freeze evidence and baseline

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B001 | TL | — | Create `.omx/context/ai-loop-v44-live-loop-<UTC>.md` containing this task statement, observed run, exact failure, acceptance objective and source touchpoints. |
| B002 | IRA | B001 | Record SHA-256 manifest of the v4.3 source tree before changes. |
| B003 | DAVE | B001 | Extract a **minimal sanitized** fixture from `R20260922T042847` containing only the active composer, Chat/Work controls, project selector, reasoning trigger and attachment region. Do not commit unrelated sidebar/history data. |
| B004 | TCE | B003 | Store the observed `ATTACH_FILE WAIT_TIMEOUT` log as a regression fixture. |
| B005 | TCE | B003 | Store the observed `CHAT_SURFACE_CONTROL_NOT_FOUND` + later selected Chat state as a hydration-race fixture. |

---

## WS1 — Canonical active composer

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B006 | DAVE | B003 | Define `resolveActiveComposer()` schema and positive/negative evidence. |
| B007 | BBE | B006 | Implement priority selection of `form[data-chatgpt-composer]` containing the active editor. |
| B008 | BBE | B007 | Add fallback to a semantic outer composer container only when the form signal is absent. |
| B009 | BBE | B008 | Remove generic nearest `contains(@class,"composer")` as authoritative root selection. |
| B010 | DAVE | B007 | Enumerate attachment regions only inside the resolved composer root. |
| B011 | DAVE | B010 | Enumerate exact attachment name control, remove control, visible label, upload/error state. |
| B012 | TCE | B006-B011 | Add unit tests using the exact minimized R20260922T042847 DOM. |
| B013 | IRA | B012 | Audit that attachment proof cannot be satisfied by history/sidebar/body text outside active composer. |

---

## WS2 — Idempotent attachment transaction

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B014 | CFE | B006 | Extend broker ATTACH_FILE request with `deliveryId`, local SHA-256 and byte length. |
| B015 | BBE | B014 | Implement pre-upload attachment reconciliation. |
| B016 | BBE | B015 | Return `ALREADY_ATTACHED` when one exact expected attachment already exists in active composer. |
| B017 | BBE | B015 | Detect and fail/normalize duplicate expected attachments before Send. |
| B018 | DAVE | B015 | Implement input compatibility resolver preferring `aria-label="Attach files"` / unrestricted file input. |
| B019 | BBE | B018 | Replace `.first()` generic file input selection with compatibility resolver. |
| B020 | BBE | B019 | Preserve filechooser fallback through `Add files and more`. |
| B021 | BBE | B020 | Implement post-upload proof from attachment region; do not require durable `input.files`. |
| B022 | BBE | B021 | Require exact expected attachment count == 1 and no upload error. |
| B023 | CFE | B021 | Persist attachment ledger keyed by run + delivery id. |
| B024 | CFE | B023 | On retry/resume, reconcile ledger + UI before deciding to upload. |
| B025 | TCE | B014-B024 | Test direct file input path with Markdown file. |
| B026 | TCE | B014-B024 | Test filechooser path. |
| B027 | TCE | B014-B024 | Test input cleared after upload while chip remains; must PASS. |
| B028 | TCE | B014-B024 | Test exact filename appearing only outside composer; must FAIL. |
| B029 | TCE | B014-B024 | Test existing exact attachment on retry; no second upload. |
| B030 | TCE | B014-B024 | Test duplicate attachment state; Send must remain fenced. |
| B031 | IRA | B025-B030 | Review attachment transaction against zero-duplicate invariant. |

---

## WS3 — Clean draft and stale-unsent-state handling

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B032 | CFE | B006 | Expand fresh-draft state to include composer text and attachment count. |
| B033 | BBE | B032 | Require empty composer text for a brand-new run. |
| B034 | BBE | B032 | Require zero attachments before current-run attachment. |
| B035 | BBE | B032 | Detect `STALE_UNSENT_DRAFT` when 0 turns but text/attachment remains. |
| B036 | BBE | B035 | Implement deterministic clean-draft reset/recreation for a new run. |
| B037 | CFE | B035 | Implement same-run resume exception only when delivery/attachment ledger matches observed draft. |
| B038 | TCE | B032-B037 | Test new run starting after v4.3 crash with the old canary file still attached. |
| B039 | TCE | B032-B037 | Test stale composer text without turns. |
| B040 | TCE | B032-B037 | Test valid same-run resume of a prepared unsent draft. |
| B041 | IRA | B038-B040 | Confirm no new run can inherit previous unsent plan/text. |

---

## WS4 — Hydration-safe Chat/Sol/High policy

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B042 | BBE | B005 | Add `waitForSurfaceHydration()` before declaring Chat control missing. |
| B043 | BBE | B042 | If Chat becomes selected during wait, return PASS without clicking. |
| B044 | BBE | B042 | If Work/Codex is selected and Chat becomes available, click and re-prove selected Chat. |
| B045 | BBE | B042 | Return a dedicated hydration timeout only after the configured budget. |
| B046 | BBE | B042 | Add `waitForReasoningHydration()` for reasoning trigger. |
| B047 | BBE | B046 | Preserve current High→Sol contract proof when High is selected. |
| B048 | SRE | B042,B046 | Add operation-local hydration timeline to diagnostics. |
| B049 | TCE | B042-B048 | Test Chat control appearing after 100 ms. |
| B050 | TCE | B042-B048 | Test Chat control appearing after 2 s. |
| B051 | TCE | B042-B048 | Test permanent missing Chat control; must timeout safely. |
| B052 | TCE | B046-B048 | Test delayed High/reasoning trigger. |
| B053 | IRA | B049-B052 | Confirm outer bootstrap retry is not consumed by normal UI hydration. |

---

## WS5 — Pre-send milestone reconciliation

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B054 | CFE | B014,B032,B042 | Define pre-send milestones: `FRESH_DRAFT_PROVEN`, `POLICY_PROVEN`, `ATTACHMENT_PROVEN`, `TEXT_PROVEN`, `READY_TO_SEND`. |
| B055 | CFE | B054 | Persist milestone state after each proof. |
| B056 | CFE | B055 | On safe pre-send retry, reconcile observed browser state before replaying an action. |
| B057 | CFE | B056 | Do not reattach if attachment milestone reconciles successfully. |
| B058 | CFE | B056 | Do not rewrite identical composer text unnecessarily. |
| B059 | BBE | B054 | Gate `SEND_ATOMIC` on all milestones + live final proof in one broker transaction. |
| B060 | TCE | B054-B059 | Inject failure after physical upload but before proof response; retry must continue without duplicate attachment. |
| B061 | TCE | B054-B059 | Inject failure after text fill but before READY_TO_SEND; reconcile safely. |
| B062 | IRA | B060-B061 | Verify no safe pre-send retry creates duplicate UI state. |

---

## WS6 — Delivery and post-send proof

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B063 | BBE | B059 | Re-audit Send button resolver against current live composer root. |
| B064 | BBE | B063 | Before click, prove exact delivery marker text and expected attachment still present. |
| B065 | CFE | B063 | Persist `READY` → `SENDING` before click. |
| B066 | BBE | B065 | Perform exactly one Send click. |
| B067 | BBE | B066 | Observe exact delivery marker as user turn. |
| B068 | BBE | B067 | Prove project still TARGET after Send. |
| B069 | CFE | B067 | Persist `SENT` only after user-turn proof. |
| B070 | CFE | B066 | If click may have occurred and proof is missing, transition to ambiguity reconciliation; never blind resend. |
| B071 | TCE | B063-B070 | Test crash immediately before click. |
| B072 | TCE | B063-B070 | Test crash immediately after click. |
| B073 | TCE | B063-B070 | Test delayed `/c/` navigation after successful user turn. |
| B074 | IRA | B071-B073 | Approve zero-duplicate Send evidence. |

---

## WS7 — Response observation and semantic classification

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B075 | BBE | B067 | Verify `OBSERVE_RESPONSE` handles NO_ASSISTANT→GENERATING→SETTLED. |
| B076 | BBE | B075 | Verify rate-limit detection and bounded backoff. |
| B077 | SOE | B075 | Verify OpenCode receives only normalized assistant text + bounded metadata. |
| B078 | SOE | B077 | Harden semantic parser to select newest valid classification object. |
| B079 | SOE | B078 | Safe retry classification on malformed model output without browser side effect. |
| B080 | TCE | B075-B079 | Test delayed assistant start. |
| B081 | TCE | B075-B079 | Test long generation. |
| B082 | TCE | B075-B079 | Test malformed semantic output followed by valid retry. |
| B083 | IRA | B080-B082 | Verify no partial assistant message can authorize an action. |

---

## WS8 — Secure action extraction/materialization

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B084 | BBE | B075 | Enumerate fenced code blocks with message id, index, SHA and bytes. |
| B085 | SOE | B084 | Semantic classifier may choose only block index/SHA/target, never command bytes. |
| B086 | BBE | B085 | Materialize exact chosen block from the same settled assistant turn. |
| B087 | CFE | B086 | Re-hash and length-check immediately before execution. |
| B088 | TCE | B084-B087 | Test multiple code blocks. |
| B089 | TCE | B084-B087 | Test 12KB+ command. |
| B090 | TCE | B084-B087 | Test UTF-8 command. |
| B091 | TCE | B084-B087 | Test tampered expected SHA; must block. |
| B092 | IRA | B088-B091 | Confirm model cannot alter execution bytes. |

---

## WS9 — Tool adapters

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B093 | TAE | — | Re-run local adapter contract tests. |
| B094 | TAE | — | Re-run GitHub read-only adapter contract tests against exact repo/branch identity. |
| B095 | TAE | — | Re-run VPS adapter contract tests enforcing `/opt/ai-loop/bin/vps-ssh`. |
| B096 | TAE | — | Re-run Semaphore deterministic/API/browser-readonly collector contract tests. |
| B097 | TAE | B094 | Verify GitHub transient network retry classification. |
| B098 | TAE | B096 | Verify Semaphore auth-required state is explicit and cannot be mistaken for pipeline failure. |
| B099 | TCE | B093-B098 | Add fake adapter failures and recovery tests. |
| B100 | IRA | B093-B099 | Audit route ownership and exact identity binding. |

---

## WS10 — Evidence delivery

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B101 | CFE | B069 | Verify short evidence is sent inline with unique delivery id. |
| B102 | CFE | B101 | Verify large evidence uses an attached evidence file and exact attachment proof. |
| B103 | BBE | B102 | Reuse v4.4 idempotent attachment transaction for evidence-file attachment. |
| B104 | TCE | B101-B103 | Test two sequential post-bootstrap controller messages to same chat. |
| B105 | TCE | B101-B103 | Test evidence send after controller restart. |
| B106 | IRA | B104-B105 | Confirm evidence is delivered once and to same conversation identity. |

---

## WS11 — CI, failure analysis and artifact/replan lane

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B107 | TAE | B094 | Verify `candidate_sha` detection against GitHub HEAD. |
| B108 | TAE | B107 | Verify CI status binds provider + candidate SHA + run/pipeline id. |
| B109 | TAE | B108 | Verify SUCCESS → FINAL_REVIEW transition. |
| B110 | TAE | B108 | Verify FAILURE → FAILURE_ANALYSIS transition. |
| B111 | TAE | B110 | Verify Semaphore failure evidence collection. |
| B112 | CFE | B111 | Verify diagnosis request is sent once per failure fingerprint. |
| B113 | CFE | B112 | Verify `/ralplan` request is sent once after diagnosis. |
| B114 | BBE | B113 | Verify plan artifact discovery/download through broker. |
| B115 | CFE | B114 | Validate artifact bytes, UTF-8, SHA and plan contract before new iteration. |
| B116 | TCE | B107-B115 | Run synthetic SUCCESS path. |
| B117 | TCE | B107-B115 | Run synthetic FAILURE→diagnosis→replan→new plan path. |
| B118 | IRA | B116-B117 | Approve CI/replan identity and idempotency invariants. |

---

## WS12 — Restart and chaos matrix

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B119 | TCE | B054-B118 | Kill broker during fresh-draft wait; recover safely. |
| B120 | TCE | B054-B118 | Kill broker after attachment physical success; no duplicate upload. |
| B121 | TCE | B054-B118 | Kill controller after ATTACHMENT_PROVEN; resume safely. |
| B122 | TCE | B054-B118 | Kill controller immediately before Send. |
| B123 | TCE | B054-B118 | Kill controller immediately after Send click. |
| B124 | TCE | B054-B118 | Kill controller during assistant generation. |
| B125 | TCE | B054-B118 | Kill controller after action execution before evidence delivery. |
| B126 | TCE | B054-B118 | Kill controller during WAIT_CI. |
| B127 | TCE | B054-B118 | Kill controller after CI success before final review. |
| B128 | IRA | B119-B127 | Prove zero duplicate Send/action/pipeline/commit effects across restart matrix. |

---

## WS13 — Diagnostics and performance

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B129 | SRE | B042 | Add hydration timeline to broker diagnostics. |
| B130 | SRE | B006 | Add canonical composer state to browser diagnostics. |
| B131 | SRE | B014 | Add attachment transaction state/ledger to diagnostics without exposing file contents. |
| B132 | SRE | — | Preserve JSON + sanitized HTML + screenshot on every browser failure. |
| B133 | SRE | — | Add phase timing for draft, policy, attach, fill, send, response, action, CI and GO. |
| B134 | SRE | B042 | Remove any newly discovered blind fixed sleeps >1s from normal browser path; use condition waits. |
| B135 | TCE | B129-B134 | Test delayed attachment chip and delayed hydration under configurable budgets. |
| B136 | IRA | B129-B135 | Verify diagnostics do not expose cookies, tokens or credentials. |

---

## WS14 — Local executable test harness

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B137 | TCE | B003-B136 | Extend fake ChatGPT Projects app with the exact v4.3 composer attachment DOM structure. |
| B138 | TCE | B137 | Add three simultaneous file inputs: photos/videos, photos, generic files. |
| B139 | TCE | B137 | Simulate file input clearing after UI attachment adoption. |
| B140 | TCE | B137 | Simulate delayed Chat surface hydration. |
| B141 | TCE | B137 | Simulate stale unsent attachment after controller crash. |
| B142 | TCE | B137 | Simulate post-send delayed route change. |
| B143 | TCE | B137 | Simulate assistant action request → tool action → evidence → final GO. |
| B144 | TCE | B137 | Simulate CI failure → diagnosis → replan → second iteration → GO. |
| B145 | TCE | B137-B144 | Run 100 consecutive synthetic full loops. |
| B146 | IRA | B145 | Require 100/100 GO, 0 duplicate sends, 0 duplicate attachments, 0 duplicate actions, 0 uncaught exceptions. |

---

## WS15 — Ubuntu real-environment preflight

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B147 | SRE | B146 | Run clean extraction verification on the Ubuntu machine. |
| B148 | SRE | B147 | Verify Node/Playwright/Chrome persistent profile. |
| B149 | SRE | B147 | Verify authenticated ChatGPT session and `bot_trading` access. |
| B150 | TAE | B147 | Verify `git`, `gh`, exact repo/branch and GitHub auth. |
| B151 | TAE | B147 | Verify `/opt/ai-loop/bin/vps-ssh`. |
| B152 | TAE | B147 | Verify Semaphore access/status collector. |
| B153 | SRE | B147-B152 | Verify no stale controller/broker/OpenCode/Playwright profile processes. |
| B154 | TL | B147-B153 | Block live Send if any required integration preflight fails. |

---

## WS16 — Mandatory live canary and fix-until-GO loop

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B155 | TL | B154 | Launch a brand-new safe acceptance loop using the read-only acceptance plan. |
| B156 | IRA | B155 | Prove new clean `bot_trading` draft with no stale text/attachments. |
| B157 | IRA | B155 | Prove Chat + Sol + High. |
| B158 | IRA | B155 | Prove exact plan attached once using real live DOM. |
| B159 | IRA | B155 | Prove exact one bootstrap Send. |
| B160 | IRA | B155 | Prove assistant response observation to SETTLED. |
| B161 | IRA | B155 | Prove OpenCode semantic classification. |
| B162 | IRA | B155 | Prove local operator round-trip. |
| B163 | IRA | B155 | Prove GitHub read-only round-trip. |
| B164 | IRA | B155 | Prove VPS wrapper round-trip. |
| B165 | IRA | B155 | Prove Semaphore evidence round-trip. |
| B166 | IRA | B155 | Prove at least two post-bootstrap controller messages to same chat. |
| B167 | IRA | B155 | Prove canary reaches `FINAL_GO` and controller validates it independently. |
| B168 | SRE | B155-B167 | Archive complete log, state, action receipts, browser evidence and timing report. |
| B169 | TL | B155-B168 | If ANY bug/error occurs, open a defect item, capture evidence, add a regression test, fix it and return to B145 before re-running B155. Do not declare completion. |
| B170 | IRA | B169 | Require a final live canary run with no controller/browser/parser/tool exception from start to GO. |

### Mandatory convergence rule

B169 is recursive by design:

```text
live bug
→ fix
→ regression
→ full local suite
→ 100-run synthetic soak
→ new clean live canary
```

There is no maximum number of bug-fix iterations for implementation defects.

After the same failure class recurs twice, TL + BBE + CFE + IRA must perform a short architecture review before attempting another patch.

---

## WS17 — Real target-loop acceptance

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B171 | TL | B170 | Preflight the actual target plan/repository state. |
| B172 | IRA | B171 | Verify re-entry/duplicate-commit guard against current `feature/GRU` HEAD and CI state. |
| B173 | SRE | B171-B172 | Launch a brand-new loop for the actual target plan when safe/required. |
| B174 | IRA | B173 | Observe the run through all required operator/CI stages. |
| B175 | TL | B173-B174 | Apply the same fix-until-success protocol to any ai-loop implementation bug discovered by the real run. |
| B176 | IRA | B173-B175 | Require validated GO or, only for a genuinely external unavailable service/credential, preserve state and resume after the external dependency is restored. An ai-loop bug is never an acceptable blocker. |

---

## WS18 — Packaging and release

| ID | Owner | Depends on | Atomic task / deliverable |
|---|---|---|---|
| B177 | TL | B170 | Bump runtime version to `4.4.0`. |
| B178 | TL | B177 | Update migration notes with exact v4.3 attachment/hydration root causes. |
| B179 | TCE | B177 | Run `python3 -m py_compile` across Python sources. |
| B180 | TCE | B177 | Run `node --check` across Node workers/broker. |
| B181 | TCE | B177 | Run all legacy v2/v3/v4 compatibility selftests still applicable. |
| B182 | TCE | B177 | Run v4.4 regression suite. |
| B183 | TCE | B177 | Run 100-loop synthetic soak again from clean extraction. |
| B184 | SRE | B177-B183 | Validate `install.sh` upgrade from v4.3 on a clean test install. |
| B185 | IRA | B170,B176,B184 | Build release evidence matrix G0–G14. |
| B186 | IRA | B185 | Generate source/artifact SHA-256 manifest. |
| B187 | TL | B185-B186 | Produce `ai-loop-v4.4.tar.gz` only when every mandatory release gate is green. |

---

# 13. Mandatory test matrix

## 13.1 Attachment regression tests

The exact v4.3 real DOM scenario is mandatory:

```text
active composer root:
  form[data-chatgpt-composer]

attachment region:
  [data-composer-attachments][data-visible-attachments]

exact file:
  AI_LOOP_FULL_ACCEPTANCE_20260922T0155-0500.md

signals:
  visible filename
  aria-label exact filename
  aria-label Remove <filename>

file input after upload:
  may be cleared
```

Expected:

```text
ATTACH_FILE = PASS / ALREADY_ATTACHED
```

not:

```text
WAIT_TIMEOUT:attachment_proof
```

Additional cases:

| Case | Expected |
|---|---|
| filename only in sidebar/history | FAIL |
| filename only in page body | FAIL |
| exact chip inside wrong composer | FAIL |
| exact chip in active composer | PASS |
| exact remove control + chip | PASS |
| input cleared after chip creation | PASS |
| wrong file extension selected into image input | input resolver must avoid |
| three file inputs like real DOM | select `Attach files` compatible input |
| delayed chip appears within budget | PASS |
| upload error indicator | FAIL |
| same exact file already attached on retry | ALREADY_ATTACHED, zero new uploads |
| duplicate exact chips | Send fenced until normalized/fixed |

## 13.2 Hydration tests

| Case | Expected |
|---|---|
| Chat already selected immediately | PASS |
| Chat appears after 100 ms | PASS |
| Chat appears after 2 s | PASS |
| High trigger appears late | PASS |
| Work selected then Chat appears | switch + prove |
| control never appears | bounded hydration timeout |
| diagnostic snapshot sees Chat after initial miss | timeline reveals late hydration |

## 13.3 Draft-cleanliness tests

| Case | Expected |
|---|---|
| TARGET + 0 turns + empty text + 0 attachments | fresh |
| TARGET + 0 turns + stale file | stale, not fresh |
| TARGET + 0 turns + stale text | stale, not fresh |
| TARGET + old conversation turns | not fresh |
| same-run matching prepared draft | resumable |
| previous-run prepared draft | not adoptable |

## 13.4 Send/idempotency tests

- one click only;
- failure before click → safe retry;
- failure after possible click → read-only reconciliation;
- delayed user-turn DOM;
- delayed route update;
- controller crash immediately after click;
- browser crash immediately after click;
- no duplicate Send after restart.

## 13.5 Operator/tool tests

- local success/failure/timeout;
- GitHub read-only exact identity;
- VPS wrapper success/failure/timeout;
- Semaphore success/pending/failure/auth-required;
- action SHA mismatch;
- wrong target routing;
- evidence inline and attached.

## 13.6 CI/replan tests

- candidate detected;
- pending→success;
- pending→failure;
- failure evidence delivered;
- diagnosis;
- replan;
- artifact download;
- second implementation iteration;
- success→final review→GO.

## 13.7 Soak

Required:

```text
100/100 synthetic full loops reach GO
0 duplicate attachments
0 duplicate Sends
0 duplicate actions
0 duplicate CI side effects
0 wrong-project sends
0 unverified attachment sends
0 uncaught Python exceptions
0 uncaught Node exceptions
```

---

# 14. Live-test protocol on Ubuntu

The implementation team is explicitly authorized by this plan to perform live validation on the Ubuntu execution environment.

## 14.1 Before every live run

```text
stop/kill prior ai-loop processes
confirm no stale browser broker
confirm no stale OpenCode/Playwright owner
run preflight
archive previous run state
start a brand-new run
```

## 14.2 First live target: safe acceptance canary

The canary must exercise all available integrations without intentionally modifying production state.

Required observable sequence:

```text
BROWSER_BROKER=PASS
PROJECT_CONTEXT PASS project=bot_trading
FRESH_PROJECT_DRAFT PASS clean=true
CHAT_SURFACE PASS surface=chat
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high
ATTACHMENT_GUARD PASS filename=...
DELIVERY_READY ...
DELIVERY_SENT ...
DELIVERY_PROOF PASS ...
ASSISTANT_OBSERVER SETTLED ...
SEMANTIC_EVENT ...
ACTION_MATERIALIZED ...
ACTION_EXECUTED target=local ...
EVIDENCE_SENT ...
ACTION_EXECUTED target=github-readonly ...
EVIDENCE_SENT ...
ACTION_EXECUTED target=vps ...
EVIDENCE_SENT ...
SEMAPHORE_EVIDENCE ...
EVIDENCE_SENT ...
FINAL_GO_VALIDATED ...
AI_LOOP_COMPLETE=GO
```

## 14.3 What to do on any live failure

Do not merely rerun.

Mandatory:

1. freeze/stop the failed run if necessary;
2. preserve:
   - controller log;
   - state JSON;
   - broker JSON/HTML/screenshot;
   - action receipts;
   - CI evidence;
3. classify whether side effect occurred;
4. reproduce in a deterministic test fixture;
5. identify root cause in source;
6. implement systemic fix;
7. add regression test named after the run/failure;
8. run full local suite;
9. run 100-loop soak;
10. run a **new clean live canary**;
11. continue until GO.

---

# 15. Performance targets

Normal healthy conditions:

| Metric | Target |
|---|---:|
| controller start → broker healthy | ≤5 s |
| broker → clean target draft | ≤15 s |
| draft → Chat/Sol/High proven | ≤10 s |
| policy → attachment proven | ≤10 s |
| attachment → text ready | ≤5 s |
| ready → Send | ≤5 s |
| startup → initial Send | ≤60 s; stretch ≤30 s |
| redundant Chrome relaunches normal path | 0 |
| duplicate upload attempts normal path | 0 |
| OpenCode ChatGPT browser ownership | 0 |
| blind fixed sleeps >1 s normal browser path | 0 |

A timeout must never justify bypassing an invariant.

---

# 16. Release gates

| Gate | Requirement |
|---|---|
| G0 | v4.3 evidence/context frozen |
| G1 | real attachment DOM fixture reproduces old false negative |
| G2 | canonical active-composer resolver green |
| G3 | idempotent attachment transaction green |
| G4 | stale-draft/new-run isolation green |
| G5 | hydration-safe Chat/Sol/High green |
| G6 | pre-send milestone reconciliation green |
| G7 | Send/recovery/idempotency matrix green |
| G8 | response/semantic/action materialization green |
| G9 | local/GitHub/VPS/Semaphore adapter tests green |
| G10 | CI/replan/artifact synthetic path green |
| G11 | restart/chaos matrix green |
| G12 | 100/100 synthetic full loops GO |
| G13 | real Ubuntu safe canary reaches independently validated FINAL_GO with all required tools |
| G14 | actual target loop reaches validated GO, or is paused only for a genuinely external unavailable service/credential and subsequently resumed before release |
| G15 | independent release audit approves complete evidence bundle |

**No gate may be waived because an earlier version passed unit tests.**

---

# 17. Acceptance log contract

The final successful v4.4 live run should contain, at minimum:

```text
ai-loopd-v3 version=4.4.0
BROWSER_BROKER=PASS ...
PROJECT_CONTEXT PASS project=bot_trading ...
FRESH_PROJECT_DRAFT PASS turns=0 clean=true attachments=0
CHAT_SURFACE PASS surface=chat
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high ...
ATTACHMENT_GUARD PASS filename=... mode=ATTACHED|ALREADY_ATTACHED count=1
COMPOSER_TEXT_GUARD PASS ...
DELIVERY_READY id=...
DELIVERY_SENT id=...
DELIVERY_PROOF PASS id=...
ASSISTANT_OBSERVER SETTLED ...
SEMANTIC_EVENT ...
ACTION_MATERIALIZED ...
ACTION_EXECUTED ...
EVIDENCE_SENT ...
CI_EVIDENCE ...
FINAL_GO_VALIDATED ...
AI_LOOP_COMPLETE=GO
```

The release run must not end with any uncaught:

```text
Traceback
UnhandledPromiseRejection
WAIT_TIMEOUT:attachment_proof
CHAT_SURFACE_CONTROL_NOT_FOUND
duplicate attachment
duplicate delivery
AMBIGUOUS_SEND_UNRESOLVED caused by controller defect
```

---

# 18. Pre-mortem — deliberate mode

## Scenario 1 — attachment upload succeeds but verifier fails again

**Likely cause**
- UI attachment structure changes or proof remains too selector-specific.

**Prevention**
- canonical active composer;
- multi-signal attachment enumeration;
- exact real-DOM fixture;
- UI semantic attributes preferred over hashed classes;
- no body-wide proof.

**Detection**
- diagnostic emits active composer tree + enumerated attachment state.

**Recovery**
- because attachment transaction is idempotent, retry observes `ALREADY_ATTACHED` rather than uploading again.

---

## Scenario 2 — React hydration produces another false “control not found”

**Likely cause**
- synchronous first-look logic executes before UI control mounts.

**Prevention**
- wait-for-hydration states;
- condition-driven polling;
- operation timeline.

**Detection**
- timeline proves when control appeared.

**Recovery**
- remain inside same broker operation; do not spend an outer retry for ordinary hydration.

---

## Scenario 3 — bootstrap finally succeeds but a later untested path fails

**Likely cause**
- post-Send paths have not yet completed a live end-to-end run in v4.x.

**Prevention**
- mandatory safe live canary exercises every integration;
- team cannot finish at bootstrap success;
- recursive live bug-fix loop.

**Detection**
- phase-specific diagnostics and durable state.

**Recovery**
- reproduce, regression-test, fix, full soak, new clean canary.

---

## Scenario 4 — process dies after a side effect and restart duplicates it

**Likely cause**
- intent/result state not persisted at the correct boundary.

**Prevention**
- durable milestone/ledger before and after every side effect;
- reconciliation before retry.

**Detection**
- restart/chaos matrix at each boundary.

**Recovery**
- read-only observation of current state; never blind replay.

---

# 19. ADR

## Decision

Implement v4.4 around a **canonical active-composer state model**, an **idempotent attachment transaction**, **hydration-safe browser policy**, and a **mandatory iterative live acceptance loop until FINAL_GO**.

## Drivers

1. real diagnostics prove the file was attached while the verifier returned timeout;
2. real diagnostics prove Chat hydration can race immediate control lookup;
3. the remaining post-Send pipeline has not yet completed a real end-to-end v4.x acceptance.

## Alternatives considered

- one selector patch;
- paste plan instead of attach;
- separate upload browser;
- canonical composer/transaction model.

## Chosen

Canonical composer + transaction model.

## Why

It fixes the exact failure without weakening project/file integrity and prevents retry-driven duplicate attachments.

## Consequences

### Positive
- upload becomes observable and idempotent;
- stale draft is no longer mistaken for fresh;
- hydration does not cause false failure;
- live failures become regression tests;
- release finally depends on actual end-to-end behavior.

### Costs
- larger broker-state refactor;
- additional state/ledger migration;
- longer implementation campaign because live acceptance must continue until GO.

## Follow-ups
- retain sanitized real-DOM fixtures for every future ChatGPT UI drift;
- version attachment/composer evidence schema separately;
- consider a generic semantic locator registry only after v4.4 live acceptance.

---

# 20. Planner / Architect / Critic consensus record

## Planner

The immediate failure is not an upload failure. The file reached the live composer. The proof scope is wrong.

A narrow selector patch is insufficient because the same evidence exposes:

- ambiguous file-input selection;
- stale-draft risk;
- duplicate attachment retry risk;
- policy hydration race.

Therefore v4.4 must treat attachment as a stateful idempotent transaction.

**Planner verdict:** proceed with Option B.

---

## Architect review

### Strongest steelman counterargument

The requested objective can tempt the team into over-expanding scope: after each live bug, the implementation could grow indefinitely and destabilize otherwise-working paths.

### Real tradeoff

```text
minimal change / lower regression risk
vs.
systemic transaction model / lower recurrence risk
```

### Synthesis

Keep the refactor bounded around explicit invariants:

- canonical active composer;
- exact attachment transaction;
- clean draft;
- hydration wait;
- milestone reconciliation.

Do not redesign unrelated semantic/CI code unless a test or live failure proves a defect.

However, all downstream paths MUST still be exercised in live acceptance, and any actual defect found there must be fixed before release.

**Architect verdict:** APPROVE with mandatory regression-per-live-bug rule.

---

## Critic review

The plan is testable because it specifies:

- exact real-DOM regression evidence;
- atomic responsibilities;
- side-effect invariants;
- 100-loop soak;
- restart matrix;
- live safe canary;
- explicit “fix until GO” convergence loop.

The implementation must not claim G13 from screenshots or logs that stop before final GO.

**Critic verdict:** APPROVE.

---

# 21. Team execution guidance

Recommended parallel lanes:

```text
Lane A — BBE + DAVE
  WS1, WS2, WS4

Lane B — CFE
  WS3, WS5, WS6, restart state

Lane C — SOE
  WS7, WS8 semantic side

Lane D — TAE
  WS9, WS11 adapters/CI

Lane E — TCE
  regression fixtures, fake app, chaos, soak continuously

Lane F — SRE
  diagnostics, timing, Ubuntu live validation

Lane G — IRA
  invariant and evidence audits

TL
  integration order, live defect loop, release gates
```

Suggested `/team` handoff:

```text
/team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_4_LIVE_END_TO_END_RELIABILITY_20260922T1252-0500.md; do not finish until the Ubuntu live acceptance loop reaches independently validated FINAL_GO. If any test or live test exposes a bug, add a regression, fix it, rerun the full suite and rerun the live canary until success.
```

---

# 22. Team → Ralph independent verification path

After the team reports completion, run an independent sequential verifier:

```text
/ralph verify every invariant, backlog acceptance item, release gate, real-DOM attachment regression, hydration regression, restart matrix, 100-loop soak, Ubuntu safe-canary evidence, tool round-trips and final GO evidence in IMPLEMENTATION_PLAN_AI_LOOP_V4_4_LIVE_END_TO_END_RELIABILITY_20260922T1252-0500.md. Do not accept source assertions as proof. If any gate is not evidenced, report it as incomplete.
```

`/ralph` should not “rubber stamp” the team result. It must inspect the evidence generated by the actual tests.

---

# 23. Definition of Done

v4.4 is DONE only when all of the following are evidenced:

```text
[PASS] real v4.3 attachment DOM now proves attachment successfully
[PASS] file input resolver selects compatible generic file input
[PASS] input.files clearing does not cause false failure
[PASS] retry does not create duplicate attachment
[PASS] stale unsent draft from previous run is not accepted as fresh
[PASS] delayed Chat/High hydration does not consume outer bootstrap retry
[PASS] Send is gated by clean project/policy/attachment/text state
[PASS] no blind resend
[PASS] assistant response observation works
[PASS] OpenCode semantic classification works browser-free
[PASS] exact action bytes are SHA/length verified
[PASS] local adapter live round-trip works
[PASS] GitHub live round-trip works
[PASS] VPS live round-trip works
[PASS] Semaphore live round-trip works
[PASS] multiple post-bootstrap evidence messages work
[PASS] CI identity is exact
[PASS] restart matrix produces zero duplicates
[PASS] 100/100 synthetic full loops reach GO
[PASS] real Ubuntu safe canary reaches independently validated FINAL_GO
[PASS] actual target-loop acceptance reaches validated GO or resumes after any external-only dependency
[PASS] no uncaught controller/browser exception in final acceptance run
[PASS] complete evidence bundle exists
[PASS] independent auditor approves G0–G15
```

Anything less is an **unfinished release candidate**, not completion.

---

# 24. Final implementation instruction

The implementation team must treat this plan as an execution-and-validation contract, not a coding checklist.

The goal is not:

```text
fix WAIT_TIMEOUT:attachment_proof
```

The goal is:

```text
make ai-loop complete a real end-to-end loop successfully,
with every required integration,
without duplicate side effects,
and prove it with live evidence.
```

If clearing the current attachment defect exposes another bug at the next phase, fixing that next bug is **part of this same implementation**, not future work.

The team may finish only after the live Ubuntu loop reaches validated `FINAL_GO`.
