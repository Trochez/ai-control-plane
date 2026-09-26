#!/usr/bin/env python3
"""Deterministic Semaphore evidence normalization and retry policy."""
import hashlib
import json
import sys
from datetime import datetime, timezone

SCHEMA_VERSION = 1
COLLECTOR_VERSION = "4.8.1"
TERMINAL_FAILURE = {"failed", "failure", "error", "stopped", "canceled", "cancelled"}
TERMINAL_SUCCESS = {"passed", "pass", "success", "succeeded"}


def fingerprint(provider, sha, workflow_id, pipeline_id, error_code):
    raw = "\0".join(str(x or "").strip().lower() for x in
                      (provider, sha, workflow_id, pipeline_id, error_code))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _pipeline_status(pipeline):
    state = str(pipeline.get("state") or "").lower()
    result = str(pipeline.get("result") or "").lower()
    if state in {"done", "completed"}:
        return "SUCCESS" if result in TERMINAL_SUCCESS else "FAILURE"
    return "RUNNING" if state in {"running", "initializing"} else "PENDING"


def normalize(payload, expected):
    """Return canonical evidence or raise ValueError on identity mismatch."""
    if not isinstance(payload, dict):
        raise ValueError("SEMAPHORE_PAYLOAD_NOT_OBJECT")
    pipeline = payload.get("pipeline") if isinstance(payload.get("pipeline"), dict) else payload
    observed_sha = str(payload.get("sha") or payload.get("commit_sha") or
                       pipeline.get("commit_sha") or "")
    observed_workflow = str(payload.get("workflow_id") or payload.get("wf_id") or "")
    observed_pipeline = str(payload.get("pipeline_id") or payload.get("ppl_id") or
                            pipeline.get("pipeline_id") or pipeline.get("ppl_id") or "")
    for label, got, want in (("SHA", observed_sha, expected.get("sha")),
                             ("WORKFLOW", observed_workflow, expected.get("workflow_id")),
                             ("PIPELINE", observed_pipeline, expected.get("pipeline_id"))):
        if str(got) != str(want):
            raise ValueError("SEMAPHORE_%s_MISMATCH expected=%s observed=%s" % (label, want, got))
    jobs = payload.get("jobs") if isinstance(payload.get("jobs"), list) else []
    failed = [j for j in jobs if str(j.get("result") or j.get("state") or
                                      j.get("status") or "").lower() in TERMINAL_FAILURE]
    out = {
        "schema_version": SCHEMA_VERSION,
        "provider": "semaphore",
        "repo": expected.get("repo", ""),
        "branch": expected.get("branch", ""),
        "sha": observed_sha,
        "workflow_id": observed_workflow,
        "pipeline_id": observed_pipeline,
        "pipeline": {"state": pipeline.get("state", ""), "result": pipeline.get("result", "")},
        "blocks": payload.get("blocks") if isinstance(payload.get("blocks"), list) else [],
        "jobs": jobs,
        "failed_jobs": failed,
        "collector": {"source": payload.get("collector_source", "api"),
                       "status": "PASS", "version": COLLECTOR_VERSION},
    }
    out["status"] = _pipeline_status(out["pipeline"])
    if payload.get("detail_error"):
        out["partial_detail"] = {"error": str(payload["detail_error"]),
                                  "jobs_available": bool(jobs)}
    return out


def retry_record(record, error_code, max_attempts=3):
    record = dict(record or {})
    attempts = int(record.get("attempts") or 0)
    fp = fingerprint(record.get("provider", "semaphore"), record.get("sha"),
                     record.get("workflow_id"), record.get("pipeline_id"), error_code)
    record.update({"provider": "semaphore", "error_code": error_code,
                   "fingerprint": fp, "attempts": attempts + 1,
                   "last_attempt_at": datetime.now(timezone.utc).isoformat()})
    record["circuit_breaker"] = "OPEN" if record["attempts"] >= max_attempts else "CLOSED"
    if record["circuit_breaker"] == "OPEN":
        record["terminal_error"] = "SEMAPHORE_EVIDENCE_CIRCUIT_BREAKER_OPEN"
    return record


if __name__ == "__main__":
    obj = json.load(sys.stdin)
    print(json.dumps(normalize(obj, obj["expected"]), indent=2))
