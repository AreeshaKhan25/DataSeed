# Getting a public URL without a card

Render turned out to want a card on file before it would create even a free
service, and the card that was added never attached to the workspace the service
lived in. This page records what was checked afterwards, what actually worked,
and how to reproduce it.

## One constraint that rules several options out

This platform keeps projects, fitted models and generated tables **in memory**.
That was a deliberate choice: no database, no queue, nothing to migrate, far
fewer ways to fail on stage.

It does mean the app needs a **persistent process**, not serverless functions.
Vercel, Netlify Functions and AWS Lambda all spin up a fresh process per request,
so a project created by one click would be gone by the next. They are not
options here, however free they are.

## What the free tiers look like now

Checked on 29 September 2026, by opening each signup page rather than trusting
a pricing summary.

| Host | Card at signup | Runs a persistent Python process | Verdict |
|---|---|---|---|
| Cloudflare quick tunnel | no account at all | your machine does | **works, used below** |
| Hugging Face Spaces | no | **no, not on the free tier** | ruled out |
| PythonAnywhere | no | yes, WSGI only | fallback, needs an adapter |
| Render | yes | yes | blocked |
| Fly.io, Railway, Koyeb | yes | yes | blocked |

The Hugging Face line is the one that changed. Spaces used to give a free Docker
container, and `Dockerfile.spaces` in this repo was written for exactly that. The
new Space form now says, in a box under the SDK picker:

> Gradio and Docker Spaces require a paid plan. Static Spaces stay free for
> everyone.

Static means files served as they are, with no process behind them. That can host
the compiled frontend in `web/`, but there would be no API for it to call, so it
is not a deployment of this project. `Dockerfile.spaces` is kept in the repo
because it is still correct for a PRO account or any other Docker host.

---

## 1. Cloudflare quick tunnel, which is what is running

No account, no card, no configuration, HTTPS included.

```powershell
# terminal 1, the app
.\run.ps1

# terminal 2, the public front door
cloudflared tunnel --url http://localhost:8000
```

It prints a `https://<four-random-words>.trycloudflare.com` address. That address
is the deployment. Everything answers on it: the interface at `/`, the API under
`/api`, the reference at `/docs`.

Install it once with `winget install Cloudflare.cloudflared`, or drop the single
`cloudflared.exe` from the project releases page anywhere on PATH.

**The catch, stated plainly.** The URL lives only while both commands are
running, and it is a different URL each time. Your machine is the server, so it
has to stay awake and online. Start it before you present and it just works;
close the laptop and the link dies.

### It is slower than localhost, so plan the demo around that

Measured against the live tunnel, same machine, same project:

| Call | Size | Over the tunnel |
|---|---|---|
| Invoice HTML | 5.6 KB | 22s |
| Invoice bundle | 47 KB | 24s |
| Export, CSV | 1.0 MB | 26s |
| Export, Parquet | 1.0 MB | 26s |
| Export, JSON | 15 MB | 63s |

All of these are close to instant on `localhost`, so the time is the tunnel, not
the engine. Note that JSON is fifteen times the size of the others because it is
the one format that is not zipped, and it is the only call that takes over a
minute. If you are showing exports live, click CSV or Parquet and describe JSON
rather than waiting on it.

### What a new push means here

There is no build step in the middle, so a push does not reach this URL by
itself. The URL points at the working copy on your machine:

```powershell
git pull            # or just keep working in the folder
# Ctrl+C the run.ps1 window, then start it again
```

The tunnel window can stay open through the restart. The address does not change
as long as `cloudflared` keeps running, so you can restart the app as often as
you like behind a stable link.

---

## 2. PythonAnywhere, if you need a URL that survives the laptop closing

Free tier, no card, one web app at `<username>.pythonanywhere.com`, and the
process stays up without you. Two adjustments are needed.

**It serves WSGI, and FastAPI speaks ASGI.** Bridge it in the WSGI config file
the dashboard gives you:

```python
from a2wsgi import ASGIMiddleware
from api.main import app as asgi_app

application = ASGIMiddleware(asgi_app)
```

`a2wsgi` is listed in `requirements.txt`, commented out, for this
reason. Uncomment it before installing on that host and leave it alone
everywhere else.

**Outbound network is limited to an allowlist.** Calls to Mistral or Anthropic
will not leave the machine. That is survivable: the AI layer falls back to
deterministic heuristics and every feature keeps working, with
`/api/ai/status` reporting `heuristic` rather than pretending otherwise. Only
the generated field descriptions get less fluent.

Account creation is yours to do. The steps after that are the usual ones: upload
or `git clone` the repo, make a virtualenv, `pip install -r requirements.txt`,
point the web app at the WSGI file above, reload.

---

## 3. If you go back to Render

The card dialog reappearing with empty fields almost always means the card was
saved against a **different account**. Two accounts appeared in the browser
during setup: the `Dataseed` workspace, and a separate signup still pending email
verification. Check the avatar in the top right, confirm which one is active, and
add the card there.

The configuration itself was already correct and is in `render.yaml`:

| Field | Value |
|---|---|
| Language | Python 3 |
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/api/health` |
| Plan | Free, 0.1 CPU, 512 MB |

One thing to fix while you are there: the Render account's GitHub App can only
see `cuischeduler`, not `DataSeed`. Grant it access to the repo, otherwise the
service cannot be created through the Git provider and will not auto deploy on
push. With that connection in place, `.github/workflows/deploy.yml` becomes
unnecessary and can be deleted.

---

## Checking any of them the same way

```bash
curl -s https://<host>/api/health
curl -s -X POST https://<host>/api/projects/demo
```

A healthy host answers the first with `{"status":"ok",...}` and the second with a
project containing five tables. That was run against the live tunnel and both
came back clean, along with a 5,000 row generation scoring 98.1 overall, five
reconciled invoices, and CSV, JSON and Parquet exports.
