# IMPLEMENTATION PLAN — ai-loop v4.8.8
## Artifact-bound proof for successor-preflight result delivery

**Authoritative run:** `R20260923T012014`  
**Current state:** `BLOCKED_NO_SEND`  
**Prior blocker:** the live conversation does not yet contain the two-successor preflight result, so requiring the current rendered response to contain the successor SHAs is circular.  
**Purpose:** authorize a no-send delivery proof by binding the intended outbound payload directly to immutable local preflight artifacts plus the exact live conversation identity.

---

## 1. Existing authoritative preflight

Do NOT rerun the preflight.

Authoritative evidence:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight/
```

Require:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT=COMPLETED
SHA256_MANIFEST_VALIDATION=PASS

TARGET_SHA=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
SUCCESSOR_1_SHA=cd43645e4e38c574bc728e6f383745e160ae766d
SUCCESSOR_2_SHA=2d429e66d185241e0efda9f3385f5aea55b65f5d
```

Read all relevance and change classifications from persisted artifacts only.

---

## 2. Corrected proof model

The current conversation does NOT need to already contain the successor-preflight result.

That result has not been delivered yet.

Therefore this plan explicitly removes the invalid requirement:

```text
current rendered assistant response must contain successor SHAs
```

Instead use:

```text
PROVENANCE_MODE=ARTIFACT_BOUND_OUTBOUND_PROOF
```

The proof binds:

```text
exact live conversation identity
+
immutable preflight manifest
+
deterministically constructed outbound payload
+
outbound idempotency
```

No prior assistant response content is required to mention the new evidence.

---

## 3. Scope

This plan is NO-SEND.

It may:

- inspect the already-open authoritative conversation read-only;
- read immutable local preflight artifacts;
- construct the exact future outbound payload in a proof directory;
- hash that payload;
- create one fresh READY/unconsumed proof lease.

It MUST NOT:

- type into the composer;
- click Send;
- create a delivery intent;
- consume the lease;
- navigate away;
- rerun the preflight;
- run tests/CI;
- query Semaphore;
- query VPS;
- use SSH;
- query GitHub;
- mutate repositories before the explicitly authorized final Git publication phase;
- deploy/sync;
- declare FINAL_GO;
- declare AI_LOOP_COMPLETE=GO.

---

## 4. Authoritative live conversation

Require current browser page to be exactly:

```text
https://chatgpt.com/g/g-p-68782097d6388191b7538c01b189cce8-bot-trading/c/6ab36fa5-78a8-83e9-9926-6ca0ede44589
```

Require read-only:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
PROJECT=Bot_trading
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
```

No navigation is authorized in this plan. If the page is not already the target, stop BLOCKED.

---

## 5. Model/reasoning proof

Require read-only proof where available:

```text
MODEL=GPT-5.6 Sol
REASONING=High
MODEL_POLICY_PROOF=PASS
```

If direct model text is not visible but the exact same conversation/session has a prior immutable successful proof with GPT-5.6 Sol + High and there is no contradictory current UI state, allow:

```text
MODEL_POLICY_PROOF=BOUND_PRIOR_PASS
```

Do not click model/reasoning controls.

---

## 6. Construct the future payload from authoritative artifacts

Create the exact message that a later separately authorized delivery would send.

The payload MUST be constructed from persisted preflight evidence, not from memory.

It must report at minimum:

1. `TWO_SUCCESSOR_COMMITS_PREFLIGHT=COMPLETED`.
2. Target SHA:
   `0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390`.
3. Successor 1:
   `cd43645e4e38c574bc728e6f383745e160ae766d`.
4. Successor 2:
   `2d429e66d185241e0efda9f3385f5aea55b65f5d`.
5. The persisted relevance classifications for both successors.
6. The persisted findings for:
   - first Core CI block changes;
   - full-corpus transport/evidence handling;
   - Semaphore-related changes;
   - deployment contract changes;
   - runtime-equivalence verification;
   - deployment/sync logic.
7. Source repository remained unchanged.
8. No tests, Semaphore, VPS, SSH, production, deployment, or outbound action occurred during the preflight.
9. This result does NOT establish FINAL_GO or AI_LOOP_COMPLETE.
10. Request ChatGPT to reconcile the preflight and state the exact next action.

Do NOT invent any relevance or change classification.

Persist exact payload bytes as:

```text
payload.txt
payload.sha256
```

---

## 7. Artifact binding

Create:

```text
artifact-binding.json
```

It must bind:

```text
authoritative_run
conversation_id
project
delivery_purpose=TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
preflight_manifest_sha256
target_sha
successor_1_sha
successor_2_sha
payload_sha256
payload_source_files
constructed_at
```

Require that every value comes from validated local artifacts.

Set:

```text
ARTIFACT_BINDING=PASS
```

only after recomputing and verifying the preflight manifest and payload hash.

---

## 8. Outbound idempotency

For delivery purpose:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
```

