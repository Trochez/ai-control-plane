# IMPLEMENTATION PLAN — ai-loop v4.6 Startup Policy Deferral, Hydration-Safe Hard Gate & Live Full-Loop Convergence

**Generated:** 2026-09-22T23:57-05:00  
**Current runtime family:** ai-loop v4.x  
**Target release:** ai-loop `v4.6.0`  
**Execution environment:** Ubuntu / WSL control plane  
**Controller:** `/opt/ai-loop/ai-loopd-v3.py`  
**Browser broker:** `/opt/ai-loop/browser-broker-v1.cjs`  
**Target project:** `bot_trading`  
**Target branch:** `feature/GRU`  
**Observed failing run:** `R20260922T160843`  

---

# 0. Mandatory objective

The implementation is complete only when a real Ubuntu live canary executes the entire loop successfully and ends at independently validated:

```text
FINAL_GO
AI_LOOP_COMPLETE=GO
```

The implementation team MUST NOT stop after fixing the current startup policy bug.

If any new bug appears during unit, integration, restart, synthetic, or live testing, the team must:

```text
capture evidence
→ reproduce deterministically
→ add regression test
→ fix root cause
→ rerun complete test suite
→ rerun 100-loop synthetic soak
→ rerun a brand-new live canary
→ repeat until FINAL_GO
```

An ai-loop implementation defect is never an acceptable final blocker.

---

# 1. Current diagnosis

The last real run produced:

```text
ai-loopd-v3 version=4.4.0 run=R20260922T160843 phase=IMPLEMENTING
OPENCODE_SEMANTIC_CAPABILITY=PASS
BROWSER_BROKER=PASS
DETERMINISTIC_CHAT_POLICY RETRY attempt=1 purpose=startup
  CHAT_SURFACE_HYDRATION_TIMEOUT
DETERMINISTIC_CHAT_POLICY RETRY attempt=2 purpose=startup
  CHAT_SURFACE_HYDRATION_TIMEOUT
CHATGPT_CHAT_POLICY_GUARD_FAILED
```

The controller exited before doing useful reconciliation.

The current failure class has two distinct root causes.

## 1.1 Hydration ordering bug

The browser policy logic can treat the presence of the reasoning trigger (`High`) as enough evidence that policy controls are hydrated.

Conceptually:

```javascript
return q.chat || q.trigger ? q : null;
```

This is unsafe because the reasoning trigger may mount before the Chat/Work surface control.

Possible live sequence:

```text
t=0 ms     High trigger exists
           Chat control absent

t=300 ms   High trigger exists
           Chat control absent

t=900 ms   High trigger exists
           Chat control appears and is selected
```

The current implementation may stop waiting at `t=0` because `q.trigger` is truthy.

It then tries to interact with Chat before Chat exists.

## 1.2 Truthy-object wait predicate bug

A wait such as:

```javascript
waitUntil(() => observe('surface_actionable'))
```

is unsafe if `observe()` always returns an object.

The object itself is truthy even when:

```text
surface_actionable = false
```

The wait can therefore finish immediately.

Every wait predicate must return either:

```text
true / valid terminal state
```

or:

```text
false / null
```

until its actual condition is satisfied.

## 1.3 Startup policy guard is placed too early

The runtime currently treats startup policy verification as a fatal gate.

That is unnecessary during a resume/startup phase when the controller is only trying to:

- observe current state;
- reconcile an existing run;
- read an existing conversation;
- decide what phase it is in.

There is no outbound side effect yet.

The hard Chat/Sol/High gate belongs immediately before any outbound controller message.

Correct architecture:

```text
startup / resume
    ↓
browser starts
    ↓
best-effort startup policy probe
    ├─ PASS → checkpoint
    └─ temporarily unproven → log + continue read-only
    ↓
reconcile state
    ↓
observe assistant / CI / pending actions
    ↓
before ANY outbound Send
    ↓
HARD POLICY GATE
    ↓
Chat + GPT-5.6 Sol + High proven
    ↓
Send allowed
```

---

# 2. Non-negotiable invariants

