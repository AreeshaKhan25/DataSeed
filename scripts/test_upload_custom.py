"""Test custom CSV upload, generation, and Trust Report computation."""
from __future__ import annotations

import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.main import app

def test_custom_upload():
    client = TestClient(app)
    sample_file = ROOT / "data" / "samples" / "ecommerce_orders.csv"
    assert sample_file.exists(), "Sample file missing"

    with open(sample_file, "rb") as f:
        response = client.post(
            "/api/projects/ingest?name=Custom+Ecommerce",
            files={"files": ("ecommerce_orders.csv", f, "text/csv")},
        )
    assert response.status_code == 200, f"Ingest failed: {response.text}"
    project = response.json()["project"]
    pid = project["id"]
    print(f"[PASS] Custom dataset ingested cleanly. Project ID: {pid}")

    # Test generation
    gen_res = client.post(f"/api/projects/{pid}/generate", json={"rows": 200, "seed": 42})
    assert gen_res.status_code == 200, f"Generate request failed: {gen_res.text}"
    print("[PASS] Generation background job started")

    # Re-validate trust report
    val_res = client.post(f"/api/projects/{pid}/validate")
    assert val_res.status_code == 200, f"Validate failed: {val_res.text}"
    report = val_res.json()
    assert report.get("available") is True, f"Report unavailable: {report}"
    print(f"[PASS] Trust Report generated successfully! Overall score: {report.get('overall')}")
    print(f"       Integrity: {report['integrity']['score']}, Fidelity: {report['fidelity']['score']}, Privacy: {report['privacy']['score']}")

if __name__ == "__main__":
    test_custom_upload()
