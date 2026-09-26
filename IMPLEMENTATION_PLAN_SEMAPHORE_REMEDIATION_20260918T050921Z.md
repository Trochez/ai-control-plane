# Implementation & Release Plan â€” Semaphore COMPLETE_GO with One Remediation Commit

**Generated:** 2026-09-17 14:01:10 -05  
**Repository:** `Trochez/bot_trading`  
**Target branch:** `feature/GRU`  
**Failed accidental SHA:** `258a111c031dee9643cffb920518fcc1ca392565`  
**Base implementation SHA:** `dc4e2eef1eaeaf439f0d3b8b995a17f0c3940c60`  
**Canonical remediation commit:** `44505ddbfa5062dc1c712fc90db72cb0c54de924`  
**Required final topology:** `d4960be... -> dc4e2eef... -> 44505ddb...`  
**Commit budget after `dc4e2eef...`: exactly 1 remediation commit in final branch history**  
**Additional commits after `44505ddb...`: 0**

---

## 1. Mandatory objective

Achieve **Semaphore COMPLETE_GO** for `feature/GRU` while satisfying all of the following simultaneously:

1. The final branch history contains exactly one remediation commit after `dc4e2eef1eaeaf439f0d3b8b995a17f0c3940c60`.
2. That remediation commit contains the complete implementation necessary to close every finding from the previous diagnosis.
3. No follow-up, hotfix, revert, â€œfix CIâ€, or evidence-only commit is permitted after the canonical remediation commit.
4. The accidental commit `258a111c031dee9643cffb920518fcc1ca392565` must **not** remain in the final `feature/GRU` history.
5. Semaphore must be triggered only after exhaustive exact-SHA preflight validation has passed.
6. The complete six-block Semaphore production workflow must reach GO.
7. Production must finish at the same exact SHA as `feature/GRU`, tracked-clean, without mutating `/tmp/log`.
8. No Semaphore credits are to be spent on known-bad or incompletely validated SHAs.

The canonical remediation commit is already available as:

`44505ddbfa5062dc1c712fc90db72cb0c54de924`

The plan therefore treats this SHA as immutable. **No new code commit is allowed.**

---

## 2. Diagnosis translated into implementation requirements

The previous failure establishes two implementation requirements and one repository-state requirement.

### R1 â€” Restore `unittest` lifecycle

The failed candidate defined a project helper named:

```python
def run(self, root, service="inactive", expect=0):
```

inside a `unittest.TestCase` subclass.

This replaced `unittest.TestCase.run(...)`, causing the observed:

```text
Ran 0 tests
NO TESTS RAN
```

Required correction:

```python
run(...) -> run_state(...)
```

and update every project call site accordingly.

### R2 â€” Enforce exact P2 result identity

The P2 observer must never authorize the current execution using a terminal result produced by a different build that happens to share the same Git SHA.

Required authority key:

```text
(CIRCLE_BUILD_NUM, EXPECTED_SHA)
```

Required result path:

```text
p2-${CIRCLE_BUILD_NUM}-${EXPECTED_SHA}.status
```

The observer must reject stale same-SHA/different-build results.

### R3 â€” Remove the accidental branch head without adding a commit

`feature/GRU` currently references accidental SHA `258a111...`.

A revert commit is forbidden because it would consume the one-commit budget and preserve the accidental commit in final history.

Required operation:

```text
feature/GRU
258a111...  --controlled ref rewrite-->  44505ddb...
```

This is a Git ref operation, **not a new commit**.

---

## 3. Non-negotiable invariants

| ID | Invariant |
|---|---|
| INV-01 | Final `feature/GRU` HEAD = `44505ddbfa5062dc1c712fc90db72cb0c54de924` |
| INV-02 | Parent of final HEAD = `dc4e2eef1eaeaf439f0d3b8b995a17f0c3940c60` |
| INV-03 | `258a111...` is not reachable from final `feature/GRU` |
| INV-04 | No commit is created after `44505ddb...` |
| INV-05 | No amend/rebase/cherry-pick/revert is used after final SHA publication |
| INV-06 | Semaphore is never launched for `258a111...` again |
| INV-07 | Semaphore is launched only when remote `feature/GRU` equals final SHA |
| INV-08 | Exact-SHA validation must be executed from a fresh detached clone |
| INV-09 | Production deployment must use the exact final SHA, not â€œlatest branchâ€ semantics |
| INV-10 | Production tracked files must be clean after deployment |
| INV-11 | Existing untracked runtime artifacts must not be deleted merely to obtain cleanliness |
| INV-12 | `/tmp/log` must remain unchanged by implementation/deployment cleanup |
| INV-13 | No broad `git clean`, destructive reset, or runtime artifact deletion |
| INV-14 | Dummy/test branches such as `__dummy_should_not_use` must be absent before COMPLETE_GO |
| INV-15 | Six Semaphore blocks must pass in dependency order |
| INV-16 | Any retry consumes credits only after evidence proves the failure was infrastructure/transient and the exact SHA remains unchanged |
| INV-17 | A code/contract failure after final publication does not authorize an additional commit under this plan |

