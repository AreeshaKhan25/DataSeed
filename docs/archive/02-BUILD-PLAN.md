# Build Plan, 4 HOURS

> This replaces the original phased plan. With 4 hours, the enemy is not difficulty, it is
> setup cost, install waits, and decision paralysis. Every choice below is made **for you**.
> Do not re-litigate any of them mid-build.

## The three rules for a 4-hour build
1. **No decisions during the build.** Everything is decided in this document. If you hit a fork
   that isn't covered here, take the uglier, faster option.
2. **Nothing is built twice.** No refactors. No "I'll clean this up later." There is no later.
3. **The demo path is sacred.** Anything not on the 5-minute demo path does not get built.

## Scope: what you are building (and what you are NOT)

**IN, this is the whole product:**
- Upload a CSV → generate a synthetic version → download it
- A 3-table relational demo with FK integrity and reconciled totals
- Invoices + bank statements as HTML documents
- **The Trust Report** (fidelity + TSTR + privacy + integrity), non-negotiable
- One good-looking page

**OUT, cut these now, do not reconsider:**
CTGAN · Postgres · Docker · auth · job queues · SSE streaming · Parquet · N:N cardinality ·
database connectors · differential privacy · React Flow · a Next.js build step · tests beyond one
smoke check · multi-user anything

---

## Stack, revised for 4 hours

| Layer | Choice | Why this and not the other thing |
|---|---|---|
| Backend | **FastAPI, ~4 Python files** | No Docker, no Postgres. `uvicorn app:app --reload` and you're running. |
| Engine | **SDV `GaussianCopulaSynthesizer`** | You said libraries are fine. Writing a copula by hand costs 90 minutes you do not have. |
| Metadata | **`sdv.metadata.Metadata.detect_from_dataframe`** | Free schema inference. Your ingest step is now three lines. |
| Metrics | **SDMetrics** `QualityReport` + `DiagnosticReport` | Free fidelity and validity scores. Only TSTR is hand-written. |
| Relational | **Hand-rolled FK assignment, ~40 lines** | NOT SDV's `HMASynthesizer`, it is slow, fussy, and will eat an hour. See §Relational below. |
| Documents | **Jinja2 → HTML + print CSS** | NOT WeasyPrint. Its native deps (GTK/Pango) break on Windows and will cost you 40 minutes. Render HTML, print to PDF from the browser if asked. |
| Storage | **Local `./data` folder + an in-memory dict** | No database. Restarting the server clears state; that is fine. |
| Frontend | **ONE `index.html`, Tailwind via CDN + Alpine.js** | No npm, no build step, no `node_modules`. Paste Stitch's HTML export almost directly. |
| AI | **Claude API, 2 jobs only** | Semantic type inference + edge-case proposal. Both cached to a JSON file. |

**Why a single HTML file beats Next.js here:** `create-next-app` + installing shadcn + wiring a client
is 45 minutes before you render one pixel. Tailwind CDN renders the Stitch design in 5 minutes.
The judges cannot see your build tooling.

---

## T-0: Do these three things AT THE SAME TIME, before writing any code

Losing 20 minutes to a serial install is the most common way a 4-hour build dies.

**Terminal 1, start the install and walk away:**
```
python -m venv .venv
.venv\Scripts\activate
pip install sdv fastapi uvicorn jinja2 python-multipart scikit-learn pandas
```
> `sdv` pulls in torch and is a large download. Start it first. Do not wait on it.

**Browser, start Stitch generating:**
Open `docs/03-STITCH-PROMPTS.md`. Paste **Prompt 0** (design system), then **Prompt 5**
(Workspace) and **Prompt 6** (Trust Report). Those two screens are your entire UI.
Skip every other screen prompt. Let Stitch work while you code.

