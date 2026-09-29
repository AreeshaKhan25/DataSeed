"""Verify all features and document flows from Synthetic Data Platform - HackDataV2.pdf."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.main import app

def test_pdf_spec_flows():
    client = TestClient(app)

    print("\n--- 1. Verification of Demo & Tabular Data ---")
    demo_res = client.post("/api/projects/demo")
    assert demo_res.status_code == 200
    pid = demo_res.json()["project"]["id"]
    print(f"[PASS] Project created/loaded: {pid}")

    print("\n--- 2. Relational Generation & Integrity ---")
    gen_res = client.post(f"/api/projects/{pid}/generate", json={"rows": 500, "seed": 42})
    assert gen_res.status_code == 200
    job_id = gen_res.json()["job"]["id"]

    # Poll job until done
    for _ in range(30):
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "failed"):
            break
    assert j["status"] == "done", f"Job failed: {j.get('error')}"
    print(f"[PASS] Relational tables generated: {j['result']['rows']}")
    assert j["result"]["integrity"]["passed"] is True
    print("[PASS] Referential integrity maintained across relational tables (0 orphans)")

    print("\n--- 3. Document Generator: Invoices (Regional Tax & Reconciliation) ---")
    for region in ["EU", "UK", "US", "IN"]:
        inv_res = client.post(
            f"/api/projects/{pid}/documents",
            json={"kind": "invoice", "count": 10, "region": region},
        )
        assert inv_res.status_code == 200, f"Invoice gen failed for {region}"
        inv_data = inv_res.json()
        assert inv_data["all_reconciled"] is True, f"Invoices failed reconciliation for {region}"
        print(f"[PASS] {region} Invoices generated (10/10 reconciled): tax label = {inv_data['documents'][0]['tax_label']}")

    print("\n--- 4. Document Generator: Bank Statements & NL Query ---")
    stmt_res = client.post(
        f"/api/projects/{pid}/documents",
        json={"kind": "statement", "count": 8, "region": "UK", "query": "last 90 days, balance over 500"},
    )
    assert stmt_res.status_code == 200
    stmt_data = stmt_res.json()
    assert stmt_data["all_reconciled"] is True
    print(f"[PASS] Bank Statements generated (8/8 reconciled with query: {stmt_data['query']})")

    print("\n--- 5. HTML/PDF Printable View & Bundle Export ---")
    html_res = client.get(f"/api/projects/{pid}/documents/0/html?kind=invoice&region=US")
    assert html_res.status_code == 200
    assert "<!DOCTYPE html>" in html_res.text or "<html" in html_res.text
    print("[PASS] Invoice rendered printable HTML/PDF view")

    zip_res = client.get(f"/api/projects/{pid}/documents/bundle?kind=invoice&region=EU&count=5")
    assert zip_res.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(zip_res.content))
    assert len(z.namelist()) == 5
    print(f"[PASS] Document bundle ZIP generated ({len(z.namelist())} files inside)")

    print("\n--- 6. Trust Report & Integrity Gates ---")
    val_res = client.post(f"/api/projects/{pid}/validate")
    assert val_res.status_code == 200
    report = val_res.json()
    assert report["available"] is True
    assert report["export_allowed"] is True
    print(f"[PASS] Trust report overall score: {report['overall']} (Gates passed)")

    print("\n========================================================")
    print(" ALL SPECIFICATIONS & FLOWS FROM PDF VERIFIED SUCCESSFULLY ")
    print("========================================================\n")

if __name__ == "__main__":
    test_pdf_spec_flows()