---

## 4. Required final Git topology

### Accepted topology

```text
d4960be98cee3edef96413ee77f200ce744d3461
    |
    v
dc4e2eef1eaeaf439f0d3b8b995a17f0c3940c60
    |
    v
44505ddbfa5062dc1c712fc90db72cb0c54de924   <-- feature/GRU
```

### Forbidden topology

```text
dc4e2eef...
    |
    +-- 258a111...  noop
            |
            +-- any fix commit
```

Also forbidden:

```text
dc4e2eef... -> 258a111... -> revert -> final fix
```

The accidental SHA may remain as an unreachable Git object until normal GitHub garbage collection; it simply must not be reachable from `feature/GRU`.

---

## 5. Team

**Team size: 5**

| Role | Count | Responsibility |
|---|---:|---|
| Release / Integration Lead | 1 | Owns commit budget, branch topology, final gates, Semaphore trigger decision |
| Python & Test Engineer | 1 | Validates unittest fix, targeted tests, complete Python test discovery |
| CI / Semaphore Engineer | 1 | Reproduces `GRU validation`, validates six-block workflow and watches Semaphore |
| Runtime / P2 & Production Engineer | 1 | Validates P2 exact identity, deployment, production SHA/cleanliness/runtime invariants |
| Independent Verification Engineer | 1 | Performs read-only second-person verification of SHA, tree, diff, evidence, COMPLETE_GO checklist |

### Separation of duties

No person/agent that changes the final branch ref may be the only verifier of the final branch topology.

No Semaphore trigger occurs until the Independent Verification Engineer records GO for the preflight package.

---

## 6. Execution strategy

The plan uses a **validate-before-publish** strategy:

```text
validate immutable commit object
        â†“
independent audit
        â†“
controlled branch ref rewrite
        â†“
fresh remote exact-SHA validation
        â†“
ONE Semaphore production workflow
        â†“
six blocks PASS
        â†“
production exact-SHA verification
        â†“
COMPLETE_GO
```

The key credit-saving mechanism is that all deterministic checks are run before Semaphore.

---

## 7. Phase gates

### Gate G0 â€” Evidence freeze

Required before any write:

- previous failure bundle archived;
- failed SHA recorded as `258a111...`;
- final remediation SHA recorded as `44505ddb...`;
- no uncertainty about which SHA contains which implementation.

**Exit:** `G0_GO`

### Gate G1 â€” Canonical remediation commit audit

Verify commit `44505ddb...` directly, without relying on branch names.

Required assertions:

```text
commit = 44505ddbfa5062dc1c712fc90db72cb0c54de924
parent = dc4e2eef1eaeaf439f0d3b8b995a17f0c3940c60
```

Diff relative to parent must contain exactly:

```text
ops/ci/observe_gru_p2_remote.sh
ops/ci/tests/test_p2_handoff_state_machine.py
```

Required validated blob identities:

```text
ops/ci/observe_gru_p2_remote.sh
blob = 001a58683d9bb791ad5bbc58ff8b9a9145d3960a

ops/ci/tests/test_p2_handoff_state_machine.py
blob = e46b9a0733c3866805b5177713293eb4c63f1a95
```

Verify no third file changed.

**Exit:** `G1_GO`

### Gate G2 â€” Exhaustive exact-SHA preflight

Use a fresh temporary detached clone checked out at `44505ddb...`.

Do not use the production checkout as the test workspace.

Run every mandatory check in Section 8.

**Exit:** `G2_GO` only if every mandatory check passes.

### Gate G3 â€” Independent review

Independent verifier checks:

- commit SHA;
- parent SHA;
- two-file diff;
- blob SHAs;
- preflight test outputs;
- no mandatory test failure hidden by a skip;
- Semaphore YAML still contains exactly six expected blocks;
- no additional commit is necessary.