1. `startup` / `resume` policy failure caused only by temporary UI hydration MUST NOT terminate the controller.
2. Startup must never send a message while policy is unproven.
3. Every outbound Send MUST execute a fresh hard policy gate.
4. The hard policy gate must prove:
   ```text
   surface = Chat
   model contract = GPT-5.6 Sol
   reasoning = High
   ```
5. The reasoning trigger MUST NOT satisfy the Chat surface hydration wait.
6. A truthy object MUST NOT accidentally satisfy a wait predicate.
7. No blind resend after possible Send.
8. No duplicate attachment/action/commit/pipeline side effect after restart.
9. Startup deferral must not weaken final pre-Send safety.
10. The implementation team must continue live debugging until a full loop reaches validated GO.

---

# 3. Target architecture

## 3.1 Startup policy probe

Introduce explicit modes:

```text
POLICY_PROBE
POLICY_HARD_GATE
```

### `POLICY_PROBE`

Used at:

```text
startup
resume
read-only reconciliation
```

Behavior:

```text
try to observe Chat/Sol/High
if PASS:
    persist policy checkpoint
if temporarily unavailable:
    persist DEFERRED
    preserve diagnostics
    continue read-only
if definitely wrong but correctable:
    optional bounded correction is allowed
if unsafe/unknown:
    do not Send
    continue only read-only paths
```

A probe must not cause process termination merely because the UI is not hydrated.

### `POLICY_HARD_GATE`

Used immediately before:

```text
bootstrap Send
evidence Send
procede
follow-up
final-review request
diagnosis request
replan request
any other controller-originated message
```

Behavior:

```text
wait until Chat surface controls are actually hydrated
prove Chat selected
wait until reasoning/model control is hydrated
prove High
prove Sol contract
only then permit Send
```

A hard gate failure blocks Send but should leave the controller alive when safe to retry later.

---

# 4. Surface hydration state machine

Implement explicit states:

```text
SURFACE_UNKNOWN
SURFACE_WAITING
SURFACE_CHAT_SELECTED
SURFACE_WORK_SELECTED
SURFACE_OTHER_SELECTED
SURFACE_TIMEOUT
```

## 4.1 Surface wait predicate

Correct predicate shape:

```javascript
const q = await observeSurface();

if (q.chatSelected) return q;
if (q.chatActionable) return q;
if (q.otherSurfaceSelected && q.chatActionable) return q;

return null;
```

Do NOT use:

```javascript
return q;
```

Do NOT use reasoning state as a substitute for surface readiness.

## 4.2 Reasoning wait

Only after the surface phase is complete:

```text
surface == Chat
```

begin the reasoning phase.

Correct reasoning predicate:

```javascript
const q = await observeReasoning();

if (q.selectedEffort === 'high') return q;
if (q.reasoningControlActionable) return q;

return null;
```

---

# 5. Hard policy gate

The final proof immediately before Send must be performed in one deterministic broker operation.

Required proof:

```json
{
  "surface": "chat",
  "surface_selected": true,
  "reasoning": "high",
  "model_contract": "gpt-5.6-sol",
  "proof": {
    "surface": "...",
    "reasoning": "...",
    "model": "..."
  }
}
```

If any field is UNKNOWN:

```text
SEND FORBIDDEN
```

---

# 6. Startup/resume behavior

Current behavior:

```text
ensure_chat_policy(startup)
→ error
→ raise RuntimeError
→ daemon exits
```

Target:

```text
startup_policy_probe()
    ↓
PASS
or
DEFERRED_TRANSIENT
    ↓
persist checkpoint
    ↓
continue FSM read-only reconciliation
```

Example desired log:

```text
STARTUP_POLICY PROBE_DEFERRED reason=CHAT_SURFACE_NOT_HYDRATED
STARTUP_POLICY controller_continues_read_only=true
```

Later, before a Send:

```text
OUTBOUND_POLICY HARD_GATE purpose=evidence_send
CHAT_SURFACE PASS surface=chat
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high
DELIVERY_READY ...
```

---

# 7. Controller changes

The controller must classify policy errors.

## 7.1 Retryable/deferred

Examples:

