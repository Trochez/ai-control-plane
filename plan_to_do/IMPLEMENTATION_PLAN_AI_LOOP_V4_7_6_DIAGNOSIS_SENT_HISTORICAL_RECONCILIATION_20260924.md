# IMPLEMENTATION PLAN — ai-loop v4.7.6 Historical DIAGNOSIS_SENT Reconciliation

**Target release:** 4.7.6  
**Authoritative run:** `R20260923T012014`  
**State file:** `/var/lib/ai-loop/state/R20260923T012014.v3.json`  
**Current phase:** `FAILURE_ANALYSIS`  
**Current stage:** `DIAGNOSIS_SENT`  
**Candidate SHA:** `0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390`

## 1. Proven current state

v4.7.5 already proves:

- Browser Broker is installed and active from the expected artifact.
- Browser-realm `normalizeTurnInventory` failure is fixed.
- Live DOM extraction succeeds.
- Canonical turn inventory contains 3 user turns, 2 assistant turns, total 5.
- Immutable delivery `failure-evidence-025d7f19b1dd83b26733` is matched to its following assistant response.
- Immutable delivery `diagnosis-0c11a13e0c6c` is matched to its following assistant diagnosis response.
- No immutable delivery was resent.
- Controller still waits at `DIAGNOSIS_SENT` as if a new response were required.

Therefore the remaining defect is controller-side milestone reconciliation.

## 2. Mandatory objective

When resuming an already-delivered milestone such as `DIAGNOSIS_SENT`, the controller MUST accept an already-existing, settled, causally-matched historical assistant turn as satisfying the response milestone.

It MUST NOT wait for a new response and MUST NOT resend the diagnosis request.

However, satisfying `DIAGNOSIS_SENT` does not automatically make the diagnosis authoritative if an earlier operator action remains unresolved.

## 3. Required controller behavior

### 3.1 Historical response adoption

For:

```text
delivery_id = diagnosis-0c11a13e0c6c
stage       = DIAGNOSIS_SENT
```

if canonical turn inventory proves the matching user delivery exists, a following assistant turn exists, and that assistant turn is settled, then persist:

```text
HISTORICAL_RESPONSE_RECONCILED
delivery_id=diagnosis-0c11a13e0c6c
assistant_turn_id=<existing assistant id>
assistant_turn_index=<existing index>
resend=false
```

and semantically process that existing assistant turn exactly once.

### 3.2 Idempotency

Persist a consumed-response ledger keyed by:

```text
delivery_id
assistant_turn_id
assistant_text_sha256
```

A resume must not classify or act on the same assistant response twice.

### 3.3 Stage advancement

`DIAGNOSIS_SENT` must not wait forever once its historical assistant response has been reconciled.

## 4. Causal precedence requirement

The earlier assistant response following:

```text
failure-evidence-025d7f19b1dd83b26733
```

requested an exact read-only Semaphore Bash action.

That action was skipped before the diagnosis request was sent.

Therefore the existing diagnosis response following:

```text
diagnosis-0c11a13e0c6c
```

must be marked:

```text
provisional=true
authoritative=false
reason=UNRESOLVED_PRIOR_OPERATOR_ACTION
```

Required sequence:

```text
historical diagnosis response reconciled
        ↓
detect unresolved earlier ACTION_REQUIRED
        ↓
mark diagnosis provisional
        ↓
materialize exact requested command
        ↓
execute once through authorized operator adapter
        ↓
persist execution ledger
        ↓
deliver literal result once to SAME ChatGPT chat
        ↓
wait for settled assistant response
        ↓
request/obtain diagnosis reconciliation/update
        ↓
mark reconciled diagnosis authoritative
        ↓
DIAGNOSIS_READY
        ↓
replan
```

## 5. Operator-action execution contract

OpenCode/controller MAY operate in `bot_trading` and on the VPS for controller-authorized operational work.

Execution requirements:

- exact fenced block materialization;
- exact block SHA;
- exact command SHA;
- target recorded;
- execute at most once;
- stdout/stderr captured;
- exit code captured;
- started/completed timestamps persisted;
- result delivery has unique immutable delivery id;
- resume must not execute the same action twice.