**Exit:** `G3_GO`

### Gate G4 â€” Branch cutover

Precondition: explicit authorization for the non-fast-forward ref rewrite.

Atomically move:

```text
feature/GRU:
258a111c031dee9643cffb920518fcc1ca392565
    ->
44505ddbfa5062dc1c712fc90db72cb0c54de924
```

Do **not** create a revert commit.

Immediately verify remote branch HEAD, parent and compare topology.

**Exit:** `G4_GO`

### Gate G5 â€” Remote branch exact-SHA revalidation

Fresh-clone `feature/GRU` from GitHub and assert:

```text
HEAD == 44505ddb...
HEAD^ == dc4e2eef...
```

Run the deterministic CI validation set again against the remote branch state.

**Exit:** `G5_GO`

### Gate G6 â€” Single Semaphore launch

Only now trigger a **new** Semaphore workflow for the final SHA.

Do not rerun the failed workflow tied to `258a111...`.

The new workflow must report:

```text
SEMAPHORE_GIT_SHA = 44505ddbfa5062dc1c712fc90db72cb0c54de924
branch = feature/GRU
```

**Exit:** workflow accepted for exact SHA.

### Gate G7 â€” Six-block Semaphore GO

Required blocks, in order:

1. `GRU validation`
2. `Full-corpus acceptance launch`
3. `Full-corpus acceptance final watch`
4. `Deploy exact feature GRU SHA`
5. `P2 acceptance launch`
6. `P2 acceptance final watch`

Every block must be `Passed` or a contractually valid reused PASS backed by exact-SHA durable evidence.

No downstream block may be manually promoted around a failed dependency.

**Exit:** `G7_GO`

### Gate G8 â€” Production final verification

Verify production checkout:

```text
branch = feature/GRU
HEAD = 44505ddbfa5062dc1c712fc90db72cb0c54de924
tracked_status = clean
```

Confirm:

- `/tmp/log` unchanged by cleanup/deploy actions;
- no tracked drift;
- no deletion of runtime untracked artifacts;
- P2 durable final status belongs to exact final SHA/build;
- full-corpus evidence belongs to exact final SHA;
- no accidental/dummy remote branch remains if prohibited by release contract.

**Exit:** `G8_GO`

### Gate G9 â€” COMPLETE_GO

COMPLETE_GO can be declared only when all G0â€“G8 gates are GO.

---

## 8. Mandatory pre-Semaphore test matrix

All deterministic tests below must pass before spending another Semaphore run.

### 8.1 Test-file syntax

```bash
python3 -m py_compile \
  ops/ci/tests/test_p2_handoff_state_machine.py
```

Expected: exit `0`.

### 8.2 Observer shell syntax

```bash
bash -n ops/ci/observe_gru_p2_remote.sh
```

Expected: exit `0`.

### 8.3 Targeted P2 state-machine suite

```bash
python3 -m unittest -v \
  ops.ci.tests.test_p2_handoff_state_machine
```

Mandatory expected result:

```text
Ran 6 tests
OK
```

Mandatory named regressions:

```text
test_observer_rejects_stale_same_sha_other_build_result ... ok
test_observer_accepts_exact_current_build_result ... ok
```

### 8.4 Related remediation contracts

```bash
python3 -m unittest -v \
  ops.ci.tests.test_p2_external_evidence_contract \
  ops.ci.tests.test_single_commit_semaphore_contract \
  ops.ci.tests.test_post_p2_live_durability
```

Expected:

```text
Ran 3 tests
OK
```

### 8.5 Complete CI-contract discovery

```bash
python3 -m unittest discover \
  -s ops/ci/tests \
  -p 'test_*.py' \
  -v
```

Known validated baseline:

```text
Ran 38 tests
OK
```

Any reduction in discovered test count requires investigation before Semaphore.

### 8.6 Exact reproduction of `GRU validation / Core CI contracts`

Execute, in the same order as Semaphore:

```text
ops.ci.breaker.tests.test_ci_breaker
ops.gru.test_remediate_orphan_recovery_wait
apy.tests.test_gru_plan01_data_foundation.DataLoaderPlan01Tests
ops.ci.tests.test_p2_memory_bound_contract
apy.tests.test_raw_payload_persistence
ops.ci.tests.test_full_corpus_durability_contract
ops.ci.tests.test_p1_dependency_validator_contract
ops.ci.tests.test_p2_handoff_state_machine
ops.ci.tests.test_p2_external_evidence_contract
ops.ci.tests.test_post_p2_live_acceptance_contract
ops.ci.tests.test_post_p2_live_durability
ops.ci.tests.test_single_commit_semaphore_contract
apy.tests.test_gru_minimum_history_boundary
```

