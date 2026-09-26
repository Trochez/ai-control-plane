# IMPLEMENTATION PLAN — ai-loop v4.8.4
## Restore already-collected Semaphore evidence without re-querying Semaphore

**Authoritative run:** `R20260923T012014`  
**Current state:** `BLOCKED_NO_SEND`  
**Proof lease:** `READY`, unconsumed  
**Outbound authorization in this plan:** NONE  
**Semaphore recollection authorization:** NONE

## 1. Objective

Restore or materialize the already-collected read-only Semaphore evidence into the authoritative local directory:

```text
/var/lib/ai-loop/runs/R20260923T012014/semaphore-readonly-python/
```

without re-running the Semaphore collection and without querying Semaphore again.

This plan is an evidence-recovery operation only.

## 2. Current authoritative state

Preserve:

```text
STATUS=BLOCKED_NO_SEND
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
DELIVERY_INTENT_CREATED=false
PHYSICAL_SEND_PERFORMED=false
OUTBOUND_SEND=BLOCKED
FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

Do not consume or invalidate the proof lease merely because the evidence directory is missing.

## 3. Hard prohibitions

Do NOT:

- call Semaphore API;
- retry/restart any workflow or pipeline;
- rerun the Python Semaphore collection;
- rerun the historical jq-based action;
- install jq;
- send or type any ChatGPT message;
- create a delivery intent;
- consume the proof lease;
- navigate/switch chats;
- mutate Git/GitHub/bot_trading/VPS/production;
- create commits or push;
- synthesize evidence from memory;
- fabricate missing raw API responses;
- declare FINAL_GO or AI_LOOP_COMPLETE=GO.

## 4. Recovery source priority

Search for already-existing copies in this order.

### Tier A — exact authoritative copies

Search read-only for directories/files matching:

```text
R20260923T012014
semaphore-readonly-python
request-summary.json
workflow.json
pipeline.json
blocks.json
jobs.json
stop-analysis.json
identity-verification.json
RESULT.md
evidence.json
sha256-manifest.txt
```

under:

```text
/var/lib/ai-loop/
/tmp/
/mnt/d/works/ai-control-plane/
/opt/ai-loop/
```

and other already-known ai-loop run/evidence roots.

### Tier B — remote already-persisted copy

If prior evidence was written on an already-authorized remote/control-plane host, locate that exact directory read-only.

Allowed remote action:

```text
find / ls / stat / sha256sum / cat
```

and a file transfer of the already-existing evidence back to the local authoritative run directory.

Do NOT query Semaphore from the remote host.

### Tier C — immutable archives/backups

Search existing tar/zip/gz backups, run bundles, diagnostics bundles, install backups, or archival directories for an exact copy of the evidence.

Extraction to a temporary local directory is allowed.

### Tier D — prior run evidence that contains the exact original raw response files

A prior run directory may be used only if it contains the same exact Semaphore identities and actual persisted raw API responses from the completed Python collection.

Do not use narrative summaries alone as a substitute for raw evidence.

## 5. Candidate validation

For every candidate evidence set, require:

```text
SHA=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
BRANCH=feature/GRU
WORKFLOW_ID=0f6fcfa4-4fb0-419d-ba4d-ca77af5d0c62
PIPELINE_ID=4df05bd2-6a81-41dc-9dfe-9e0051cd602c
```

Require the candidate to contain the already-observed facts:

```text
PIPELINE_STATE=done
PIPELINE_RESULT=stopped
STOP_REASON=test
STOP_ACTOR=UNKNOWN
terminated_by empty
workflow detail HTTP 404
block/job endpoints HTTP 404
pipeline blocks=[]
```

These facts are validation anchors only. They must be read from the candidate evidence, not rewritten into it from memory.

If a `sha256-manifest.txt` exists, validate every listed artifact.

If no manifest exists, compute a new recovery manifest over the recovered candidate but do not claim it is the original manifest.

## 6. Restoration rules

If and only if one candidate validates:

1. Copy the exact candidate files into a staging directory:
   ```text
   /var/lib/ai-loop/runs/R20260923T012014/semaphore-readonly-python.restore-staging/
   ```

2. Preserve file bytes exactly.

3. Record:
   ```text
   source_location
   source_host if applicable
   source_file_sha256
   restored_file_sha256
   byte_count
   mtime if known
   recovery_method
   ```

4. Require source/restored SHA256 equality for every copied artifact.

5. Atomically rename the validated staging directory to:
   ```text
   /var/lib/ai-loop/runs/R20260923T012014/semaphore-readonly-python/
   ```

6. Do not overwrite an existing non-empty authoritative directory. If one appears during recovery, stop and reconcile first.

## 7. Required recovery evidence

Create separately:

```text
/var/lib/ai-loop/runs/R20260923T012014/semaphore-evidence-restore-v484/
```

Persist:

```text
candidate-search.json
candidate-validation.json
source-inventory.json
copy-verification.json
restored-manifest.sha256
RESULT.md
evidence.json
```

Do not mix recovery metadata into the restored original evidence directory.

## 8. Successful terminal state

Success requires:

```text
SEMAPHORE_EVIDENCE_RESTORE=PASS
AUTHORITATIVE_EVIDENCE_DIR_PRESENT=true
IDENTITY_VERIFICATION=PASS
RESTORED_BYTES_MATCH_SOURCE=PASS
SEMAPHORE_REQUERY_PERFORMED=false
```

Preserve:

```text
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
DELIVERY_INTENT_CREATED=false
PHYSICAL_SEND_PERFORMED=false
OUTBOUND_SEND=BLOCKED
reason=AWAITING_EXPLICIT_SEMAPHORE_EVIDENCE_DELIVERY_AUTHORIZATION
FINAL_GO=UNVERIFIED
AI_LOOP_COMPLETE=UNVERIFIED
```

No outbound message is sent.

## 9. Safe-block terminal state

If no exact persisted copy is found:

```text
SEMAPHORE_EVIDENCE_RESTORE=NOT_FOUND
SEMAPHORE_REQUERY_PERFORMED=false
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED
```

Stop and report all searched locations.

Do NOT reconstruct the missing raw evidence from remembered facts.

## 10. `/omo-team` prompt

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_4_SEMAPHORE_EVIDENCE_RESTORE_NO_RECOLLECTION_20260925.md for authoritative run R20260923T012014.

This is EVIDENCE RESTORATION ONLY.

The required authoritative directory is currently missing:

/var/lib/ai-loop/runs/R20260923T012014/semaphore-readonly-python/

The Semaphore evidence was already collected previously. Do NOT recollect it and do NOT query Semaphore.

Search read-only for an already-existing exact copy in local run roots, /tmp, ai-control-plane files, archives/backups, and any already-authorized remote/control-plane host where the prior collection may have been persisted.

Validate candidates against the exact authoritative IDs:

SHA=0c11a13e0c6ceb4c9eab3258ce4a10728fcb6390
BRANCH=feature/GRU
WORKFLOW_ID=0f6fcfa4-4fb0-419d-ba4d-ca77af5d0c62
PIPELINE_ID=4df05bd2-6a81-41dc-9dfe-9e0051cd602c

A valid candidate must itself contain the observed facts:
pipeline state done;
result stopped;
reason test;
actor unknown;
terminated_by empty;
workflow detail 404;
block/job endpoints 404;
blocks empty.

Do not inject those facts into a candidate.

Validate any original SHA256 manifest if present.

If exactly one valid evidence set is found:
- copy it byte-for-byte through a staging directory;
- verify source/restored SHA256 equality;
- atomically materialize it at the authoritative directory;
- write separate recovery metadata under semaphore-evidence-restore-v484/.

Do NOT:
- query Semaphore;
- rerun Python collection;
- rerun jq action;
- type/send ChatGPT messages;
- create delivery intent;
- consume the proof lease;
- navigate/switch chat;
- mutate Git/GitHub/VPS/bot_trading/production;
- fabricate raw API responses.

Success terminal state:
SEMAPHORE_EVIDENCE_RESTORE=PASS
AUTHORITATIVE_EVIDENCE_DIR_PRESENT=true
IDENTITY_VERIFICATION=PASS
RESTORED_BYTES_MATCH_SOURCE=PASS
SEMAPHORE_REQUERY_PERFORMED=false
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
OUTBOUND_SEND=BLOCKED

If no exact persisted copy exists, stop with:
SEMAPHORE_EVIDENCE_RESTORE=NOT_FOUND
SEMAPHORE_REQUERY_PERFORMED=false
OUTBOUND_SEND=BLOCKED

Do not send anything.
```

## 11. Definition of done

The missing authoritative evidence is restored from an already-existing persisted source with byte-level verification, or the system safely proves no recoverable persisted copy was found.

Re-querying Semaphore is outside this plan.
