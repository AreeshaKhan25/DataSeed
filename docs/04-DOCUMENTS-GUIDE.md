# Documents and Invoices: what the feature is for and how to use it

## The idea in one line

A document is not a fourth kind of generated data. It is the **relational data you
already generated, laid out on a page**.

An invoice is a header with lines beneath it. That is the same shape as any parent
row with children: an order and its items, a shop and its products, an account and
its charges. So the document engine does not generate anything new. It takes the
tables the relational engine produced and renders them.

That matters because it is what makes the totals correct. The invoice total is not
a number the model invented that happens to look plausible. It is the sum of the
line items sitting directly above it.

## Why anyone needs this

A CSV of fake invoices is easy. What is hard, and what teams actually get stuck on,
is a **document that is internally consistent**:

* An invoicing pipeline needs PDFs where the tax is right for the region and the
  total matches the lines, or every test is testing the wrong thing.
* A reconciliation system needs bank statements where the running balance is
  arithmetic, not decorative. A single wrong row invalidates the whole test.
* An OCR or document-parsing model needs hundreds of layout variants that are
  nonetheless all arithmetically valid, so a parsing failure is a real failure.
* None of this can use production documents, because they are full of real names,
  real addresses and real amounts.

## The two document types

### Invoices

| | |
|---|---|
| Built from | a parent table and its child table |
| Header | billed-to, from, invoice number, issue and due dates |
| Lines | one per child row: description, quantity, unit price, amount |
| Arithmetic | `subtotal = sum(lines)`, `tax = subtotal x rate`, `total = subtotal + tax` |
| Regions | EU (VAT 20%), UK (VAT 20%), US (sales tax 8.75%), India (GST 18%) |

The region changes four things at once: the tax rate, the tax label, the currency
symbol, and the date format. An EU invoice reads `14/03/2025` and `VAT 20%`; a US
invoice reads `03/14/2025` and `Sales tax 8.75%`.

### Bank statements

| | |
|---|---|
| Built from | transaction rows, generated or drawn from your data |
| Header | account number, holder, statement period |
| Summary | opening balance, paid in, paid out, closing balance |
| Rows | date, description, paid out, paid in, running balance |
| Arithmetic | `balance[i] = balance[i-1] + credit - debit`, computed in one pass |

**The running balance is never generated.** It is computed. A language model asked
to produce a balance column will drift within ten rows, and a statement with a
wrong balance is worthless for testing reconciliation.

## How to use it

### 1. Generate data first

Documents render whatever the relational engine last produced. Generate on the
Workspace screen before opening Documents, or the engine falls back to standalone
invoices that are correct but not connected to your data.

### 2. Pick a template

The left column lists invoice templates per region plus the bank statement. The
selected one renders immediately.

### 3. Check the banner

At the top:

* **"All N documents reconcile"** means every total was recomputed from its lines
  and matched.
* **"Line items come from the generated order_items table"** means the documents
  are bound to your data.
* If it says the items are generated standalone, see *When it falls back* below.

### 4. Filter statements in plain English

The statement template accepts a natural language query:

```
last 90 days, balance over 500
only deposits above 1000
payments to utilities last month
```

This is parsed into a filter and applied **by code**. The model decides what you
meant; it never writes a balance. The interpretation is shown back to you so you
can see what was actually applied.

One deliberate behaviour worth knowing: a balance filter selects **whole
statements**, not individual rows. Removing rows from the middle of a statement
would leave the running balance with gaps, and a statement with holes in it is not
a statement.

### 5. Export

* **Open printable** renders one document as HTML with print styles. Ctrl+P gives
  a PDF.
* **Download all** returns a zip of every document as a separate printable file.

## What the engine looks for

Document generation binds to your schema automatically. It scans the foreign keys
for a parent/child pair where the child carries a **price-like column**, meaning a
numeric column named price, rate, cost, amount, value, fee or charge.

It then uses, if present:

* a **quantity** column named qty, quantity, units, count or pieces, and treats it
  as 1 if there is none
* a **label** column named sku, product, description, item, name, title, category
  or label, for the line text

Where several pairs qualify, the one with both a quantity and a label wins, so a
classic `orders` / `order_items` pair is preferred over a looser match.

### Worked examples

| Schema | Parent | Child | Reads as |
|---|---|---|---|
| Retail demo | `orders` | `order_items` | an order and its line items |
| Storefront fixture | `shops` | `products` | a shop and its catalogue, quantity 1 |
| Any billing schema | `accounts` | `charges` | an account and its charges |

### When it falls back

If no pair qualifies, invoices are still produced from a built-in catalogue and
still reconcile exactly. The response sets `from_generated_data: false` so you can
tell the difference.

The usual reason is that no child table has a numeric price-like column. Adding one
column named `price` or `amount` to the child table is normally enough.

## The guarantees, and where they are enforced

| Guarantee | Enforced in |
|---|---|
| Invoice subtotal equals the sum of its lines | `api/documents.py`, `Invoice.subtotal` |
| Total equals subtotal plus tax | `Invoice.total` |
| Tax matches the region | `REGIONS` table, never a model |
| Running balances follow from the opening balance | `build_statements`, single pass |
| Every document is re-checked before it renders | `reconciles()` on both types |

Both types carry a badge on the rendered page showing whether reconciliation
passed, so a broken document announces itself rather than hiding.

## Demonstrating it in 40 seconds

1. Generate on Workspace, then open Documents.
2. Point at the banner: *"twenty invoices, every one reconciled, and the line items
   are the order_items rows we just generated."*
3. Switch to Bank statement and run down the balance column: *"each row follows
   from the one above. That column is computed, not generated, because a model
   writing it drifts within ten rows."*
4. Type `last 90 days, balance over 500`, apply, and read the interpretation line:
   *"the model parses the request, the code applies it."*
5. Click **Open printable** and note the filter still holds.

## API, if you prefer curl

```bash
# JSON for every document, including the reconciliation flags
curl -X POST localhost:8000/api/projects/{id}/documents \
  -H "Content-Type: application/json" \
  -d '{"kind":"invoice","count":20,"region":"EU"}'

# One printable document
curl "localhost:8000/api/projects/{id}/documents/0/html?kind=invoice&region=EU&count=20"

# All of them, zipped
curl -OJ "localhost:8000/api/projects/{id}/documents/bundle?kind=invoice&region=EU&count=25"

# A filtered statement
curl -X POST localhost:8000/api/projects/{id}/documents \
  -H "Content-Type: application/json" \
  -d '{"kind":"statement","count":10,"region":"UK","query":"last 90 days, balance over 500"}'
```

## Known limits

* Output is printable HTML, not PDF bytes. Ctrl+P produces a correct PDF; there is
  no server-side PDF renderer.
* Statements are synthetic accounts unless your schema has a transactions-shaped
  table. The invoice path binds to your data; the statement path is more prescriptive.
* The statement period is anchored to a fixed date in the generated data rather
  than to today, so "last 90 days" means the last 90 days of the dataset.
