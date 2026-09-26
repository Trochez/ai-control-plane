# IMPLEMENTATION PLAN — ai-loop v4.7 Semaphore API Evidence, Bounded Recovery & OpenCode Operator Boundaries

**Generated:** 2026-09-23T14:10-05:00  
**Current runtime:** ai-loop `v4.6.0`  
**Target release:** ai-loop `v4.7.0`  
**Control plane:** `/mnt/d/works/ai-control-plane`  
**Target repository:** `/mnt/d/works/bot_trad/bot_trading`  
**GitHub repository:** `Trochez/bot_trading`  
**Branch:** `feature/GRU`  
**Current resumable run:** `R20260923T012014`  
**Candidate SHA:** `0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390`  
**Semaphore workflow:** `0f6fcfa4-4fb0-419d-ba4d-ca77af5d0c62`  
**Semaphore pipeline:** `4df05bd2-6a81-41dc-9dfe-9e0051cd602c`  
**Observed CI terminal result:** `state=done`, `result=stopped`, normalized `FAILURE`

---

# 0. Mandatory objective

The implementation is complete only when the **same resumable run** can progress from:

```text
WAIT_CI
→ CI FAILURE
→ FAILURE_ANALYSIS
→ Semaphore detailed evidence
→ exact-SHA local investigation
→ evidence round-trip to GPT Web
→ diagnosis
→ replan
→ next implementation iteration
→ CI success
→ final review
→ FINAL_GO
→ AI_LOOP_COMPLETE=GO
```

The team MUST continue fixing any ai-loop defect exposed during testing or the live run until the full loop succeeds.

Do not create a new run merely to bypass the current failure state. Preserve and resume:

```text
/var/lib/ai-loop/state/R20260923T012014.v3.json
```

unless the run is proven unrecoverable by deterministic state validation.

---

# 1. Confirmed current state

v4.6 already proved:

```text
✓ controller resumes
✓ OpenCode server starts
✓ OpenCode semantic capability passes
✓ Browser Broker starts
✓ startup Chat-policy hydration failure is deferred instead of killing controller
✓ VPS connectivity works
✓ CI helper identifies exact Semaphore workflow/pipeline by candidate SHA
✓ `done/stopped` normalizes to `FAILURE`
✓ FSM exits WAIT_CI and enters failure-analysis lane
```

Current blocker:

```text
Semaphore evidence collector status=NOT_FOUND
SEMAPHORE_EXACT_ANCHORS_NOT_FOUND:
  workflow_id
  pipeline_id
  candidate_sha
```

The detailed evidence collector currently relies on discovering exact UUID/SHA anchors in Semaphore Web UI. This is fragile and unnecessary because the API-backed `ci-status` path already has authoritative workflow and pipeline identity.

---

# 2. Architecture decision

## 2.1 Primary Semaphore evidence path

Use **Semaphore API evidence collection as the authoritative path**.

Credentials remain on the VPS. Do not move Semaphore API secrets into ChatGPT, OpenCode prompts, logs, or committed files.

Target flow:

```text
ai-loop controller
      ↓
versioned Semaphore evidence helper
      ↓
VPS / existing protected Semaphore environment
      ↓
Semaphore API
      ↓
workflow exact by candidate SHA
      ↓
pipeline exact
      ↓
blocks
      ↓
jobs
      ↓
failed/stopped job(s)
      ↓
job/step details + logs where API supports them
      ↓
canonical evidence JSON
```

## 2.2 Browser fallback

Browser UI becomes a fallback only for information that cannot be retrieved through the supported API path.

It MUST NOT rediscover the pipeline by searching visible UUID/SHA text.

When browser fallback is needed, it must navigate using API-derived exact URLs/identifiers or structured project navigation.

---

# 3. Canonical Semaphore evidence schema

Create one schema version, for example:

```text
semaphore_evidence_schema = 1
```

Required top-level fields:

```json
{
  "schema_version": 1,
  "provider": "semaphore",
  "repo": "Trochez/bot_trading",
  "branch": "feature/GRU",
  "sha": "0c11a13e...",
  "workflow_id": "0f6fcfa4-...",
  "pipeline_id": "4df05bd2-...",
  "pipeline": {
    "state": "done",
    "result": "stopped"
  },
  "blocks": [],
  "jobs": [],
  "failed_jobs": [],
  "collector": {
    "source": "api",
    "status": "PASS"
  }
}
```

