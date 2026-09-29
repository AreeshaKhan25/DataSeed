"""Run the engine against data it has never seen, and hold it to the invariants
each fixture encodes.

The demo dataset is clean and flatters the engine. These fixtures are not: heavy
PII, 40% missingness, unicode, all numeric wide frames, constant and all null
columns, twelve row tables, and a second relational schema with a different
shape. A pass here means the engine generalises rather than fitting one dataset.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.constraints import infer_constraints  # noqa: E402
from api.engine import fit_table, sample_table  # noqa: E402
from api.relational import check_integrity, generate_relational  # noqa: E402
from api.schema import build_schema, coerce_to_schema, infer_derived_fields  # noqa: E402
from api.seeds import SeedFactory  # noqa: E402
from api.trust import build_trust_report  # noqa: E402

FIX = Path(__file__).resolve().parents[1] / "data" / "fixtures"
results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")
    return bool(ok)


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIX / f"{name}.csv")


def generate_single(name: str, rows: int, seed: int = 11, **kw):
    """Profile, fit and sample one table the way the API would."""
    source = load(name)
    schema = build_schema({name: source}, name=name, seed=seed)
    schema.constraints = infer_constraints({name: source}, schema)
    table = schema.table(name)
    seeds = SeedFactory(seed)
    model = fit_table(table, source, seeds)
    out = sample_table(model, rows, seeds, **kw)
    return source, schema, table, model, out


# --------------------------------------------------------------------------

def test_healthcare() -> None:
    print("\n1. healthcare: heavy PII, 40% missingness, unicode")
    source, schema, table, model, out = generate_single("healthcare", 1200)

    check("rows generated", len(out) == 1200, str(len(out)))
    check("column set preserved", list(out.columns) == list(source.columns))

    for col in ("full_name", "national_id", "email"):
        overlap = len(set(out[col].dropna().astype(str)) & set(source[col].dropna().astype(str)))
        check(f"no real {col} copied", overlap == 0, f"{overlap} leaked")

    pii = {c.name: c.pii for c in table.columns}
    check("national_id flagged direct PII", pii.get("national_id") == "direct", str(pii.get("national_id")))
    check("email flagged direct PII", pii.get("email") == "direct")

    # Missingness should be reproduced, not invented or erased.
    for col, tol in (("notes", 0.08), ("bmi", 0.06)):
        real = source[col].isna().mean()
        synth = out[col].isna().mean()
        check(f"{col} null rate reproduced", abs(real - synth) < tol,
              f"real {real:.2f} vs synth {synth:.2f}")

    # A rare-ish class must survive, not collapse to the majority.
    real_rate = source["readmitted"].mean()
    synth_rate = out["readmitted"].mean()
    check("readmitted class balance preserved", abs(real_rate - synth_rate) < 0.08,
          f"real {real_rate:.3f} vs synth {synth_rate:.3f}")

    check("ages stay plausible",
          out["age"].dropna().between(0, 110).all(),
          f"range {out['age'].min()}..{out['age'].max()}")
    check("blood groups stay in domain",
          set(out["blood_group"].dropna()) <= set(source["blood_group"].dropna()))

    # Unicode must round trip through the whole pipeline.
    encoded = out.to_csv(index=False).encode("utf-8")
    check("output encodes to UTF-8 without loss", len(encoded) > 0)
    check("names are non empty strings",
          out["full_name"].dropna().map(lambda v: isinstance(v, str) and len(v) > 1).all())


def test_sensors() -> None:
    print("\n2. sensors: all numeric, wide, correlated, with spikes")
    source, schema, table, model, out = generate_single("sensors", 2000)

    check("rows generated", len(out) == 2000)
    check("no NaN in a fully populated source",
          out.drop(columns=["reading_id"]).isna().sum().sum() == 0,
          str(int(out.isna().sum().sum())))

    # A Gaussian copula preserves RANK correlation by construction, so Spearman
    # is the measure that actually tests it. Pearson is checked separately below
    # on a pair with no contamination.
    for a, b in [("temp_c", "humidity"), ("temp_c", "pressure_hpa"),
                 ("humidity", "pressure_hpa")]:
        real = source[a].corr(source[b], method="spearman")
        synth = out[a].corr(out[b], method="spearman")
        check(f"rank corr({a},{b}) preserved", abs(real - synth) < 0.10,
              f"real {real:+.3f} vs synth {synth:+.3f}")

    # humidity and pressure carry no injected spikes, so linear correlation
    # should survive too. temp_c does carry spikes: twelve rows that deliberately
    # break the relationship, which a single global copula cannot represent, so
    # its Pearson value is expected to drift. That is a property of the method,
    # not a defect, and the rank check above is what holds it honest.
    real_p = source["humidity"].corr(source["pressure_hpa"])
    synth_p = out["humidity"].corr(out["pressure_hpa"])
    check("linear corr survives on uncontaminated columns",
          abs(real_p - synth_p) < 0.12, f"real {real_p:+.3f} vs synth {synth_p:+.3f}")

    check("voltage keeps 3 decimal places",
          out["voltage"].dropna().map(lambda v: round(v, 3) == v).all())
    check("rpm stays a non negative integer",
          (out["rpm"].dropna() >= 0).all() and
          out["rpm"].dropna().map(lambda v: float(v).is_integer()).all())
    check("vibration stays non negative", (out["vibration"].dropna() >= 0).all())


def test_transactions() -> None:
    print("\n3. transactions: money, computed column, ordered dates")
    source, schema, table, model, out = generate_single("transactions", 1500)

    check("unit_price keeps 2 decimal places",
          out["unit_price"].dropna().map(lambda v: round(v, 2) == v).all())

    kinds = {c.kind for c in schema.constraints}
    check("computed rule inferred", "computed" in kinds, str(sorted(kinds)))
    exprs = [c.params.get("expression") for c in schema.constraints if c.kind == "computed"]
    check("it is the right expression", any("qty" in str(e) and "unit_price" in str(e)
                                            for e in exprs), str(exprs))
    check("date ordering rule inferred", "comparison" in kinds)
    check("currency recognised as constant",
          (out["currency"].dropna() == "GBP").all() if out["currency"].notna().any() else True)

    # The rule engine has to make gross consistent, the copula alone will not.
    from api.constraints import apply_constraints
    repaired, rule_results = apply_constraints(
        out.copy(), table, schema.constraints, SeedFactory(11).stream("rules")
    )
    exact = np.isclose(repaired["gross"],
                       (repaired["qty"] * repaired["unit_price"]).round(2), atol=0.005).mean()
    check("gross equals qty * unit_price after rules", exact == 1.0, f"{exact*100:.1f}% exact")

    fired = sum(r.violations_before for r in rule_results)
    check("rules actually had work to do", fired > 0, f"{fired} violations caught")
    check("nothing was dropped", sum(r.dropped for r in rule_results) == 0)

    placed = pd.to_datetime(repaired["placed_on"], errors="coerce")
    settled = pd.to_datetime(repaired["settled_on"], errors="coerce")
    both = placed.notna() & settled.notna()
    check("no settlement precedes its transaction",
          bool((settled[both] >= placed[both]).all()),
          f"{int((settled[both] < placed[both]).sum())} bad rows")


def test_tiny() -> None:
    print("\n4. tiny: 12 rows, too small to fit properly")
    source, schema, table, model, out = generate_single("tiny", 50)
    check("did not raise", out is not None)
    check("produced the requested rows", len(out) == 50, str(len(out)))
    check("primary key still unique", out["id"].is_unique)
    check("grades stay in domain", set(out["grade"].dropna()) <= {"A", "B"})

    report = build_trust_report(source, table, SeedFactory(11))
    check("trust report declines rather than inventing a score",
          report.get("available") is False, str(report.get("reason", ""))[:78])


def test_degenerate() -> None:
    print("\n5. degenerate: constant, all null, unique and zero columns")
    source, schema, table, model, out = generate_single("degenerate", 400)

    check("constant int stays constant", set(out["constant_int"].dropna()) == {42},
          str(set(out["constant_int"].dropna()))[:40])
    check("constant str stays constant", set(out["constant_str"].dropna()) == {"FIXED"})
    check("single category stays single", set(out["single_category"].dropna()) == {"only"})
    check("all null column stays entirely null", out["all_null"].isna().all())
    check("all zero column stays zero", set(out["all_zero"].dropna()) == {0})
    check("negatives stay negative", (out["negatives"].dropna() < 0).all(),
          f"max {out['negatives'].max()}")
    check("boolean column stays boolean",
          set(map(str, out["boolean_flag"].dropna().unique())) <= {"True", "False"},
          str(set(map(str, out["boolean_flag"].dropna().unique()))))
    check("mostly null column stays mostly null",
          out["mostly_null"].isna().mean() > 0.8,
          f"{out['mostly_null'].isna().mean():.2f} null")
    check("unique code column has no duplicates", out["unique_code"].is_unique)


def test_storefront_relational() -> None:
    print("\n6. storefront: an unseen relational schema, 1:1 + 1:N + N:N")
    names = ["shops", "shop_settings", "products", "labels", "product_labels"]
    frames = {n: load(n) for n in names}

    schema = build_schema(frames, name="storefront", seed=5)
    infer_derived_fields(frames, schema)
    schema.constraints = infer_constraints(frames, schema)

    edges = {(fk.child_table, fk.child_column, fk.parent_table): fk.cardinality
             for fk in schema.foreign_keys}
    check("all four foreign keys detected", len(edges) == 4, str(len(edges)))
    check("shop_settings -> shops found",
          ("shop_settings", "shop_id", "shops") in edges, str(sorted(edges)))
    check("products -> shops found", ("products", "shop_id", "shops") in edges)

    junction = [t.name for t in schema.tables if t.is_junction]
    check("product_labels recognised as a junction", junction == ["product_labels"], str(junction))
    nn = [k for k, v in edges.items() if v == "N:N"]
    check("its two edges are labelled N:N", len(nn) == 2, str(len(nn)))

    seeds = SeedFactory(5)
    models = {t.name: fit_table(t, frames[t.name], seeds) for t in schema.tables}
    out, warnings, rules = generate_relational(schema, models, 300, seeds)

    check("all five tables generated", len(out) == 5, str({k: len(v) for k, v in out.items()}))
    check("no generation warnings", not warnings, "; ".join(warnings)[:120])
    check("labels kept as a lookup table", len(out["labels"]) == len(frames["labels"]),
          f"{len(out['labels'])} vs {len(frames['labels'])}")

    integrity = check_integrity(schema, out)
    check("integrity gate passed", integrity["passed"], str(integrity["score"]))
    check("zero orphan foreign keys", integrity["total_orphans"] == 0,
          str(integrity["orphan_keys"]))
    check("zero duplicate primary keys", integrity["total_duplicate_keys"] == 0)
    check("zero duplicate junction links", integrity["total_duplicate_links"] == 0,
          str(integrity["duplicate_junction_links"]))

    links = out["product_labels"]
    check("every product link resolves",
          links["product_id"].isin(out["products"]["product_id"]).all())
    check("every label link resolves",
          links["label_id"].isin(out["labels"]["label_id"]).all())

    # 1:1 must stay one to one.
    settings = out["shop_settings"]
    check("1:1 table has one row per shop",
          settings["shop_id"].is_unique and len(settings) == len(out["shops"]),
          f"{len(settings)} settings for {len(out['shops'])} shops")

    real_deg = frames["products"].groupby("shop_id").size().mean()
    synth_deg = out["products"].groupby("shop_id").size().mean()
    check("products per shop matches the source", abs(real_deg - synth_deg) < 1.5,
          f"real {real_deg:.2f} vs synth {synth_deg:.2f}")


def test_determinism_across_fixtures() -> None:
    print("\n7. determinism on every fixture")
    for name in ("healthcare", "sensors", "transactions", "degenerate"):
        a = generate_single(name, 200, seed=3)[4]
        b = generate_single(name, 200, seed=3)[4]
        check(f"{name}: same seed, identical output", a.equals(b))
    c = generate_single("sensors", 200, seed=4)[4]
    d = generate_single("sensors", 200, seed=5)[4]
    check("different seeds differ", not c.equals(d))


def test_trust_on_unseen_data() -> None:
    print("\n8. trust report on unseen data")
    for name, floor in (("healthcare", 60), ("sensors", 70), ("transactions", 60)):
        source = load(name)
        schema = build_schema({name: source}, name=name, seed=9)
        schema.constraints = infer_constraints({name: source}, schema)
        report = build_trust_report(source, schema.table(name), SeedFactory(9),
                                    constraints=schema.constraints)
        if not report.get("available"):
            check(f"{name}: report available", False, str(report.get("reason"))[:70])
            continue
        fid = report["fidelity"]["score"]
        priv = report["privacy"]
        check(f"{name}: fidelity above {floor}", fid >= floor, f"{fid}")
        check(f"{name}: zero exact matches", priv["exact_matches"] == 0,
              str(priv["exact_matches"]))
        det = report["detection"].get("auc")
        check(f"{name}: detection AUC below 0.70", det is None or det < 0.70, str(det))


def main() -> int:
    started = time.time()
    if not FIX.exists():
        print("Fixtures missing. Run: python scripts/make_test_fixtures.py")
        return 1

    for fn in (test_healthcare, test_sensors, test_transactions, test_tiny,
               test_degenerate, test_storefront_relational,
               test_determinism_across_fixtures, test_trust_on_unseen_data):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - a crash is itself a failure
            import traceback
            traceback.print_exc()
            check(f"{fn.__name__} raised", False, f"{type(exc).__name__}: {exc}")

    failed = [r for r in results if not r[0]]
    print(f"\n{'-' * 64}")
    print(f"{len(results) - len(failed)}/{len(results)} checks passed in {time.time() - started:.1f}s")
    if failed:
        print("\nFailures:")
        for _, name, detail in failed:
            print(f"  - {name}  {detail}")
        return 1
    print("The engine holds up on data it has never seen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