```text
CHAT_SURFACE_HYDRATION_TIMEOUT
REASONING_CONTROL_HYDRATION_TIMEOUT
SURFACE_TEMPORARILY_UNAVAILABLE
BROWSER_UI_NOT_SETTLED
```

At startup/resume:

```text
defer + continue read-only
```

Before Send:

```text
block Send + bounded retry/poll
```

## 7.2 Fatal policy errors

Examples:

```text
WRONG_ACCOUNT
PROJECT_CONTEXT_OTHER
UNSAFE_SURFACE
UNRECOVERABLE_BROWSER_AUTH
```

These may stop outbound work and require explicit resolution.

They must not be conflated with hydration delay.

---

# 8. Team

**Team size: 8**

| Role | Code | Responsibility |
|---|---|---|
| Technical Lead | TL | integration, invariants, release decision |
| Browser Policy Engineer | BPE | hydration and Chat/Sol/High broker logic |
| Controller/FSM Engineer | CFE | startup deferral, pre-Send hard gate |
| State/Idempotency Engineer | SIE | restart/reconcile safety |
| Semantic/OpenCode Engineer | SOE | verify browser-free semantic path remains intact |
| Test & Chaos Engineer | TCE | regressions, fault injection, soak |
| SRE / Live Validation Engineer | SRE | Ubuntu canary, diagnostics, repeated live cycles |
| Independent Auditor | IRA | evidence review and release gates |

---

# 9. Atomic backlog

## WS0 — Freeze evidence

| ID | Owner | Task |
|---|---|---|
| B001 | TL | Create context snapshot for `R20260922T160843`. |
| B002 | IRA | Preserve current source SHA manifest. |
| B003 | TCE | Preserve both `ENSURE_CHAT_POLICY` diagnostics as fixtures. |
| B004 | TCE | Add exact log regression for startup hydration timeout. |

## WS1 — Surface hydration correctness

| ID | Owner | Task |
|---|---|---|
| B005 | BPE | Separate surface observation from reasoning observation. |
| B006 | BPE | Remove any `q.chat || q.trigger` style readiness predicate. |
| B007 | BPE | Implement `waitForChatSurfaceHydration()`. |
| B008 | BPE | Ensure wait predicate returns null until Chat is selected/actionable. |
| B009 | BPE | Add Chat-selected fast path. |
| B010 | BPE | Add Work/Codex→Chat correction path. |
| B011 | TCE | Test High present before Chat. |
| B012 | TCE | Test Chat appears after 100 ms. |
| B013 | TCE | Test Chat appears after 1 s. |
| B014 | TCE | Test Chat appears near timeout boundary. |
| B015 | TCE | Test Chat never appears. |
| B016 | IRA | Audit no reasoning signal can terminate surface wait. |

## WS2 — Reasoning hydration correctness

| ID | Owner | Task |
|---|---|---|
| B017 | BPE | Start reasoning check only after Chat surface proof. |
| B018 | BPE | Implement `waitForReasoningHydration()`. |
| B019 | BPE | Preserve High→Sol proof contract. |
| B020 | BPE | Require persisted selected High state. |
| B021 | TCE | Test delayed High trigger. |
| B022 | TCE | Test Medium→High transition. |
| B023 | TCE | Test trigger exists but selected state unknown. |
| B024 | IRA | Audit no successful click is treated as proof by itself. |

## WS3 — Fix truthy-object waits

| ID | Owner | Task |
|---|---|---|
| B025 | BPE | Locate all broker `waitUntil` predicates. |
| B026 | BPE | Replace object-truthiness waits with explicit condition predicates. |
| B027 | TCE | Add a regression where observer object exists but condition=false. |
| B028 | TCE | Add a regression where condition becomes true only on fifth observation. |
| B029 | IRA | Audit entire broker for equivalent truthy-object bugs. |

## WS4 — Startup policy deferral

