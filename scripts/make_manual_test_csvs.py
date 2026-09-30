"""Builds the CSV files used for manual testing, in data/manual_tests/.

These are for driving the product by hand, which is a different job from the
fixtures in data/fixtures/ that the automated suites assert against. Each file
here is meant to be uploaded through the interface so a human can look at what
comes back.

Every set is deliberately small enough to eyeball and large enough to profile:
the engine needs roughly 50 rows before it will score a trust report, so
nothing here sits below that except the file that is meant to test exactly that
boundary.

    python scripts/make_manual_test_csvs.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "manual_tests"

FIRST = ["Ayesha", "Bilal", "Hina", "Usman", "Sana", "Tariq", "Zara", "Imran",
         "Nadia", "Faisal", "Rabia", "Kashif", "Mehwish", "Adnan", "Sadia",
         "Junaid", "Amna", "Rizwan", "Iqra", "Shahid", "Omar", "Laiba",
         "Hamza", "Areeba", "Danish", "Maryam", "Saad", "Noor", "Bilquis", "Yasir"]
LAST = ["Khan", "Malik", "Ahmed", "Sheikh", "Butt", "Qureshi", "Chaudhry",
        "Hussain", "Raza", "Iqbal", "Siddiqui", "Farooq", "Javed", "Nawaz"]
CITIES = ["Lahore", "Karachi", "Islamabad", "Multan", "Peshawar", "Quetta", "Faisalabad"]


def _write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {name:34} {len(rows):5} rows, {len(rows[0])} columns")


def _person(rng: random.Random) -> str:
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


# --------------------------------------------------------------------------
# Single table sets
# --------------------------------------------------------------------------

def employees(rng: random.Random) -> None:
    """The ordinary case. Named columns, mixed types, one computed column.

    Check: Name and Email must come back completely invented, Bonus must stay
    at exactly 10% of Salary, and JoinDate must stay a plausible date.
    """
    depts = ["Engineering", "Sales", "Finance", "Operations", "Marketing"]
    rows = []
    for i in range(400):
        salary = round(rng.uniform(60_000, 320_000), 2)
        first, last = rng.choice(FIRST), rng.choice(LAST)
        rows.append({
            "employee_id": 1000 + i,
            "Name": f"{first} {last}",
            "Email": f"{first.lower()}.{last.lower()}{i}@acme.pk",
            "Department": rng.choice(depts),
            "City": rng.choice(CITIES),
            "Salary": salary,
            "Bonus": round(salary * 0.10, 2),
            "JoinDate": (date(2020, 1, 1) + timedelta(days=rng.randint(0, 1800))).isoformat(),
            "IsManager": rng.random() < 0.15,
        })
    _write("single_employees.csv", rows)


def awkward_headers(rng: random.Random) -> None:
    """The case that used to leak real names into the output.

    Every one of these columns holds a person, and not one of them is called
    "name". Check: none of the generated values appear anywhere in this file.
    """
    rows = []
    for i in range(300):
        rows.append({
            "Customer": _person(rng),
            "Contact Person": _person(rng),
            "Employee Name": _person(rng),
            "accountOwner": _person(rng),
            "customer_id": f"C{i:05d}",          # must stay an identifier
            "order_total": round(rng.uniform(10, 4000), 2),
            "branch": rng.choice(CITIES),
        })
    _write("single_awkward_headers.csv", rows)


def messy(rng: random.Random) -> None:
    """Nulls, unicode, money written as text, and a constant column.

    Check: the platform ingests it without erroring, the null rate is roughly
    preserved, and the constant column stays constant.
    """
    rows = []
    for i in range(250):
        rows.append({
            "ref": f"REF-{i:04d}",
            "client_name": _person(rng) if rng.random() > 0.15 else None,
            "notes": rng.choice([
                "Delivered on time", "Customer asked for a refund",
                "Réclamation reçue", "تم التسليم", "—", None,
            ]),
            "price_text": f"PKR {rng.randint(500, 90_000):,}",
            "discount_pct": rng.choice([0, 5, 10, 15, None]),
            "country": "Pakistan",                     # constant on purpose
            "recorded_at": (date(2024, 1, 1) + timedelta(days=rng.randint(0, 600))).isoformat(),
        })
    _write("single_messy.csv", rows)


def tiny(rng: random.Random) -> None:
    """Under the scoring threshold on purpose.

    Check: generation still works and the trust report explains that there were
    too few rows to score rather than failing silently.
    """
    rows = [{
        "id": i,
        "full_name": _person(rng),
        "amount": round(rng.uniform(5, 500), 2),
    } for i in range(18)]
    _write("single_tiny_18_rows.csv", rows)


# --------------------------------------------------------------------------
# Multi table set: upload all four together
# --------------------------------------------------------------------------

def retail(rng: random.Random) -> None:
    """Four related tables covering 1:N and N:N.

    customers 1:N orders, orders 1:N order_items, and order_items is the
    junction between orders and products.

    Check: no orphan foreign keys in the trust report's integrity section, the
    N:N relationship is detected on the relationships screen, and invoices in
    the documents screen bind to orders and order_items.
    """
    customers = []
    for i in range(150):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        customers.append({
            "customer_id": i + 1,
            "customer_name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{i}@example.pk",
            "city": rng.choice(CITIES),
            "signed_up": (date(2023, 1, 1) + timedelta(days=rng.randint(0, 900))).isoformat(),
        })

    products = []
    names = ["Kettle", "Toaster", "Blender", "Lamp", "Chair", "Desk", "Monitor",
             "Keyboard", "Mouse", "Headset", "Backpack", "Bottle"]
    for i, base in enumerate([f"{n} {v}" for n in names for v in ("Basic", "Pro")]):
        products.append({
            "product_id": i + 1,
            "product_name": base,
            "category": rng.choice(["Kitchen", "Furniture", "Computing", "Travel"]),
            "unit_price": round(rng.uniform(500, 25_000), 2),
        })

    orders, items = [], []
    order_id = 0
    for _ in range(500):
        order_id += 1
        placed = date(2024, 1, 1) + timedelta(days=rng.randint(0, 600))
        orders.append({
            "order_id": order_id,
            "customer_id": rng.choice(customers)["customer_id"],
            "placed_on": placed.isoformat(),
            # settled always falls 1 to 5 days after placed: an offset rule
            "settled_on": (placed + timedelta(days=rng.randint(1, 5))).isoformat(),
            "status": rng.choice(["paid", "paid", "paid", "refunded", "pending"]),
        })
        for product in rng.sample(products, rng.randint(1, 4)):
            qty = rng.randint(1, 5)
            items.append({
                "order_id": order_id,
                "product_id": product["product_id"],
                "quantity": qty,
                "unit_price": product["unit_price"],
                # gross is exactly quantity * unit_price: a computed rule
                "gross": round(qty * product["unit_price"], 2),
            })

    _write("multi_customers.csv", customers)
    _write("multi_products.csv", products)
    _write("multi_orders.csv", orders)
    _write("multi_order_items.csv", items)


def main() -> None:
    rng = random.Random(20260930)
    print(f"Writing manual test CSVs to {OUT}\n")
    print("single table:")
    employees(rng)
    awkward_headers(rng)
    messy(rng)
    tiny(rng)
    print("\nmulti table, upload these four together:")
    retail(rng)
    print(f"\nDone. See {OUT / 'README.md'} for what to check in each.")


if __name__ == "__main__":
    main()
