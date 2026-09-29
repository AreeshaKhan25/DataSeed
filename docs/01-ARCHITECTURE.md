# Architecture, Synthetic Data Platform

## 0. Design principle
**One schema, one seed, one pipeline.** Tabular, relational and document generation are not three
products, they are three *exits* from the same pipeline. Say this on stage; build it this way.

```
Ingest → Profile → Schema IR → [AI enrich] → Plan → Generate → Constrain → Reconcile → Validate → Export
                                     ^                                                      |
                                     +--------------- user edits / re-run -------------------+
```

Everything hangs off a single object: the **Schema IR** (intermediate representation).
Get this right and the rest is mechanical.

---

## 1. Schema IR, the spine of the system

```python
class Column(BaseModel):
    name: str
    dtype: Literal["int","float","str","bool","date","datetime","uuid"]
    semantic: str                  # person_name | email | address | iban | sku | free_text | category
    nullable: bool
    null_rate: float = 0.0
    unique: bool = False
    pii: Literal["none","quasi","direct"] = "none"
    privacy: Literal["passthrough","mask","hash","noise","synthesize"] = "synthesize"
    stats: ColumnStats | None       # histogram / categories+freqs / min,max,mean,std
    generator: GeneratorSpec        # how to produce it (copula | faker | llm | formula | sequence)

class Table(BaseModel):
    name: str
    columns: list[Column]
    primary_key: list[str]
    row_count: int
    derived: list[DerivedField]     # e.g. total = SUM(order_items.qty * order_items.price)

class ForeignKey(BaseModel):
    child_table: str; child_cols: list[str]
    parent_table: str; parent_cols: list[str]
    cardinality: Literal["1:1","1:N","N:N"]
    child_count_dist: CountDist     # empirical histogram of children-per-parent
    nullable: bool = False          # used to break cycles

class SchemaIR(BaseModel):
    tables: list[Table]
    foreign_keys: list[ForeignKey]
    constraints: list[Constraint]
    seed: int
    locale: str = "en_US"
```

**Rule:** every engine reads `SchemaIR` and nothing else. No engine reaches back to the raw upload.

---

## 2. Engines

### 2.1 Tabular engine (default path: Gaussian Copula)
Fast, deterministic, no GPU, never fails. This is your workhorse, **make it the default**.

**Fit**
1. Per column, build a CDF `F`:
   - numeric → empirical CDF (sorted values + linear interpolation)
   - categorical → frequency-ordered ordinal mapping, then a step CDF
   - datetime → epoch seconds, then treat as numeric
2. Transform each value: `u = F(x)`, clip to `[1e-6, 1-1e-6]`, then `z = PPF_normal(u)`
3. Fit covariance `Sigma` on the `Z` matrix. Apply shrinkage + nearest-PSD correction
   (`Sigma + eps*I`) so the Cholesky decomposition never fails on near-singular data.

**Sample**
4. `z ~ N(0, Sigma)` → `u = CDF_normal(z)` → `x = F_inverse(u)`

**Gotchas that will bite you, handle each explicitly**
- constant columns → bypass the copula, emit the constant
- single-category columns → same
- all-null columns → emit nulls
- `PPF_normal` at u in {0,1} → infinity. The clip above is mandatory.
- `F_inverse` for categoricals must return the *category*, not the ordinal index
- integer columns must be rounded AND re-clipped to the observed min/max

**Optional "advanced" path:** CTGAN / TVAE via SDV. Slow, flaky, needs torch.
Ship it behind a toggle labelled *Advanced (slower)*. **Do not put it on the demo path.**

### 2.2 Relational engine, two-pass
The single most important algorithm in the project.

