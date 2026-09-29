# Effective Usage & Optimization Guide: Mistral Free Tier API

This guide provides strategies, technical implementation details, and best practices for leveraging **Mistral AI's Free Tier API Key** within the DataSeed Synthetic Data Platform without hitting rate limits (`429 Too Many Requests`), running out of quota, or degrading system performance.

---

---

## 0. Before anything else: is the key actually usable?

A Mistral key can authenticate perfectly and still have **no chat quota at all**.
This is the single most common reason the AI layer sits in heuristic mode, and it
is not a rate limit you can wait out.

Check it directly:

```bash
python tests/probe_mistral.py
```

Read the header in the output, not the status code:

| What you see | What it means | What to do |
|---|---|---|
| `x-ratelimit-limit-req-minute: 0` | The account has **no allocation**. Every chat call returns 429 forever. | Activate the account, see below |
| `limit` above 0, `remaining: 0` | A genuine rate limit | Wait, the platform already backs off and retries |
| HTTP 200 | Working | Nothing |

### Activating a free tier account

`GET /v1/models` succeeding proves only that the key is valid. Chat completions
are gated separately. On La Plateforme the free tier requires **phone number
verification** before any quota is issued:

1. Sign in at <https://console.mistral.ai>
2. Complete phone verification under billing or plan settings
3. Re-run `python tests/probe_mistral.py` and confirm the limit header is above 0
4. Confirm end to end with `python tests/test_ai_live.py`

Measured on this project's key before activation:

```
GET  /v1/models            -> 200, 46 models listed
POST /v1/chat/completions  -> 429, x-ratelimit-limit-req-minute: 0
```

Four attempts over roughly sixty seconds all returned 429 with a limit of zero,
which is what distinguishes "no allocation" from "briefly throttled".

### This is not an outage

With no usable key the platform runs every AI job on deterministic heuristics and
stays fully functional. The interface reports this honestly rather than implying a
model is at work:

| Badge | Meaning |
|---|---|
| **Heuristics** | No credential set |
| **AI ready** | Credential present, not yet called |
| **AI unreachable** | Credential present, calls are failing, check quota |
| **AI live** | A call has actually succeeded |

`tests/test_ai_fallback.py` removes every credential from the environment and
asserts the whole pipeline still works, which is why a dead key is a cosmetic
problem rather than a demo-stopping one.

---

## 1. Free Tier Limits & Architecture Overview

Mistral AI provides free tier access for development and testing. However, the free tier enforces strict operational constraints:

| Constraint Metric | Typical Free Tier Boundary | Impact on Application |
| :--- | :--- | :--- |
| **Request Rate (RPM)** | 1 request per second (~30–60 RPM) | Burst requests trigger `429 Too Many Requests` |
| **Token Rate (TPM)** | 50,000 – 100,000 tokens/min | Large prompts rapidly exhaust token budget |
| **Concurrency** | 1–2 concurrent HTTP requests | Parallel requests fail immediately |

### Architectural Design Rule
In this platform, **the AI layer is purely additive (polish layer) and never in the load-bearing critical path**. Every AI call returns a Pydantic schema object or falls back to a deterministic heuristic. If the API key is missing, rate-limited, or out of quota, the pipeline continues without breaking.

---

## 2. Implemented Optimization Strategies

The backend (`api/ai.py`) includes several built-in optimizations designed specifically for Mistral:

```
                  ┌──────────────────────────────┐
                  │    Incoming Request / Job    │
                  └──────────────┬───────────────┘
                                 │
                        [ 1. Disk Cache Check ]
                        (SHA-256 Payload Hash)
                                 │
                 ┌───────────────┴───────────────┐
             Hit │                               │ Miss
                 ▼                               ▼
        ┌────────────────┐             [ 2. Rate Throttle ]
        │ Return Cached  │             (Wait min interval 1.2s)
        │ 0ms / 0 Tokens │                       │
        └────────────────┘                       ▼
                                       [ 3. Tiered Model Selection ]
                                       (Reasoning vs. Bulk Model)
                                                 │
                                                 ▼
                                       [ 4. JSON Schema Call ]
                                       (Strict Pydantic Output)
                                                 │
                                 ┌───────────────┴───────────────┐
                             200 │                               │ 429 / Error
                                 ▼                               ▼
                        ┌────────────────┐             [ 5. Backoff & Retry ]
                        │ Write to Cache │             (Up to 4 retries)
                        └────────────────┘                       │
                                                                 ▼
                                                        [ 6. Heuristic Fallback ]
                                                        (Zero crash guaranteed)
```

### Strategy A: SHA-256 Disk Caching
- Every structured request generates a key derived from `job_name` and a SHA-256 hash of the sorted prompt payload.
- Cache entries are stored under `data/ai_cache/*.json`.
- **Benefit**: Re-running schema inference, relationship detection, or rules on the same dataset costs **0 tokens** and executes instantly (0ms latency).

### Strategy B: Micro-Throttling (`MISTRAL_MIN_INTERVAL`)
- Requests are serialized through a thread-safe rate limiter (`_rate_lock`).
- A minimum interval of `1.2 seconds` is enforced between consecutive HTTP requests.
- **Benefit**: Prevents burst request rate limits from being triggered when navigating rapidly in the UI.

### Strategy C: Tiered Model Routing
- **Reasoning Jobs** (`infer-types`, `infer-relations`, `rules`): Routed to `mistral-medium-latest` for higher classification accuracy.
- **Bulk Data Generation**: Routed to `mistral-small-latest` to conserve tokens and minimize latency.

### Strategy D: Single-Pass JSON Schema Enforcement
- API requests use Mistral's native `json_schema` response format mode (`"strict": True`).
- **Benefit**: Eliminates retry loops caused by missing keys or invalid JSON formatting.

---

## 3. Best Practices for Developers & Users

### 1. Preserve the Local Disk Cache
During development and testing, do not delete `data/ai_cache/` unless testing cold API calls explicitly. Keeping the cache populated saves your daily Mistral API quota.

### 2. Prompt Payload Truncation & Compression
When constructing prompts for new AI endpoints:
- Never pass thousands of raw database rows.
- Send only column headers, data types, statistical summary metrics (null rate, unique counts), and **3 to 5 sample values**.
- Strip unnecessary formatting whitespaces from prompt strings.

### 3. Monitor AI Engine Status in Real Time
The application exposes an engine status endpoint:
```http
GET /api/ai/status
```
Response format:
```json
{
  "available": true,
  "provider": "mistral",
  "reasoning_model": "mistral-medium-latest",
  "bulk_model": "mistral-small-latest",
  "cached_responses": 18,
  "mode": "live",
  "note": "12 successful call(s) on mistral.",
  "calls_ok": 12,
  "calls_failed": 0
}
```
- If `mode` reports `"degraded"`, it means Mistral returned repeated 429s or quota errors. The UI and engine automatically fall back to deterministic heuristics without interrupting user workflows.

### 4. Low Temperature Settings
Always use `temperature: 0.0` or `0.2` for schema classification and constraint extraction. Lower temperature ensures deterministic outputs, preventing unnecessary re-runs.

---

## 4. Environment Setup

To activate live Mistral API calls:
1. Obtain an API key from [Mistral AI Console](https://console.mistral.ai/).
2. Add the key to your `.env` file in the project root:
   ```env
   MISTRAL_API_KEY=your_mistral_api_key_here
   ```
3. Restart the FastAPI server:
   ```bash
   python -m uvicorn api.main:app --reload --port 8000
   ```