**Terminal 2, prepare the demo data now, while both run:**
Get three small CSVs into `./data/demo/`:
- `customers.csv`, ~500 rows: `customer_id, name, email, signup_date, segment, balance`
- `orders.csv`, ~1,500 rows: `order_id, customer_id, order_date, status, total`
- `order_items.csv`, ~4,000 rows: `item_id, order_id, sku, qty, price`

Generate them with a 20-line Faker script. **These are your "real" data.** Everything you demo is
generated from them. Have them before hour 1 or you will be inventing data at minute 200.

---

## The clock

### 0:00, 0:30 · Skeleton + ingest
- `app.py` with FastAPI, CORS open, and `GET /` serving `index.html`
- `POST /ingest`, accept a CSV, load to a DataFrame, run `Metadata.detect_from_dataframe`,
  store in a module-level `PROJECTS = {}` dict, return the detected schema as JSON
- `GET /schema/{id}`, return it

**Gate:** you can upload `customers.csv` with curl and get a schema back.

### 0:30, 1:15 · Tabular generation
- `POST /generate/{id}` with `{rows, seed}` → fit `GaussianCopulaSynthesizer`, sample, return
  the first 100 rows as JSON plus a full CSV written to `./data/out/`
- **Cache the fitted synthesizer in the dict.** Refitting on every request will make the demo feel
  broken. Fit once, sample many times.
- `GET /download/{id}?fmt=csv|json`
- Null-rate and outlier-rate injection: a 15-line post-processing pass over the sampled frame

**Gate:** upload a CSV → get 10,000 synthetic rows back → download them. **This alone is a product.**

### 1:15, 2:00 · The Trust Report ← YOUR HIGHEST-VALUE 45 MINUTES
Build this before relational and before documents. If the clock beats you, this is what wins.

- **Fidelity**, `QualityReport.generate(real, synth, metadata)` → overall score + per-column scores. Free.
- **Integrity**, `DiagnosticReport` for validity, plus your own FK orphan count and PK uniqueness check.
- **TSTR**, hand-written, about 30 lines, the only real code in this block:
  ```
  split real 70/30 -> train_real, holdout_real
  fit the synthesizer on train_real ONLY      <- critical; fitting on all of it leaks
  sample synth with len(synth) == len(train_real)
  pick a target column (let the user choose; default to the last categorical)
  train HistGradientBoostingClassifier twice: once on synth, once on train_real
  score both on holdout_real (roc_auc_score)
  utility = min(1.0, tstr_auc / trtr_auc) * 100
  ```
- **Privacy**, two cheap, high-impact numbers:
  - exact-match count: `len(synth.merge(real, how="inner"))` → must be 0
  - DCR: `sklearn.neighbors.NearestNeighbors` on normalized numerics, report the 5th percentile
- **Detection AUC**, label real as 0 and synth as 1, train one classifier, report AUC.
  0.50 means indistinguishable. This is your best single number on stage.
- `GET /report/{id}` returns all of it as one JSON object.

**Gate:** a JSON response with four scores and a real TSTR number above 80.

### 2:00, 2:35 · Relational
Do **not** use `HMASynthesizer`. Do this instead, it is faster to write, faster to run, and you can
explain every line:

```
1. Fit a separate GaussianCopulaSynthesizer per table (you already have the code).
2. Generate customers -> assign fresh sequential PKs 1..N.
3. Generate orders -> DISCARD the generated customer_id column ->
   reassign each order a real synthetic customer_id sampled from the customers PKs,
   using the empirical children-per-parent distribution from the source data.
4. Same for order_items against orders.
5. RECONCILE: orders.total = order_items.groupby(order_id)[qty * price].sum()
   Overwrite the generated total. Never keep the generated one.
6. Assert: zero FK orphans, zero duplicate PKs. Raise if violated.
```

Step 3 is the whole trick, **generate the column, then throw it away and reassign it.** Step 5 is why
totals reconcile: parent aggregates are computed from children, never generated.

**Gate:** 3 tables generated, FK orphans = 0, and `orders.total` exactly equals the sum of its items.