| ID | Owner | Task |
|---|---|---|
| B030 | CFE | Split startup probe from hard policy gate. |
| B031 | CFE | Introduce `STARTUP_POLICY=PASS|DEFERRED|BLOCKED`. |
| B032 | CFE | Treat hydration timeout as DEFERRED at startup. |
| B033 | CFE | Persist startup policy checkpoint/diagnostics. |
| B034 | CFE | Continue read-only FSM after DEFERRED. |
| B035 | CFE | Prevent startup DEFERRED state from authorizing Send. |
| B036 | TCE | Test existing-run resume with startup hydration timeout. |
| B037 | TCE | Verify controller stays alive. |
| B038 | TCE | Verify assistant/state reconciliation continues. |
| B039 | IRA | Verify startup deferral does not weaken Send protection. |

## WS5 — Mandatory pre-Send hard gate

| ID | Owner | Task |
|---|---|---|
| B040 | CFE | Route every outbound controller message through hard policy gate. |
| B041 | CFE | Audit bootstrap Send. |
| B042 | CFE | Audit evidence Send. |
| B043 | CFE | Audit `procede`. |
| B044 | CFE | Audit diagnosis request. |
| B045 | CFE | Audit replan request. |
| B046 | CFE | Audit final review request. |
| B047 | CFE | Audit artifact follow-up message. |
| B048 | TCE | Assert no Send path bypasses hard gate. |
| B049 | IRA | Perform source-wide outbound-message audit. |

## WS6 — Restart/idempotency

| ID | Owner | Task |
|---|---|---|
| B050 | SIE | Verify deferred startup state survives restart. |
| B051 | SIE | Verify pending delivery ledger survives restart. |
| B052 | SIE | Reconcile existing user-turn marker before resend. |
| B053 | TCE | Kill controller during startup deferred state. |
| B054 | TCE | Kill controller immediately before hard gate. |
| B055 | TCE | Kill controller immediately after Send click. |
| B056 | TCE | Verify zero duplicate Send after all restart scenarios. |
| B057 | IRA | Approve idempotency evidence. |

## WS7 — Preserve previous v4.4 fixes

| ID | Owner | Task |
|---|---|---|
| B058 | BPE | Re-run canonical project tests. |
| B059 | BPE | Re-run fresh-draft tests. |
| B060 | BPE | Re-run attachment proof tests. |
| B061 | BPE | Re-run attachment idempotency tests. |
| B062 | TCE | Re-run stale unsent draft tests. |
| B063 | TCE | Re-run exact attachment DOM regression. |
| B064 | IRA | Verify v4.6 does not regress project/attachment fixes. |

## WS8 — Post-Send pipeline

| ID | Owner | Task |
|---|---|---|
| B065 | SOE | Verify assistant observer path. |
| B066 | SOE | Verify OpenCode text-only classification. |
| B067 | SOE | Verify fenced-block metadata selection. |
| B068 | TCE | Test malformed semantic output retry. |
| B069 | TCE | Test GENERATING→SETTLED. |
| B070 | TCE | Test rate-limit path. |
| B071 | IRA | Verify no model browser authority reintroduced. |

## WS9 — Tool integrations

| ID | Owner | Task |
|---|---|---|
| B072 | SRE | Verify local operator path. |
| B073 | SRE | Verify GitHub read-only path. |
| B074 | SRE | Verify VPS wrapper path. |
| B075 | SRE | Verify Semaphore read-only/evidence path. |
| B076 | TCE | Test integration failure classifications. |
| B077 | IRA | Verify exact identity binding for GitHub/CI/VPS evidence. |

## WS10 — Synthetic full-loop acceptance

| ID | Owner | Task |
|---|---|---|
| B078 | TCE | Run full fake loop startup→Send→action→evidence→CI→GO. |
| B079 | TCE | Run failure→diagnosis→replan→second iteration→GO. |
| B080 | TCE | Inject startup hydration delay in full fake loop. |
| B081 | TCE | Inject browser crash during startup probe. |
| B082 | TCE | Inject browser crash before Send. |
| B083 | TCE | Run 100 consecutive synthetic full loops. |
| B084 | IRA | Require 100/100 GO and zero duplicate side effects. |

## WS11 — Live Ubuntu canary