For a terminal non-success pipeline, evidence is valid when immutable identity is exact even if a particular optional log endpoint is temporarily unavailable.

Optional detail failures must be represented as structured partial-evidence fields, not by changing the known terminal pipeline result to `UNKNOWN`.

---

# 4. Semaphore API collector

Implement a versioned executable shipped inside the release, e.g.:

```text
/opt/ai-loop/bin/semaphore-evidence
```

or extend a versioned `ci-status` module with a distinct evidence operation.

It must accept:

```text
repo
branch
candidate SHA
workflow_id
pipeline_id
```

and verify that all returned resources belong to the same candidate.

## Required operations

1. query exact workflow/pipeline;
2. validate commit SHA;
3. retrieve pipeline metadata;
4. retrieve blocks;
5. retrieve jobs;
6. identify failed/stopped/canceled jobs;
7. retrieve job/step metadata;
8. retrieve logs where supported;
9. return canonical JSON;
10. never expose credentials.

## Identity rule

If API returns a different SHA/workflow/pipeline:

```text
FAIL_CLOSED
```

Do not continue diagnosis with mismatched CI evidence.

---

# 5. Normalization rules

Terminal states:

```text
done + passed/success/succeeded → SUCCESS
done + failed/error/stopped/canceled/cancelled → FAILURE
```

Non-terminal:

```text
pending
queued
running
initializing
→ PENDING/RUNNING
```

A terminal failure MUST NOT become `UNKNOWN` solely because:

```text
jobs detail is incomplete
repo/branch came from controller config rather than provider payload
optional logs are temporarily unavailable
```

For failure analysis, exact identity + terminal provider result is enough to enter the evidence lane. Detail collection can enrich it.

For SUCCESS/final GO, retain strict proof requirements.

---

# 6. Bounded evidence recovery

Remove infinite:

```text
NOT_FOUND
→ sleep
→ NOT_FOUND
→ sleep
→ ...
```

Introduce a fingerprint:

```text
provider
candidate_sha
workflow_id
pipeline_id
error_code
```

Persist retry count and timestamps.

Suggested behavior:

```text
attempt 1: immediate API evidence
attempt 2: transient retry
attempt 3: final API retry / fallback
same deterministic failure thereafter:
    circuit breaker OPEN
```

Result:

```text
SEMAPHORE_EVIDENCE_CIRCUIT_BREAKER_OPEN
```

The controller remains resumable and preserves diagnostics.

Do not burn an unbounded loop.

---

# 7. OpenCode operator boundary — clarified requirement

OpenCode launched by:

```text
start-loop-v3
resume-current-v3
```

**IS allowed to enter `bot_trading`** for operational work that GPT Web cannot physically perform.

It is NOT restricted to `ai-control-plane`.

## 7.1 Allowed OpenCode operational actions in `bot_trading`

When authorized by the controller/action protocol, OpenCode may:

```text
git fetch
git status
git rev-parse
git log
git diff
verify branch/SHA
compare local checkout vs GitHub
synchronize a clean checkout using approved safe strategy
create/use temporary detached clone or worktree
inspect repository files needed for diagnosis
run tests
run linters/static checks
run build commands
run read-only diagnostic scripts
collect local evidence
inspect generated artifacts
use approved VPS wrapper
perform operational actions GPT Web cannot physically execute
```

It may also run a controller-authorized synchronization to GitHub when the exact operation is within policy.

## 7.2 Allowed mutation boundary

OpenCode may perform a mutation only when ALL are true:

```text
1. GPT Web/controller requested the operation;
2. target/repo/branch are explicit;
3. controller policy authorizes the action;
4. command bytes are obtained through the authoritative action transport;
5. side-effect ledger is persisted;
6. result is captured as literal evidence.
```

Examples may include a specifically authorized repository synchronization or operational file generation.

## 7.3 OpenCode must NOT

OpenCode must not independently decide to:

```text
implement a new fix in bot_trading
edit application source merely because it found a failure
commit/push without explicit authorized action
change branch arbitrarily
reset --hard / clean destructively
rewrite history
modify production outside a requested adapter action
perform browser navigation owned by Browser Broker
```

The key rule is:

> OpenCode may OPERATE on `bot_trading`; it may not autonomously become the implementation decision-maker.

