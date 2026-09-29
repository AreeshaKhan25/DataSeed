"""The AI layer — four scoped jobs, none of them in the critical path.

The rule that makes this safe to ship:

    Every model response is parsed into a Pydantic model. A parse failure, a
    missing key, a timeout or a missing credential all fall through to a
    deterministic heuristic, and the pipeline continues.

That is why pulling the API key changes the polish of the product and nothing
else. Jobs 1 and 2 return *proposals* the user accepts or edits in the UI, so a
wrong guess is a review step rather than corrupted data.

Results are cached to disk by a hash of the input, so a demo never waits on a
cold call and re-running costs nothing.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Literal, TypeVar

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from .schema import SchemaIR, Table

log = logging.getLogger("synth.ai")

# Reasoning jobs go to Opus; the bulk text job goes to Sonnet, which is the one
# place volume justifies trading a little judgement for cost and latency.
REASONING_MODEL = "claude-opus-5-5"
BULK_MODEL = "claude-sonnet-5-5"

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "ai_cache"
REQUEST_TIMEOUT = 45.0
MAX_RETRIES = 1

T = TypeVar("T", bound=BaseModel)


# --------------------------------------------------------------------------
# Response schemas — the contract the model must satisfy
# --------------------------------------------------------------------------

SEMANTIC_TYPES = [
    "person_name", "email", "phone", "address", "city", "country", "postcode",
    "company", "iban", "national_id", "sku", "identifier", "currency",
    "category", "free_text", "date", "numeric", "url", "boolean", "unknown",
]


class ColumnProposal(BaseModel):
    column: str
    semantic: str
    pii: Literal["none", "quasi", "direct"]
    privacy: Literal["passthrough", "mask", "hash", "noise", "synthesize"]
    reason: str = ""


class ColumnProposals(BaseModel):
    columns: list[ColumnProposal] = Field(default_factory=list)


class RelationProposal(BaseModel):
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    cardinality: Literal["1:1", "1:N"] = "1:N"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""


class RelationProposals(BaseModel):
    relations: list[RelationProposal] = Field(default_factory=list)


class EdgeCase(BaseModel):
    name: str
    description: str
    column: str = ""
    kind: Literal["null", "outlier", "boundary", "unicode", "duplicate", "format"] = "outlier"
    rate: float = Field(default=0.01, ge=0.0, le=0.25)


class EdgeCaseProposals(BaseModel):
    edge_cases: list[EdgeCase] = Field(default_factory=list)


class RuleProposal(BaseModel):
    table: str
    kind: Literal["range", "comparison", "enum", "not_null", "conditional"]
    column: str
    description: str
    operator: str = ">="
    other_column: str = ""
    minimum: float | None = None
    maximum: float | None = None
    allowed: list[str] = Field(default_factory=list)
    when_column: str = ""
    when_value: str = ""


class RuleProposals(BaseModel):
    rules: list[RuleProposal] = Field(default_factory=list)


class TextValues(BaseModel):
    values: list[str] = Field(default_factory=list)


class StatementFilter(BaseModel):
    """A natural-language statement query, turned into something executable."""

    days: int | None = None
    min_balance: float | None = None
    max_balance: float | None = None
    min_amount: float | None = None
    direction: Literal["credit", "debit"] | None = None
    description_contains: str | None = None
    interpretation: str = ""


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------

_client_lock = threading.Lock()
_client: Any = None
_client_ready = False
_provider: str = "none"

# Mistral's free tier throttles hard, so calls are spaced and 429s are retried
# rather than treated as failure. Anything still failing falls through to the
# heuristic path like any other error.
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_REASONING_MODEL = "mistral-medium-latest"
MISTRAL_BULK_MODEL = "mistral-small-latest"
MISTRAL_MIN_INTERVAL = 1.2
MISTRAL_RETRIES = 4

_rate_lock = threading.Lock()
_last_call = 0.0

# A credential being present is not the same as the model being reachable. A
# key with no quota answers every request with a 429, so reporting "live"
# because a key exists would be a lie the UI repeats on every screen.
_health_lock = threading.Lock()
_calls_ok = 0
_calls_failed = 0


def _record(success: bool) -> None:
    global _calls_ok, _calls_failed
    with _health_lock:
        if success:
            _calls_ok += 1
            _calls_failed = 0
        else:
            _calls_failed += 1


def _get_client() -> Any:
    """Resolve a provider once. No credential is a normal state, not an error.

    Anthropic is preferred when both are present because the reasoning jobs were
    written against it; Mistral is a complete substitute, not a degraded one --
    both go through the same schema-validated contract.
    """
    global _client, _client_ready, _provider
    with _client_lock:
        if _client_ready:
            return _client
        _client_ready = True

        if os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import anthropic

                _client = anthropic.Anthropic(timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES)
                _provider = "anthropic"
                return _client
            except Exception as exc:  # noqa: BLE001
                log.warning("Anthropic client unavailable (%s).", exc)

        if os.environ.get("MISTRAL_API_KEY"):
            try:
                import httpx

                _client = httpx.Client(timeout=REQUEST_TIMEOUT)
                _provider = "mistral"
                return _client
            except Exception as exc:  # noqa: BLE001
                log.warning("Mistral client unavailable (%s).", exc)

        log.info("No AI credential set — running on deterministic heuristics.")
        _client = None
        _provider = "none"
        return None


def ai_available() -> bool:
    return _get_client() is not None


def ai_provider() -> str:
    _get_client()
    return _provider


def ai_status() -> dict[str, Any]:
    provider = ai_provider()
    reasoning, bulk = _models_for(provider)
    configured = ai_available()

    # Three honest states rather than two: no credential, a credential that has
    # not worked, and a credential proven by a successful call.
    if not configured:
        mode, note = "heuristic", "No AI credential set. Running on deterministic heuristics."
    elif _calls_ok:
        mode, note = "live", f"{_calls_ok} successful call(s) on {provider}."
    elif _calls_failed:
        mode, note = "degraded", (
            f"{provider} is configured but the last {_calls_failed} call(s) failed — "
            "falling back to heuristics. Check the key's quota."
        )
    else:
        mode, note = "configured", f"{provider} is configured but has not been called yet."

    return {
        "available": configured,
        "provider": provider,
        "reasoning_model": reasoning,
        "bulk_model": bulk,
        "cached_responses": len(list(CACHE_DIR.glob("*.json"))) if CACHE_DIR.exists() else 0,
        "mode": mode,
        "note": note,
        "calls_ok": _calls_ok,
        "calls_failed": _calls_failed,
    }


def _models_for(provider: str) -> tuple[str, str]:
    if provider == "mistral":
        return MISTRAL_REASONING_MODEL, MISTRAL_BULK_MODEL
    if provider == "anthropic":
        return REASONING_MODEL, BULK_MODEL
    return "—", "—"


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------

def _cache_key(job: str, payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return f"{job}-{hashlib.sha256(blob).hexdigest()[:20]}"


def _cache_read(key: str) -> dict[str, Any] | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_write(key: str, value: dict[str, Any]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{key}.json").write_text(
            json.dumps(value, indent=2, default=str), encoding="utf-8"
        )
    except OSError as exc:  # noqa: BLE001
        log.debug("Could not cache %s: %s", key, exc)


# --------------------------------------------------------------------------
# The single call site
# --------------------------------------------------------------------------

def _ask(
    schema: type[T],
    system: str,
    prompt: str,
    *,
    model: str = REASONING_MODEL,
    max_tokens: int = 8000,
) -> T | None:
    """One structured request. Returns None on any failure, never raises.

    `messages.parse` constrains the response to the Pydantic schema, so a
    malformed payload cannot reach the caller. Everything else — auth, network,
    rate limits, validation — collapses to None so the caller takes its
    deterministic path.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        if _provider == "mistral":
            result = _ask_mistral(client, schema, system, prompt, model, max_tokens)
        else:
            result = _ask_anthropic(client, schema, system, prompt, model, max_tokens)
        _record(result is not None)
        return result
    except ValidationError as exc:
        log.warning("AI response failed validation (%s) — using heuristics.", exc)
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        log.warning("AI call failed (%s: %s) — using heuristics.", type(exc).__name__, exc)
    _record(False)
    return None


