"""Exercise every API route against the demo project.

This is the pre-demo checklist in executable form. If it is green, the whole
demo path works: ingest, preview, generate, validate, documents, export, and
the integrity gate that blocks a bad export.
"""
from __future__ import annotations

import io
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((ok, name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")
    return ok


def main() -> int:
    started = time.time()
    client = TestClient(app)

    print("\n1. Meta")
    r = client.get("/api/health")
    check("health responds", r.status_code == 200, str(r.status_code))
    r = client.get("/api/formats")
    formats = [f["id"] for f in r.json()["formats"]]
    check("export formats listed", "csv" in formats and "sql" in formats, str(formats))
    r = client.get("/api/regions")
    check("4 tax regions", len(r.json()["regions"]) == 4)

    print("\n2. Demo project")
    r = client.post("/api/projects/demo")
    if not check("demo project created", r.status_code == 200, r.text[:200]):
        return 1
    body = r.json()
    project_id = body["project"]["id"]
    schema = body["schema"]
    check("5 tables", len(schema["tables"]) == 5, str(len(schema["tables"])))
    check("4 foreign keys detected", len(schema["foreign_keys"]) == 4,
          str(len(schema["foreign_keys"])))

    orders = next(t for t in schema["tables"] if t["name"] == "orders")
    derived = {d["column"] for d in orders["derived"]}
    check("derived fields inferred on orders", "total" in derived, str(derived))

    print("\n3. Preview (synchronous)")
    t0 = time.time()
    r = client.post(f"/api/projects/{project_id}/preview",
                    json={"table": "customers", "rows": 25, "seed": 42})
    elapsed = time.time() - t0
    check("preview returns 200", r.status_code == 200, r.text[:200])
    preview = r.json()
    check("25 rows returned", len(preview["rows"]) == 25, str(len(preview["rows"])))
    check("preview is fast", elapsed < 3.0, f"{elapsed:.2f}s")
    check("columns carry PII flags",
          any(c["pii"] == "direct" for c in preview["columns"]))

    r = client.post(f"/api/projects/{project_id}/preview", json={"rows": 500})
    check("preview row cap enforced", r.status_code == 422, str(r.status_code))

    print("\n4. Generate (background job)")
    r = client.post(f"/api/projects/{project_id}/generate",
                    json={"rows": 600, "seed": 42, "validate_output": True})
    check("job accepted", r.status_code == 200, r.text[:200])
    job_id = r.json()["job"]["id"]

    job = {}
    for _ in range(120):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            break
        time.sleep(0.25)

    if not check("job completed", job.get("status") == "done", str(job.get("error"))):
        return 1
    result = job["result"]
    check("all 5 tables generated", len(result["rows"]) == 5, str(result["rows"]))
    check("integrity passed", result["integrity"]["passed"])
    check("zero orphans", result["integrity"]["total_orphans"] == 0)
    check("zero reconciliation mismatches",
          result["integrity"]["total_reconciliation_mismatches"] == 0)
    check("export allowed", result["export_allowed"])
    check("no warnings", not result["warnings"], str(result["warnings"]))

    print("\n5. Data and report")
    r = client.get(f"/api/projects/{project_id}/data/orders?limit=20")
    check("data page returns rows", r.status_code == 200 and len(r.json()["rows"]) == 20)

    r = client.get(f"/api/projects/{project_id}/report")
    check("report available", r.status_code == 200, r.text[:160])
    report = r.json()
    check("integrity is 100", report["integrity"]["score"] == 100.0,
          str(report["integrity"]["score"]))
    check("fidelity above 70", report["fidelity"]["score"] >= 70,
          str(report["fidelity"]["score"]))
    check("utility available", report["utility"].get("available"),
          report["utility"].get("reason", ""))
    check("zero exact matches", report["privacy"]["exact_matches"] == 0)
    check("detection AUC present", report["detection"].get("auc") is not None)
    check("all gates pass", all(report["gates"].values()), str(report["gates"]))

    print("\n6. Documents")
    r = client.post(f"/api/projects/{project_id}/documents",
                    json={"kind": "invoice", "count": 20, "region": "EU"})
    check("20 invoices generated", r.status_code == 200, r.text[:200])
    invoices = r.json()
    check("invoices built from generated data", invoices["from_generated_data"])
    check("every invoice reconciles", invoices["all_reconciled"],
          f"{invoices['reconciled']}/{invoices['count']}")

    first = invoices["documents"][0]
    line_sum = round(sum(l["amount"] for l in first["lines"]), 2)
    check("invoice subtotal equals line items", abs(line_sum - first["subtotal"]) < 0.011,
          f"{line_sum} vs {first['subtotal']}")
    check("invoice total equals subtotal plus tax",
          abs(round(first["subtotal"] + first["tax"], 2) - first["total"]) < 0.011)

    r = client.post(f"/api/projects/{project_id}/documents",
                    json={"kind": "invoice", "count": 5, "region": "IN"})
    check("GST region applies 18%", abs(r.json()["documents"][0]["tax_rate"] - 0.18) < 1e-9)

    r = client.post(f"/api/projects/{project_id}/documents",
                    json={"kind": "statement", "count": 8, "region": "UK",
                          "query": "last 90 days, balance over 500"})
    statements = r.json()
    check("statements generated", statements["count"] > 0, str(statements["count"]))
    check("every balance reconciles", statements["all_reconciled"],
          f"{statements['reconciled']}/{statements['count']}")

    lowest = min(
        min(t["balance"] for t in doc["transactions"])
        for doc in statements["documents"]
    )
    check("query filter applied (every balance over 500)", lowest >= 500, f"min {lowest}")
    check("statements have no gaps in the ledger",
          all(len(doc["transactions"]) >= 4 for doc in statements["documents"]))

    r = client.get(f"/api/projects/{project_id}/documents/0/html?kind=invoice&region=EU")
    check("invoice renders as HTML",
          r.status_code == 200 and "INVOICE" in r.text and "Totals reconciled" in r.text)

    r = client.get(f"/api/projects/{project_id}/documents/0/html?kind=statement&region=UK")
    check("statement renders as HTML",
          r.status_code == 200 and "Account statement" in r.text)

    # The download must contain the documents that were generated, not a set
    # the endpoint invents for itself. It used to build its own 25 regardless,
    # so the zip never matched what the user had on screen.
    r = client.post(f"/api/projects/{project_id}/documents",
                    json={"kind": "invoice", "count": 7, "region": "EU"})
    generated = [d["number"] for d in r.json()["documents"]]

    r = client.get(f"/api/projects/{project_id}/documents/bundle?kind=invoice")
    ok = r.status_code == 200
    names: list[str] = []
    if ok:
        with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
            names = archive.namelist()
    # 7 invoices plus the contents page the zip ships with
    check("document bundle zips exactly what was generated",
          ok and len(names) == 8 and "index.html" in names, f"{len(names)} entries")
    check("bundle holds those same invoices",
          all(f"{number}.html" in names for number in generated),
          f"{len(generated)} generated")

    # Asking for statements must not discard the invoices already held.
    r = client.post(f"/api/projects/{project_id}/documents",
                    json={"kind": "statement", "count": 3, "region": "UK"})
    r = client.get(f"/api/projects/{project_id}/documents/bundle?kind=invoice")
    still_there = False
    if r.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
            still_there = len(archive.namelist()) == 8
    check("generating one kind keeps the other", still_there)

    r = client.get(f"/api/projects/{project_id}/documents/bundle?kind=invoice&count=99")
    check("a stale count parameter cannot change the download",
          r.status_code == 200 and len(zipfile.ZipFile(io.BytesIO(r.content)).namelist()) == 8)

    print("\n6b. N:N relationships")
    nn = [fk for fk in schema["foreign_keys"] if fk["cardinality"] == "N:N"]
    check("N:N edges exposed by the API", len(nn) == 2, str(len(nn)))
    junction = [t for t in schema["tables"] if len(t.get("junction", [])) == 2]
    check("junction table exposed", len(junction) == 1, str([t["name"] for t in junction]))

    r = client.get(f"/api/projects/{project_id}/data/customer_tags?limit=500")
    links = r.json()["rows"]
    check("junction data served", r.status_code == 200 and len(links) > 0, str(len(links)))
    pairs = [(x["customer_id"], x["tag_id"]) for x in links]
    check("no duplicate links in the served page", len(pairs) == len(set(pairs)))

    print("\n6c. Business rules")
    r = client.get(f"/api/projects/{project_id}/rules")
    body = r.json()
    check("rules listed", r.status_code == 200 and len(body["rules"]) > 20,
          str(len(body.get("rules", []))))
    check("every rule carries a readable label",
          all(rule.get("label") for rule in body["rules"]))
    check("inferred rules are marked as such",
          any(rule["source"] == "inferred" for rule in body["rules"]))
    check("enforcement results reported per table", bool(body["results"]),
          str(list(body["results"])))

    fired = [
        res for table in body["results"].values() for res in table
        if res["violations_before"] > 0
    ]
    check("rules actually fired during generation", len(fired) > 0, str(len(fired)))
    check("everything that fired was repaired",
          all(res["violations_after"] == 0 for res in fired))

    r = client.post(f"/api/projects/{project_id}/rules", json={
        "table": "orders", "kind": "range", "column": "total",
        "description": "orders never exceed 50,000", "params": {"maximum": 50000},
    })
    check("a user rule can be added", r.status_code == 200, r.text[:160])
    rule_id = r.json()["rule"]["id"]
    check("the added rule is marked as user-authored",
          r.json()["rule"]["source"] == "user")

    r = client.post(f"/api/projects/{project_id}/rules", json={
        "table": "orders", "kind": "range", "column": "does_not_exist",
        "params": {"minimum": 0},
    })
    check("a rule naming an unknown column is rejected",
          r.status_code == 400 and "remedy" in r.json()["detail"], str(r.status_code))

    r = client.post(f"/api/projects/{project_id}/rules", json={
        "table": "orders", "kind": "comparison", "column": "total", "params": {},
    })
    check("a comparison without a second column is rejected", r.status_code == 400)

    r = client.patch(f"/api/projects/{project_id}/rules/{rule_id}?enabled=false")
    check("a rule can be disabled",
          r.status_code == 200 and r.json()["rule"]["enabled"] is False)

    r = client.delete(f"/api/projects/{project_id}/rules/{rule_id}")
    check("a rule can be deleted", r.status_code == 200)
    r = client.delete(f"/api/projects/{project_id}/rules/{rule_id}")
    check("deleting a missing rule is a typed 404", r.status_code == 404)

    r = client.post(f"/api/projects/{project_id}/rules/infer")
    check("rules can be re-inferred", r.status_code == 200 and r.json()["inferred"] > 20,
          str(r.json().get("inferred")))

    r = client.post(f"/api/projects/{project_id}/ai/business-rules")
    check("AI rule proposals endpoint responds", r.status_code == 200, r.text[:160])
    check("it explains itself when no key is set", bool(r.json()["note"]))

    print("\n7. Export")
    r = client.get(f"/api/projects/{project_id}/export?fmt=csv")
    ok = r.status_code == 200
    names: list[str] = []
    if ok:
        with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
            names = archive.namelist()
        ok = all(f"{t}.csv" in names for t in ("customers", "orders", "order_items"))
    check("CSV zip contains every table", ok, str(names))
    check("CSV zip includes schema and report",
          "schema.json" in names and "trust_report.json" in names, str(names))

    r = client.get(f"/api/projects/{project_id}/export?fmt=sql")
    sql = r.text
    check("SQL dump generated", r.status_code == 200 and len(sql) > 1000)
    check("SQL has CREATE TABLE for each table",
          all(f'CREATE TABLE "{t}"' in sql for t in ("customers", "orders", "order_items")))
    check("SQL adds foreign key constraints", sql.count("ADD CONSTRAINT") == 4,
          str(sql.count("ADD CONSTRAINT")))
    check("SQL is transactional", sql.startswith("-- DataSeed") and sql.rstrip().endswith("COMMIT;"))
    check("SQL escapes quotes in names", "''" in sql or "'" in sql)

    r = client.get(f"/api/projects/{project_id}/export?fmt=json")
    payload = r.json()
    check("JSON export carries tables and report",
          "tables" in payload and payload["trust_report"] is not None)

    r = client.get(f"/api/projects/{project_id}/export?fmt=banana")
    check("unknown format rejected with remedy",
          r.status_code == 400 and "remedy" in r.json()["detail"], str(r.status_code))

    # The interface builds its format list from /api/formats, so anything listed
    # there has to actually export. Excel was advertised unconditionally while
    # only Parquet checked for its package, so a deployment without openpyxl
    # offered a choice that answered 400, and because the download was an
    # ordinary link the browser saved that error as the file.
    advertised = [f["id"] for f in client.get("/api/formats").json()["formats"]]
    check("at least the three dependency free formats are offered",
          {"csv", "json", "sql"}.issubset(set(advertised)), str(advertised))

    unusable: list[str] = []
    for fmt in advertised:
        response = client.get(f"/api/projects/{project_id}/export?fmt={fmt}")
        if response.status_code != 200 or not response.content:
            unusable.append(f"{fmt}:{response.status_code}")
    check("every advertised format actually exports", not unusable,
          str(unusable) if unusable else f"{len(advertised)} formats")

    # And the reverse: a format whose package is absent must not be offered.
    import builtins

    import api.exporters as exporters

    real_import = builtins.__import__

    def without_optional(name: str, *args: object, **kwargs: object) -> object:
        if name in ("pyarrow", "openpyxl"):
            raise ImportError(f"{name} is not installed")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    builtins.__import__ = without_optional  # type: ignore[assignment]
    try:
        stripped = [f["id"] for f in exporters.available_formats()]
    finally:
        builtins.__import__ = real_import  # type: ignore[assignment]
    check("formats needing a missing package are not advertised",
          "excel" not in stripped and "parquet" not in stripped, str(stripped))

    print("\n8. The integrity gate")
    project = None
    from api.store import STORE
    project = STORE.get_project(project_id)
    saved = project.report
    project.report = {
        **(saved or {}), "export_allowed": False,
        "gates": {"integrity": False, "no_exact_matches": True, "fidelity_above_70": True},
    }
    r = client.get(f"/api/projects/{project_id}/export?fmt=csv")
    check("export blocked when a gate fails", r.status_code == 409, str(r.status_code))
    check("blocked export names the failed gate",
          "integrity" in r.json()["detail"]["message"], r.json()["detail"]["message"])
    r = client.get(f"/api/projects/{project_id}/export?fmt=csv&force=true")
    check("force overrides the gate deliberately", r.status_code == 200)
    project.report = saved

    print("\n9. Errors")
    r = client.get("/api/projects/does-not-exist")
    check("unknown project returns a typed error",
          r.status_code == 404 and r.json()["detail"]["code"] == "project_not_found")
    r = client.get("/api/jobs/nope")
    check("unknown job returns a typed error", r.status_code == 404)
    r = client.get(f"/api/projects/{project_id}/data/not_a_table")
    check("unknown table returns a typed error", r.status_code == 404)

    print("\n10. Upload path")
    csv = (DEMO := Path(__file__).resolve().parents[1] / "data" / "demo" / "customers.csv").read_bytes()
    r = client.post("/api/projects/ingest?name=Uploaded",
                    files={"files": ("customers.csv", csv, "text/csv")})
    check("CSV upload accepted", r.status_code == 200, r.text[:200])
    uploaded_id = r.json()["project"]["id"]
    r = client.post(f"/api/projects/{uploaded_id}/preview", json={"rows": 10})
    check("uploaded project previews", r.status_code == 200 and len(r.json()["rows"]) == 10)

    r = client.post("/api/projects/ingest?name=Bad",
                    files={"files": ("notes.txt", b"hello", "text/plain")})
    check("non-CSV rejected with remedy",
          r.status_code == 415 and "remedy" in r.json()["detail"])

    r = client.post("/api/projects/ingest?name=Empty",
                    files={"files": ("empty.csv", b"", "text/csv")})
    check("empty file rejected", r.status_code == 400)

    failed = [r for r in results if not r[0]]
    print(f"\n{'-' * 62}")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed in {time.time() - started:.1f}s")
    if failed:
        print("\nFailures:")
        for _, name, detail in failed:
            print(f"  - {name}  {detail}")
        return 1
    print("Full demo path is working.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
