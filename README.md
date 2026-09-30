<div align="center">

<img src="web/dataseed-logo.png" alt="DataSeed" width="300">

### Real looking data. Zero real records.

Privacy safe **tabular**, **relational** and **document** data, generated on demand,
with a Trust Report that proves the output is actually usable.

<a href="https://dataseed.169.58.151.43.sslip.io"><strong>Live demo</strong></a> &nbsp;·&nbsp;
<a href="docs/USER_GUIDE.md">User guide</a> &nbsp;·&nbsp;
<a href="docs/01-ARCHITECTURE.md">Architecture</a> &nbsp;·&nbsp;
<a href="docs/04-DOCUMENTS-GUIDE.md">Documents guide</a>

<img src="https://img.shields.io/badge/python-3.12-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.12">
<img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black" alt="React 18">
<img src="https://img.shields.io/badge/tests-317%20passing-2EA043?style=flat" alt="317 tests passing">
<img src="https://img.shields.io/badge/GPU-not%20required-6E56CF?style=flat" alt="No GPU required">

<br>
<br>

<img src="docs/assets/dataseed-demo.gif" alt="DataSeed walkthrough" width="900">

</div>

<br>

## What this is

Upload a CSV, or several that reference each other, and DataSeed learns their statistical
shape without keeping a single real value. It then generates as much new data as you ask
for: the columns keep their distributions, the relationships between columns survive, the
foreign keys resolve, and the business rules still hold.

Then it scores its own output and tells you, in numbers, whether that data is safe to use.

The scoring is the part that matters. Anything can emit plausible looking rows. The
question is whether a model trained on them works on real data, and whether a real person
can be recovered from them. DataSeed answers both, and blocks the export when the answer
is no.

<br>

## Quick start

<table>
<tr>
<td width="50%" valign="top">

**With Docker, nothing else installed**

```bash
docker compose up --build
```

Then open <http://localhost:8000>

Builds the frontend, installs dependencies,
generates the demo data and starts the server.

</td>
<td width="50%" valign="top">

**Locally**

```powershell
pip install -r requirements.txt
python scripts/make_demo_data.py
.\run.ps1
```

Then open <http://127.0.0.1:8000>

Interactive API reference at `/docs`.

</td>
</tr>
</table>

No API key is required. The AI layer is optional and the product is complete without it.

<br>

## What it does

| Capability | How it works |
|:--|:--|
| **Tabular** | A Gaussian copula fitted per table. Empirical marginals keep each column's exact shape, and a covariance matrix carries the correlation between columns. Deterministic, no GPU, no training loop. |
| **Conditional** | Where a categorical column genuinely partitions the data, the generator fits one copula per group rather than averaging them into one. The column is chosen from the data by correlation ratio, and the report discloses which one was used. |
| **Relational** | Two passes. Top down, parents first, each child drawing its row count from the real distribution of children per parent. Then bottom up, recomputing parent aggregates from the children that actually exist. |
| **N:N** | Junction tables are detected by shape, where exactly two foreign keys point at different parents and the pair is unique, then regenerated without duplicating a link. |
| **Business rules** | Nine kinds, covering ranges, comparisons, computed columns, enumerations, patterns, uniqueness, conditional presence and date offsets. Inferred from the source, repaired first and rejected second. |
| **Documents** | Invoices and bank statements rendered from the same generated tables. Tax comes from a region rule table, and running balances are computed in a single pass. |
| **Trust Report** | Integrity, fidelity, utility, privacy and detection, with the export blocked when integrity fails. |
| **AI layer** | Six scoped jobs covering semantic typing, relationship inference, free text synthesis, business rule proposal, edge cases and plain English query parsing. Every response is schema validated, and every job has a deterministic fallback. |
| **Interface** | Eleven screens, React and Framer Motion, served by the same process at `/`. |

<br>

## Reading the Trust Report

Five sections, each answering a different question. They are not interchangeable, and a
good score in one says nothing about the others.