def _ask_anthropic(
    client: Any, schema: type[T], system: str, prompt: str, model: str, max_tokens: int
) -> T | None:
    response = client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": system,
            # The system prompt is identical across every call for a job, so
            # caching it makes repeated schema work nearly free.
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )
    if getattr(response, "stop_reason", None) == "refusal":
        log.warning("Model declined the request; using heuristics.")
        return None
    return response.parsed_output


def _mistral_model(model: str) -> str:
    """Map an Anthropic model name onto its Mistral counterpart by tier."""
    return MISTRAL_BULK_MODEL if model == BULK_MODEL else MISTRAL_REASONING_MODEL


def _throttle() -> None:
    """Space out calls. The free tier rejects bursts outright."""
    global _last_call
    with _rate_lock:
        wait = MISTRAL_MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _ask_mistral(
    client: Any, schema: type[T], system: str, prompt: str, model: str, max_tokens: int
) -> T | None:
    """Same contract as the Anthropic path: schema-valid object, or None.

    Mistral's `json_schema` response format constrains the reply, and the result
    is still validated against the Pydantic model afterwards -- the provider is
    trusted to try, never to be correct.
    """
    body = {
        "model": _mistral_model(model),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__.lower(),
                "schema": _strict_schema(schema),
                "strict": True,
            },
        },
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}",
        "Content-Type": "application/json",
    }

    for attempt in range(MISTRAL_RETRIES):
        _throttle()
        response = client.post(MISTRAL_URL, headers=headers, json=body)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return schema.model_validate_json(content)
        if response.status_code == 429:
            # Free-tier throttling is expected, not a fault. Back off and retry;
            # if it never clears, the caller takes the heuristic path.
            time.sleep(2.5 * (attempt + 1))
            continue
        log.warning("Mistral returned %s: %s", response.status_code, response.text[:200])
        return None

    log.warning("Mistral rate limit did not clear — using heuristics.")
    return None