search authoritative local evidence/ledgers.

Require:

```text
EXISTING_DELIVERY_INTENT=false
EXISTING_PHYSICAL_SEND=false
EXISTING_RECONCILED_DELIVERY=false
OUTBOUND_IDEMPOTENCY=PASS
```

The blocked v4.8.6/v4.8.7 proof packages do not count as deliveries because they created no delivery intent and no physical send.

Do not create a delivery intent in this plan.

---

## 9. Combined proof

Require:

```text
EXACT_URL=PASS
EXACT_CONVERSATION_ID=PASS
PROJECT_CONTEXT=TARGET
NORMAL_CHAT_SURFACE=PASS
COMPOSER_EMPTY=PASS
RESPONSE_SETTLED=PASS
MODEL_POLICY_PROOF=PASS or BOUND_PRIOR_PASS
ARTIFACT_BINDING=PASS
OUTBOUND_IDEMPOTENCY=PASS
```

Then persist:

```text
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
CROSS_SOURCE_PROVENANCE=PASS
PROVENANCE_MODE=ARTIFACT_BOUND_OUTBOUND_PROOF
LIVE_RANGE_WITNESS=NOT_REQUIRED_FOR_UNDELIVERED_NEW_RESULT
VISIBLE_SETTLED_RESPONSE_WITNESS=NOT_REQUIRED_FOR_UNDELIVERED_NEW_RESULT
```

Rationale: the outbound result is new evidence not yet present in the conversation; therefore prior rendered response content is not a valid identity requirement for the payload.

---

## 10. Fresh proof lease

Only if every gate above passes, create one new immutable lease:

```text
proof_lease_id=<new unique id>
authoritative_run=R20260923T012014
conversation_id=6ab36fa5-78a8-83e9-9926-6ca0ede44589
project=Bot_trading
delivery_purpose=TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT
provenance_mode=ARTIFACT_BOUND_OUTBOUND_PROOF
state=READY
consumed=false
created_at=<timestamp>
preflight_manifest_sha256=<sha>
payload_sha256=<sha>
artifact_binding_sha256=<sha>
page_identity_sha256=<sha>
idempotency_sha256=<sha>
```

Any subsequent navigation, chat switch, composer mutation, or outbound send invalidates the lease.

---

## 11. Evidence directory

Create a NEW directory:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v488/
```

Persist at minimum:

```text
page-identity.json
model-policy-proof.json
payload.txt
payload.sha256
artifact-binding.json
outbound-idempotency.json
live-conversation-identity-proof.json
cross-source-provenance.json
proof-lease.json
RESULT.md
evidence.json
sha256-manifest.txt
```

Validate the manifest.

---

## 12. Successful terminal state

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS

PROVENANCE_MODE=ARTIFACT_BOUND_OUTBOUND_PROOF
ARTIFACT_BINDING=PASS
OUTBOUND_IDEMPOTENCY=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
CROSS_SOURCE_PROVENANCE=PASS

LIVE_RANGE_WITNESS=NOT_REQUIRED_FOR_UNDELIVERED_NEW_RESULT
VISIBLE_SETTLED_RESPONSE_WITNESS=NOT_REQUIRED_FOR_UNDELIVERED_NEW_RESULT

PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false

OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_TWO_SUCCESSOR_PREFLIGHT_RESULT_DELIVERY_AUTHORIZATION

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

Stop there.

---

## 13. Safe-block conditions

Stop without lease creation if:

- current URL/conversation/project is not exact;
- composer is not empty;
- response is not settled;
- model policy is contradicted;
- preflight manifest fails;
- payload cannot be constructed entirely from authoritative persisted evidence;
- artifact binding fails;
- prior delivery intent/send/reconciled delivery already exists for this purpose.

Do not attempt to solve those failures by sending or rerunning the preflight.

---

## 14. `/omo-team` prompt

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_8_ARTIFACT_BOUND_SUCCESSOR_PREFLIGHT_DELIVERY_PROOF_20260926.md for authoritative run R20260923T012014.

This is NO-SEND.

Do NOT rerun TWO_SUCCESSOR_COMMITS_PREFLIGHT.

The v4.8.7 blocker is expected and logically valid:
the current live conversation does not yet contain the successor-preflight result because that result has never been delivered.

Therefore use:
PROVENANCE_MODE=ARTIFACT_BOUND_OUTBOUND_PROOF

Do NOT require the existing rendered assistant response to contain:
cd43645e4e38c574bc728e6f383745e160ae766d
or
2d429e66d185241e0efda9f3385f5aea55b65f5d.

Instead require:
- exact current target URL/conversation/project;
- normal Chat;
- empty composer;
- settled response;
- GPT-5.6 Sol + High direct proof or safe prior-bound proof;
- authoritative two-successor preflight manifest PASS;
- construct the exact future payload solely from persisted preflight artifacts;
- compute payload SHA256;
- bind payload SHA + preflight manifest SHA + commit chain + conversation ID in artifact-binding.json;
- require outbound idempotency PASS for TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT.

Set:
LIVE_RANGE_WITNESS=NOT_REQUIRED_FOR_UNDELIVERED_NEW_RESULT
VISIBLE_SETTLED_RESPONSE_WITNESS=NOT_REQUIRED_FOR_UNDELIVERED_NEW_RESULT

If and only if all gates pass:
create one NEW proof lease READY/unconsumed.

Persist under:
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v488/

Do NOT:
- type/send;
- navigate;
- create delivery intent;
- consume lease;
- rerun preflight;
- run tests/CI;
- query Semaphore/VPS/GitHub;
- mutate repositories before the final Git publication phase;
- deploy;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

After the proof package is successfully created and validated, execute the FINAL GIT PUBLICATION PHASE below, then stop.
```