| ID | Owner | Task |
|---|---|---|
| B085 | SRE | Clean all old controller/broker/OpenCode processes. |
| B086 | SRE | Run full preflight. |
| B087 | SRE | Launch brand-new safe live canary. |
| B088 | IRA | Prove project/fresh draft. |
| B089 | IRA | Prove Chat/Sol/High. |
| B090 | IRA | Prove exact attachment once. |
| B091 | IRA | Prove exact bootstrap Send once. |
| B092 | IRA | Prove assistant settlement. |
| B093 | IRA | Prove local action round-trip. |
| B094 | IRA | Prove GitHub round-trip. |
| B095 | IRA | Prove VPS round-trip. |
| B096 | IRA | Prove Semaphore round-trip. |
| B097 | IRA | Prove multiple post-bootstrap Sends. |
| B098 | IRA | Prove FINAL_GO validation. |
| B099 | SRE | Archive complete live evidence. |

## WS12 — Mandatory fix-until-GO loop

| ID | Owner | Task |
|---|---|---|
| B100 | TL | If live canary fails, do not finish. |
| B101 | TL | Create defect record from live evidence. |
| B102 | TCE | Add deterministic regression reproducer. |
| B103 | Assigned engineer | Implement root-cause fix. |
| B104 | TCE | Run complete local suite. |
| B105 | TCE | Run 100-loop soak. |
| B106 | SRE | Run a brand-new live canary. |
| B107 | TL | Repeat B100-B106 until GO. |
| B108 | IRA | Approve only a final clean run ending in GO. |

## WS13 — Target plan acceptance

| ID | Owner | Task |
|---|---|---|
| B109 | TL | Preflight real target plan. |
| B110 | IRA | Verify re-entry guard against current branch state. |
| B111 | SRE | Launch new real target loop. |
| B112 | IRA | Observe through all required tool/CI phases. |
| B113 | TL | Apply same fix-until-success rule to any ai-loop bug. |
| B114 | IRA | Require validated GO. |

## WS14 — Release

| ID | Owner | Task |
|---|---|---|
| B115 | TL | Set runtime version to 4.6.0. |
| B116 | TCE | Run py_compile. |
| B117 | TCE | Run node --check. |
| B118 | TCE | Run applicable legacy selftests. |
| B119 | TCE | Run v4.6 regression suite. |
| B120 | TCE | Run final 100-loop soak. |
| B121 | SRE | Test clean install and v4.5→v4.6 upgrade. |
| B122 | IRA | Build release evidence matrix. |
| B123 | IRA | Generate SHA-256 manifest. |
| B124 | TL | Produce `ai-loop-v4.6.tar.gz` only after all gates pass. |

---

# 10. Mandatory regression scenarios

## Regression R160843-A — reasoning appears before Chat

```text
read 1:
  reasoning=high
  chat absent

read 2:
  reasoning=high
  chat absent

read 5:
  reasoning=high
  chat present+selected
```

Expected:

```text
PASS
no outer retry
no premature timeout
```

## Regression R160843-B — observer object truthiness

Observer returns:

```json
{"surface_actionable": false}
```

for the first four reads.

Expected:

```text
wait continues
```

On fifth read:

```json
{"surface_actionable": true}
```

Expected:

```text
wait completes
```

## Regression R160843-C — startup probe deferred

Existing run resumes while Chat surface is not hydrated.

Expected:

```text
STARTUP_POLICY=DEFERRED
controller remains alive
no Send
FSM read-only reconciliation continues
```

## Regression R160843-D — hard gate later succeeds

After deferred startup, before a later evidence Send:

```text
Chat hydrates
High selected
```

Expected:

```text
HARD_POLICY_GATE=PASS
Send occurs exactly once
```

---

# 11. Release gates

| Gate | Requirement |
|---|---|
| G0 | evidence frozen |
| G1 | R160843-A regression green |
| G2 | R160843-B regression green |
| G3 | startup deferral green |
| G4 | hard pre-Send gate green |
| G5 | project/fresh-draft regressions green |
| G6 | attachment regressions green |
| G7 | restart/idempotency matrix green |
| G8 | assistant/semantic/action path green |
| G9 | local/GitHub/VPS/Semaphore paths green |
| G10 | CI/replan path green |
| G11 | 100/100 synthetic loops GO |
| G12 | live Ubuntu safe canary FINAL_GO |
| G13 | real target loop FINAL_GO |
| G14 | independent audit approves evidence |
| G15 | clean release artifact + manifest |

