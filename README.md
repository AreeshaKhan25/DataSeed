# DataSeed — Synthetic Data Platform

Realistic, privacy-safe **tabular**, **relational** and **document** data, generated on demand —
and a Trust Report that proves the output is actually usable.

## Run it with Docker (one command, nothing else installed)

```bash
docker compose up --build     # http://localhost:8000
```

Builds the frontend, installs the dependencies, generates the demo data and starts the server.
Deployment details, hosted options and CI are in [DEPLOY.md](DEPLOY.md).

## Run it locally

```powershell
pip install -r requirements.txt
python scripts/make_demo_data.py     # first time only
.\run.ps1                            # http://127.0.0.1:8000  (docs at /docs)
```

## Check it

```powershell
.\check.ps1
```

`smoke_test.py` covers the engine (38 checks), `api_test.py` covers every route (60 checks).
Run both before the demo.

## What it does

| | |
|---|---|
| **Tabular** | A Gaussian copula fitted per table: empirical marginals keep each column's exact shape, a covariance matrix carries the cross-column correlation. Deterministic, no GPU, no training loop. |
| **Conditional** | Where a categorical column genuinely partitions the data, the generator fits one copula per group instead of averaging them together. Chosen from the data by correlation ratio, and disclosed in the report. |
| **Relational** | Two passes. Top-down, parents first, each child drawing its row count from the real children-per-parent distribution. Then bottom-up, recomputing parent aggregates from the children that actually exist. |
| **Documents** | Invoices and bank statements rendered from the same generated tables. Tax comes from a region rule table; running balances are computed in one pass. |
| **Trust Report** | Integrity, Fidelity, Utility (TSTR) and Privacy — with export blocked when integrity fails. |
| **AI layer** | Four scoped jobs — semantic typing, relationship inference, free-text synthesis, edge-case proposal — each schema-validated with a deterministic fallback. |
| **Interface** | Nine screens, React + Framer Motion, served by the same process at `/`. |

## The guarantees, and where they are enforced

Each of these is a test, not a claim.

| Guarantee | Enforced in |
|---|---|
| Same seed produces byte-identical output | `api/seeds.py` |
| No synthetic row is a copy of a real one | `api/engine.py` — source values kept as one-way fingerprints |
| Names, emails and free text are regenerated, never resampled | `api/engine.py` |
| Zero orphan foreign keys, zero duplicate primary keys | `api/relational.py` |
| Parent totals equal the sum of their line items | `api/relational.py` — computed, never generated |
| Invoice total = subtotal + tax | `api/documents.py` |
| `balance[i] = balance[i-1] + credit - debit` | `api/documents.py` |
| Export refuses to run when integrity fails | `api/main.py` |
| A `date` column never emits a timestamp | `api/engine.py` |
| Group sub-models cannot leak another group's real values | `api/engine.py` |
| The report discloses what it conditioned on, and scores an independent target | `api/trust.py` |
| An LLM response never reaches the pipeline unvalidated | `api/ai.py` |
| Pulling `ANTHROPIC_API_KEY` changes nothing but polish | `scripts/ai_test.py` |

## Layout

```
api/
  seeds.py        one generator per named stream, derived from the seed
  schema.py       Schema IR, profiling, FK and derived-field inference
  engine.py       Gaussian copula: fit, sample, privacy modes
  relational.py   topological generation, reconciliation, integrity gate
  trust.py        fidelity, TSTR utility, privacy, detection AUC
  documents.py    invoices, statements, region tax rules, NL query parsing
  exporters.py    CSV / JSON / SQL / Parquet / Excel
  ai.py           the four AI jobs, with fallbacks and disk caching
  store.py        in-memory projects and jobs
  main.py         FastAPI routes
  templates/      invoice.html, statement.html
frontend/         Vite + React + Tailwind + Framer Motion (see its own README)
web/              the built frontend, served at /
scripts/
  make_demo_data.py   builds the "real" source data
  smoke_test.py       engine guarantees
  api_test.py         every route, end to end
  ai_test.py          the AI layer with the credential removed
docs/                 brief, architecture, build plan, Stitch prompts
```

## API

```
GET    /api/health                              limits and status
POST   /api/projects/demo                       seed the demo project
POST   /api/projects/ingest                     upload CSVs (multipart)
GET    /api/projects                            list
GET    /api/projects/{id}/schema                the Schema IR
PATCH  /api/projects/{id}/schema                user edits; invalidates fitted models
POST   /api/projects/{id}/preview               synchronous, max 100 rows
POST   /api/projects/{id}/generate              background job
GET    /api/jobs/{job_id}                       progress and result
GET    /api/projects/{id}/data/{table}          paged output
GET    /api/projects/{id}/report                the Trust Report
POST   /api/projects/{id}/validate              re-run validation without regenerating
POST   /api/projects/{id}/documents             invoices or statements as JSON
GET    /api/projects/{id}/documents/{i}/html    one printable document
GET    /api/projects/{id}/documents/bundle      all documents, zipped
GET    /api/projects/{id}/export?fmt=           csv | json | sql | parquet | excel

GET    /api/ai/status                           live or heuristic, and which models
POST   /api/projects/{id}/ai/infer-types        semantic type and PII proposals
POST   /api/projects/{id}/ai/infer-relations    foreign-key proposals
POST   /api/projects/{id}/ai/edge-cases         edge cases worth injecting
POST   /api/projects/{id}/ai/apply              apply the proposals the user accepted
POST   /api/ai/parse-query                      plain English into statement filters
```

Every error returns `{code, message, remedy}`. The UI renders the remedy; a raw stack trace never
reaches the screen.

## Notes

- **No SDV.** It pulls in ~2 GB of torch for a copula that is ~200 lines of scipy. Writing it
  directly removed the install risk and made every step explainable.
- **No database, no Docker, no job queue.** State is in memory and jobs run on a background task.
  Restarting the server reseeds the demo. Fewer moving parts, fewer ways to fail on stage.
- **Parquet and Excel are optional.** Without `pyarrow` / `openpyxl` those two formats return a
  typed error naming the missing package; everything else still works.
- **The AI layer is optional, and provider-agnostic.** It uses Anthropic when `ANTHROPIC_API_KEY`
  is set, Mistral when `MISTRAL_API_KEY` is, and deterministic heuristics when neither is.
  All three go through the same schema-validated contract — Mistral is a substitute, not a
  degraded mode. `scripts/ai_test.py` removes the key and asserts the product still works;
  `scripts/provider_test.py` proves the Mistral adapter without spending a request.
- **AI proposals are never applied automatically.** Jobs 1 and 2 return suggestions the user
  accepts or edits, so a wrong model guess is a review step rather than corrupted data.