GPT Web remains the planner/decision source. The controller remains the execution authority.

---

# 8. Repository synchronization contract

Create a deterministic operation such as:

```text
SYNC_TARGET_REPO
```

Inputs:

```json
{
  "repo_dir": "/mnt/d/works/bot_trad/bot_trading",
  "remote": "origin",
  "branch": "feature/GRU",
  "expected_remote_sha": "..."
}
```

Safe sequence:

```text
git status --porcelain
git fetch --prune origin feature/GRU
git rev-parse HEAD
git rev-parse origin/feature/GRU
```

If working tree is clean and synchronization is explicitly authorized:

```text
git merge --ff-only origin/feature/GRU
```

or use an isolated detached worktree/clone when synchronization of the primary checkout is not required.

Do not use:

```text
git reset --hard
git clean -fdx
force push
```

as generic sync mechanisms.

Persist before/after SHA and status.

---

# 9. Exact-SHA investigation

After CI FAILURE and Semaphore evidence PASS:

```text
candidate_sha
      ↓
temporary isolated clone/worktree
      ↓
checkout exact candidate SHA
      ↓
identify failed Semaphore job/step
      ↓
map to repository CI commands
      ↓
run only allowed reproduction commands
      ↓
capture stdout/stderr/exit/time
```

The main `bot_trading` working tree does not need to be modified for this reproduction.

OpenCode can run these tests because this is precisely operational work GPT Web cannot execute itself.

---

# 10. CI helper packaging

The current `/opt/ai-loop/bin/ci-status` is a legacy installed helper and is not guaranteed to come from the current bundle.

v4.7 MUST:

1. include `bin/ci-status` in the release;
2. include its SHA in `MANIFEST.sha256`;
3. install it explicitly;
4. record helper version in output;
5. ensure upgrade replaces known-old helper;
6. test helper from a clean installation;
7. test helper from a v4.6 upgrade.

Add output such as:

```json
"collector_version": "4.7.0"
```

---

# 11. Team

**Team size: 8**

| Role | Responsibility |
|---|---|
| Technical Lead | architecture/release coordination |
| CI/Semaphore Engineer | API collector and normalization |
| Controller/FSM Engineer | failure-analysis transitions and circuit breaker |
| OpenCode Operator Engineer | operational permissions and repo synchronization |
| Repository/Test Engineer | exact-SHA test reproduction |
| Test/Chaos Engineer | deterministic and restart regressions |
| SRE/Live Validator | Ubuntu resume/live run |
| Independent Auditor | evidence and release-gate validation |

---

# 12. Atomic backlog

## A. Evidence collector

- **B001 — CI/Semaphore Engineer:** freeze current `ci-status` output fixture for candidate SHA.
- **B002 — CI/Semaphore Engineer:** freeze current `SEMAPHORE_EXACT_ANCHORS_NOT_FOUND` fixture.
- **B003 — CI/Semaphore Engineer:** define canonical evidence schema v1.
- **B004 — CI/Semaphore Engineer:** implement exact workflow/pipeline identity validation.
- **B005 — CI/Semaphore Engineer:** implement blocks retrieval.
- **B006 — CI/Semaphore Engineer:** implement jobs retrieval.
- **B007 — CI/Semaphore Engineer:** implement failed/stopped job classification.
- **B008 — CI/Semaphore Engineer:** implement optional job/log retrieval.
- **B009 — CI/Semaphore Engineer:** ensure partial optional detail does not erase terminal FAILURE.
- **B010 — Independent Auditor:** audit SHA/workflow/pipeline mismatch handling.

## B. Controller integration

- **B011 — Controller Engineer:** call API evidence collector before browser fallback.
- **B012 — Controller Engineer:** populate repo/branch from trusted project config.
- **B013 — Controller Engineer:** persist canonical evidence under run directory.
- **B014 — Controller Engineer:** transition FAILURE evidence PASS to local exact-SHA investigation.
- **B015 — Controller Engineer:** preserve resumable state on transient collector error.
- **B016 — Controller Engineer:** add error fingerprint and retry counter.
- **B017 — Controller Engineer:** implement bounded circuit breaker.
- **B018 — Test Engineer:** verify no infinite NOT_FOUND loop.

## C. Browser fallback

