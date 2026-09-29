"""Build CSV fixtures that are deliberately harder than the demo data.

The demo set is clean, well shaped and flatters the engine. These are not. Each
fixture targets a property that could plausibly break a synthetic data pipeline,
so that a passing run means something.

Written to data/fixtures/. Every file is small enough to open in a spreadsheet
and inspect by hand.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 7
OUT = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def healthcare(rng: np.random.Generator, faker: Faker) -> pd.DataFrame:
    """Heavy PII, heavy missingness, a skewed target, unicode names.

    Tests: direct PII is regenerated not copied, high null rates survive,
    a rare positive class is preserved, non ASCII does not corrupt output.
    """
    n = 900
    age = np.clip(rng.normal(52, 18, n).round(), 0, 103).astype(int)
    bmi = np.clip(rng.normal(27, 6, n), 13, 62).round(1)
    # Readmission depends on age and bmi, so there is genuine signal to recover.
    logit = -4.2 + 0.035 * age + 0.045 * bmi + rng.normal(0, 0.6, n)
    readmitted = (1 / (1 + np.exp(-logit)) > 0.5).astype(int)

    df = pd.DataFrame({
        "patient_id": np.arange(100000, 100000 + n),
        "full_name": [faker.name() for _ in range(n)],
        "national_id": [faker.ssn() for _ in range(n)],
        "email": [faker.email() for _ in range(n)],
        "age": age,
        "bmi": bmi,
        "blood_group": rng.choice(["A+", "O+", "B+", "AB+", "O-", "A-"], n,
                                  p=[.34, .31, .16, .06, .08, .05]),
        "admitted_on": (pd.to_datetime("2025-01-01")
                        + pd.to_timedelta(rng.integers(0, 300, n), unit="D")).strftime("%Y-%m-%d"),
        "readmitted": readmitted,
        "notes": [faker.sentence(nb_words=10) for _ in range(n)],
    })
    # Unicode in a name column, which has broken CSV pipelines before.
    for i in rng.choice(n, 40, replace=False):
        df.loc[i, "full_name"] = rng.choice(
            ["Zoë O'Brien", "José Álvarez", "Björn Müller", "Aisha Þórsdóttir",
             "李 伟", "Đặng Thu Hà"]
        )
    # Aggressive, uneven missingness.
    df.loc[rng.random(n) < 0.42, "notes"] = None
    df.loc[rng.random(n) < 0.18, "bmi"] = None
    df.loc[rng.random(n) < 0.05, "blood_group"] = None
    return df


def sensors(rng: np.random.Generator) -> pd.DataFrame:
    """All numeric, wide, strongly correlated, with real outliers.

    Tests: the copula preserves a correlation structure, outlier injection does
    not destroy it, and a wide frame does not blow up the covariance fit.
    """
    n = 1500
    base = rng.normal(0, 1, n)
    df = pd.DataFrame({
        "reading_id": np.arange(1, n + 1),
        "temp_c": (18 + 6 * base + rng.normal(0, 0.8, n)).round(2),
        "humidity": np.clip(55 - 9 * base + rng.normal(0, 3, n), 0, 100).round(1),
        "pressure_hpa": (1013 + 2.5 * base + rng.normal(0, 1.2, n)).round(1),
        "voltage": (3.3 + rng.normal(0, 0.04, n)).round(3),
        "rpm": np.clip(rng.normal(1450, 120, n), 0, None).round().astype(int),
        "vibration": np.abs(rng.normal(0.4, 0.15, n)).round(3),
    })
    # A handful of genuine sensor spikes.
    for col, mult in (("temp_c", 4.0), ("vibration", 12.0), ("rpm", 3.0)):
        idx = rng.choice(n, 12, replace=False)
        df.loc[idx, col] = df[col].max() * mult
    return df


def transactions(rng: np.random.Generator, faker: Faker) -> pd.DataFrame:
    """Money, dates in order, a computed column, a conditional null.

    Tests: decimal precision is reproduced, arithmetic relationships are
    inferred, date ordering holds, and a conditional rule can be learned.
    """
    n = 1200
    qty = rng.integers(1, 9, n)
    unit = np.round(rng.lognormal(2.9, 0.7, n), 2)
    placed = pd.to_datetime("2025-02-01") + pd.to_timedelta(rng.integers(0, 240, n), unit="D")
    status = rng.choice(["settled", "pending", "reversed"], n, p=[.78, .15, .07])
    settled = placed + pd.to_timedelta(rng.integers(1, 6, n), unit="D")

    df = pd.DataFrame({
        "txn_id": np.arange(900000, 900000 + n),
        "merchant": [faker.company() for _ in range(n)],
        "category": rng.choice(["grocery", "fuel", "utilities", "travel", "dining"], n),
        "qty": qty,
        "unit_price": unit,
        "gross": np.round(qty * unit, 2),          # exactly qty * unit_price
        "placed_on": placed.strftime("%Y-%m-%d"),
        "settled_on": settled.strftime("%Y-%m-%d"),
        "status": status,
        "currency": "GBP",                          # constant column
    })
    # Unsettled rows genuinely have no settlement date. A conditional rule.
    df.loc[df["status"] != "settled", "settled_on"] = None
    return df


def tiny(rng: np.random.Generator, faker: Faker) -> pd.DataFrame:
    """Barely enough rows to fit anything.

    Tests: the engine degrades gracefully instead of raising when there is not
    enough data for a covariance estimate or a train/test split.
    """
    n = 12
    return pd.DataFrame({
        "id": range(1, n + 1),
        "name": [faker.first_name() for _ in range(n)],
        "score": rng.integers(0, 100, n),
        "grade": rng.choice(["A", "B"], n),
    })


def degenerate(rng: np.random.Generator) -> pd.DataFrame:
    """Every column is pathological in a different way.

    Tests: constant columns, all null columns, a single category, a column that
    is unique per row, zeros, and negatives all survive a round trip.
    """
    n = 300
    return pd.DataFrame({
        "row_id": np.arange(1, n + 1),
        "constant_int": 42,
        "constant_str": "FIXED",
        "all_null": [None] * n,
        "single_category": "only",
        "unique_code": [f"U{i:05d}" for i in range(n)],
        "all_zero": 0,
        "negatives": -np.abs(rng.normal(50, 20, n)).round(2),
        "boolean_flag": rng.choice([True, False], n),
        "mostly_null": [round(float(rng.normal(10, 2)), 2) if rng.random() < 0.08 else None
                        for _ in range(n)],
    })


def storefront(rng: np.random.Generator, faker: Faker) -> dict[str, pd.DataFrame]:
    """A second relational schema, shaped differently from the demo.

    Deliberately not customers/orders/order_items: a self contained shop with a
    1:1 table, a 1:N table and an N:N junction, so the relational engine is
    exercised on a schema it has never seen.
    """
    n_shops = 120
    shop_ids = np.arange(3000, 3000 + n_shops)
    shops = pd.DataFrame({
        "shop_id": shop_ids,
        "shop_name": [faker.company() for _ in range(n_shops)],
        "city": [faker.city() for _ in range(n_shops)],
        "tier": rng.choice(["bronze", "silver", "gold"], n_shops, p=[.55, .3, .15]),
        "rating": np.clip(rng.normal(4.1, 0.5, n_shops), 1, 5).round(1),
    })

    # 1:1  exactly one settings row per shop
    settings = pd.DataFrame({
        "setting_id": np.arange(1, n_shops + 1),
        "shop_id": shop_ids,
        "currency": rng.choice(["GBP", "EUR", "USD"], n_shops),
        "auto_restock": rng.choice([True, False], n_shops),
    })

    # 1:N  products per shop, more for higher tiers
    rate = np.select([shops["tier"] == "bronze", shops["tier"] == "silver"],
                     [3.0, 6.0], default=11.0)
    counts = rng.poisson(rate)
    prod_rows = []
    pid = 50000
    for shop_id, k in zip(shop_ids, counts):
        for _ in range(max(int(k), 1)):
            prod_rows.append({
                "product_id": pid,
                "shop_id": int(shop_id),
                "title": faker.catch_phrase(),
                "price": float(np.round(rng.lognormal(3.0, 0.6), 2)),
                "stock": int(rng.integers(0, 400)),
            })
            pid += 1
    products = pd.DataFrame(prod_rows)

    # N:N  products tagged with labels, pair unique
    labels = pd.DataFrame({
        "label_id": np.arange(700, 708),
        "label": ["new", "sale", "bestseller", "clearance", "organic",
                  "imported", "fragile", "bulk"],
    })
    weights = rng.dirichlet(np.ones(len(labels)) * 1.4)
    link_rows = []
    for product_id in products["product_id"]:
        k = int(rng.poisson(1.6))
        if k <= 0:
            continue
        for j in rng.choice(len(labels), size=min(k, len(labels)), replace=False, p=weights):
            link_rows.append({
                "product_id": int(product_id),
                "label_id": int(labels["label_id"].iloc[j]),
            })
    product_labels = pd.DataFrame(link_rows)

    return {
        "shops": shops,
        "shop_settings": settings,
        "products": products,
        "labels": labels,
        "product_labels": product_labels,
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    faker = Faker("en_GB")
    faker.seed_instance(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    single = {
        "healthcare": healthcare(rng, faker),
        "sensors": sensors(rng),
        "transactions": transactions(rng, faker),
        "tiny": tiny(rng, faker),
        "degenerate": degenerate(rng),
    }
    for name, frame in single.items():
        frame.to_csv(OUT / f"{name}.csv", index=False)

    for name, frame in storefront(rng, faker).items():
        frame.to_csv(OUT / f"{name}.csv", index=False)

    print(f"Fixtures written to {OUT}\n")
    for path in sorted(OUT.glob("*.csv")):
        frame = pd.read_csv(path)
        nulls = frame.isna().sum().sum()
        print(f"  {path.name:22} {len(frame):>6} rows x {len(frame.columns):>2} cols"
              f"  ({nulls} nulls)")

    # State the properties the harness will hold the engine to.
    txn = pd.read_csv(OUT / "transactions.csv")
    links = pd.read_csv(OUT / "product_labels.csv")
    print("\nInvariants these fixtures encode:")
    print(f"  transactions.gross == qty * unit_price : "
          f"{bool(np.isclose(txn['gross'], (txn['qty'] * txn['unit_price']).round(2)).all())}")
    print(f"  settled_on is null unless settled      : "
          f"{bool(txn.loc[txn['status'] != 'settled', 'settled_on'].isna().all())}")
    print(f"  product_labels pair is unique          : "
          f"{not links.duplicated().any()}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    main()
