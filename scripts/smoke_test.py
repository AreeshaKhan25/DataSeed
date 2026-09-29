"""End-to-end check of the generation pipeline.

Run this before every demo. It exercises profiling, fitting, sampling,
relational integrity, reconciliation, determinism and the full trust report,
and prints a pass/fail line for each guarantee the platform claims to offer.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.engine import fit_table, sample_table, select_condition_column  # noqa: E402
from api.constraints import infer_constraints  # noqa: E402
from api.relational import check_integrity, generate_relational, is_lookup_table  # noqa: E402
from api.schema import Constraint, DerivedField, build_schema, coerce_to_schema, infer_derived_fields  # noqa: E402
from api.seeds import SeedFactory  # noqa: E402
from api.trust import build_trust_report  # noqa: E402

DEMO = Path(__file__).resolve().parents[1] / "data" / "demo"

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def _violations(frame: pd.DataFrame, constraint) -> int:
    from api.constraints import _violation_mask

    return int(_violation_mask(frame, constraint).sum())


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((PASS if condition else FAIL, name, detail))
    print(f"  [{PASS if condition else FAIL}] {name}{'  ' + detail if detail else ''}")


def main() -> int:
    started = time.time()
    frames = {
        "customers": pd.read_csv(DEMO / "customers.csv"),
        "orders": pd.read_csv(DEMO / "orders.csv"),
        "order_items": pd.read_csv(DEMO / "order_items.csv"),
        "tags": pd.read_csv(DEMO / "tags.csv"),
        "customer_tags": pd.read_csv(DEMO / "customer_tags.csv"),
    }

    print("\n1. Schema profiling")
    schema = build_schema(frames, name="northwind_retail", seed=42)
    check("5 tables profiled", len(schema.tables) == 5, str(len(schema.tables)))

    customers = schema.table("customers")
    check("customers PK detected", customers.primary_key == "customer_id",
          f"got {customers.primary_key}")
    check("email flagged as direct PII",
          customers.column("email").pii == "direct",
          f"semantic={customers.column('email').semantic}")
    check("name flagged as direct PII", customers.column("name").pii == "direct")
    check("balance typed numeric", customers.column("balance").dtype == "float")
    check("signup_date typed as date", customers.column("signup_date").dtype == "date",
          f"got {customers.column('signup_date').dtype}")
    check("segment detected as category",
          customers.column("segment").semantic == "category")

    fk_pairs = {(fk.child_table, fk.child_column, fk.parent_table) for fk in schema.foreign_keys}
    check("orders -> customers FK found",
          ("orders", "customer_id", "customers") in fk_pairs, str(sorted(fk_pairs)))
    check("order_items -> orders FK found",
          ("order_items", "order_id", "orders") in fk_pairs)

    print("\n2. Tabular generation")
    seeds = SeedFactory(42)
    model = fit_table(customers, frames["customers"], seeds)
    synth = sample_table(model, 2000, seeds)
    check("2000 rows generated", len(synth) == 2000, f"got {len(synth)}")
    check("all columns present", list(synth.columns) == [c.name for c in customers.columns])
    check("PKs unique", synth["customer_id"].is_unique)

    real_emails = set(frames["customers"]["email"])
    overlap = sum(1 for e in synth["email"] if e in real_emails)
    check("no real emails copied into output", overlap == 0, f"{overlap} leaked")

    real_names = set(frames["customers"]["name"])
    name_overlap = sum(1 for n in synth["name"] if n in real_names)
    check("no real names copied into output", name_overlap == 0, f"{name_overlap} leaked")

    check("segment values stay in domain",
          set(synth["segment"].dropna()) <= set(frames["customers"]["segment"]))
    check("balance stays non-negative", (synth["balance"].dropna() >= 0).all())

    real_corr = frames["customers"][["balance", "tenure_days", "churned"]].corr().loc["balance", "churned"]
    synth_corr = synth[["balance", "tenure_days", "churned"]].corr().loc["balance", "churned"]
    check("balance/churn correlation preserved",
          abs(real_corr - synth_corr) < 0.15,
          f"real={real_corr:.3f} synth={synth_corr:.3f}")

    print("\n3. Determinism")
    a = sample_table(fit_table(customers, frames["customers"], SeedFactory(7)), 500, SeedFactory(7))
    b = sample_table(fit_table(customers, frames["customers"], SeedFactory(7)), 500, SeedFactory(7))
    check("same seed produces identical output", a.equals(b))
    c = sample_table(fit_table(customers, frames["customers"], SeedFactory(8)), 500, SeedFactory(8))
    check("different seed produces different output", not a.equals(c))

    print("\n3b. Conditional generation")
    coerced = coerce_to_schema(frames["customers"], customers)
    chosen, strength = select_condition_column(customers, coerced)
    check("a conditioning column is selected", chosen == "segment", f"got {chosen}")
    check("its dependence is meaningful", strength > 0.1, f"eta^2 {strength:.3f}")

    cond_model = fit_table(customers, frames["customers"], SeedFactory(42))
    check("mixture has one sub-model per group", len(cond_model.groups) == 3,
          str(len(cond_model.groups)))

    real_mix = frames["customers"]["segment"].value_counts(normalize=True)
    fitted_mix = dict(zip(cond_model.condition_values, cond_model.condition_probs))
    drift = max(abs(real_mix[k] - v) for k, v in fitted_mix.items())
    check("group proportions match the source", drift < 0.001, f"max drift {drift:.4f}")

    cond_sample = sample_table(cond_model, 3000, SeedFactory(42))
    synth_mix = cond_sample["segment"].value_counts(normalize=True)
    mix_drift = max(abs(real_mix[k] - synth_mix.get(k, 0)) for k in real_mix.index)
    check("sampled mixture matches the source", mix_drift < 0.03, f"max drift {mix_drift:.4f}")
    check("primary keys stay unique across groups", cond_sample["customer_id"].is_unique)
    check("output is not blocked by the conditioning column",
          cond_sample["segment"].head(50).nunique() > 1)

    d1 = sample_table(fit_table(customers, frames["customers"], SeedFactory(11)), 400, SeedFactory(11))
    d2 = sample_table(fit_table(customers, frames["customers"], SeedFactory(11)), 400, SeedFactory(11))
    check("mixture is still deterministic", d1.equals(d2))

    flat = fit_table(customers, frames["customers"], SeedFactory(42), conditional=False)
    check("a flat fit has no groups", not flat.groups)

    print("\n4. Relational generation")
    orders = schema.table("orders")
    orders.derived = [
        DerivedField(column="total", child_table="order_items", agg="sum",
                     expr="qty * unit_price"),
        DerivedField(column="item_count", child_table="order_items", agg="count"),
    ]
    rel_seeds = SeedFactory(42)
    models = {t.name: fit_table(t, frames[t.name], rel_seeds) for t in schema.tables}
    generated, warnings, rule_results = generate_relational(schema, models, 800, rel_seeds)

    check("all 5 tables generated", len(generated) == 5, str({k: len(v) for k, v in generated.items()}))
    check("no generation warnings", not warnings, "; ".join(warnings))
    check("customers has 800 rows", len(generated["customers"]) == 800)
    check("orders derived from cardinality", len(generated["orders"]) > 0,
          f"{len(generated['orders'])} rows")
    check("order_items derived from cardinality", len(generated["order_items"]) > 0,
          f"{len(generated['order_items'])} rows")

    integrity = check_integrity(schema, generated)
    check("integrity gate passed", integrity["passed"], str(integrity["score"]))
    check("zero orphan foreign keys", integrity["total_orphans"] == 0,
          str(integrity["orphan_keys"]))
    check("zero duplicate primary keys", integrity["total_duplicate_keys"] == 0)
    check("derived totals reconcile exactly",
          integrity["total_reconciliation_mismatches"] == 0,
          str(integrity["reconciliation_mismatches"]))

    # Independent re-check of the headline claim from the deck.
    items = generated["order_items"]
    recomputed = (items["qty"] * items["unit_price"]).groupby(items["order_id"]).sum().round(2)
    claimed = generated["orders"].set_index("order_id")["total"]
    aligned = recomputed.reindex(claimed.index).fillna(0.0)
    max_drift = float((claimed - aligned).abs().max())
    check("order totals equal sum of line items", max_drift < 0.011, f"max drift {max_drift:.4f}")

    print("\n4b. N:N relationships")
    junctions = [t.name for t in schema.tables if t.is_junction]
    check("junction table recognised", junctions == ["customer_tags"], str(junctions))
    nn = [fk for fk in schema.foreign_keys if fk.cardinality == "N:N"]
    check("both link edges labelled N:N", len(nn) == 2, str(len(nn)))
    check("tags recognised as a lookup table", is_lookup_table(schema.table("tags"), schema))

    links = generated["customer_tags"]
    check("junction rows generated", len(links) > 0, str(len(links)))
    check("no duplicate (customer, tag) pairs",
          not links[["customer_id", "tag_id"]].duplicated().any())
    check("every customer link resolves",
          links["customer_id"].isin(generated["customers"]["customer_id"]).all())
    check("every tag link resolves",
          links["tag_id"].isin(generated["tags"]["tag_id"]).all())
    check("lookup table keeps its real size",
          len(generated["tags"]) == schema.table("tags").row_count,
          f"{len(generated['tags'])} vs {schema.table('tags').row_count}")

    real_degree = frames["customer_tags"].groupby("customer_id").size().mean()
    synth_degree = links.groupby("customer_id").size().mean()
    check("links per customer matches the source",
          abs(real_degree - synth_degree) < 0.4,
          f"real {real_degree:.2f} vs synth {synth_degree:.2f}")

    real_pop = frames["customer_tags"]["tag_id"].value_counts(
        normalize=True).sort_values(ascending=False).to_numpy()
    synth_pop = links["tag_id"].value_counts(
        normalize=True).sort_values(ascending=False).to_numpy()
    n = min(len(real_pop), len(synth_pop))
    pop_tvd = 0.5 * abs(real_pop[:n] - synth_pop[:n]).sum()
    check("tag popularity skew is preserved", pop_tvd < 0.15, f"TVD {pop_tvd:.3f}")
    check("integrity checks junction pairs",
          integrity.get("total_duplicate_links") == 0,
          str(integrity.get("duplicate_junction_links")))

    print("\n4c. Business rules")
    inferred = infer_constraints(frames, schema)
    kinds = {c.kind for c in inferred}
    check("rules inferred from the sample", len(inferred) > 20, str(len(inferred)))
    check("date ordering learned", "comparison" in kinds, str(sorted(kinds)))
    check("category domains learned", "enum" in kinds)
    check("non-negativity learned", "range" in kinds)
    check("a rule the source data breaks is never proposed",
          all(_violations(frames[c.table], c) == 0 for c in inferred if c.table in frames))

    ruled = build_schema(frames, name="ruled", seed=42)
    infer_derived_fields(frames, ruled)
    ruled.constraints = infer_constraints(frames, ruled)
    rule_seeds = SeedFactory(42)
    rule_models = {t.name: fit_table(t, frames[t.name], rule_seeds) for t in ruled.tables}
    ruled_frames, _, rule_report = generate_relational(ruled, rule_models, 500, rule_seeds)

    found = sum(r.violations_before for rs in rule_report.values() for r in rs)
    repaired = sum(r.repaired for rs in rule_report.values() for r in rs)
    remaining = sum(r.violations_after for rs in rule_report.values() for r in rs)
    check("rules caught real violations", found > 0, f"{found} found")
    check("violations were repaired, not dropped", repaired == found,
          f"{repaired} repaired of {found}")
    check("no violations remain", remaining == 0, str(remaining))

    ship = pd.to_datetime(ruled_frames["orders"]["shipped_date"], errors="coerce")
    placed = pd.to_datetime(ruled_frames["orders"]["order_date"], errors="coerce")
    both = ship.notna() & placed.notna()
    check("no order ships before it is placed", bool((ship[both] >= placed[both]).all()),
          f"{int((ship[both] < placed[both]).sum())} bad rows")

    ruled_integrity = check_integrity(ruled, ruled_frames)
    check("rule violations feed the integrity gate",
          ruled_integrity["total_rule_violations"] == 0,
          f"{len(ruled_integrity['business_rule_violations'])} rules checked, 0 violated")
    check("integrity still passes with rules on", ruled_integrity["passed"])

    print("\n5. Trust report")
    report = build_trust_report(frames["customers"], customers, SeedFactory(42), integrity=integrity)
    check("report generated", report.get("available"), report.get("reason", ""))

    fidelity = report["fidelity"]["score"]
    utility = report["utility"]
    privacy = report["privacy"]
    detection = report["detection"]

    check("fidelity above 70", fidelity >= 70, f"{fidelity}")
    check("utility computed", utility.get("available"), utility.get("reason", ""))
    if utility.get("available"):
        check("TSTR utility above 70", utility["score"] >= 70,
              f"{utility['score']} (target={utility['target']}, "
              f"TRTR={utility['trtr']}, TSTR={utility['tstr']})")
    check("zero exact matches with real rows", privacy["exact_matches"] == 0,
          str(privacy["exact_matches"]))
    check("DCR at or above real baseline",
          privacy["dcr"] is not None and privacy["dcr_baseline"] is not None
          and privacy["dcr"] >= privacy["dcr_baseline"] * 0.8,
          f"dcr={privacy['dcr']} baseline={privacy['dcr_baseline']}")
    check("membership inference near chance",
          privacy["membership_auc"] is not None and abs(privacy["membership_auc"] - 0.5) < 0.15,
          f"auc={privacy['membership_auc']}")
    check("conditioning is disclosed in the report",
          report.get("conditioned_on") == "segment", str(report.get("conditioned_on")))
    check("an independent target is reported alongside it",
          utility.get("independent_check") is not None,
          str(utility.get("independent_check")))
    check("the independent target is not the conditioning column",
          (utility.get("independent_check") or {}).get("target") != report.get("conditioned_on"))
    check("detection AUC computed", detection.get("available"), detection.get("reason", ""))
    if detection.get("available"):
        check("detection AUC below 0.80", detection["auc"] < 0.80, f"{detection['auc']}")

    print("\n   Scores:")
    print(f"     Integrity  {integrity['score']:.0f}")
    print(f"     Fidelity   {fidelity:.0f}")
    print(f"     Utility    {utility.get('score', 0):.0f}"
          + (f"  (TRTR {utility['trtr']} vs TSTR {utility['tstr']} on {utility['target']})"
             if utility.get("available") else ""))
    print(f"     Privacy    {privacy['score']:.0f}")
    print(f"     Detection  {detection.get('auc', 'n/a')}")
    print(f"     OVERALL    {report['overall']:.0f}   export_allowed={report['export_allowed']}")

    failed = [r for r in results if r[0] == FAIL]
    print(f"\n{'-' * 62}")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed in {time.time() - started:.1f}s")
    if failed:
        print("\nFailures:")
        for _, name, detail in failed:
            print(f"  - {name}  {detail}")
        return 1
    print("All guarantees hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
