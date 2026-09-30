# Two stages, so the runtime image carries no Node and no frontend source:
# the UI is compiled once and only its built assets cross over.

# ---- stage 1: build the frontend ----------------------------------------
FROM node:22-alpine AS web
WORKDIR /build/frontend

# The lockfile is resolved by npm 11, and the npm 10 that ships inside
# node:22-alpine reads the same file differently: it rejects it with
# "lock file's picomatch@2.3.2 does not satisfy picomatch@4.0.7" and the build
# dies here. Pinning the client makes the install depend on the lockfile rather
# than on whichever npm happens to be bundled with the base image.
RUN npm install --global npm@11

# Manifests first, so `npm ci` stays cached until a dependency actually changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# vite.config.ts already targets ../web, which resolves to /build/web here.
RUN npm run build

# ---- stage 2: the runtime -----------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY scripts/ ./scripts/

# Generate the demo dataset at build time, so a fresh container has a working
# project the moment it starts with no first-run setup.
RUN python scripts/make_demo_data.py

COPY --from=web /build/web ./web/

# Run unprivileged. data/ stays writable for the AI response cache.
RUN useradd --create-home --uid 10001 dataseed && chown -R dataseed:dataseed /app
USER dataseed

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8000') + '/api/health').status == 200 else 1)"

CMD ["sh", "-c", "exec uvicorn api.main:app --host ${HOST} --port ${PORT}"]