Then execute the exact:

- `py_compile` checks;
- `bash -n` checks;
- full-corpus marker greps;
- privilege-dependency scan;
- final production-validation marker.

Expected terminal marker:

```text
SEMAPHORE_PRODUCTION_VALIDATION=PASS
```

### 8.7 Minimum-history runtime boundary

The CI interpreter may legitimately skip the pandas-dependent runtime portion if pandas is absent.

To reduce risk further, additionally run the `24/25/26` runtime-boundary test in a dependency-complete project environment where pandas is installed.

Required result:

```text
24 rows -> rejected as insufficient
25 rows -> accepted boundary
26 rows -> accepted
```

This must not modify production data.

### 8.8 Static exact-result identity checks

Verify source contains:

```text
p2-${CIRCLE_BUILD_NUM}-${EXPECTED_SHA}.status
```

Verify source no longer contains:

```text
latest_result_file
```

Expected count: `0`.

### 8.9 Test lifecycle collision check

Verify no project helper overrides the unittest lifecycle method:

```text
def run(self,
```

within `test_p2_handoff_state_machine.py`.

Expected project-helper count: `0`.

### 8.10 Repository integrity

Run:

```bash
git diff --check
git status --porcelain
```

Expected:

```text
no whitespace errors
clean fresh validation clone
```

### 8.11 Commit-object integrity

Verify:

```text
HEAD = 44505ddb...
parent = dc4e2eef...
changed files = exactly 2
```

### 8.12 Semaphore topology

Verify `.semaphore/semaphore-production.yml` contains exactly six production blocks and the dependency chain is unchanged.

### 8.13 No-privilege dependency

Validate full-corpus live runtime scripts do not require privileged execution.

The safety scan itself must use a form accepted by the operator/runtime policy so the preflight is actually executed rather than skipped by an external safety parser.

### 8.14 Deployment script syntax and exact-SHA semantics

Validate deployment scripts with `bash -n`.

Confirm deployment resolves the expected exact SHA and fails closed on branch/SHA mismatch.

### 8.15 Production read-only preflight

Before Semaphore launch, read-only verify:

- production current SHA;
- production branch;
- tracked status;
- relevant runtime services;
- available disk/memory sufficient for workflow;
- `/tmp/log` baseline fingerprint/metadata for immutability comparison.

Do not alter production in this gate.

---

## 9. Semaphore credit-saving policy

### Before launch

Semaphore launch is forbidden unless all are true:

```text
G0_GO
G1_GO
G2_GO
G3_GO
G4_GO
G5_GO
```

### During launch

Use one new workflow tied to final exact SHA.

Do not launch parallel duplicate pipelines.

### If a block fails

**Code/contract failure**

- no automatic retry;
- no additional commit under this plan;
- capture exact failure evidence;
- mark zero-additional-commit objective as not achieved.

**Transient infrastructure failure**

A retry is allowed only if evidence proves all of:

- exact Git SHA unchanged;
- source command did not produce a code/test failure;
- failure occurred in provisioning/network/agent/tooling layer;
- rerun does not hide a deterministic failure.

---

## 10. Six-block acceptance criteria

### Block 1 â€” GRU validation

Must pass all test, compile, syntax, marker and privilege gates.

Critical regression:

```text
test_p2_handoff_state_machine:
6 tests, not 0
```

### Block 2 â€” Full-corpus acceptance launch

Must create/attach exact-SHA durable authority without privileged runtime dependency.

### Block 3 â€” Full-corpus acceptance final watch

Must finish with durable exact-SHA acceptance evidence.

No stale run may satisfy current acceptance.

### Block 4 â€” Deploy exact feature GRU SHA

Production must deploy exactly:

`44505ddbfa5062dc1c712fc90db72cb0c54de924`

Deployment must fail closed on SHA mismatch.

### Block 5 â€” P2 acceptance launch

Must bind durable launch authority to exact build + SHA.

### Block 6 â€” P2 acceptance final watch

Must accept only the terminal result corresponding to the same build + SHA.

A stale same-SHA result from another build must not produce GO.

---

## 11. Atomic assigned backlog