- **B019 — Browser Engineer:** remove visible-text UUID/SHA rediscovery as primary path.
- **B020 — Browser Engineer:** accept API-derived exact pipeline identifiers/URLs.
- **B021 — Browser Engineer:** use browser only for evidence not available from API.
- **B022 — Test Engineer:** test UI with UUID absent from visible body.
- **B023 — Independent Auditor:** verify UI fallback cannot silently switch pipeline identity.

## D. OpenCode operational boundary

- **B024 — OpenCode Engineer:** update operator policy: OpenCode may enter `bot_trading`.
- **B025 — OpenCode Engineer:** explicitly allow sync/status/test/diagnostic operations.
- **B026 — OpenCode Engineer:** forbid autonomous implementation decisions.
- **B027 — OpenCode Engineer:** ensure action must originate through controller-authorized transport.
- **B028 — OpenCode Engineer:** keep Browser Broker as exclusive ChatGPT browser owner.
- **B029 — Test Engineer:** test allowed repo inspection.
- **B030 — Test Engineer:** test allowed test execution.
- **B031 — Test Engineer:** test authorized safe synchronization.
- **B032 — Test Engineer:** test unauthorized edit/commit is rejected.
- **B033 — Independent Auditor:** approve operator boundary.

## E. Repository synchronization

- **B034 — Repository Engineer:** implement status/fetch/remote-SHA verification.
- **B035 — Repository Engineer:** implement clean-checkout guard.
- **B036 — Repository Engineer:** implement `--ff-only` synchronization when authorized.
- **B037 — Repository Engineer:** prefer temporary worktree/clone for candidate investigation.
- **B038 — Repository Engineer:** persist before/after SHA evidence.
- **B039 — Test Engineer:** dirty working tree blocks primary-checkout sync.
- **B040 — Test Engineer:** divergent branch blocks ff-only sync.

## F. Exact-SHA failure reproduction

- **B041 — Repository/Test Engineer:** create isolated candidate checkout.
- **B042 — Repository/Test Engineer:** map failed Semaphore job/step to repository CI definition.
- **B043 — Repository/Test Engineer:** run allowed exact reproduction command.
- **B044 — Repository/Test Engineer:** persist stdout/stderr/exit/time.
- **B045 — Controller Engineer:** package evidence for GPT Web.
- **B046 — Test Engineer:** test failed command reproduction.
- **B047 — Test Engineer:** test reproduction timeout.

## G. Helper packaging

- **B048 — CI Engineer:** add versioned `bin/ci-status`.
- **B049 — CI Engineer:** add versioned detailed evidence helper.
- **B050 — Release Engineer:** include helpers in manifest.
- **B051 — Release Engineer:** install/upgrade helpers.
- **B052 — Test Engineer:** clean-install helper tests.
- **B053 — Test Engineer:** v4.6→v4.7 upgrade tests.

## H. Resume current run

- **B054 — SRE:** stop current controller cleanly before install.
- **B055 — SRE:** archive current state and diagnostics.
- **B056 — SRE:** install v4.7.
- **B057 — SRE:** verify same state file remains intact.
- **B058 — SRE:** resume `R20260923T012014`.
- **B059 — Auditor:** observe `CI FAILURE`.
- **B060 — Auditor:** require `Semaphore evidence PASS`.
- **B061 — Auditor:** require local exact-SHA investigation.
- **B062 — Auditor:** require literal evidence delivery to GPT Web.
- **B063 — Auditor:** require diagnosis.
- **B064 — Auditor:** require replan artifact.
- **B065 — Auditor:** require next implementation iteration.
- **B066 — Auditor:** require CI success.
- **B067 — Auditor:** require final review and FINAL_GO.

## I. Fix-until-GO loop

- **B068 — TL:** on any new ai-loop bug, freeze evidence.
- **B069 — Test Engineer:** create deterministic reproducer.
- **B070 — Assigned Engineer:** fix root cause.
- **B071 — Test Engineer:** rerun complete suite.
- **B072 — Test Engineer:** rerun 100-loop synthetic soak.
- **B073 — SRE:** resume/restart according to state semantics.
- **B074 — TL:** repeat until full loop GO.
- **B075 — Auditor:** release only after clean final run.

---

# 13. Mandatory tests

## Semaphore

- exact SHA → exact workflow/pipeline;
- terminal `done/stopped` remains FAILURE;
- jobs missing temporarily → terminal failure retained with partial-detail marker;
- different SHA → fail closed;
- different pipeline → fail closed;
- transient API timeout → bounded retry;
- repeated deterministic NOT_FOUND → circuit breaker;
- UUID not visible in web UI → API path still passes;
- browser fallback does not rediscover wrong pipeline.