---

## 15. FINAL GIT PUBLICATION PHASE — authorized commit + push to `main`

This phase runs **only after** the no-send proof package has completed successfully with:

```text
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS
ARTIFACT_BINDING=PASS
OUTBOUND_IDEMPOTENCY=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
CROSS_SOURCE_PROVENANCE=PASS
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
```

This phase explicitly authorizes Git mutation in the control-plane repository:

```text
REPOSITORY=/mnt/d/works/ai-control-plane
EXPECTED_REMOTE=git@github.com:Trochez/ai-control-plane.git
BRANCH=main
```

### 15.1 Repository identity gate

Before staging anything, require:

```bash
cd /mnt/d/works/ai-control-plane
git rev-parse --is-inside-work-tree
git branch --show-current
git remote get-url origin
git status --short
```

Require exactly:

```text
branch=main
origin=git@github.com:Trochez/ai-control-plane.git
```

If branch or remote differs:

```text
FINAL_GIT_PUBLICATION=BLOCKED
reason=REPOSITORY_IDENTITY_MISMATCH
```

Stop without commit or push.

### 15.2 Remote divergence gate

Read-only remote synchronization is authorized:

```bash
git fetch origin main
```

Require that local `main` can be pushed without force.

Do NOT use:

```text
--force
--force-with-lease
reset
rebase
clean
```

If `origin/main` contains commits not present locally and a normal push would be non-fast-forward:

```text
FINAL_GIT_PUBLICATION=BLOCKED
reason=REMOTE_MAIN_DIVERGED
```

Stop. Do not rewrite history.

### 15.3 Secret/sensitive-file gate

The user requested committing **all repository changes** after completion.

Stage all tracked/untracked repository changes with:

```bash
git add -A
```

However, before creating the commit, inspect the staged file names/content for obvious secrets or private credential material.

At minimum block on staged content that includes:

- private SSH keys;
- API tokens;
- passwords;
- `.key_ssh_server`;
- credential environment files;
- browser authentication/session secrets;
- files under known secret/key directories.

Do NOT print secret values.

If sensitive material is detected:

```text
FINAL_GIT_PUBLICATION=BLOCKED
reason=SENSITIVE_MATERIAL_STAGED
```

Unstage only for safety if necessary, report the blocking path names without secret contents, and stop.

Otherwise continue with **all staged repository changes**, including pre-existing tracked and untracked changes.

### 15.4 Single commit

Create exactly one commit containing all staged non-secret repository changes.

Recommended commit message:

```text
chore(ai-loop): persist successor preflight proof workflow
```

Before commit persist:

```text
PRE_COMMIT_HEAD=<sha>
STAGED_FILE_COUNT=<count>
STAGED_DIFF_SHA256=<sha256>
```

Then:

```bash
git commit -m "chore(ai-loop): persist successor preflight proof workflow"
```

Require:

```text
COMMIT_CREATED=YES
COMMIT_COUNT=1
```

Persist new commit SHA:

```text
COMMIT_SHA=<sha>
```

Do not create a second commit.

### 15.5 Push exactly once to `main`

Push the new commit using:

```bash
git push origin main
```

No force push.

Require successful remote update.

After push verify:

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Require local `HEAD` == remote `origin/main` SHA.

Persist:

```text
PUSH_PERFORMED=YES
PUSH_COUNT=1
REMOTE_MAIN_SHA=<sha>
LOCAL_HEAD_SHA=<sha>
REMOTE_MAIN_MATCH=PASS
```

### 15.6 Post-push repository state

Persist:

```bash
git status --short
git status --branch --short
```

Expected:

```text
POST_PUSH_WORKTREE_CLEAN=YES
```

If ignored/runtime files remain but there are no tracked/untracked commit-worthy changes, record that fact explicitly.

### 15.7 Final Git evidence

Persist Git publication evidence under a new local run directory, for example:

```text
/var/lib/ai-loop/runs/R20260923T012014/control-plane-main-publication/
```

At minimum:

```text
repository-identity.txt
pre-commit-status.txt
staged-files.txt
staged-diff-sha256.txt
commit-result.txt
push-result.txt
remote-main-verification.txt
post-push-status.txt
RESULT.md
evidence.json
sha256-manifest.txt
```

Do not persist credentials or authentication material.

Validate the evidence manifest.

### 15.8 Git publication terminal state

Successful terminal state:

```text
FINAL_GIT_PUBLICATION=PASS

REPOSITORY=/mnt/d/works/ai-control-plane
BRANCH=main
REMOTE=git@github.com:Trochez/ai-control-plane.git

COMMIT_CREATED=YES
COMMIT_COUNT=1
PUSH_PERFORMED=YES
PUSH_COUNT=1

REMOTE_MAIN_MATCH=PASS
POST_PUSH_WORKTREE_CLEAN=YES

PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED

FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

The Git commit/push does **not** authorize any ChatGPT send, delivery intent, proof-lease consumption, CI run, deployment, VPS mutation, or production action.

Stop after the verified push to `main`.

---

## 16. Updated `/omo-team` execution prompt

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_8_ARTIFACT_BOUND_SUCCESSOR_PREFLIGHT_DELIVERY_PROOF_WITH_MAIN_PUSH_20260926.md for authoritative run R20260923T012014.

First execute the artifact-bound NO-SEND successor-preflight delivery proof exactly as specified.

Do NOT rerun TWO_SUCCESSOR_COMMITS_PREFLIGHT.

Require successful proof terminal state:
TWO_SUCCESSOR_COMMITS_PREFLIGHT_RESULT_PROOF=PASS
PROVENANCE_MODE=ARTIFACT_BOUND_OUTBOUND_PROOF
ARTIFACT_BINDING=PASS
OUTBOUND_IDEMPOTENCY=PASS
LIVE_CONVERSATION_IDENTITY_PROOF=PASS
CROSS_SOURCE_PROVENANCE=PASS
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED

Only AFTER that proof package and its manifest validate, execute the explicitly authorized FINAL GIT PUBLICATION PHASE.

Repository:
 /mnt/d/works/ai-control-plane

Require:
 branch=main
 origin=git@github.com:Trochez/ai-control-plane.git

Then:
- git fetch origin main read-only;
- block if normal push would be non-fast-forward;
- git add -A to stage all repository changes;
- inspect staged paths/content for secrets/private credentials without printing values;
- block rather than commit secrets;
- otherwise create exactly ONE commit containing all staged repository changes;
- commit message:
  chore(ai-loop): persist successor preflight proof workflow
- push exactly once:
  git push origin main
- do NOT force push;
- verify local HEAD equals refs/heads/main on origin;
- persist commit/push evidence and SHA-256 manifest.

Do NOT:
- send/type ChatGPT messages;
- create delivery intent;
- consume the proof lease;
- run CI;
- query Semaphore/VPS/GitHub APIs;
- deploy/sync;
- mutate production;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

Successful final state:
FINAL_GIT_PUBLICATION=PASS
COMMIT_CREATED=YES
COMMIT_COUNT=1
PUSH_PERFORMED=YES
PUSH_COUNT=1
REMOTE_MAIN_MATCH=PASS
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED

Stop immediately after verified push to main.
```
