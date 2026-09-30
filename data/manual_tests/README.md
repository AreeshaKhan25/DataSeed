# Manual test files

CSVs for driving the platform by hand. Regenerate them at any time with:

```bash
python scripts/make_manual_test_csvs.py
```

These are separate from `data/fixtures/`, which the automated suites assert
against. These are for looking at with your own eyes.

Each file below says what to check and, where relevant, which bug it exists to
catch. A file that passes its checks is not proof the platform is correct, but
a file that fails one is proof it is not.

---

## Single table

Upload one file on its own.

### `single_employees.csv` — 400 rows, the ordinary case

Named columns, mixed types, one computed column.

| Check | What correct looks like |
|---|---|
| `Name` and `Email` | **Completely invented.** Not one value may appear in the source file. |
| `Bonus` | Exactly 10% of `Salary` on every row. The rules engine should infer this. |
| `JoinDate` | Real dates in a plausible range, not 1970 and not the year 3000. |
| `Department`, `City` | The same set of values as the source, in roughly the same proportions. These are categories, so reusing them is correct. |
| Trust report | Should appear, with integrity 100. |

The distinction in that table is the important one: reusing "Engineering" is
correct, reusing a person's name is a data breach.

### `single_awkward_headers.csv` — 300 rows, the file that used to leak

Every column here holds a person, and **not one of them is called "name"**:
`Customer`, `Contact Person`, `Employee Name`, `accountOwner`.

| Check | What correct looks like |
|---|---|
| All four person columns | Detected as **direct PII** on the schema screen, and fully invented in the output. |
| `customer_id` | Stays an identifier. It must **not** be treated as a person just because it starts with "customer". |
| Privacy section | Exact matches: 0. |

This is the regression test for the leak where an unrecognised header meant real
names were copied into the output verbatim.

### `single_messy.csv` — 250 rows, hostile input

Nulls, unicode (Arabic and French), money written as text, and a constant column.

| Check | What correct looks like |
|---|---|
| Ingest | Succeeds without an error. |
| `country` | Stays "Pakistan" on every row. It is constant in the source. |
| `client_name`, `notes` | Nulls appear at roughly the source rate, not zero and not everywhere. |
| Unicode | Survives the round trip and the CSV export opens cleanly. |

### `single_tiny_18_rows.csv` — 18 rows, below the scoring threshold

| Check | What correct looks like |
|---|---|
| Generation | Works. |
| Trust report | **Explains that there were too few rows to score**, rather than failing silently or claiming a score it cannot support. |

Roughly 50 rows are needed before the scores mean anything. This file exists to
confirm the platform says so instead of inventing a number.

---

## Multi table

Upload all four **together**, in one go, so the relationships are detected.

- `multi_customers.csv` — 150 rows
- `multi_products.csv` — 24 rows
- `multi_orders.csv` — 500 rows
- `multi_order_items.csv` — 1201 rows

Shape: `customers` 1:N `orders` 1:N `order_items`, and `order_items` is the
junction between `orders` and `products`, which makes orders to products N:N.

| Check | What correct looks like |
|---|---|
| Relationships screen | Three foreign keys found, and the orders to products N:N detected through the junction. |
| Integrity | **No orphan keys.** Every `customer_id` in orders exists in customers, every `order_id` in items exists in orders. |
| `gross` | Exactly `quantity` × `unit_price`, to the cent, on every row. |
| `settled_on` | Always 1 to 5 days after `placed_on`, never before it. |
| `customer_name`, `email` | Invented, never copied. |
| Documents screen | Invoices bind to `orders` and `order_items` and reconcile: the line items add up to the invoice total. |
| Detection score | Should be high, meaning AUC near 0.50. A detection AUC near 1.00 means a classifier can separate real from synthetic perfectly, and something structural is broken. |

The last row is the most informative single number in the report. Per column
fidelity can look excellent while the relationships between columns are broken,
and detection is what catches that.

---

## Reading the trust report

| Section | Question it answers |
|---|---|
| Integrity | Do the keys and rules hold? |
| Fidelity | Does each column look like its source? |
| Utility | Does a model trained on synthetic data work on real data? |
| Privacy | Can a real record be recovered from the output? |
| Detection | Can a classifier tell the two apart at all? |

Fidelity high and detection low is the classic failure: every column is right on
its own, and the joint structure between them is wrong.