def _strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """A JSON schema Mistral's strict mode accepts.

    Strict mode requires `additionalProperties: false` and every property listed
    as required on each object, and it rejects the `$defs`/`$ref` indirection
    Pydantic emits by default -- so references are inlined.
    """
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].rsplit("/", 1)[-1]
                return resolve(defs.get(name, {}))
            # anyOf is how Pydantic spells `X | None`; strict mode wants a plain
            # type, so take the first non-null branch.
            if "anyOf" in node:
                options = [o for o in node["anyOf"] if o.get("type") != "null"]
                if options:
                    merged = resolve(options[0])
                    if isinstance(merged, dict):
                        return merged
            out = {k: resolve(v) for k, v in node.items() if k not in ("$ref", "anyOf", "default")}
            if out.get("type") == "object":
                out["additionalProperties"] = False
                if "properties" in out:
                    out["required"] = list(out["properties"])
            return out
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return resolve(raw)


# --------------------------------------------------------------------------
# Job 1 — semantic type and PII inference
# --------------------------------------------------------------------------

_JOB1_SYSTEM = """You classify database columns for a synthetic data platform.

For each column decide three things:

1. `semantic` — what the values MEAN, from this list only:
   person_name, email, phone, address, city, country, postcode, company, iban,
   national_id, sku, identifier, currency, category, free_text, date, numeric,
   url, boolean, unknown

2. `pii` — "direct" if a value identifies one person on its own (name, email,
   phone, address, national id, bank account). "quasi" if it narrows someone
   down in combination with other columns (city, postcode, employer, birth date,
   free text). "none" otherwise.

3. `privacy` — how the platform should treat it:
   - "synthesize" (default) regenerate a realistic value
   - "hash" one-way hash, when downstream systems only join on it
   - "mask" partially redact, when the shape matters but the value does not
   - "noise" add calibrated noise, numeric columns only
   - "passthrough" keep as generated; correct for keys and non-sensitive values

Be conservative about PII: a false "direct" costs a little fidelity, a missed
one leaks a real person. Column names can lie — weigh the sample values more.
Return one entry per column given, using the exact column names supplied."""


