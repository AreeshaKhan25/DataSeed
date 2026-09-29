"""Generate the "real" source data the demo learns from.

These three CSVs stand in for a customer's production extract. They are built
with genuine structure -- balance drives segment, tenure and spend drive churn,
order totals really are the sum of their line items -- so that the fidelity and
utility metrics have something meaningful to recover. Random noise would produce
a TSTR score near zero and make the platform look broken.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 20240929
OUT = Path(__file__).resolve().parents[1] / "data" / "demo"

N_CUSTOMERS = 1200
SEGMENTS = ["Standard", "Plus", "Premium"]
STATUSES = ["shipped", "pending", "refunded", "cancelled"]
CATEGORIES = ["Electronics", "Home", "Apparel", "Grocery", "Sports"]


def main() -> None:
    rng = np.random.default_rng(SEED)
    faker = Faker("en_US")
    faker.seed_instance(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- customers -------------------------------------------------------
    customer_ids = np.arange(10000, 10000 + N_CUSTOMERS)

    # Log-normal balances, so the distribution is skewed like real money.
    balance = np.round(rng.lognormal(mean=5.6, sigma=0.9, size=N_CUSTOMERS), 2)
    balance = np.clip(balance, 5.0, 20000.0)

    tenure_days = rng.integers(20, 1500, size=N_CUSTOMERS)
    signup = pd.to_datetime("2025-09-01") - pd.to_timedelta(tenure_days, unit="D")

    # Segment follows balance, with deliberate overlap at the boundaries so the
    # relationship is learnable but not trivially separable.
    noise = rng.normal(0, 0.28, size=N_CUSTOMERS)
    score = np.log(balance) + noise
    cuts = np.quantile(score, [0.55, 0.85])
    segment = np.select(
        [score < cuts[0], score < cuts[1]], [SEGMENTS[0], SEGMENTS[1]], default=SEGMENTS[2]
    )

    # Churn: low balance and short tenure raise the probability.
    logit = 2.2 - 0.00045 * balance - 0.0016 * tenure_days + rng.normal(0, 0.55, N_CUSTOMERS)
    churned = (1 / (1 + np.exp(-logit)) > 0.5).astype(int)

    customers = pd.DataFrame({
        "customer_id": customer_ids,
        "name": [faker.name() for _ in range(N_CUSTOMERS)],
        "email": [faker.email() for _ in range(N_CUSTOMERS)],
        "city": [faker.city() for _ in range(N_CUSTOMERS)],
        "country": rng.choice(
            ["United Kingdom", "Germany", "France", "Spain", "Italy"],
            size=N_CUSTOMERS, p=[0.34, 0.24, 0.18, 0.13, 0.11],
        ),
        "signup_date": signup.strftime("%Y-%m-%d"),
        "segment": segment,
        "balance": balance,
        "tenure_days": tenure_days,
        "churned": churned,
    })

    # A realistic sprinkle of missing values in a non-critical column.
    missing = rng.random(N_CUSTOMERS) < 0.04
    customers.loc[missing, "city"] = None

    # ---- orders ----------------------------------------------------------
    # Premium customers order more often. Counts come from a Poisson draw whose
    # rate depends on the segment, which is what the FK detector later recovers
    # as the children-per-parent distribution.
    rate = np.select(
        [segment == "Standard", segment == "Plus"], [1.4, 3.1], default=5.2
    )
    order_counts = rng.poisson(rate)

    order_rows = []
    order_id = 50000
    for idx, count in enumerate(order_counts):
        for _ in range(count):
            offset = int(rng.integers(0, max(int(tenure_days[idx]), 1)))
            order_rows.append({
                "order_id": order_id,
                "customer_id": int(customer_ids[idx]),
                "order_date": (pd.to_datetime("2025-09-01") - pd.Timedelta(days=offset)).strftime("%Y-%m-%d"),
                "status": rng.choice(STATUSES, p=[0.72, 0.14, 0.09, 0.05]),
                "channel": rng.choice(["web", "mobile", "store"], p=[0.51, 0.38, 0.11]),
            })
            order_id += 1
    orders = pd.DataFrame(order_rows)

    # A second date, so the platform has a genuine ordering rule to learn:
    # a shipment never precedes its order, and unshipped orders have no date.
    lead_days = rng.integers(1, 9, size=len(orders))
    shipped = pd.to_datetime(orders["order_date"]) + pd.to_timedelta(lead_days, unit="D")
    orders["shipped_date"] = shipped.dt.strftime("%Y-%m-%d")
    orders.loc[orders["status"].isin(["pending", "cancelled"]), "shipped_date"] = None

    # ---- order_items -----------------------------------------------------
    item_rows = []
    item_id = 900000
    n_items = rng.integers(1, 7, size=len(orders))
    for row_idx, order in enumerate(orders.itertuples(index=False)):
        for _ in range(int(n_items[row_idx])):
            price = float(np.round(rng.lognormal(mean=3.1, sigma=0.7), 2))
            item_rows.append({
                "item_id": item_id,
                "order_id": int(order.order_id),
                "sku": f"SKU-{int(rng.integers(10000, 99999))}",
                "category": rng.choice(CATEGORIES),
                "qty": int(rng.integers(1, 5)),
                "unit_price": min(price, 900.0),
            })
            item_id += 1
    order_items = pd.DataFrame(item_rows)
    order_items["line_total"] = (order_items["qty"] * order_items["unit_price"]).round(2)

    # ---- reconcile the parent aggregate ---------------------------------
    # orders.total is COMPUTED, never invented. The platform must reproduce
    # exactly this property in its own output.
    totals = order_items.groupby("order_id")["line_total"].sum().round(2)
    counts = order_items.groupby("order_id").size()
    orders["total"] = orders["order_id"].map(totals).fillna(0.0).round(2)
    orders["item_count"] = orders["order_id"].map(counts).fillna(0).astype(int)

    # ---- tags and customer_tags (a genuine N:N) --------------------------
    # Customers carry many tags and each tag covers many customers. The link is
    # a junction table whose (customer_id, tag_id) pair is unique -- which is
    # what the FK detector keys on to recognise the relationship as N:N.
    tag_names = [
        "newsletter", "high-value", "churn-risk", "beta-tester", "referrer",
        "mobile-first", "enterprise", "seasonal", "support-heavy", "advocate",
    ]
    tags = pd.DataFrame({
        "tag_id": np.arange(500, 500 + len(tag_names)),
        "tag_name": tag_names,
        "tag_group": rng.choice(["lifecycle", "behaviour", "value"], size=len(tag_names)),
    })

    # Tag popularity is uneven, and premium customers carry more tags -- so the
    # degree distribution on both sides is worth learning rather than uniform.
    tag_weights = rng.dirichlet(np.ones(len(tag_names)) * 1.6)
    tags_per_customer = rng.poisson(
        np.select([segment == "Standard", segment == "Plus"], [1.2, 2.4], default=3.6)
    )

    link_rows = []
    for idx, n_tags in enumerate(tags_per_customer):
        if n_tags <= 0:
            continue
        picked = rng.choice(
            len(tag_names), size=min(int(n_tags), len(tag_names)),
            replace=False, p=tag_weights,
        )
        for t in picked:
            link_rows.append({
                "customer_id": int(customer_ids[idx]),
                "tag_id": int(tags["tag_id"].iloc[t]),
                "applied_on": (pd.to_datetime("2025-09-01")
                               - pd.Timedelta(days=int(rng.integers(0, 400)))).strftime("%Y-%m-%d"),
            })
    customer_tags = pd.DataFrame(link_rows)

    tags.to_csv(OUT / "tags.csv", index=False)
    customer_tags.to_csv(OUT / "customer_tags.csv", index=False)

    customers.to_csv(OUT / "customers.csv", index=False)
    orders.to_csv(OUT / "orders.csv", index=False)
    order_items.to_csv(OUT / "order_items.csv", index=False)

    # ---- bank transactions (for the document demo) ----------------------
    n_tx = 900
    merchants = [
        "Greenleaf Market", "Riverside Utilities", "Payroll deposit", "Northbank Fuel",
        "Cloudhost Ltd", "Metro Transit", "Blue Fig Cafe", "Orchard Pharmacy",
        "Summit Insurance", "Lakeside Gym",
    ]
    is_credit = rng.random(n_tx) < 0.22
    amount = np.where(
        is_credit,
        np.round(rng.lognormal(6.8, 0.5, n_tx), 2),
        np.round(rng.lognormal(3.6, 0.9, n_tx), 2),
    )
    tx_dates = pd.to_datetime("2025-06-01") + pd.to_timedelta(
        np.sort(rng.integers(0, 120, n_tx)), unit="D"
    )
    transactions = pd.DataFrame({
        "transaction_id": np.arange(700000, 700000 + n_tx),
        "account_id": rng.choice([np.int64(x) for x in range(88001, 88013)], size=n_tx),
        "tx_date": tx_dates.strftime("%Y-%m-%d"),
        "description": rng.choice(merchants, size=n_tx),
        "direction": np.where(is_credit, "credit", "debit"),
        "amount": np.clip(amount, 1.0, 6000.0),
    })
    transactions.to_csv(OUT / "transactions.csv", index=False)

    print(f"Wrote demo data to {OUT}")
    for name, frame in [
        ("customers", customers), ("orders", orders),
        ("order_items", order_items), ("tags", tags),
        ("customer_tags", customer_tags), ("transactions", transactions),
    ]:
        print(f"  {name:14} {len(frame):>6} rows x {len(frame.columns)} cols")

    reconciled = np.isclose(
        orders["total"],
        orders["order_id"].map(totals).fillna(0.0),
    ).all()
    print(f"  orders.total reconciles with order_items: {reconciled}")
    pair_unique = not customer_tags.duplicated(["customer_id", "tag_id"]).any()
    print(f"  customer_tags is a valid N:N junction (pair unique): {pair_unique}")
    print(f"  tags per customer: min {tags_per_customer.min()} "
          f"avg {tags_per_customer.mean():.1f} max {tags_per_customer.max()}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    main()
