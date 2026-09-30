"""Builds the relational test sets in data/relational_tests/.

Each set is a separate upload. Upload all the files of one set together, in one
go, or the relationships between them cannot be detected.

The sets cover the shapes a relational generator has to get right, and they are
separate from data/manual_tests/ because each one isolates a single structure.
When something breaks, a set that fails tells you which structure broke rather
than only that something did.

    python scripts/make_relational_test_csvs.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "relational_tests"

FIRST = ["Ayesha", "Bilal", "Hina", "Usman", "Sana", "Tariq", "Zara", "Imran",
         "Nadia", "Faisal", "Rabia", "Kashif", "Mehwish", "Adnan", "Sadia",
         "Junaid", "Amna", "Rizwan", "Iqra", "Shahid", "Omar", "Laiba"]
LAST = ["Khan", "Malik", "Ahmed", "Sheikh", "Butt", "Qureshi", "Chaudhry",
        "Hussain", "Raza", "Iqbal", "Siddiqui", "Farooq"]


def _write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"    {name:32} {len(rows):5} rows")


def _person(rng: random.Random) -> str:
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def _day(rng: random.Random, start: date = date(2024, 1, 1), span: int = 600) -> str:
    return (start + timedelta(days=rng.randint(0, span))).isoformat()


# --------------------------------------------------------------------------

def self_reference(rng: random.Random) -> None:
    """Set 1. A table whose foreign key points at itself.

    Every employee except the four at the top reports to another employee in the
    same table. The generator has to fill manager_id from rows of the table it
    is currently generating, without pointing at a row that does not exist and
    without creating a cycle where two people manage each other.

    Check: every manager_id that is not blank exists as an employee_id, and
    nobody is their own manager.
    """
    print("  set 1, self reference: upload on its own")
    rows = []
    for i in range(220):
        # The first four have no manager, and everyone else reports to someone
        # created before them, which is what keeps the hierarchy acyclic.
        manager = "" if i < 4 else f"E{rng.randint(0, max(0, i - 1)):04d}"
        rows.append({
            "employee_id": f"E{i:04d}",
            "employee_name": _person(rng),
            "manager_id": manager,
            "department": rng.choice(["Engineering", "Sales", "Finance", "Support"]),
            "salary": round(rng.uniform(60_000, 300_000), 2),
            "hired_on": _day(rng, date(2019, 1, 1), 2000),
        })
    _write("selfref_employees.csv", rows)


def one_to_one(rng: random.Random) -> None:
    """Set 2. A strict one to one.

    Exactly one profile per user, no more and no fewer. A generator that treats
    this as an ordinary 1:N will produce users with two profiles or none.

    Check: the generated tables have the same row count, and every user_id in
    profiles appears exactly once.
    """
    print("  set 2, one to one: upload both together")
    users, profiles = [], []
    for i in range(180):
        users.append({
            "user_id": i + 1,
            "username": f"user{i:04d}",
            "email": f"user{i:04d}@example.pk",
            "joined_on": _day(rng, date(2022, 1, 1), 1200),
            "is_active": rng.random() < 0.85,
        })
        profiles.append({
            "profile_id": i + 1,
            "user_id": i + 1,
            "display_name": _person(rng),
            "city": rng.choice(["Lahore", "Karachi", "Islamabad", "Multan"]),
            "bio_length": rng.randint(0, 300),
        })
    _write("onetoone_users.csv", users)
    _write("onetoone_profiles.csv", profiles)


def deep_chain(rng: random.Random) -> None:
    """Set 3. A three level chain, plus a lookup table too small to score.

    regions has one row per region and stays well under the fifty rows the trust
    report needs. It is here deliberately: the report must still be produced,
    from one of the larger tables, instead of giving up because a small table
    happened to be first.

    Check: sales roll up correctly through stores and cities to regions, no
    orphans at any level, and a trust report appears whatever order these are
    uploaded in.
    """
    print("  set 3, deep chain with a tiny lookup: upload all four together")
    region_names = ["Punjab", "Sindh", "KPK", "Balochistan", "Gilgit Baltistan"]
    regions = [{"region_id": i + 1, "region_name": n,
                "region_code": f"R{i + 1:02d}"} for i, n in enumerate(region_names)]

    cities = []
    for i in range(60):
        cities.append({
            "city_id": i + 1,
            "region_id": rng.choice(regions)["region_id"],
            "city_name": f"City {i + 1:02d}",
            "population": rng.randint(50_000, 9_000_000),
        })

    stores = []
    for i in range(200):
        stores.append({
            "store_id": i + 1,
            "city_id": rng.choice(cities)["city_id"],
            "store_name": f"Store {i + 1:03d}",
            "floor_area_sqft": rng.randint(400, 9000),
            "opened_on": _day(rng, date(2015, 1, 1), 3000),
        })

    sales = []
    for i in range(1500):
        units = rng.randint(1, 12)
        unit_price = round(rng.uniform(150, 9000), 2)
        sales.append({
            "sale_id": i + 1,
            "store_id": rng.choice(stores)["store_id"],
            "sold_on": _day(rng),
            "units": units,
            "unit_price": unit_price,
            # A computed column, so the rules engine has something to hold
            "line_total": round(units * unit_price, 2),
        })

    _write("chain_regions.csv", regions)
    _write("chain_cities.csv", cities)
    _write("chain_stores.csv", stores)
    _write("chain_sales.csv", sales)


def star_schema(rng: random.Random) -> None:
    """Set 4. One fact table with three foreign keys to three different parents.

    This is the shape a warehouse fact table takes. The generator has to satisfy
    three parents at once for every row, rather than one.

    Check: all three foreign keys resolve, and the mix across each dimension
    roughly matches the source rather than collapsing onto a few popular values.
    """
    print("  set 4, star schema: upload all four together")
    customers = [{
        "customer_id": i + 1,
        "customer_name": _person(rng),
        "segment": rng.choice(["retail", "wholesale", "online"]),
    } for i in range(120)]

    products = [{
        "product_id": i + 1,
        "product_name": f"Product {i + 1:03d}",
        "category": rng.choice(["Kitchen", "Furniture", "Computing", "Travel"]),
        "list_price": round(rng.uniform(300, 40_000), 2),
    } for i in range(90)]

    channels = [{
        "channel_id": i + 1,
        "channel_name": n,
        "commission_pct": pct,
    } for i, (n, pct) in enumerate(
        [("Storefront", 0.0), ("Marketplace", 12.5), ("Reseller", 8.0),
         ("Direct", 2.0), ("Affiliate", 15.0)]
    )]

    facts = []
    for i in range(1800):
        qty = rng.randint(1, 8)
        price = round(rng.uniform(300, 40_000), 2)
        facts.append({
            "transaction_id": i + 1,
            "customer_id": rng.choice(customers)["customer_id"],
            "product_id": rng.choice(products)["product_id"],
            "channel_id": rng.choice(channels)["channel_id"],
            "occurred_on": _day(rng),
            "quantity": qty,
            "unit_price": price,
            "revenue": round(qty * price, 2),
        })

    _write("star_customers.csv", customers)
    _write("star_products.csv", products)
    _write("star_channels.csv", channels)
    _write("star_transactions.csv", facts)


def nullable_and_siblings(rng: random.Random) -> None:
    """Set 5. An optional foreign key, and two children of the same parent.

    coupon_id is null on most orders, which is what an optional relationship
    looks like in practice. A generator that treats a foreign key as mandatory
    will invent a coupon for every order and change the meaning of the data.

    shipments and payments are both children of orders, so orders has to satisfy
    two independent child tables at once.

    Check: the share of orders with no coupon stays close to the source, every
    coupon_id that is present resolves, and neither shipments nor payments
    contains an order_id that does not exist.
    """
    print("  set 5, nullable FK and sibling children: upload all four together")
    coupons = [{
        "coupon_id": i + 1,
        "code": f"SAVE{i + 1:03d}",
        "discount_pct": rng.choice([5, 10, 15, 20, 25]),
    } for i in range(40)]

    orders = []
    for i in range(700):
        has_coupon = rng.random() < 0.18          # most orders have none
        orders.append({
            "order_id": i + 1,
            "buyer_name": _person(rng),
            "coupon_id": rng.choice(coupons)["coupon_id"] if has_coupon else "",
            "placed_on": _day(rng),
            "order_total": round(rng.uniform(500, 60_000), 2),
        })

    shipments, payments = [], []
    for order in orders:
        if rng.random() < 0.92:                   # a few orders never ship
            shipments.append({
                "shipment_id": len(shipments) + 1,
                "order_id": order["order_id"],
                "carrier": rng.choice(["TCS", "Leopards", "M&P", "DHL"]),
                "shipped_on": order["placed_on"],
                "weight_kg": round(rng.uniform(0.2, 25.0), 2),
            })
        for _ in range(rng.choice([1, 1, 1, 2])):  # some orders pay in parts
            payments.append({
                "payment_id": len(payments) + 1,
                "order_id": order["order_id"],
                "method": rng.choice(["card", "cash", "bank transfer", "wallet"]),
                "paid_on": order["placed_on"],
                "amount": round(rng.uniform(100, 60_000), 2),
            })

    _write("optional_coupons.csv", coupons)
    _write("optional_orders.csv", orders)
    _write("optional_shipments.csv", shipments)
    _write("optional_payments.csv", payments)


def many_to_many_with_payload(rng: random.Random) -> None:
    """Set 6. N:N where the junction carries its own columns.

    A student takes many courses and a course has many students, and the
    enrolment itself holds a grade and a date. The junction has to be detected
    by shape, and the pair of foreign keys has to stay unique: the same student
    must not be enrolled on the same course twice.

    Check: the relationships screen shows students to courses as N:N, and no
    (student_id, course_id) pair repeats in the generated enrolments.
    """
    print("  set 6, N:N with payload: upload all three together")
    students = [{
        "student_id": i + 1,
        "student_name": _person(rng),
        "year_group": rng.randint(1, 4),
        "enrolled_on": _day(rng, date(2021, 9, 1), 1000),
    } for i in range(160)]

    courses = [{
        "course_id": i + 1,
        "course_name": f"Course {i + 1:02d}",
        "credits": rng.choice([5, 10, 15, 20]),
        "department": rng.choice(["Computing", "Business", "Design", "Physics"]),
    } for i in range(55)]

    seen: set[tuple[int, int]] = set()
    enrolments = []
    for student in students:
        for course in rng.sample(courses, rng.randint(3, 7)):
            pair = (student["student_id"], course["course_id"])
            if pair in seen:
                continue
            seen.add(pair)
            enrolments.append({
                "enrolment_id": len(enrolments) + 1,
                "student_id": pair[0],
                "course_id": pair[1],
                "grade": rng.choice(["A", "A", "B", "B", "B", "C", "D", "F"]),
                "attendance_pct": rng.randint(40, 100),
            })

    _write("nn_students.csv", students)
    _write("nn_courses.csv", courses)
    _write("nn_enrolments.csv", enrolments)


def main() -> None:
    rng = random.Random(20260930)
    print(f"Writing relational test sets to {OUT}\n")
    self_reference(rng)
    one_to_one(rng)
    deep_chain(rng)
    star_schema(rng)
    nullable_and_siblings(rng)
    many_to_many_with_payload(rng)
    print(f"\nDone. {OUT / 'README.md'} says what to check in each set.")


if __name__ == "__main__":
    main()