| ID | Owner | Atomic task | Acceptance evidence |
|---|---|---|---|
| B001 | Release Lead | Freeze failed SHA, base SHA and final SHA in release record | Three literal SHAs recorded |
| B002 | Independent Verifier | Verify `44505ddb...` exists in GitHub | Commit metadata captured |
| B003 | Independent Verifier | Verify parent of `44505ddb...` is exactly `dc4e2eef...` | Parent SHA evidence |
| B004 | Independent Verifier | Compare `dc4e2eef...` â†’ `44505ddb...` | Exactly two files changed |
| B005 | Independent Verifier | Verify observer blob SHA | `001a58683d9...` |
| B006 | Independent Verifier | Verify handoff-test blob SHA | `e46b9a0733c...` |
| B007 | Python Engineer | Fresh-clone exact final SHA | Detached clean HEAD evidence |
| B008 | Python Engineer | Run Python syntax check on handoff tests | Exit 0 |
| B009 | Runtime Engineer | Run Bash syntax check on P2 observer | Exit 0 |
| B010 | Python Engineer | Run targeted P2 handoff suite | 6 tests OK |
| B011 | Python Engineer | Verify stale-build rejection test | named test OK |
| B012 | Python Engineer | Verify exact-build acceptance test | named test OK |
| B013 | Python Engineer | Run related remediation contracts | 3 tests OK |
| B014 | Python Engineer | Run full `ops/ci/tests` discovery | â‰¥38 tests, all OK |
| B015 | Python Engineer | Run dependency-complete 24/25/26 runtime-boundary test | boundary PASS |
| B016 | Runtime Engineer | Verify no `latest_result_file` remains | count 0 |
| B017 | Python Engineer | Verify no custom `TestCase.run` remains | count 0 |
| B018 | CI Engineer | Reproduce full Semaphore `Core CI contracts` command sequence | terminal PASS marker |
| B019 | CI Engineer | Run all `py_compile` gates from Semaphore | all exit 0 |
| B020 | CI Engineer | Run all `bash -n` gates from Semaphore | all exit 0 |
| B021 | CI Engineer | Run full-corpus contract marker checks | all markers present |
| B022 | CI Engineer | Run policy-compatible privilege-dependency scan | no live runtime privilege dependency |
| B023 | Release Lead | Run `git diff --check` | no errors |
| B024 | Release Lead | Verify validation worktree clean | clean |
| B025 | CI Engineer | Verify six-block Semaphore topology | exact six blocks/dependencies |
| B026 | Runtime Engineer | Read-only production capacity/state preflight | evidence bundle |
| B027 | Runtime Engineer | Record `/tmp/log` baseline | immutable baseline evidence |
| B028 | Independent Verifier | Review B001â€“B027 evidence | `PREPUBLISH_GO` |
| B029 | Release Lead | Obtain explicit authorization for non-fast-forward branch ref rewrite | authorization recorded |
| B030 | Release Lead | Move `feature/GRU` from `258a111...` to `44505ddb...` | remote ref exact |
| B031 | Independent Verifier | Verify `258a111...` unreachable from `feature/GRU` | ancestry PASS |
| B032 | Independent Verifier | Verify final branch parent = `dc4e2eef...` | exact parent evidence |
| B033 | Release Lead | Confirm no commit created during branch cutover | commit invariant |
| B034 | Python Engineer | Fresh-clone remote `feature/GRU` after cutover | HEAD exact final SHA |
| B035 | CI Engineer | Re-run deterministic `Core CI contracts` preflight from remote clone | PASS |
| B036 | Independent Verifier | Issue `SEMAPHORE_TRIGGER_GO` | checklist GO |
| B037 | CI Engineer | Trigger one new Semaphore workflow | new run ID, exact final SHA |
| B038 | CI Engineer | Verify Semaphore checkout SHA | `44505ddb...` |
| B039 | CI Engineer | Observe Block 1 `GRU validation` | Passed |
| B040 | CI Engineer | Observe Block 2 full-corpus launch | Passed |
| B041 | Runtime Engineer | Verify full-corpus durable authority identity | exact SHA/run |
| B042 | CI Engineer | Observe Block 3 full-corpus final watch | Passed |
| B043 | Runtime Engineer | Validate durable full-corpus evidence | PASS |
| B044 | CI Engineer | Observe Block 4 exact-SHA deploy | Passed |
| B045 | Runtime Engineer | Verify production HEAD immediately after deploy | exact final SHA |
| B046 | CI Engineer | Observe Block 5 P2 acceptance launch | Passed |
| B047 | Runtime Engineer | Verify P2 launch authority = exact build + SHA | identity PASS |
| B048 | CI Engineer | Observe Block 6 P2 final watch | Passed |
| B049 | Runtime Engineer | Verify terminal P2 result exact build + SHA | durable PASS |
| B050 | Runtime Engineer | Verify production tracked status clean | tracked-clean |
| B051 | Runtime Engineer | Compare `/tmp/log` against baseline | no prohibited mutation |
| B052 | Release Lead | Remove prohibited dummy remote branch if still present, without commit | branch absent |
| B053 | Independent Verifier | Verify no commit exists after `44505ddb...` on `feature/GRU` | topology PASS |
| B054 | Independent Verifier | Verify all six Semaphore blocks passed | six PASS records |
| B055 | Release Lead | Publish COMPLETE_GO record | all gates G0â€“G8 GO |

