#!/usr/bin/env python3
import importlib.util
from pathlib import Path

p = Path(__file__).parents[1] / "semaphore_evidence.py"
s = importlib.util.spec_from_file_location("semaphore_evidence", p)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)

expected = {"repo": "Trochez/bot_trading", "branch": "feature/GRU",
            "sha": "a" * 40, "workflow_id": "wf", "pipeline_id": "ppl"}

payload = {"sha": "a" * 40, "workflow_id": "wf", "pipeline_id": "ppl",
           "pipeline": {"state": "done", "result": "stopped"},
           "jobs": [{"name": "test", "result": "failed"}]}
out = m.normalize(payload, expected)
assert out["status"] == "FAILURE"
assert out["schema_version"] == 1 and len(out["failed_jobs"]) == 1

for bad in ({**payload, "sha": "b" * 40}, {**payload, "pipeline_id": "other"}):
    try: m.normalize(bad, expected)
    except ValueError: pass
    else: raise AssertionError("identity mismatch accepted")

r = {}
for _ in range(3): r = m.retry_record({**r, **expected}, "NOT_FOUND")
assert r["circuit_breaker"] == "OPEN"
assert r["terminal_error"] == "SEMAPHORE_EVIDENCE_CIRCUIT_BREAKER_OPEN"
print("SEMAPHORE_EVIDENCE_V4_7=PASS")