**Pass 1, top-down generation**
1. Build a directed graph: edge `parent -> child` for each FK.
2. Detect cycles. Break at a `nullable=True` FK (set those to NULL on pass 1, fill them later).
3. Topological sort.
4. Generate root tables with the tabular engine. Assign synthetic PKs (sequential ints or UUIDv4).
5. For each child table, for each parent row: draw `k ~ child_count_dist` (empirical histogram from
   the real data, or user-configured). Emit `k` child rows carrying that parent's PK.
   - `1:1` → k is always 1, and enforce UNIQUE on the FK
   - `1:N` → k drawn from the distribution
   - `N:N` → build a junction table by sampling `(a_id, b_id)` pairs matched to both degree
     distributions, then **dedupe on the pair** and top up to the target count

**Pass 2, bottom-up reconciliation**
6. Walk the topological order *in reverse*. Recompute every `DerivedField` from the actual children:
   `orders.total = SUM(order_items.qty * order_items.unit_price)`,
   `orders.item_count = COUNT(order_items)`.

This two-pass design is *why* "order totals reconcile with their line items" is guaranteed rather than
hoped for. **Parent aggregates are computed, never generated.** Put this on a slide.

### 2.1b Conditional generation (implemented)
A single copula has one covariance matrix for the whole table, so it can only express relationships
that hold globally. When a categorical column genuinely partitions the data, premium customers
behave differently from standard ones, the global fit averages those groups together and the
dependence washes out.

The fix is a **mixture**: one copula per group, with the group drawn first.

```
1. Pick the conditioning column by correlation ratio (eta-squared): the share of the
   numeric columns' variance that the categorical explains. Purely a property of the
   data, computed before anything knows what will later be predicted.
2. Require >= 2 groups of >= 60 rows each, and eta-squared >= 0.06. Below that,
   splitting costs more in estimation noise than it buys.
3. Fit one ordinary copula per group. Categories too rare to fit pool into a
   remainder group that uses the global model, so nothing is dropped.
4. Sample: draw group counts from the real proportions, sample each group from its
   own copula, concatenate, shuffle, then reassign primary keys across the whole frame.
```

**Two things that will bite you here:**
- **Primary keys.** Each group's sampler starts its own counter, so keys must be reassigned
  after concatenation or they collide.
- **PII fingerprints.** A group only sees its own rows, so its collision guard would only know
  its own values, and could emit a real name belonging to a different group. Every sub-model
  gets the whole table's fingerprints.

**Measured on the demo data: utility 74.3 → 98.6, fidelity 96.2 → 97.2, detection AUC 0.53 → 0.47.**

**Report it honestly.** The conditioning column and the best utility target can land on the same
column, because both are driven by the same underlying fact, that column explains the table. The
headline score then partly reflects the modelling choice. The report therefore discloses
`conditioned_on` and also scores an *independent* target the generator was not conditioned on
(on the demo: 98.6 on `segment`, 71.1 on `churned`). A number a reviewer cannot check is worth less
than a smaller number they can.

### 2.3 Document engine
Documents are **a rendering of relational data**, not a separate generation path. Reuse everything.

```
SchemaIR (invoice header + line items) → generate relationally → reconcile totals
   → Jinja2 template (per region) → HTML → WeasyPrint → PDF
                                       +→ also export raw JSON / CSV
```

- **Invoices:** header + lines; tax computed from a region rule table (VAT / GST / sales tax), never by an LLM.
- **Bank statements:** sort transactions by date, then compute `balance[i] = balance[i-1] + credit - debit`
  in a single pass. **Never let a model produce the running balance**, it will drift within ten rows.
- **Query-style generation** ("last 90 days, balance over $500"): parse the natural-language query with
  the LLM into a strict `FilterSpec` (date range, predicates, counts), then apply it as a deterministic
  *constraint* on the generator. **The LLM plans; code executes.**
- Region templates control date format, currency symbol, tax label, and address layout.

---

## 3. Constraint engine, repair, then reject
Applied after sampling, before validation.

Types: `range`, `regex`, `enum`, `unique`, `cross-column` (`ship_date >= order_date`),
`computed` (`amount = qty * price`), `conditional` (`if status='cancelled' then paid_at is null`).