def infer_semantic_types(table: Table, sample: pd.DataFrame) -> list[dict[str, Any]]:
    """Propose semantic type, PII level and privacy mode per column."""
    payload = []
    for column in table.columns:
        values: list[str] = []
        if column.name in sample.columns:
            values = [
                str(v)[:80] for v in sample[column.name].dropna().head(12).tolist()
            ]
        payload.append({
            "column": column.name,
            "detected_dtype": column.dtype,
            "distinct_values": column.stats.n_unique,
            "null_rate": round(column.null_rate, 3),
            "samples": values,
        })

    key = _cache_key(f"types-{table.name}", payload)
    if (cached := _cache_read(key)) is not None:
        return cached["columns"]

    result = _ask(
        ColumnProposals,
        _JOB1_SYSTEM,
        f"Table `{table.name}`, {table.row_count} rows.\n\n"
        f"Columns:\n{json.dumps(payload, indent=2, default=str)}",
        model=REASONING_MODEL,
    )

    if result is None:
        proposals = _heuristic_types(table)
    else:
        known = {c.name for c in table.columns}
        proposals = [
            {**p.model_dump(), "source": "ai"}
            for p in result.columns
            if p.column in known and p.semantic in SEMANTIC_TYPES
        ]
        # A short or partial response must not silently drop columns.
        covered = {p["column"] for p in proposals}
        proposals += [p for p in _heuristic_types(table) if p["column"] not in covered]

    _cache_write(key, {"columns": proposals})
    return proposals


def _heuristic_types(table: Table) -> list[dict[str, Any]]:
    """The profiler's own inference, reused as the fallback."""
    return [
        {
            "column": c.name,
            "semantic": c.semantic,
            "pii": c.pii,
            "privacy": "hash" if c.pii == "direct" and c.semantic == "email" else c.privacy,
            "reason": "Pattern match on column name and sample values.",
            "source": "heuristic",
        }
        for c in table.columns
    ]


# --------------------------------------------------------------------------
# Job 2 — relationship inference
# --------------------------------------------------------------------------

_JOB2_SYSTEM = """You infer foreign-key relationships between database tables.

You are given each table's columns and, for candidate pairs, the fraction of the
child's values that appear in the parent's key ("containment"). Containment below
0.9 almost always means the columns are unrelated despite a similar name.

Propose an edge only when BOTH the naming and the containment support it. Set
`cardinality` to "1:1" when the child column is unique, otherwise "1:N".
`confidence` should reflect how certain you are; a human reviews every edge.

Prefer missing a relationship over inventing one. A wrong edge makes the
generator build data with the wrong shape."""


def infer_relationships(
    schema: SchemaIR, frames: dict[str, pd.DataFrame]
) -> list[dict[str, Any]]:
    """Propose FK edges, with the overlap statistics the model needs to judge."""
    tables_payload = []
    for table in schema.tables:
        tables_payload.append({
            "table": table.name,
            "rows": table.row_count,
            "primary_key": table.primary_key,
            "columns": [
                {"name": c.name, "dtype": c.dtype, "unique": c.unique}
                for c in table.columns
            ],
        })

    overlaps = []
    for child in schema.tables:
        child_frame = frames.get(child.name)
        if child_frame is None:
            continue
        for parent in schema.tables:
            if parent.name == child.name or not parent.primary_key:
                continue
            parent_frame = frames.get(parent.name)
            if parent_frame is None or parent.primary_key not in parent_frame.columns:
                continue
            parent_values = set(parent_frame[parent.primary_key].dropna().tolist())
            if not parent_values:
                continue
            for column in child.columns:
                if column.name not in child_frame.columns or column.dtype not in ("int", "str"):
                    continue
                child_values = child_frame[column.name].dropna()
                if child_values.empty:
                    continue
                containment = float(child_values.isin(parent_values).mean())
                if containment > 0.5:
                    overlaps.append({
                        "child": f"{child.name}.{column.name}",
                        "parent": f"{parent.name}.{parent.primary_key}",
                        "containment": round(containment, 3),
                        "child_unique": column.unique,
                    })

    key = _cache_key("relations", {"tables": tables_payload, "overlaps": overlaps})
    if (cached := _cache_read(key)) is not None:
        return cached["relations"]

    result = _ask(
        RelationProposals,
        _JOB2_SYSTEM,
        f"Tables:\n{json.dumps(tables_payload, indent=2)}\n\n"
        f"Candidate overlaps:\n{json.dumps(overlaps, indent=2)}",
        model=REASONING_MODEL,
    )

    names = {t.name for t in schema.tables}
    if result is None:
        relations = _heuristic_relations(schema)
    else:
        relations = []
        for proposal in result.relations:
            if proposal.child_table not in names or proposal.parent_table not in names:
                continue
            child = schema.table(proposal.child_table)
            parent = schema.table(proposal.parent_table)
            if child is None or parent is None:
                continue
            if child.column(proposal.child_column) is None:
                continue
            if parent.column(proposal.parent_column) is None:
                continue
            relations.append({**proposal.model_dump(), "source": "ai"})
        if not relations:
            relations = _heuristic_relations(schema)

    _cache_write(key, {"relations": relations})
    return relations


