"""Verify the AI layer degrades cleanly.

The whole design rests on one claim: pull the credential and the product still
works, only with less polish. These checks prove it.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((ok, name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")
    return ok


def main() -> int:
    started = time.time()
    # Clear EVERY provider credential. The claim under test is that the product
    # works with no AI at all, so one provider slipping through would quietly
    # invalidate the whole suite.
    had_key = any(
        os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "MISTRAL_API_KEY")
    )
    # Set empty rather than delete: importing the package loads .env, which
    # would put a deleted key straight back. An existing-but-empty variable is
    # left alone by the loader and reads as falsy to the provider check.
    for key in ("ANTHROPIC_API_KEY", "MISTRAL_API_KEY"):
        os.environ[key] = ""

    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    print(f"\nAI layer (key present in env: {had_key}; forced to heuristic mode)")
    r = client.get("/api/ai/status")
    status = r.json()
    check("status endpoint responds", r.status_code == 200)
    check("reports heuristic mode without a key", status["mode"] == "heuristic", str(status["mode"]))
    check("no provider is selected", status["provider"] == "none", status["provider"])
    check("it does not name a model it cannot call",
          status["reasoning_model"] == " ", status["reasoning_model"])

    pid = client.post("/api/projects/demo").json()["project"]["id"]

    print("\nJob 1, semantic types")
    r = client.post(f"/api/projects/{pid}/ai/infer-types?table=customers")
    body = r.json()
    check("returns proposals", r.status_code == 200 and len(body["proposals"]) == 10,
          str(len(body.get("proposals", []))))
    check("covers every column",
          {p["column"] for p in body["proposals"]} ==
          {"customer_id", "name", "email", "city", "country", "signup_date",
           "segment", "balance", "tenure_days", "churned"})
    check("flags direct PII", body["pii_flagged"] >= 2, str(body["pii_flagged"]))
    check("every proposal has a privacy mode",
          all(p.get("privacy") for p in body["proposals"]))
    check("marked as heuristic", all(p["source"] == "heuristic" for p in body["proposals"]))

    print("\nJob 2, relationships")
    r = client.post(f"/api/projects/{pid}/ai/infer-relations")
    body = r.json()
    check("returns relationships", r.status_code == 200 and len(body["proposals"]) == 4,
          str(len(body.get("proposals", []))))
    check("marks already-applied edges", all(p["already_applied"] for p in body["proposals"]))

    print("\nJob 4, edge cases")
    r = client.post(f"/api/projects/{pid}/ai/edge-cases")
    body = r.json()
    check("returns edge cases", r.status_code == 200 and len(body["edge_cases"]) >= 6,
          str(len(body.get("edge_cases", []))))
    check("each has a name and a rate",
          all(c.get("name") and 0 < c.get("rate", 0) <= 0.25 for c in body["edge_cases"]))

    print("\nJob 5 - business rules")
    r = client.post(f"/api/projects/{pid}/ai/business-rules")
    body = r.json()
    check("endpoint responds without a key", r.status_code == 200, r.text[:160])
    check("no proposals are invented in heuristic mode", body["proposals"] == [],
          str(len(body["proposals"])))
    check("it explains why", "no rules were proposed" in body["note"], body["note"])

    r = client.get(f"/api/projects/{pid}/rules")
    check("rules inferred from the data are active regardless",
          len(r.json()["rules"]) > 20, str(len(r.json()["rules"])))

    print("\nQuery parsing")
    r = client.post("/api/ai/parse-query?q=last%2090%20days%2C%20balance%20over%20500")
    body = r.json()
    check("parses days", body.get("days") == 90, str(body.get("days")))
    check("parses min balance", body.get("min_balance") == 500.0, str(body.get("min_balance")))
    check("explains what it applied", bool(body.get("interpretation")),
          str(body.get("interpretation")))

    r = client.post("/api/ai/parse-query?q=only%20deposits%20above%201000")
    check("parses direction", r.json().get("direction") == "credit", str(r.json().get("direction")))

    print("\nApplying proposals")
    r = client.post(f"/api/projects/{pid}/ai/apply", json={
        "table": "customers",
        "columns": [{"column": "email", "semantic": "email", "pii": "direct",
                     "privacy": "hash", "source": "ai"}],
    })
    check("apply succeeds", r.status_code == 200, r.text[:160])
    schema = r.json()["schema"]
    email = next(c for c in next(t for t in schema["tables"] if t["name"] == "customers")["columns"]
                 if c["name"] == "email")
    check("privacy mode was written", email["privacy"] == "hash", email["privacy"])

    r = client.post(f"/api/projects/{pid}/ai/apply", json={
        "table": "customers",
        "columns": [{"column": "customer_id", "semantic": "free_text", "pii": "direct",
                     "privacy": "synthesize"}],
    })
    pk = next(c for c in next(t for t in r.json()["schema"]["tables"]
                              if t["name"] == "customers")["columns"]
              if c["name"] == "customer_id")
    check("primary key is protected from reassignment", pk["semantic"] == "primary_key",
          pk["semantic"])

    print("\nThe whole pipeline still runs without a key")
    r = client.post(f"/api/projects/{pid}/generate", json={"rows": 300, "seed": 42})
    job_id = r.json()["job"]["id"]
    job = {}
    for _ in range(120):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.25)
    check("generation completes", job.get("status") == "done", str(job.get("error")))
    check("integrity still passes", job["result"]["integrity"]["passed"])

    r = client.post(f"/api/projects/{pid}/documents",
                    json={"kind": "statement", "count": 5, "region": "UK",
                          "query": "last 60 days, balance over 800"})
    body = r.json()
    check("documents honour a parsed query", body["count"] > 0 and body["all_reconciled"])
    check("query interpretation surfaced", bool(body.get("interpretation")))

    failed = [r for r in results if not r[0]]
    print(f"\n{'-' * 62}")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed in {time.time() - started:.1f}s")
    if failed:
        print("\nFailures:")
        for _, name, detail in failed:
            print(f"  - {name}  {detail}")
        return 1
    print("AI layer degrades cleanly: no key, no crash, full functionality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
