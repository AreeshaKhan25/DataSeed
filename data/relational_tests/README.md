# Relational test sets

Six uploads, each isolating one relational structure. Regenerate them with:

```bash
python scripts/make_relational_test_csvs.py
```

**Upload all the files of one set together, in a single go.** Relationships are
detected across the files in one upload, so selecting them one at a time leaves
the platform with several unrelated tables and nothing to link.

These are separate from `data/manual_tests/`, which exercises the ordinary path.
Each set here isolates a structure, so a set that fails tells you which one
broke rather than only that something did.

---

## Set 1: a self reference

**Upload:** `selfref_employees.csv` on its own.

`manager_id` points at `employee_id` in the same table.

| Check | What correct looks like |
|:--|:--|
| Relationships screen | One foreign key, from the table to itself |
| Every `manager_id` | Exists as an `employee_id` in the generated output |
| Nobody manages themselves | No row where `manager_id` equals its own `employee_id` |
| No cycles | Following managers upward always terminates |
| Roots | Around 2% of rows have a blank manager, matching the source |

This is a regression test. Self references used to be skipped by the detector,
so `manager_id` was treated as an ordinary text column and came back filled with
unrelated English words like "politics" and "building", with **every single
value dangling**. Integrity reported no orphans, because with no foreign key
recorded there was nothing to check, and the trust report scored it 95.5.

## Set 2: a strict one to one

**Upload:** `onetoone_users.csv`, `onetoone_profiles.csv`

Exactly one profile per user, never two and never none.

| Check | What correct looks like |
|:--|:--|
| Cardinality | Reported as 1:1, not 1:N |
| Row counts | The two generated tables have the same number of rows |
| `user_id` in profiles | Appears exactly once each, no duplicates |

## Set 3: a three level chain, with a lookup table too small to score

**Upload:** `chain_regions.csv`, `chain_cities.csv`, `chain_stores.csv`, `chain_sales.csv`

regions to cities to stores to sales. `chain_regions.csv` has 5 rows, well under
the 50 the trust report needs.

| Check | What correct looks like |
|:--|:--|
| Foreign keys | Three, forming a chain rather than a star |
| Orphans | Zero at every level |
| `line_total` | Exactly `units` × `unit_price`, to the cent |
| Trust report | **Appears**, scored from one of the larger tables |

That last row is the point of the 5 row table. The report used to be built from
whichever file was selected first, so uploading a small lookup table first
produced no report at all while the same four files in another order scored
fine. Try uploading this set with `chain_regions.csv` first and then again with
it last: the report must be identical both times.

## Set 4: a star schema

**Upload:** `star_customers.csv`, `star_products.csv`, `star_channels.csv`, `star_transactions.csv`

One fact table with three foreign keys to three different parents.

| Check | What correct looks like |
|:--|:--|
| Foreign keys | Three, all from `star_transactions` |
| Orphans | Zero on all three |
| Spread | Each dimension keeps a realistic mix, rather than most rows collapsing onto a few popular values |
| `revenue` | Exactly `quantity` × `unit_price` |

## Set 5: an optional foreign key, and two children of one parent

**Upload:** `optional_coupons.csv`, `optional_orders.csv`, `optional_shipments.csv`, `optional_payments.csv`

`coupon_id` is blank on most orders. `shipments` and `payments` are both
children of `orders`.

| Check | What correct looks like |
|:--|:--|
| Blank `coupon_id` | Still blank on roughly 82% of orders, as in the source |
| Present `coupon_id` | Always resolves to a real coupon |
| Both children | No `order_id` in either that does not exist in orders |

An optional relationship is the one most often got wrong. A generator that
treats every foreign key as mandatory will give every order a coupon, which
quietly changes what the data says.

## Set 6: N:N where the junction carries its own columns

**Upload:** `nn_students.csv`, `nn_courses.csv`, `nn_enrolments.csv`

A student takes many courses, a course has many students, and the enrolment
itself holds a grade and an attendance figure.

| Check | What correct looks like |
|:--|:--|
| Relationships screen | Students to courses shown as **N:N** |
| The junction | Detected as a junction, not as two unrelated 1:N links |
| Uniqueness | No `(student_id, course_id)` pair appears twice |
| `grade`, `attendance_pct` | Keep their distributions, rather than being discarded as junction noise |

---

## Results when these were last run

All six, generated at 600 rows with validation on:

| Set | Foreign keys found | Orphans | Trust report |
|:--|:--|:--|--:|
| 1 self reference | 1, self | none | 95.5 |
| 2 one to one | 1, as 1:1 | none | 95.7 |
| 3 deep chain | 3, chained | none | 97.1 |
| 4 star schema | 3, all from the fact table | none | 96.2 |
| 5 optional and siblings | 3 | none | 96.4 |
| 6 N:N with payload | 2, both N:N | none | 98.0 |

Treat those as a baseline rather than a target. What matters is the structural
checks in each section above, not the number.