def _heuristic_relations(schema: SchemaIR) -> list[dict[str, Any]]:
    return [
        {
            "child_table": fk.child_table, "child_column": fk.child_column,
            "parent_table": fk.parent_table, "parent_column": fk.parent_column,
            "cardinality": fk.cardinality, "confidence": 0.9,
            "reason": "Name match with value containment above 90%.",
            "source": "heuristic",
        }
        for fk in schema.foreign_keys
    ]


# --------------------------------------------------------------------------
# Job 3 — free-text synthesis
# --------------------------------------------------------------------------

_JOB3_SYSTEM = """You write realistic free-text values for a synthetic dataset.

You are given a column, a few real examples for tone and length, and the row
context for each value to produce. Match the register, length and vocabulary of
the examples. Vary the output — repetitive filler is worse than plain Faker text.

Never reuse an example verbatim, and never invent a real person, company or
brand name. Return exactly as many values as rows requested, in order."""


def synthesize_text(
    column_name: str,
    examples: list[str],
    contexts: list[dict[str, Any]],
    *,
    batch_size: int = 50,
) -> list[str] | None:
    """Generate realistic free text. Returns None so the caller uses Faker."""
    if not contexts:
        return []

    key = _cache_key(f"text-{column_name}", {"examples": examples[:5], "n": len(contexts),
                                             "contexts": contexts[:3]})
    if (cached := _cache_read(key)) is not None and len(cached["values"]) >= len(contexts):
        return cached["values"][:len(contexts)]

    out: list[str] = []
    for start in range(0, len(contexts), batch_size):
        chunk = contexts[start:start + batch_size]
        result = _ask(
            TextValues,
            _JOB3_SYSTEM,
            f"Column: `{column_name}`\n"
            f"Real examples (tone only, never copy):\n"
            f"{json.dumps(examples[:8], indent=2)}\n\n"
            f"Produce exactly {len(chunk)} values, one per row:\n"
            f"{json.dumps(chunk, indent=2, default=str)}",
            model=BULK_MODEL,
            max_tokens=8000,
        )
        if result is None or len(result.values) < len(chunk):
            return None
        out.extend(result.values[:len(chunk)])

    _cache_write(key, {"values": out})
    return out


# --------------------------------------------------------------------------
# Job 4 — edge-case proposal
# --------------------------------------------------------------------------

_JOB4_SYSTEM = """You propose edge cases for a synthetic dataset.

Engineers use synthetic data mainly to test paths real data never exercises.
Given a schema, propose 6 to 10 edge cases worth injecting — each one a concrete,
checkable condition tied to a real column.

Good: "Unicode and apostrophes in customer names", "Order dated 29 February",
"Zero-quantity line item", "Balance at exactly the overdraft limit".
Bad: "Bad data", "Invalid input", "Test the system".

`rate` is the fraction of rows to affect — keep it between 0.005 and 0.05 so the
dataset stays realistic. Use exact column names from the schema."""


_STATIC_EDGE_CASES = [
    {"name": "Unicode names", "description": "Accented characters, apostrophes and non-Latin scripts in name fields.", "kind": "unicode", "rate": 0.02},
    {"name": "Leap-year dates", "description": "29 February, to catch date arithmetic that assumes 365 days.", "kind": "boundary", "rate": 0.01},
    {"name": "Boundary amounts", "description": "Values at exactly zero and at the observed maximum.", "kind": "boundary", "rate": 0.01},
    {"name": "Negative amounts", "description": "Refunds and chargebacks expressed as negative values.", "kind": "outlier", "rate": 0.01},
    {"name": "Missing optional fields", "description": "Nulls in every column the schema marks nullable.", "kind": "null", "rate": 0.03},
    {"name": "Extreme outliers", "description": "Values well beyond the observed range, to test scaling and axes.", "kind": "outlier", "rate": 0.01},
    {"name": "Very long text", "description": "Free-text fields at the maximum plausible length.", "kind": "format", "rate": 0.01},
    {"name": "Duplicate natural keys", "description": "Rows matching on every column except the primary key.", "kind": "duplicate", "rate": 0.005},
    {"name": "Future timestamps", "description": "Dates after today, to catch clock-skew assumptions.", "kind": "boundary", "rate": 0.01},
    {"name": "Empty strings", "description": "Empty rather than null, which many validators treat differently.", "kind": "format", "rate": 0.01},
]