## 6. Hard safety invariants

The controller MUST NOT:

- resend `failure-evidence-025d7f19b1dd83b26733`;
- resend `diagnosis-0c11a13e0c6c`;
- create a new chat;
- send replan while a prior operator action is unresolved;
- treat `DIAGNOSIS_SENT` as requiring a new response when a matching settled historical assistant response already exists;
- process the same assistant response more than once;
- execute the same operator action more than once.

## 7. Regression tests

Add controller-level tests for:

1. `DIAGNOSIS_SENT` + matched settled historical assistant → reconcile existing response.
2. Same state resumed twice → assistant response consumed once.
3. Historical response present → no wait for new response.
4. Historical response present → no diagnosis resend.
5. Earlier unresolved operator action → diagnosis marked provisional.
6. Provisional diagnosis cannot trigger replan.
7. Pending historical action executes exactly once.
8. Action result delivery occurs exactly once.
9. Resume after action execution does not execute action again.
10. Post-action diagnosis reconciliation supersedes provisional diagnosis.
11. Only reconciled authoritative diagnosis can transition to `DIAGNOSIS_READY`.
12. Exact current five-turn live fixture reproduces the expected path.

## 8. Runtime/versioning

Version as `4.7.6`.

Run:

```text
python compile
node syntax
controller selftests
historical-response reconciliation tests
operator-action idempotency tests
observer tests
Semaphore tests
attachment tests
resume tests
100-loop synthetic soak
```

## 9. Live acceptance

After clean install, resume the SAME state:

```text
/var/lib/ai-loop/state/R20260923T012014.v3.json
```

Required live progression:

```text
ai-loopd-v3 version=4.7.6
TURN_INVENTORY total=5 users=3 assistants=2
DELIVERY_MATCH id=failure-evidence-025d7f19b1dd83b26733 ...
DELIVERY_MATCH id=diagnosis-0c11a13e0c6c ...
HISTORICAL_RESPONSE_RECONCILED
delivery_id=diagnosis-0c11a13e0c6c
resend=false
DIAGNOSIS_PROVISIONAL
reason=UNRESOLVED_PRIOR_OPERATOR_ACTION
HISTORICAL_CAUSAL_RECONCILIATION
PENDING_OPERATOR_ACTION
ACTION_REQUIRED
OPERATOR_ACTION_EXECUTED count=1
OPERATOR_RESULT_DELIVERED count=1
ASSISTANT_OBSERVER SETTLED
DIAGNOSIS_RECONCILED
DIAGNOSIS_READY
PLAN_READY
IMPLEMENTING
...
CI SUCCESS
FINAL_GO
AI_LOOP_COMPLETE=GO
```

If another ai-loop defect appears, capture literal evidence, add a deterministic regression, fix root cause, reinstall, and continue the SAME run.

## 10. `/team` execution prompt

```text
/team implement completely IMPLEMENTATION_PLAN_AI_LOOP_V4_7_6_DIAGNOSIS_SENT_HISTORICAL_RECONCILIATION_20260924.md. The remaining proven defect is controller-side milestone reconciliation: v4.7.5 already extracts and matches the five historical turns, including the existing assistant response following diagnosis-0c11a13e0c6c, but the controller still waits at DIAGNOSIS_SENT for a new response. Reconcile the already-existing settled historical assistant response exactly once, without resending diagnosis. Preserve causal precedence: the earlier assistant response following failure-evidence-025d7f19b1dd83b26733 requested a read-only operator action that remains unresolved, so the current diagnosis must be marked provisional until that exact action is executed once, its literal result is returned once, and GPT Web reconciles/updates the diagnosis. Do not create a new chat or resend immutable deliveries. Version as 4.7.6, run all regressions and 100-loop soak, install cleanly, resume the SAME R20260923T012014 state, and continue fixing the live run until FINAL_GO / AI_LOOP_COMPLETE=GO.
```

## 11. Definition of done

The implementation is not complete at local PASS.

It is complete only when the same authoritative run reaches:

```text
FINAL_GO
AI_LOOP_COMPLETE=GO
```

with no duplicate immutable delivery and no duplicate operator action.
