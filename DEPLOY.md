# Deployment

The whole platform is one process: FastAPI serves the API and the built frontend from the same
origin. There is no database, no queue and no second service, so there is nothing to orchestrate.

## Docker — the shortest path

```bash
docker compose up --build
# http://localhost:8000
```

That builds the frontend, installs the Python dependencies, generates the demo dataset, and starts
the server. A judge needs Docker and nothing else — no Python, no Node, no build step.

To run without compose:

```bash
docker build -t dataseed .
docker run -p 8000:8000 dataseed
```

## Hosted

**Render** — `render.yaml` is a blueprint. Point Render at the repo; it builds from the Dockerfile
and health-checks `/api/health`.

**Fly.io** —

```bash
fly launch --no-deploy   # reads fly.toml
fly deploy
```

`fly.toml` requests 1 GB because fitting a copula and running the trust report on a large table is
memory-hungry; the default 256 MB machine will be killed mid-generation.

Either way, set `ANTHROPIC_API_KEY` as a secret if you want the AI layer live. Without it every AI
job falls back to a deterministic heuristic and the product is fully functional — the UI says
"Heuristics" rather than implying a model is at work.

## Without Docker

```powershell
pip install -r requirements.txt
python scripts/make_demo_data.py
npm --prefix frontend install
npm --prefix frontend run build
./run.ps1
```

`run.ps1` generates the demo data and builds the frontend on first run, so a clean clone needs one
command after the two installs.

## Environment

| Variable | Default | Effect |
|---|---|---|
| `HOST` | `127.0.0.1` locally, `0.0.0.0` in the image | Bind address. A container must bind `0.0.0.0` or nothing outside it can connect. |
| `PORT` | `8000` | Server port. Most hosts inject this; the image reads it. |
| `ANTHROPIC_API_KEY` | unset | Optional. Preferred provider for the AI layer. |
| `MISTRAL_API_KEY` | unset | Optional. Used when no Anthropic key is set. |

With neither set, every AI job falls back to a deterministic heuristic and the platform is fully
functional — the UI reports "Heuristics" rather than implying a model is at work.

Copy `.env.example` to `.env` and fill in what you need. `.env` is excluded from the image.

## What the image contains

- Python 3.12 slim, the API, and the compiled frontend in `web/`
- The demo dataset, generated at build time so a fresh container has a working project immediately
- No Node, no frontend source, no docs, no source PDF — those are dropped by `.dockerignore`
- A non-root user (`uid 10001`) and a `HEALTHCHECK` against `/api/health`

## Persistence

State is deliberately in memory: projects, fitted models and generated output all live in the
process and are lost on restart, which reseeds the demo project. That is a considered choice for a
demo — fewer moving parts, nothing to migrate — but it means **this is not multi-instance safe.**
Run one instance. Scaling horizontally needs the store in `api/store.py` moved to Postgres or Redis
first, because a second replica would not see the first one's projects.

The only thing worth persisting is the AI response cache, which `docker-compose.yml` mounts as a
named volume so a demo never waits on a cold model call.

## Continuous integration

`.github/workflows/check.yml` runs on every push:

- the three test suites (179 checks: engine guarantees, every API route, and the AI layer with no
  credential set)
- a frontend typecheck and production build
- a Docker build, then a smoke test that the container actually serves a healthy app and a demo
  project — the image is proven to work, not just to compile

## Verifying a deployment

```bash
curl -s https://<host>/api/health
curl -s -X POST https://<host>/api/projects/demo | head -c 200
```

`/docs` serves the interactive OpenAPI reference for every route.