## OpenCode

Allowed:

```text
git status
git fetch
git rev-parse
git diff
run tests
inspect CI definitions
create isolated worktree
approved ff-only sync
VPS operational action
```

Forbidden without explicit controller authorization:

```text
edit application code
commit
push
hard reset
clean
force branch changes
production mutation
```

## Resume

Resume current state and require:

```text
CI FAILURE
→ semaphore evidence PASS
→ exact-SHA investigation
→ evidence to GPT Web
```

No new bootstrap/implementation message should be sent simply because the daemon restarted.

---

# 14. Release gates

- **G0:** current run evidence preserved.
- **G1:** canonical Semaphore API collector passes fixtures.
- **G2:** terminal FAILURE never degrades to UNKNOWN due optional detail.
- **G3:** circuit breaker eliminates infinite evidence polling.
- **G4:** browser fallback no longer depends on visible UUID/SHA.
- **G5:** OpenCode operational boundary tests pass.
- **G6:** repo synchronization safety tests pass.
- **G7:** exact-SHA reproduction passes.
- **G8:** clean install and v4.6→v4.7 upgrade pass.
- **G9:** 100/100 synthetic loops pass.
- **G10:** current run resumes into Semaphore evidence PASS.
- **G11:** current run delivers failure evidence to GPT Web.
- **G12:** diagnosis/replan/new iteration succeeds.
- **G13:** CI reaches SUCCESS.
- **G14:** FINAL_GO independently validated.
- **G15:** release artifact/manifest/evidence bundle complete.

---

# 15. Expected live progression

After v4.7 installation and resume:

```text
ai-loopd-v3 version=4.7.0 run=R20260923T012014 phase=FAILURE_ANALYSIS|WAIT_CI
...
CI FAILURE provider=semaphore ...
SEMAPHORE_API_EVIDENCE PASS workflow=... pipeline=... sha=...
SEMAPHORE_FAILED_JOBS count=...
LOCAL_EXACT_SHA_INVESTIGATION ...
EVIDENCE_BUNDLE READY ...
OUTBOUND_POLICY HARD_GATE ...
EVIDENCE_SENT ...
ASSISTANT_OBSERVER SETTLED ...
DIAGNOSIS_READY ...
PLAN_READY ...
...
CI SUCCESS ...
FINAL_GO_VALIDATED ...
AI_LOOP_COMPLETE=GO
```

---

# 16. Team execution handoff

Use:

```text
/team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_7_SEMAPHORE_API_EVIDENCE_OPERATOR_BOUNDARIES_20260923T1410-0500.md. OpenCode launched by start-loop/resume-loop MAY enter bot_trading for controller-authorized operational work such as synchronization with GitHub, repository verification, tests, diagnostics, isolated exact-SHA reproduction, VPS operations, and other actions GPT Web cannot physically execute. It MUST NOT autonomously become the implementation decision-maker or perform unrequested edits/commits/pushes. Preserve and resume R20260923T012014. Use Semaphore API evidence as the authoritative detailed-evidence path, browser only as fallback, eliminate infinite NOT_FOUND polling, and do not finish until the same loop reaches independently validated FINAL_GO / AI_LOOP_COMPLETE=GO. If any ai-loop bug appears, add a regression, fix it, rerun the complete suite and continue the live loop.
```

---

# 17. Definition of Done

```text
[PASS] Semaphore exact pipeline identity from API
[PASS] terminal stopped pipeline recognized as FAILURE
[PASS] blocks/jobs/failed-job evidence collected
[PASS] no infinite NOT_FOUND polling
[PASS] browser fallback no longer primary identity discovery
[PASS] OpenCode can operationally enter bot_trading
[PASS] OpenCode can sync/verify/test when authorized
[PASS] OpenCode cannot autonomously implement/commit/push
[PASS] exact-SHA isolated investigation works
[PASS] evidence reaches GPT Web
[PASS] diagnosis generated
[PASS] replan artifact generated
[PASS] next implementation iteration completes
[PASS] CI success
[PASS] FINAL_GO validated
[PASS] AI_LOOP_COMPLETE=GO
```

Anything less is an unfinished implementation.