| Section | The question it answers |
|:--|:--|
| **Integrity** | Do the keys and the business rules hold? Zero orphans, zero duplicate keys, every rule satisfied. |
| **Fidelity** | Does each column look like its source, distribution by distribution? |
| **Utility** | Does a model trained on the synthetic data work on the real data? Measured as TSTR against TRTR. |
| **Privacy** | Can a real record be recovered? Exact matches, distance to closest record, membership inference. |
| **Detection** | Can a classifier tell real from synthetic at all? An AUC of 0.50 means indistinguishable. |

The last one is the most informative single number in the report. Per column fidelity can
look excellent while the joint structure between the columns is broken, and detection is
what catches that. A fidelity of 96 alongside a detection AUC of 0.94 means every column
is individually right and the relationships between them are wrong.

<br>

## The guarantees

Each line is a test, not a claim.

| Guarantee | Enforced in |
|:--|:--|
| The same seed produces byte identical output | `api/seeds.py` |
| No synthetic row is a copy of a real one | `api/engine.py`, source values held as one way fingerprints |
| Names, emails and free text are regenerated, never resampled | `api/engine.py` |
| A person column is recognised whatever the header calls it | `api/schema.py` |
| A text key keeps its format, so `C00001` never becomes `1` | `api/engine.py` |
| Zero orphan foreign keys, zero duplicate primary keys | `api/relational.py` |
| Parent totals equal the sum of their line items | `api/relational.py`, computed, never generated |
| Invoice total equals subtotal plus tax | `api/documents.py` |
| `balance[i] = balance[i-1] + credit - debit` | `api/documents.py` |
| A downloaded bundle holds the documents that were generated | `api/main.py` |
| The export refuses to run when integrity fails | `api/main.py` |
| A `date` column never emits a timestamp | `api/engine.py` |
| Group sub models cannot leak another group's real values | `api/engine.py` |
| The report discloses what it conditioned on, and scores an independent target | `api/trust.py` |
| A model response never reaches the pipeline unvalidated | `api/ai.py` |
| Removing the API key changes nothing but polish | `tests/test_ai_fallback.py` |

<br>

## Testing

```powershell
.\check.ps1          # every suite, plus the frontend type check
```

| Suite | Checks | Covers |
|:--|--:|:--|
| `tests/test_engine.py` | 72 | Copula fit and sample, privacy modes, determinism |
| `tests/test_api.py` | 83 | Every route, end to end, including the document flow |
| `tests/test_fixtures.py` | 76 | Data the engine has never seen |
| `tests/test_e2e_upload.py` | 38 | The upload path a real user takes |
| `tests/test_ai_fallback.py` | 28 | The AI layer with the credential removed |
| `tests/test_provider.py` | 20 | The Mistral adapter, without spending a request |
| **Total** | **317** | |

Files for testing by hand live in `data/manual_tests/`, with a README saying what correct
looks like for each one, including which past bug it exists to catch. Regenerate them with
`python scripts/make_manual_test_csvs.py`.

<br>

## Layout

```
api/
  seeds.py         one generator per named stream, derived from the project seed
  schema.py        Schema IR, profiling, PII detection, FK and derived field inference
  engine.py        Gaussian copula: fit, sample, privacy modes, key formats
  constraints.py   the nine business rule kinds, repair first and reject second
  relational.py    topological generation, reconciliation, the integrity gate
  trust.py         fidelity, TSTR utility, privacy, detection AUC
  documents.py     invoices, statements, region tax rules, query parsing
  exporters.py     CSV, JSON, SQL, Parquet, Excel
  ai.py            the six AI jobs, with fallbacks and disk caching
  store.py         in memory projects, jobs and rendered documents
  main.py          FastAPI routes
  templates/       invoice.html, statement.html
frontend/          Vite, React, Tailwind, Framer Motion
web/               the built frontend, served at /
tests/             the six suites, plus browser and manual walkthroughs
scripts/
  make_demo_data.py         builds the source data the demo learns from
  make_test_fixtures.py     the adversarial fixtures the suites assert against
  make_manual_test_csvs.py  the files for testing by hand
data/
  demo/            the demo project's source tables
  fixtures/        automated test inputs
  manual_tests/    files to upload by hand, with a README
docs/              brief, architecture, user guide, documents guide, hosting
```