**Strategy, the order matters**
1. **Repair deterministically**, clamp to range, recompute computed fields, swap out-of-order dates,
   redraw duplicate unique values from the unused pool.
2. **Reject and resample** only what cannot be repaired, with `max_attempts = 5` per row.
3. After 5 attempts, drop the row, count it, and surface the count in the validation report.

> Pure rejection sampling is the number one cause of hangs in projects like this.
> Repair first, always cap attempts.

---

## 4. AI layer, 4 scoped jobs, never in the critical path

| # | Job | Model | Input | Output (strict schema) | Fallback on failure |
|---|---|---|---|---|---|
| 1 | Semantic type inference | `claude-opus-5` | column names, dtypes, 20 sample values | `{semantic, faker_provider, pii_level, suggested_constraints}` | regex heuristics (email / phone / date patterns) |
| 2 | Relationship inference | `claude-opus-5` | all table schemas + value-overlap stats | proposed FK edges + cardinality | name matching (`*_id` vs `id`) |
| 3 | Free-text synthesis | `claude-sonnet-5-5` | row context, batched 50 rows per call | array of strings | Faker provider |
| 4 | Edge-case proposal | `claude-sonnet-5-5` | SchemaIR | `[{name, description, column, injection_rule, rate}]` | static library of 12 generic edge cases |

**The rule that keeps this bug-free**
> Every LLM response is parsed into a Pydantic model. Parse failure → log → deterministic fallback →
> pipeline continues. **An LLM never writes a value into the output dataset without validation.**

Jobs 1 and 2 output *proposals shown in the UI for the user to accept or edit*. Human-in-the-loop means
a wrong AI guess is a UX moment, not a crash. Cache all AI results by `sha256(schema)`, the demo must
never wait on a cold call.

---

## 5. Validation layer, the Trust Report (your winning feature)

Four scores, 0 100, plus a hard gate.

### A. Integrity, hard gate, must be 100
- FK orphans = 0
- PK uniqueness = 100%
- Constraint violations = 0
- Type and nullability conformance = 100%

**If integrity is below 100, export is blocked.** Show that blocked state on stage, an enforced gate
reads as engineering maturity.

### B. Fidelity, does it look like the real thing?
- Numeric: Kolmogorov Smirnov statistic per column, `score = 1 - KS`
- Categorical: Total Variation Distance per column, `score = 1 - TVD`
- Correlation: `1 - mean(abs(corr_real - corr_synth))` across the matrix
- Visual: overlaid real vs synthetic histograms per column

### C. Utility, TSTR, the headline number
```
1. split real into train_real (70%) and holdout_real (30%)
2. fit the generator on train_real ONLY      <- never on the holdout, or every metric leaks
3. generate synth with |synth| = |train_real|
4. train M_s on synth and M_r on train_real  <- same model, same hyperparams, same seed
   (sklearn HistGradientBoosting: strong, fast, zero extra dependencies)
5. score both on holdout_real (AUC / F1, or R2 / RMSE)
6. UTILITY = min(1.0, TSTR / TRTR) * 100
```
Above 90 is excellent. 75 90 is good. Below 60 means the generator is under-fitting.

### D. Privacy
- Exact-match leakage: synthetic rows identical to a real row must be 0, drop and resample
- **DCR** (Distance to Closest Record): 5th percentile of synth→real nearest-neighbour distance,
  compared against the real→real baseline. `DCR_synth < DCR_baseline` means memorisation.
- Membership-inference proxy: attacker AUC should sit near 0.5
- k-anonymity across the quasi-identifier set
- Optional **DP-lite**: Laplace noise on the fitted marginals and covariance, with the epsilon budget
  shown in the UI. Label it honestly, "differential noise on fitted statistics, epsilon reported",
  not "differentially private".

### E. Detection AUC, the best single demo number
Train a classifier to tell real from synthetic. **AUC near 0.50 means indistinguishable.**
One number, instantly legible from the back of the room.

---