def propose_edge_cases(schema: SchemaIR) -> list[dict[str, Any]]:
    payload = [
        {
            "table": t.name,
            "columns": [
                {"name": c.name, "dtype": c.dtype, "semantic": c.semantic,
                 "nullable": c.nullable}
                for c in t.columns
            ],
        }
        for t in schema.tables
    ]

    key = _cache_key("edges", payload)
    if (cached := _cache_read(key)) is not None:
        return cached["edge_cases"]

    result = _ask(
        EdgeCaseProposals,
        _JOB4_SYSTEM,
        f"Schema:\n{json.dumps(payload, indent=2)}",
        model=BULK_MODEL,
    )

    if result is None:
        cases = [{**c, "column": "", "source": "heuristic"} for c in _STATIC_EDGE_CASES]
    else:
        valid_columns = {c.name for t in schema.tables for c in t.columns}
        cases = [
            {**c.model_dump(), "source": "ai"}
            for c in result.edge_cases
            if not c.column or c.column in valid_columns
        ]
        if not cases:
            cases = [{**c, "column": "", "source": "heuristic"} for c in _STATIC_EDGE_CASES]

    _cache_write(key, {"edge_cases": cases})
    return cases


# --------------------------------------------------------------------------
# Job 5 — business rules
# --------------------------------------------------------------------------

_JOB5_SYSTEM = """You propose business rules for a synthetic data generator.

A schema says what SHAPE the data has. A business rule says what makes a row
VALID -- the domain logic a distribution cannot express. Statistical fitting
will happily produce an order that shipped before it was placed, a cancelled
order with a payment date, or a refund larger than the original charge.

Propose rules of these kinds only:
  range        a numeric column stays within bounds (minimum and/or maximum)
  comparison   one column compares to another (usually two dates, or a discount
               against a price). Set `column`, `operator`, `other_column`.
  enum         a column only takes values from a fixed set
  not_null     a column is always present
  conditional  when `when_column` equals `when_value`, `column` must be null

Rules must reference columns that exist, on the table you name. Both columns of
a comparison must be on the SAME table.

Propose only rules that are near-certainly true of the domain. A rule the real
data violates is not a rule -- it is a bug that will silently drop rows. Six to
ten good rules beat twenty speculative ones. Write `description` as a short
sentence a non-engineer would understand."""


def propose_business_rules(schema: SchemaIR) -> list[dict[str, Any]]:
    """Ask for domain rules the schema alone cannot express."""
    payload = [
        {
            "table": t.name,
            "columns": [
                {"name": c.name, "dtype": c.dtype, "semantic": c.semantic,
                 "nullable": c.nullable}
                for c in t.columns
            ],
        }
        for t in schema.tables
    ]

    key = _cache_key("rules", payload)
    if (cached := _cache_read(key)) is not None:
        return cached["rules"]

    result = _ask(
        RuleProposals,
        _JOB5_SYSTEM,
        f"Schema:\n{json.dumps(payload, indent=2)}",
        model=REASONING_MODEL,
    )

    rules: list[dict[str, Any]] = []
    if result is not None:
        for proposal in result.rules:
            table = schema.table(proposal.table)
            if table is None or table.column(proposal.column) is None:
                continue
            if proposal.kind == "comparison":
                # Both sides must live on the same table, or the rule can never
                # be evaluated against a frame.
                if not proposal.other_column or table.column(proposal.other_column) is None:
                    continue
            if proposal.kind == "conditional" and (
                not proposal.when_column or table.column(proposal.when_column) is None
            ):
                continue

            params: dict[str, Any] = {}
            if proposal.kind == "range":
                if proposal.minimum is None and proposal.maximum is None:
                    continue
                params = {"minimum": proposal.minimum, "maximum": proposal.maximum}
            elif proposal.kind == "comparison":
                params = {"operator": proposal.operator, "other_column": proposal.other_column}
            elif proposal.kind == "enum":
                if not proposal.allowed:
                    continue
                params = {"allowed": proposal.allowed}
            elif proposal.kind == "conditional":
                params = {
                    "when_column": proposal.when_column,
                    "when_operator": "==",
                    "when_value": proposal.when_value,
                    "then_null": True,
                }

            rules.append({
                "table": proposal.table, "kind": proposal.kind,
                "column": proposal.column, "description": proposal.description,
                "params": params, "source": "ai",
            })

    _cache_write(key, {"rules": rules})
    return rules