<br>

## API

Every error returns `{code, message, remedy}`. The interface renders the remedy, and a raw
stack trace never reaches the screen.

```http
GET    /api/health                              limits and status
POST   /api/projects/demo                       seed the demo project
POST   /api/projects/ingest                     upload CSVs, multipart
GET    /api/projects                            list
GET    /api/projects/{id}/schema                the Schema IR
PATCH  /api/projects/{id}/schema                user edits, invalidates fitted models
GET    /api/projects/{id}/rules                 the inferred business rules
POST   /api/projects/{id}/rules                 replace them
POST   /api/projects/{id}/preview               synchronous, at most 100 rows
POST   /api/projects/{id}/generate              background job
GET    /api/jobs/{job_id}                       progress and result
GET    /api/projects/{id}/data/{table}          paged output
GET    /api/projects/{id}/report                the Trust Report
POST   /api/projects/{id}/validate              revalidate without regenerating
POST   /api/projects/{id}/documents             render invoices or statements
GET    /api/projects/{id}/documents/{i}/html    one printable document
GET    /api/projects/{id}/documents/bundle      those documents, zipped
GET    /api/projects/{id}/export?fmt=           csv, json, sql, parquet, excel

GET    /api/ai/status                           live or heuristic, and which models
POST   /api/projects/{id}/ai/infer-types        semantic type and PII proposals
POST   /api/projects/{id}/ai/infer-relations    foreign key proposals
POST   /api/projects/{id}/ai/business-rules     business rule proposals
POST   /api/projects/{id}/ai/edge-cases         edge cases worth injecting
POST   /api/projects/{id}/ai/apply              apply the proposals the user accepted
POST   /api/ai/parse-query                      plain English into statement filters
```

<br>

## Design decisions

**No SDV.** It pulls in roughly 2 GB of torch for a copula that is about 200 lines of
scipy. Writing it directly removed the install risk and made every step explainable.

**No database and no job queue.** State lives in memory and jobs run on a background task.
Restarting the server reseeds the demo. Fewer moving parts means fewer ways to fail during
a demonstration, at the cost of needing a persistent process rather than serverless
functions.

**Dependency majors are pinned.** A clean install once resolved pandas 3.0, whose copy on
write semantics stopped the constraint repairs from landing, and the detection AUC went
from 0.45 to 1.00 on identical input. The upper bounds in `requirements.txt` exist because
of that, not out of caution.

**Parquet and Excel are optional.** Without `pyarrow` or `openpyxl` those two formats
return a typed error naming the missing package, and everything else still works.

**The AI layer is optional and provider agnostic.** Anthropic when `ANTHROPIC_API_KEY` is
set, Mistral when `MISTRAL_API_KEY` is, and deterministic heuristics when neither is. All
three go through the same schema validated contract, so Mistral is a substitute rather
than a degraded mode. `/api/ai/status` reports which one is actually in use rather than
claiming more than it can deliver.

**AI proposals are never applied automatically.** The inference jobs return suggestions
the user accepts or edits, so a wrong guess is a review step rather than corrupted data.

<br>

## Documentation

| Document | What it covers |
|:--|:--|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Walking through the product, screen by screen |
| [docs/01-ARCHITECTURE.md](docs/01-ARCHITECTURE.md) | How the pieces fit, and why |
| [docs/04-DOCUMENTS-GUIDE.md](docs/04-DOCUMENTS-GUIDE.md) | What the Documents feature is for, with worked examples |
| [docs/MISTRAL_AI_GUIDE.md](docs/MISTRAL_AI_GUIDE.md) | Running the AI layer on a limited key |
| [docs/05-FREE-HOSTING.md](docs/05-FREE-HOSTING.md) | Getting a public URL, and what each host actually costs |
| [data/manual_tests/README.md](data/manual_tests/README.md) | What to check when testing by hand |
| [DEPLOY.md](DEPLOY.md) | Deployment and CI |
