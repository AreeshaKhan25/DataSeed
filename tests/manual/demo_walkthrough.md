# Manual test: the demo walkthrough

Run this before any demo. It is the exact path a judge will take, in order,
with the expected result at every step. If all 24 steps pass, the demo is safe.

**Setup**

```powershell
python scripts/make_demo_data.py     # only if data/demo is missing
.\run.ps1                            # http://127.0.0.1:8000
```

Tester: ______________  Date: ______________  Build: ______________

---

## 1. First load

| # | Step | Expected | Pass |
|---|---|---|---|
| 1 | Open `http://127.0.0.1:8000` in a **new tab** | The intro animation plays once, about 2.5 seconds, with no visible rectangle around it | ☐ |
| 2 | Wait for it to finish | It fades out and the Projects screen is already loaded underneath, no second wait | ☐ |
| 3 | Reload the page | The intro does **not** play again. Straight to Projects | ☐ |
| 4 | Look at the browser tab | The DataSeed emblem is the favicon, title reads `DataSeed Synthetic Data Platform` | ☐ |
| 5 | Look at the header | Full DataSeed lockup, not a placeholder icon | ☐ |

## 2. Projects

| # | Step | Expected | Pass |
|---|---|---|---|
| 6 | Read the four stat cards | Counts are non zero and tilt slightly when you move the mouse over them | ☐ |
| 7 | Count the project cards | Exactly one, `Northwind Retail`. Not two | ☐ |
| 8 | Click `Load demo` twice | Still exactly one project. Loading it again reopens it, it does not clone | ☐ |

## 3. Schema

| # | Step | Expected | Pass |
|---|---|---|---|
| 9 | Open Schema from the dock | Five tables listed: customers, orders, order_items, tags, customer_tags | ☐ |
| 10 | Look at the `customers` columns | `name` and `email` are flagged **Direct** PII in red | ☐ |
| 11 | Click `Infer types` | A banner appears. It says AI or heuristics honestly, depending on whether a key is live | ☐ |
| 12 | Change `email` privacy to `hash` | The dropdown accepts it and the schema updates | ☐ |

## 4. Relationships

| # | Step | Expected | Pass |
|---|---|---|---|
| 13 | Open Relationships | Five node cards joined by curved lines | ☐ |
| 14 | Find the `customer_tags` links | Two edges labelled **N:N**, not 1:N | ☐ |
| 15 | Click an `N:N` label | The right panel shows the children per parent histogram | ☐ |

## 5. Business rules

| # | Step | Expected | Pass |
|---|---|---|---|
| 16 | Open Business rules | Over 40 rules listed, most marked as read from your data | ☐ |
| 17 | Find `shipped_date never precedes order_date` | Present, kind `comparison` | ☐ |
| 18 | Untick any rule, then tick it again | The toggle persists both ways | ☐ |

## 6. Generate

| # | Step | Expected | Pass |
|---|---|---|---|
| 19 | Open Workspace, drag **Null rate** to about 50% | The preview fills with italic `null` across many columns, live | ☐ |
| 20 | Click `Generate` | Phase list advances, progress bar fills, finishes in well under a minute | ☐ |
| 21 | Compare the output to the preview | Both show roughly the same proportion of nulls. **The preview must not disagree with the output** | ☐ |
| 22 | Set null rate back to 2%, regenerate | Business rules banner reports violations caught and repaired, typically several hundred | ☐ |

## 7. Trust report

| # | Step | Expected | Pass |
|---|---|---|---|
| 23 | Open Trust report | Four rings. Integrity 100, the rest above 70 | ☐ |
| 24 | Read the utility card | Shows TRTR vs TSTR, and an **independent check** on a column the generator was not conditioned on | ☐ |

## 8. Documents

| # | Step | Expected | Pass |
|---|---|---|---|
| 25 | Open Documents, keep Invoice EU | An invoice renders. Subtotal plus VAT equals the total, exactly | ☐ |
| 26 | Switch to Bank statement | Running balances are arithmetically correct down the column | ☐ |
| 27 | Type `last 90 days, balance over 500`, apply | The interpretation line appears and no balance falls below 500 | ☐ |
| 28 | Click `Open printable` | The printable document honours the **same** filter. This is the step most likely to regress | ☐ |

## 9. Export and the gate

| # | Step | Expected | Pass |
|---|---|---|---|
| 29 | Open Export, pick `SQL dump`, download | A `.sql` file arrives, roughly 1 MB, opening with `-- DataSeed` | ☐ |
| 30 | Open the CSV export in a spreadsheet | `orders.total` equals the sum of its line items **to the cent**, not approximately | ☐ |

---

## Failure log

| # | What happened | Severity |
|---|---|---|
| | | |
| | | |