## 6. Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.12 + FastAPI + Pydantic v2** | Every synthetic-data library lives in Python |
| Data | **Pandas/Polars + NumPy + SciPy + scikit-learn** | Copula, KS and TSTR all come free |
| DB | **Postgres 16 + SQLAlchemy 2.0 + Alembic** | You must demo a relational DB dump anyway |
| Jobs | **jobs table + FastAPI BackgroundTasks + SSE progress** | Redis/Celery adds three failure modes for zero demo value |
| Documents | **Jinja2 + WeasyPrint** | HTML to PDF with no headless browser to babysit |
| Frontend | **Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui** | Stitch exports HTML/CSS that ports to Tailwind cleanly |
| Tables | **TanStack Table** (virtualized) | 100k-row preview without dying |
| Charts | **Recharts** | Trust Report visuals |
| ER graph | **React Flow** | The editable relationship canvas, biggest visual win per hour spent |
| AI | **Claude API**, `claude-opus-5` for inference, `claude-sonnet-5-5` for bulk | |
| Repo | pnpm monorepo: `apps/web`, `apps/api`, `packages/shared-types` | TS types generated from OpenAPI means zero drift |
| Run | `docker compose up` | One command, or you lose 40 minutes on demo day |

---

## 7. API surface, write this contract before any code

```
POST   /projects                          -> {id}
POST   /projects/{id}/ingest              multipart: csv | sql ddl | json  -> SchemaIR draft
GET    /projects/{id}/schema              -> SchemaIR
PATCH  /projects/{id}/schema              -> SchemaIR (user edits)
POST   /projects/{id}/ai/infer-types      -> column proposals
POST   /projects/{id}/ai/infer-relations  -> FK proposals
POST   /projects/{id}/ai/edge-cases       -> edge-case proposals
POST   /projects/{id}/preview             {rows<=100, seed} -> rows   (synchronous, under 2s)
POST   /projects/{id}/generate            {rows, seed, options} -> {job_id}
GET    /jobs/{job_id}/stream              SSE: {phase, pct, message, partial_rows}
GET    /jobs/{job_id}/report              -> TrustReport
POST   /projects/{id}/documents/render    {template, count} -> {job_id}
GET    /jobs/{job_id}/export?fmt=csv|json|parquet|sql|pdf-zip
```

Two paths matter and must stay separate: **`/preview` is synchronous and capped at 100 rows** so the
canvas updates instantly while the user drags sliders; **`/generate` is a job with SSE progress**.
Never mix them.

---

## 8. How to guarantee "no bugs"

1. **Contract-first.** Pydantic → OpenAPI → `openapi-typescript` → TS client. No hand-written fetch types.
2. **Determinism.** One `SeedFactory(seed)` handing out an `np.random.Generator` per table. Ban bare
   `random.` and `np.random.` calls with a CI grep. Test: *same seed produces byte-identical output.*
3. **Invariants as code.** `validate_integrity(dataset, schema)` runs after **every** generation and
   raises on failure. Export is gated on it, so a violation is impossible to ignore.
4. **Golden fixtures.** Three seeded schemas, `northwind-lite` (relational), `bank` (documents),
   `healthcare` (PII and edge cases). Snapshot-test row counts, orphans = 0, violations = 0, reproducibility.
5. **Property tests** (Hypothesis) on the constraint engine: random schemas in, invariants hold out.
6. **Hard caps everywhere.** Preview ≤ 100 rows. Generation ≤ 1M rows. Repair ≤ 5 attempts.
   LLM calls: 20s timeout, 2 retries, then fallback. Nothing in this system may loop unbounded.
7. **Typed error taxonomy.** Every failure returns `{code, message, remedy}` and the UI renders the
   remedy. A raw stack trace on screen during the demo costs you the UI score.
8. **`make check`** = ruff + mypy + pytest + tsc + eslint + a Playwright smoke test. Green before every commit.
9. **Demo safety net.** Ship a pre-seeded demo project with pre-generated artifacts and cached AI
   responses. Your live demo must survive dead wifi.