### 2:35, 3:00 · Documents
- Two Jinja2 templates: `invoice.html` and `statement.html`, both styled to match your dark theme
  but rendered on a white page.
- Invoice: pull one order plus its items from the relational output. `subtotal = sum(qty*price)`,
  `tax = subtotal * region_rate`, `total = subtotal + tax`. Region rates as a 4-entry dict.
- Bank statement: sort transactions by date, then one loop computing
  `balance[i] = balance[i-1] + credit - debit`. **Never generate the balance.**
- `GET /documents/{id}?type=invoice&count=50` returns rendered HTML, paginated in the UI.

**Gate:** an invoice whose total reconciles, and a statement whose every balance is arithmetically correct.

### 3:00, 3:40 · Frontend
Take the Stitch export for Workspace and Trust Report. Strip it to one `index.html`:
- Tailwind CDN in the `<head>`, Alpine.js for state
- Three tabs: Tabular / Relational / Documents
- Left: the data grid (plain `<table>`, slice to 100 rows, do not virtualize anything)
- Right: the config panel, rows, seed, null rate, outlier rate, a Generate button
- A Trust Report section: four score cards plus one bar chart (inline SVG is fine, skip Recharts)
- The invoice/statement preview in the Documents tab

**Gate:** click Generate, watch rows appear, see four scores, download a CSV. No console errors.

### 3:40, 4:00 · AI layer + safety net
- **AI job 1**, semantic type inference: send column names + 20 sample values to `claude-opus-5`,
  get back `{semantic, pii_level}` per column, render a cyan badge next to inferred columns.
- **AI job 2**, edge-case proposal: send the schema, get back a list of edge cases as checkboxes.
- **Wrap both in try/except with a hardcoded fallback.** Then **cache the responses to a JSON file
  and load from that cache during the demo.** Your demo must not depend on a live API call.
- Run the full demo end to end, twice. Fix only what breaks it.

---

## If you fall behind, the cut order
Drop in exactly this sequence, no agonizing:
1. AI job 2 (edge cases), keep job 1, the cyan badges are visible in every screenshot
2. Bank statements, keep invoices
3. Documents entirely
4. Relational, keep tabular
5. **Never cut the Trust Report.** If you have tabular generation and a Trust Report, you have a
   complete, defensible product. That is the floor.

## If you have a teammate
Split cleanly at minute 0 and do not touch each other's files:
- **Person A:** backend, 0:00 3:00 (skeleton → tabular → trust report → relational → documents)
- **Person B:** Stitch prompts → `index.html` → wire it to the API with fake JSON first, swap in the
  real endpoints at 3:00
Agree the JSON response shapes in the first 5 minutes and write them down. That contract is the
only coordination you have time for.

---

## Demo script, 5 minutes, rehearsed

| Time | Beat |
|---|---|
| 0:00 | "Real data is scarce, sensitive, and slow. Teams wait weeks for an extract they then can't share." |
| 0:30 | Upload `customers.csv`. "One schema-aware pipeline, everything downstream reads this one object." AI badges appear: "it flagged these two columns as direct PII." |
| 1:15 | Generate 10,000 rows, seeded. "Same seed, same bytes, every time." |
| 2:00 | **Trust Report.** "Fidelity 94. **TSTR utility 91**, a model trained *only* on this synthetic data scores 91% of one trained on real data, both tested on the same held-out real records. Detection AUC 0.52, a classifier can barely tell them apart. Zero exact matches with any real row." |
| 3:15 | Relational tab. "Three tables. FK orphans: zero. Order totals reconcile with their line items, because parent aggregates are *computed* from children, never generated." |
| 4:15 | Documents tab. "Same data, rendered. Invoices with correct regional tax. Bank statements where every running balance is arithmetic, not a guess." |
| 4:45 | Close: **"Everyone can generate data. We can prove ours is good."** |

Rehearse it twice. The second run is where you find the thing that breaks.
