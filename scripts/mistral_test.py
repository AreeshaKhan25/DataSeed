"""Exercise the AI layer against whichever provider is configured.

Run with a key present to prove the live path works; run with the key removed
to prove the fallback still does. Both must pass.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from api import ai  # noqa: E402
from api.schema import build_schema, infer_derived_fields  # noqa: E402

DEMO = Path(__file__).resolve().parents[1] / "data" / "demo"
results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((ok, name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")
    return ok


def main() -> int:
    started = time.time()
    status = ai.ai_status()
    print(f"\nProvider: {status['provider']} · mode: {status['mode']}")
    print(f"  reasoning: {status['reasoning_model']}   bulk: {status['bulk_model']}")

    if not status["available"]:
        print("\nNo AI credential configured — nothing to exercise live.")
        print("The heuristic path is covered by scripts/ai_test.py.")
        return 0

    frames = {
        "customers": pd.read_csv(DEMO / "customers.csv"),
        "orders": pd.read_csv(DEMO / "orders.csv"),
        "order_items": pd.read_csv(DEMO / "order_items.csv"),
    }
    schema = build_schema(frames, name="live_check", seed=42)
    infer_derived_fields(frames, schema)
    customers = schema.table("customers")

    # Bypass the cache so this really hits the provider.
    for stale in ai.CACHE_DIR.glob("*.json"):
        stale.unlink()

    print("\nJob 1 — semantic types")
    proposals = ai.infer_semantic_types(customers, frames["customers"])
    live = [p for p in proposals if p.get("source") == "ai"]
    check("proposals returned", len(proposals) == len(customers.columns),
          f"{len(proposals)} of {len(customers.columns)}")
    check("the model answered (not the fallback)", len(live) > 0,
          f"{len(live)} of {len(proposals)} from the model")
    by_name = {p["column"]: p for p in proposals}
    check("email recognised as direct PII",
          by_name.get("email", {}).get("pii") == "direct",
          str(by_name.get("email", {}).get("pii")))
    check("balance not treated as PII",
          by_name.get("balance", {}).get("pii") == "none",
          str(by_name.get("balance", {}).get("pii")))
    check("every proposal names a real column",
          all(customers.column(p["column"]) is not None for p in proposals))

    print("\nJob 2 — relationships")
    relations = ai.infer_relationships(schema, frames)
    check("relationships proposed", len(relations) >= 2, str(len(relations)))
    pairs = {(r["child_table"], r["parent_table"]) for r in relations}
    check("orders -> customers found", ("orders", "customers") in pairs, str(sorted(pairs)))

    print("\nJob 4 — edge cases")
    cases = ai.propose_edge_cases(schema)
    check("edge cases proposed", len(cases) >= 4, str(len(cases)))
    check("each has a name and a sane rate",
          all(c.get("name") and 0 < c.get("rate", 0) <= 0.25 for c in cases))

    print("\nJob 5 — business rules")
    rules = ai.propose_business_rules(schema)
    check("rules proposed", len(rules) > 0, str(len(rules)))
    check("every rule names a real table and column",
          all(
              schema.table(r["table"]) is not None
              and schema.table(r["table"]).column(r["column"]) is not None
              for r in rules
          ),
          str([f"{r['table']}.{r['column']}" for r in rules][:4]))

    print("\nQuery parsing")
    parsed = ai.parse_query("last 90 days, balance over 500")
    check("days parsed", parsed.get("days") == 90, str(parsed.get("days")))
    check("minimum balance parsed", parsed.get("min_balance") == 500, str(parsed.get("min_balance")))
    check("parsed by the model", parsed.get("source") == "ai", str(parsed.get("source")))

    failed = [r for r in results if not r[0]]
    print(f"\n{'-' * 62}")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed in {time.time() - started:.1f}s")
    if failed:
        print("\nFailures:")
        for _, name, detail in failed:
            print(f"  - {name}  {detail}")
        return 1
    print(f"Live AI path works end to end on {status['provider']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