# --------------------------------------------------------------------------
# Bonus — natural-language statement queries
# --------------------------------------------------------------------------

_QUERY_SYSTEM = """You turn a plain-English bank statement request into filters.

Examples:
  "last 90 days, balance over $500"  -> days 90, min_balance 500
  "only deposits above 1000"         -> direction credit, min_amount 1000
  "payments to utilities last month"  -> days 30, direction debit,
                                         description_contains "utilities"

Leave a field null when the request does not mention it. Never invent a
constraint. `interpretation` is one short sentence restating what you applied,
shown to the user for confirmation."""


def parse_query(text: str) -> dict[str, Any]:
    """Parse a statement query. Falls back to the regex parser in documents.py."""
    if not text or not text.strip():
        return {"source": "none"}

    key = _cache_key("query", text.strip().lower())
    if (cached := _cache_read(key)) is not None:
        return cached

    result = _ask(StatementFilter, _QUERY_SYSTEM, f"Request: {text}", model=BULK_MODEL,
                  max_tokens=1000)

    if result is None:
        from .documents import parse_statement_query

        parsed = parse_statement_query(text)
        out = {
            "days": parsed.days, "min_balance": parsed.min_balance,
            "max_balance": parsed.max_balance, "min_amount": parsed.min_amount,
            "direction": parsed.direction,
            "description_contains": parsed.description_contains,
            "interpretation": _describe(parsed.__dict__),
            "source": "heuristic",
        }
    else:
        out = {**result.model_dump(), "source": "ai"}

    _cache_write(key, out)
    return out


def _describe(filters: dict[str, Any]) -> str:
    parts = []
    if filters.get("days"):
        parts.append(f"the last {filters['days']} days")
    if filters.get("min_balance") is not None:
        parts.append(f"balance at or above {filters['min_balance']:,.2f}")
    if filters.get("max_balance") is not None:
        parts.append(f"balance at or below {filters['max_balance']:,.2f}")
    if filters.get("min_amount") is not None:
        parts.append(f"amounts over {filters['min_amount']:,.2f}")
    if filters.get("direction"):
        parts.append(f"{filters['direction']}s only")
    if filters.get("description_contains"):
        parts.append(f"descriptions containing '{filters['description_contains']}'")
    return "Showing " + ", ".join(parts) + "." if parts else "No filters applied."


# --------------------------------------------------------------------------
# Applying proposals
# --------------------------------------------------------------------------

def apply_column_proposals(
    table: Table, proposals: list[dict[str, Any]]
) -> int:
    """Write accepted proposals into the schema. Returns how many changed."""
    changed = 0
    for proposal in proposals:
        column = table.column(str(proposal.get("column", "")))
        if column is None:
            continue
        # Keys are structural: their semantics are not the model's to reassign.
        if column.semantic in ("primary_key", "foreign_key"):
            continue
        before = (column.semantic, column.pii, column.privacy)
        column.semantic = str(proposal.get("semantic", column.semantic))
        column.pii = proposal.get("pii", column.pii)
        column.privacy = proposal.get("privacy", column.privacy)
        column.ai_inferred = proposal.get("source") == "ai"
        if (column.semantic, column.pii, column.privacy) != before:
            changed += 1
    return changed


def sanitize_identifier(name: str) -> str:
    """Names from a model become table identifiers, so they get scrubbed."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name.strip())
    return re.sub(r"_+", "_", cleaned).strip("_").lower() or "column"