---

## 12. Backlog dependency chain

```text
B001
  â†“
B002-B006
  â†“
B007-B027
  â†“
B028 PREPUBLISH_GO
  â†“
B029 authorization
  â†“
B030 branch cutover
  â†“
B031-B035
  â†“
B036 SEMAPHORE_TRIGGER_GO
  â†“
B037
  â†“
B038
  â†“
B039
  â†“
B040-B043
  â†“
B044-B045
  â†“
B046-B049
  â†“
B050-B054
  â†“
B055 COMPLETE_GO
```

No task that triggers limited CI credits is permitted before `B036`.

---

## 13. Stop rules

Because the mandatory objective prohibits additional commits, recovery must not create commits.

### Before branch cutover

If any deterministic preflight fails:

- do not move `feature/GRU`;
- do not launch Semaphore;
- stop and report the failed gate.

### After branch cutover but before Semaphore

If remote exact-SHA revalidation fails:

- do not launch Semaphore;
- preserve evidence;
- do not create a fix commit under this plan.

### During Semaphore

If a deterministic code test fails:

- stop;
- collect exact logs;
- do not spend credits on blind reruns;
- do not create another commit.

If a proven transient infrastructure failure occurs:

- the exact same SHA may be rerun only after failure classification.

---

## 14. COMPLETE_GO definition

The release is COMPLETE_GO only when all are simultaneously true:

```text
feature/GRU HEAD
= 44505ddbfa5062dc1c712fc90db72cb0c54de924

HEAD parent
= dc4e2eef1eaeaf439f0d3b8b995a17f0c3940c60

accidental 258a111...
= not reachable from feature/GRU

additional commits after canonical remediation
= 0

Semaphore GRU validation
= PASS

Semaphore full-corpus launch
= PASS

Semaphore full-corpus final watch
= PASS

Semaphore exact-SHA deploy
= PASS

Semaphore P2 launch
= PASS

Semaphore P2 final watch
= PASS

production HEAD
= 44505ddbfa5062dc1c712fc90db72cb0c54de924

production tracked status
= clean

/tmp/log prohibited mutation
= none

full-corpus authority
= exact final SHA

P2 terminal authority
= exact final SHA + exact build

dummy/prohibited branch
= absent
```

Anything less is not COMPLETE_GO.

---

## 15. Credit-minimization rationale

The previous failure was deterministic and visible from source structure. Spending Semaphore credits before exact reproduction of the first block allowed a known-bad SHA to consume a workflow.

This plan reverses the order:

1. immutable commit-object audit;
2. exact-SHA fresh-clone tests;
3. complete first-block reproduction;
4. independent verification;
5. branch publication;
6. second remote exact-SHA preflight;
7. only then one Semaphore production workflow.

The design front-loads cheap deterministic validation and reserves Semaphore credits for live acceptance/deployment stages that cannot be fully substituted by local tests.

---

## 16. Final execution contract

> **No one may create another code commit after `44505ddbfa5062dc1c712fc90db72cb0c54de924`. The only permitted repository write required to establish the final candidate is the controlled ref rewrite of `feature/GRU` from accidental SHA `258a111...` to canonical remediation SHA `44505ddb...`. Semaphore may be triggered only after exact-SHA local and remote preflight gates pass.**

This preserves the single-remediation-commit objective and maximizes the probability that the next Semaphore workflow reaches COMPLETE_GO without consuming credits on a known deterministic failure.