No gate may be skipped.

---

# 12. Expected healthy live log

A successful resume/start may legitimately show:

```text
ai-loopd-v3 version=4.6.0 ...
BROWSER_BROKER=PASS ...
STARTUP_POLICY PROBE_DEFERRED reason=surface_not_hydrated
STARTUP_POLICY controller_continues_read_only=true
```

This is acceptable because no Send is occurring.

Before an outbound message, the log MUST show:

```text
OUTBOUND_POLICY HARD_GATE purpose=...
CHAT_SURFACE PASS surface=chat
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high
DELIVERY_READY ...
DELIVERY_SENT ...
DELIVERY_PROOF PASS ...
```

The final live run must end with:

```text
FINAL_GO_VALIDATED ...
AI_LOOP_COMPLETE=GO
```

---

# 13. Pre-mortem

## Failure 1 — startup deferral accidentally weakens Send safety

**Mitigation**
- one central outbound Send function;
- hard policy gate inside that function;
- source-wide audit;
- test that every outbound message passes through it.

## Failure 2 — hydration bug moves from Chat surface to reasoning control

**Mitigation**
- independent surface and reasoning state machines;
- explicit condition predicates;
- delayed-control fixtures.

## Failure 3 — controller remains alive but spins forever

**Mitigation**
- bounded read-only reconciliation intervals;
- phase progress watchdog;
- structured diagnostics;
- no blind high-frequency polling.

## Failure 4 — later live stage exposes new untested bug

**Mitigation**
- mandatory recursive fix-until-GO protocol;
- team cannot stop at first downstream failure.

---

# 14. ADR

## Decision

Make startup policy verification non-fatal for transient hydration failures, while making the pre-Send policy gate stronger and centralized.

## Why

Startup/read-only reconciliation has no outbound side effect and therefore does not need to die because a visual control has not mounted yet.

Outbound Send is the safety boundary.

## Consequences

Positive:

- resume is resilient to transient UI hydration;
- no weaker Send protection;
- fewer unnecessary daemon restarts;
- clearer separation between read-only reconciliation and side effects.

Costs:

- controller policy state becomes two-mode;
- requires comprehensive outbound-message audit.

---

# 15. Team execution command

Run in an OpenCode session:

```text
/team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_6_STARTUP_POLICY_DEFERRED_GUARD_20260922T2357-0500.md; execute all local, integration, restart, synthetic and live Ubuntu tests required by the plan. If any bug appears during live testing, capture evidence, add a regression, fix it, rerun the full suite and rerun a brand-new canary. Do not finish until a real live loop reaches independently validated FINAL_GO / AI_LOOP_COMPLETE=GO.
```

---

# 16. Independent verification command

After `/team` claims completion:

```text
/ralph verify every invariant, task acceptance, restart matrix, R20260922T160843 regressions, 100-loop soak, live Ubuntu tool round-trips, FINAL_GO evidence and release gate G0-G15 in IMPLEMENTATION_PLAN_AI_LOOP_V4_6_STARTUP_POLICY_DEFERRED_GUARD_20260922T2357-0500.md. Do not accept source assertions or partial logs as proof.
```

---

# 17. Definition of Done

v4.6 is complete only when:

```text
[PASS] reasoning-before-Chat regression
[PASS] truthy-object wait regression
[PASS] startup policy hydration timeout does not kill controller
[PASS] startup deferral never authorizes Send
[PASS] every outbound Send executes hard Chat/Sol/High gate
[PASS] previous project/fresh-draft fixes remain green
[PASS] previous attachment fixes remain green
[PASS] restart matrix has zero duplicate side effects
[PASS] local action live
[PASS] GitHub live
[PASS] VPS live
[PASS] Semaphore live
[PASS] multiple evidence Sends live
[PASS] 100/100 synthetic loops GO
[PASS] safe Ubuntu live canary FINAL_GO
[PASS] real target loop FINAL_GO
[PASS] no uncaught Python/Node exception in final acceptance
[PASS] independent audit G0-G15
```

Anything less is an unfinished release candidate.
