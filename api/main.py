"""FastAPI application.

Two generation paths, kept deliberately separate:

  POST /preview   synchronous, capped at 100 rows, for the live canvas
  POST /generate  a background job with progress, for the real run

Mixing them is what makes these UIs feel broken -- a slider that triggers a
30-second job, or a job that blocks the request thread.
"""
from __future__ import annotations

import io
import traceback
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, documents as docs
from .engine import fit_table, sample_table
from .exporters import ExportError, available_formats, build_export
from .constraints import apply_constraints, infer_constraints
from .relational import check_integrity, generate_relational
from .schema import (
    Constraint,
    SchemaIR,
    build_schema,
    coerce_to_schema,
    frame_to_records,
    infer_derived_fields,
)
from .seeds import SeedFactory
from .store import STORE, Job, Project
from .trust import build_trust_report

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "data" / "demo"
WEB_DIR = ROOT / "web"

MAX_PREVIEW_ROWS = 100
MAX_GENERATE_ROWS = 1_000_000
MAX_DOCUMENTS = 500

app = FastAPI(title="DataSeed, Synthetic Data Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

class ApiError(HTTPException):
    """Every failure carries a remedy, so the UI never shows a stack trace."""

    def __init__(self, status: int, code: str, message: str, remedy: str) -> None:
        super().__init__(
            status_code=status,
            detail={"code": code, "message": message, "remedy": remedy},
        )


from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Any, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    msg = "; ".join(f"{'.'.join(str(l) for l in e.get('loc', []))}: {e.get('msg')}" for e in errors)
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "invalid_request",
                "message": f"Validation error: {msg}",
                "remedy": "Check the parameters or request payload format.",
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled(_request: Any, exc: Exception) -> JSONResponse:
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": {
            "code": "internal_error",
            "message": str(exc) or exc.__class__.__name__,
            "remedy": "Check the server log. If this persists, reload the demo project.",
        }},
    )


def _project_or_404(project_id: str) -> Project:
    project = STORE.get_project(project_id)
    if project is None:
        raise ApiError(404, "project_not_found",
                       f"No project with id '{project_id}'.",
                       "Reload the project list, or create a new project.")
    return project


def _get_source_dataframe(project: Project, table_name: str) -> pd.DataFrame | None:
    if not project.sources:
        return None
    if table_name in project.sources:
        return project.sources[table_name]
    norm = table_name.lower().replace(" ", "_")
    for k, df in project.sources.items():
        if k.lower().replace(" ", "_") == norm:
            return df
    if len(project.sources) == 1:
        return next(iter(project.sources.values()))
    return None


# --------------------------------------------------------------------------
# Request models
# --------------------------------------------------------------------------

class PreviewRequest(BaseModel):
    table: str | None = None
    rows: int = Field(default=25, ge=1, le=MAX_PREVIEW_ROWS)
    seed: int | None = None
    null_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    outlier_rate: float = Field(default=0.0, ge=0.0, le=0.5)


class GenerateRequest(BaseModel):
    rows: int = Field(default=1000, ge=1, le=MAX_GENERATE_ROWS)
    seed: int | None = None
    null_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    outlier_rate: float = Field(default=0.0, ge=0.0, le=0.5)
    validate_output: bool = True
    target_column: str | None = None


class SchemaPatch(BaseModel):
    seed: int | None = None
    locale: str | None = None
    columns: list[dict[str, Any]] = Field(default_factory=list)


class DocumentRequest(BaseModel):
    kind: Literal["invoice", "statement"] = "invoice"
    count: int = Field(default=10, ge=1, le=MAX_DOCUMENTS)
    region: str = "EU"
    query: str | None = None
    rows_per_statement: int = Field(default=24, ge=3, le=200)


# --------------------------------------------------------------------------
# Meta
# --------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "projects": len(STORE.list_projects()),
        "limits": {
            "preview_rows": MAX_PREVIEW_ROWS,
            "generate_rows": MAX_GENERATE_ROWS,
            "documents": MAX_DOCUMENTS,
        },
    }


@app.get("/api/ai/status")
def ai_status() -> dict[str, Any]:
    """Whether the AI layer is live or running on heuristics.

    The UI shows this honestly rather than implying AI is at work when it isn't.
    """
    return ai.ai_status()


@app.get("/api/formats")
def formats() -> dict[str, Any]:
    return {"formats": available_formats()}


@app.get("/api/regions")
def regions() -> dict[str, Any]:
    return {
        "regions": [
            {
                "code": r.code, "name": r.name, "tax_label": r.tax_label,
                "tax_rate": r.tax_rate, "currency": r.currency,
                "symbol": r.symbol, "date_format": r.date_format,
            }
            for r in docs.REGIONS.values()
        ]
    }


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------

@app.get("/api/projects")
def list_projects() -> dict[str, Any]:
    return {"projects": [p.summary() for p in STORE.list_projects()]}


@app.post("/api/projects/demo")
def create_demo() -> dict[str, Any]:
    """Seed the pre-built project. The demo must never depend on an upload."""
    files = {
        "customers": DEMO_DIR / "customers.csv",
        "orders": DEMO_DIR / "orders.csv",
        "order_items": DEMO_DIR / "order_items.csv",
        # tags/customer_tags give the demo a genuine many-to-many relationship
        # and a small lookup table, which exercise paths the other three do not.
        "tags": DEMO_DIR / "tags.csv",
        "customer_tags": DEMO_DIR / "customer_tags.csv",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        raise ApiError(503, "demo_data_missing",
                       f"Demo files not found: {', '.join(missing)}.",
                       "Run `python scripts/make_demo_data.py` from the project root.")

    # Reopen the existing demo rather than cloning it. Clicking "Load demo"
    # twice should not leave two identical projects in the list.
    for existing in STORE.list_projects():
        if existing.name == "Northwind Retail":
            return {"project": existing.summary(), "schema": existing.schema.model_dump()}

    frames = {name: pd.read_csv(path) for name, path in files.items()}
    schema = build_schema(frames, name="northwind_retail", seed=42)
    infer_derived_fields(frames, schema)
    schema.constraints = infer_constraints(frames, schema)
    project = STORE.create_project("Northwind Retail", schema, frames)
    return {"project": project.summary(), "schema": schema.model_dump()}


@app.post("/api/projects/ingest")
async def ingest(
    files: list[UploadFile] = File(...),
    name: str = Query(default="Untitled project"),
    seed: int = Query(default=42),
) -> dict[str, Any]:
    """Upload one or more CSVs. Each file becomes one table."""
    if not files:
        raise ApiError(400, "no_files", "No files were uploaded.",
                       "Attach at least one CSV file.")

    frames: dict[str, pd.DataFrame] = {}
    for upload in files:
        filename = upload.filename or "table.csv"
        if not filename.lower().endswith(".csv"):
            raise ApiError(415, "unsupported_file",
                           f"'{filename}' is not a CSV file.",
                           "Upload .csv files, or use the demo project.")
        raw = await upload.read()
        if not raw.strip():
            raise ApiError(400, "empty_file", f"'{filename}' is empty.",
                           "Upload a file with a header row and at least one data row.")
        try:
            frame = pd.read_csv(io.BytesIO(raw))
        except Exception as exc:  # noqa: BLE001
            raise ApiError(400, "unreadable_csv",
                           f"Could not parse '{filename}': {exc}",
                           "Check the delimiter and encoding, then upload again.") from exc
        if frame.empty or not len(frame.columns):
            raise ApiError(400, "empty_table", f"'{filename}' has no rows.",
                           "Upload a file containing data.")
        frames[Path(filename).stem.lower().replace(" ", "_")] = frame

    schema = build_schema(frames, name=name.lower().replace(" ", "_"), seed=seed)
    infer_derived_fields(frames, schema)
    schema.constraints = infer_constraints(frames, schema)
    project = STORE.create_project(name, schema, frames)
    return {"project": project.summary(), "schema": schema.model_dump()}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    return {"project": project.summary(), "schema": project.schema.model_dump(),
            "warnings": project.warnings}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    STORE.delete_project(project_id)
    return {"deleted": project_id}


@app.get("/api/projects/{project_id}/schema")
def get_schema(project_id: str) -> dict[str, Any]:
    return _project_or_404(project_id).schema.model_dump()


@app.patch("/api/projects/{project_id}/schema")
def patch_schema(project_id: str, patch: SchemaPatch) -> dict[str, Any]:
    """Apply user edits. Any change invalidates the fitted models."""
    project = _project_or_404(project_id)
    schema = project.schema

    if patch.seed is not None:
        schema.seed = patch.seed
    if patch.locale:
        schema.locale = patch.locale

    editable = {"semantic", "privacy", "pii", "null_rate", "nullable", "dtype"}
    for change in patch.columns:
        table = schema.table(str(change.get("table", "")))
        if table is None:
            continue
        column = table.column(str(change.get("column", "")))
        if column is None:
            continue
        for key, value in change.items():
            if key in editable:
                setattr(column, key, value)

    project.models.clear()
    project.touch()
    return schema.model_dump()


# --------------------------------------------------------------------------
# Business rules
# --------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/rules")
def list_rules(project_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    return {
        "rules": [c.model_dump() | {"label": c.label()} for c in project.schema.constraints],
        "results": project.rule_results,
    }


@app.post("/api/projects/{project_id}/rules")
def add_rule(project_id: str, rule: Constraint) -> dict[str, Any]:
    """Add a business rule. Rejected if it does not name a real column."""
    project = _project_or_404(project_id)
    table = project.schema.table(rule.table)
    if table is None:
        raise ApiError(400, "unknown_table", f"No table '{rule.table}' in this project.",
                       "Pick a table from the schema.")
    if rule.column and table.column(rule.column) is None:
        raise ApiError(400, "unknown_column",
                       f"'{rule.column}' is not a column of {rule.table}.",
                       "Pick a column that exists on that table.")
    other = rule.params.get("other_column")
    if rule.kind == "comparison" and (not other or table.column(str(other)) is None):
        raise ApiError(400, "unknown_column",
                       f"A comparison needs a second column on {rule.table}.",
                       "Set other_column to a column that exists on that table.")

    rule.source = "user"
    project.schema.constraints.append(rule)
    project.touch()
    return {"rule": rule.model_dump() | {"label": rule.label()},
            "total": len(project.schema.constraints)}


@app.patch("/api/projects/{project_id}/rules/{rule_id}")
def toggle_rule(project_id: str, rule_id: str, enabled: bool) -> dict[str, Any]:
    project = _project_or_404(project_id)
    rule = next((c for c in project.schema.constraints if c.id == rule_id), None)
    if rule is None:
        raise ApiError(404, "rule_not_found", f"No rule with id '{rule_id}'.",
                       "Reload the rule list.")
    rule.enabled = enabled
    project.touch()
    return {"rule": rule.model_dump() | {"label": rule.label()}}


@app.delete("/api/projects/{project_id}/rules/{rule_id}")
def delete_rule(project_id: str, rule_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    before = len(project.schema.constraints)
    project.schema.constraints = [c for c in project.schema.constraints if c.id != rule_id]
    if len(project.schema.constraints) == before:
        raise ApiError(404, "rule_not_found", f"No rule with id '{rule_id}'.",
                       "Reload the rule list.")
    project.touch()
    return {"deleted": rule_id, "total": len(project.schema.constraints)}


@app.post("/api/projects/{project_id}/rules/infer")
def reinfer_rules(project_id: str) -> dict[str, Any]:
    """Re-read the rules the sample data demonstrates, keeping user-authored ones."""
    project = _project_or_404(project_id)
    user_rules = [c for c in project.schema.constraints if c.source != "inferred"]
    inferred = infer_constraints(project.sources, project.schema)
    project.schema.constraints = inferred + user_rules
    project.touch()
    return {
        "inferred": len(inferred),
        "kept": len(user_rules),
        "rules": [c.model_dump() | {"label": c.label()} for c in project.schema.constraints],
    }


# --------------------------------------------------------------------------
# AI layer
# --------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/ai/infer-types")
def ai_infer_types(project_id: str, table: str | None = None) -> dict[str, Any]:
    """Propose semantic types, PII levels and privacy modes. Does not apply them."""
    project = _project_or_404(project_id)
    target = project.schema.table(table) if table else (
        project.schema.tables[0] if project.schema.tables else None
    )
    if target is None:
        raise ApiError(404, "table_not_found",
                       f"No table '{table}' in this project.",
                       "Pick a table from the schema.")

    src_df = _get_source_dataframe(project, target.name)
    sample = src_df if src_df is not None else pd.DataFrame()
    proposals = ai.infer_semantic_types(target, sample)
    return {
        "table": target.name,
        "mode": "live" if ai.ai_available() else "heuristic",
        "proposals": proposals,
        "ai_count": sum(1 for p in proposals if p.get("source") == "ai"),
        "pii_flagged": sum(1 for p in proposals if p.get("pii") == "direct"),
    }


@app.post("/api/projects/{project_id}/ai/infer-relations")
def ai_infer_relations(project_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    proposals = ai.infer_relationships(project.schema, project.sources)
    existing = {
        (fk.child_table, fk.child_column, fk.parent_table)
        for fk in project.schema.foreign_keys
    }
    for proposal in proposals:
        key = (proposal["child_table"], proposal["child_column"], proposal["parent_table"])
        proposal["already_applied"] = key in existing
    return {
        "mode": "live" if ai.ai_available() else "heuristic",
        "proposals": proposals,
        "new_count": sum(1 for p in proposals if not p["already_applied"]),
    }


@app.post("/api/projects/{project_id}/ai/edge-cases")
def ai_edge_cases(project_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    cases = ai.propose_edge_cases(project.schema)
    return {
        "mode": "live" if ai.ai_available() else "heuristic",
        "edge_cases": cases,
    }


class ApplyProposals(BaseModel):
    table: str
    columns: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/api/projects/{project_id}/ai/apply")
def ai_apply(project_id: str, request: ApplyProposals) -> dict[str, Any]:
    """Apply proposals the user accepted. This is the only thing that mutates."""
    project = _project_or_404(project_id)
    target = project.schema.table(request.table)
    if target is None:
        raise ApiError(404, "table_not_found",
                       f"No table '{request.table}' in this project.",
                       "Pick a table from the schema.")

    changed = ai.apply_column_proposals(target, request.columns)
    if changed:
        project.models.clear()   # the fitted models no longer match the schema
        project.touch()
    return {"table": target.name, "changed": changed,
            "schema": project.schema.model_dump()}


@app.post("/api/projects/{project_id}/ai/business-rules")
def ai_business_rules(project_id: str) -> dict[str, Any]:
    """Propose domain rules the schema alone cannot express.

    Returns proposals only. Nothing is enforced until the user adds a rule,
    because a wrong rule silently drops rows rather than failing loudly.
    """
    project = _project_or_404(project_id)
    proposals = ai.propose_business_rules(project.schema)
    existing = {(c.table, c.kind, c.column) for c in project.schema.constraints}
    for p in proposals:
        p["already_present"] = (p["table"], p["kind"], p["column"]) in existing
    return {
        "mode": "live" if ai.ai_available() else "heuristic",
        "proposals": proposals,
        "note": (
            "Proposals only, add the ones you want. Rules inferred directly "
            "from your sample data are already active."
            if proposals else
            "No API key set, so no rules were proposed. The rules inferred from "
            "your sample data are already active."
        ),
    }


@app.post("/api/ai/parse-query")
def ai_parse_query(q: str) -> dict[str, Any]:
    """Turn a plain-English statement request into executable filters."""
    return ai.parse_query(q)


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def _ensure_models(project: Project, seeds: SeedFactory) -> None:
    """Fit once and cache. Refitting per request makes the UI feel broken."""
    for table in project.schema.tables:
        if table.name in project.models:
            continue
        source = _get_source_dataframe(project, table.name)
        if source is None:
            continue
        project.models[table.name] = fit_table(table, source, seeds)


@app.post("/api/projects/{project_id}/preview")
def preview(project_id: str, request: PreviewRequest) -> dict[str, Any]:
    """Fast synchronous sample for the live canvas."""
    project = _project_or_404(project_id)
    seed = request.seed if request.seed is not None else project.schema.seed
    seeds = SeedFactory(seed)
    _ensure_models(project, seeds)

    table_name = request.table or (
        project.schema.tables[0].name if project.schema.tables else None
    )
    if table_name is None:
        raise ApiError(400, "no_tables", "This project has no tables.",
                       "Ingest a CSV first.")

    table = project.schema.table(table_name)
    model = project.models.get(table_name)
    if table is None or model is None:
        raise ApiError(404, "table_not_found",
                       f"No fitted model for table '{table_name}'.",
                       "Check the table name, or re-ingest the project.")

    frame = sample_table(
        model, request.rows, seeds,
        null_rate=request.null_rate, outlier_rate=request.outlier_rate,
    )
    # The preview runs the same business rules as a real generation. A canvas
    # that shows rows the generator would never produce is worse than no canvas.
    frame, rule_results = apply_constraints(
        frame, table, project.schema.constraints, seeds.stream(f"rules:{table_name}"),
        null_override=request.null_rate,
    )
    return {
        "table": table_name,
        "rules_applied": [r.model_dump() for r in rule_results if r.violations_before],
        "seed": seed,
        "rows": frame_to_records(frame),
        "columns": [
            {"name": c.name, "dtype": c.dtype, "semantic": c.semantic, "pii": c.pii}
            for c in table.columns
        ],
    }


def _run_generation(job_id: str, project_id: str, request: GenerateRequest) -> None:
    """Background worker. Never raises -- failures land on the job."""
    job = STORE.get_job(job_id)
    project = STORE.get_project(project_id)
    if job is None or project is None:
        return

    try:
        seed = request.seed if request.seed is not None else project.schema.seed
        project.schema.seed = seed
        seeds = SeedFactory(seed)

        job.advance("Reading schema", 5, f"{len(project.schema.tables)} tables")
        job.advance("Fitting distributions", 15, "Estimating marginals and correlations")
        _ensure_models(project, seeds)

        job.advance("Generating tables", 40, f"Target {request.rows:,} rows")
        frames, warnings, rule_results = generate_relational(
            project.schema, project.models, request.rows, seeds,
            null_rate=request.null_rate, outlier_rate=request.outlier_rate,
        )

        job.advance("Reconciling derived fields", 70, "Computing parent totals from children")
        job.advance("Validating integrity", 80, "Checking keys and constraints")
        integrity = check_integrity(project.schema, frames, request.null_rate)

        report: dict[str, Any] | None = None
        if request.validate_output:
            job.advance("Building trust report", 88, "Fidelity, utility and privacy")
            primary = project.schema.tables[0]
            source = _get_source_dataframe(project, primary.name)
            if source is not None:
                report = build_trust_report(
                    source, primary, SeedFactory(seed),
                    target=request.target_column, integrity=integrity,
                    # Score the data as it will be exported, after the business
                    # rules have run, not the raw sample nobody receives.
                    constraints=project.schema.constraints,
                )
            if report is None or not report.get("available"):
                report = {
                    "available": False,
                    "reason": (report or {}).get("reason", "No source data to validate against."),
                    "integrity": integrity,
                    "export_allowed": bool(integrity.get("passed")),
                }

        project.generated = frames
        project.report = report
        project.warnings = warnings
        project.rule_results = {
            name: [r.model_dump() for r in results]
            for name, results in rule_results.items()
        }
        project.touch()

        job.finish(
            rows={name: len(frame) for name, frame in frames.items()},
            total_rows=sum(len(f) for f in frames.values()),
            integrity=integrity,
            warnings=warnings,
            rules={
                name: [r.model_dump() for r in results]
                for name, results in rule_results.items()
            },
            export_allowed=(report or {}).get("export_allowed", bool(integrity.get("passed"))),
            seed=seed,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced on the job, not the process
        traceback.print_exc()
        job.fail("generation_failed", str(exc) or exc.__class__.__name__,
                 "Check the schema for unsupported column types, then try a smaller row count.")


@app.post("/api/projects/{project_id}/generate")
def generate(
    project_id: str, request: GenerateRequest, background: BackgroundTasks
) -> dict[str, Any]:
    project = _project_or_404(project_id)
    if not project.schema.tables:
        raise ApiError(400, "no_tables", "This project has no tables.",
                       "Ingest a CSV first.")
    job = STORE.create_job(project_id, "generate")
    background.add_task(_run_generation, job.id, project_id, request)
    return {"job": job.to_dict()}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = STORE.get_job(job_id)
    if job is None:
        raise ApiError(404, "job_not_found", f"No job with id '{job_id}'.",
                       "Start a new generation.")
    return job.to_dict()


@app.get("/api/projects/{project_id}/jobs")
def project_jobs(project_id: str) -> dict[str, Any]:
    _project_or_404(project_id)
    return {"jobs": [j.to_dict() for j in STORE.list_jobs(project_id)]}


# --------------------------------------------------------------------------
# Output and validation
# --------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/data/{table}")
def get_data(
    project_id: str,
    table: str,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    project = _project_or_404(project_id)
    frame = project.generated.get(table)
    if frame is None:
        raise ApiError(404, "no_output",
                       f"No generated data for table '{table}'.",
                       "Run a generation first.")
    window = frame.iloc[offset:offset + limit]
    return {
        "table": table,
        "total_rows": len(frame),
        "offset": offset,
        "rows": frame_to_records(window),
        "columns": list(map(str, frame.columns)),
    }


@app.get("/api/projects/{project_id}/report")
def get_report(project_id: str) -> dict[str, Any]:
    project = _project_or_404(project_id)
    if project.report is None:
        raise ApiError(404, "no_report", "This project has no trust report yet.",
                       "Run a generation with validation enabled.")
    return project.report


@app.post("/api/projects/{project_id}/validate")
def revalidate(project_id: str, target_column: str | None = None) -> dict[str, Any]:
    """Re-run the trust report without regenerating the data."""
    project = _project_or_404(project_id)
    if not project.schema.tables:
        raise ApiError(400, "no_tables", "This project has no tables.", "Ingest a CSV first.")

    primary = project.schema.tables[0]
    source = _get_source_dataframe(project, primary.name)
    if source is None:
        raise ApiError(400, "no_source",
                       "The original data is no longer in memory.",
                       "Re-ingest the project, then validate again.")

    integrity = (
        check_integrity(project.schema, project.generated)
        if project.generated else {"passed": True, "score": 100.0}
    )
    report = build_trust_report(
        source, primary, SeedFactory(project.schema.seed),
        target=target_column, integrity=integrity,
        constraints=project.schema.constraints,
    )
    project.report = report
    project.touch()
    return report


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------

def _statement_filter(query: str | None) -> docs.StatementQuery | None:
    """One parser for every statement path.

    The preview used the AI parser and the printable path used the regex
    fallback, so with a key set the two could disagree -- a filter honoured on
    screen and ignored in the document the user downloads.
    """
    if not query:
        return None
    parsed = ai.parse_query(query)
    return docs.StatementQuery(
        days=parsed.get("days"),
        min_balance=parsed.get("min_balance"),
        max_balance=parsed.get("max_balance"),
        min_amount=parsed.get("min_amount"),
        direction=parsed.get("direction"),
        description_contains=parsed.get("description_contains"),
    )


@app.post("/api/projects/{project_id}/documents")
def render_documents(project_id: str, request: DocumentRequest) -> dict[str, Any]:
    project = _project_or_404(project_id)
    if request.region not in docs.REGIONS:
        raise ApiError(400, "unknown_region", f"'{request.region}' is not a known region.",
                       "Choose one of: " + ", ".join(docs.REGIONS))

    seeds = SeedFactory(project.schema.seed)
    frames = project.generated or project.sources

    interpretation = None
    if request.kind == "invoice":
        built = docs.build_invoices(
            request.count, seeds, region_code=request.region,
            frames=frames, foreign_keys=project.schema.foreign_keys,
        )
        payload = [i.to_dict() for i in built]
        reconciled = sum(1 for i in built if i.reconciles())
        source_used = docs.find_invoice_source(frames, project.schema.foreign_keys) is not None
    else:
        query = _statement_filter(request.query)
        if request.query:
            interpretation = ai.parse_query(request.query).get("interpretation")
        built = docs.build_statements(
            request.count, seeds, region_code=request.region,
            rows_per_statement=request.rows_per_statement,
            query=query, frames=frames,
        )
        payload = [s.to_dict() for s in built]
        reconciled = sum(1 for s in built if s.reconciles())
        source_used = False

    return {
        "kind": request.kind,
        "region": request.region,
        "count": len(payload),
        "reconciled": reconciled,
        "all_reconciled": reconciled == len(payload),
        "from_generated_data": source_used,
        "query": request.query,
        "interpretation": interpretation,
        "documents": payload,
    }


@app.get("/api/projects/{project_id}/documents/{index}/html", response_class=HTMLResponse)
def render_document_html(
    project_id: str,
    index: int,
    kind: Literal["invoice", "statement"] = "invoice",
    region: str = "EU",
    count: int = Query(default=10, ge=1, le=MAX_DOCUMENTS),
    query: str | None = None,
) -> HTMLResponse:
    """One rendered document, ready to print to PDF from the browser."""
    project = _project_or_404(project_id)
    seeds = SeedFactory(project.schema.seed)
    frames = project.generated or project.sources

    if kind == "invoice":
        built = docs.build_invoices(
            count, seeds, region_code=region,
            frames=frames, foreign_keys=project.schema.foreign_keys,
        )
        if not 0 <= index < len(built):
            raise ApiError(404, "document_not_found",
                           f"Document {index} does not exist (generated {len(built)}).",
                           "Request an index within range.")
        return HTMLResponse(docs.render_invoice(built[index]))

    parsed = _statement_filter(query)
    statements = docs.build_statements(
        count, seeds, region_code=region, query=parsed, frames=frames
    )
    if not 0 <= index < len(statements):
        raise ApiError(404, "document_not_found",
                       f"Document {index} does not exist (generated {len(statements)}).",
                       "Widen the query filter or request a lower index.")
    return HTMLResponse(docs.render_statement(statements[index]))


@app.get("/api/projects/{project_id}/documents/bundle")
def download_documents(
    project_id: str,
    kind: Literal["invoice", "statement"] = "invoice",
    region: str = "EU",
    count: int = Query(default=25, ge=1, le=MAX_DOCUMENTS),
    query: str | None = None,
) -> Response:
    """All documents as a zip of printable HTML files."""
    import zipfile

    project = _project_or_404(project_id)
    seeds = SeedFactory(project.schema.seed)
    frames = project.generated or project.sources

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if kind == "invoice":
            for invoice in docs.build_invoices(
                count, seeds, region_code=region,
                frames=frames, foreign_keys=project.schema.foreign_keys,
            ):
                archive.writestr(f"{invoice.number}.html", docs.render_invoice(invoice))
        else:
            parsed = _statement_filter(query)
            for i, statement in enumerate(docs.build_statements(
                count, seeds, region_code=region, query=parsed, frames=frames
            )):
                name = statement.account_number.replace("-", "")
                archive.writestr(f"statement-{i + 1:03d}-{name}.html",
                                 docs.render_statement(statement))

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{kind}s-{region}.zip"'},
    )


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/export")
def export(
    project_id: str,
    fmt: str = Query(default="csv"),
    include_schema: bool = True,
    include_report: bool = True,
    force: bool = False,
) -> Response:
    """Export is gated on the integrity check.

    A platform that will happily hand you broken synthetic data is worse than no
    platform, so this refuses rather than warns. `force` exists only so the
    refusal itself can be demonstrated and then bypassed deliberately.
    """
    project = _project_or_404(project_id)
    if not project.generated:
        raise ApiError(409, "no_output", "This project has not generated any data yet.",
                       "Run a generation, then export.")

    report = project.report or {}
    allowed = report.get("export_allowed", True)
    if not allowed and not force:
        failed = [k for k, v in (report.get("gates") or {}).items() if not v]
        raise ApiError(
            409, "integrity_gate_failed",
            "Export blocked: " + (", ".join(failed) or "the trust report did not pass") + ".",
            "Fix the schema or regenerate with a different seed, then export again.",
        )

    try:
        payload, media, filename = build_export(
            fmt, project.generated, project.schema, project.report,
            include_schema=include_schema, include_report=include_report,
        )
    except ExportError as exc:
        raise ApiError(400, exc.code, exc.message, exc.remedy) from exc

    return Response(
        content=payload,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------
# Static frontend
# --------------------------------------------------------------------------

if WEB_DIR.exists():
    @app.middleware("http")
    async def spa_fallback(request: Any, call_next: Any) -> Any:
        response = await call_next(request)
        if response.status_code == 404 and request.method == "GET" and not request.url.path.startswith("/api"):
            index_path = WEB_DIR / "index.html"
            if index_path.exists():
                return HTMLResponse(index_path.read_text(encoding="utf-8"))
        return response

    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
else:
    @app.get("/")
    def placeholder() -> HTMLResponse:
        return HTMLResponse(
            "<h1>DataSeed API</h1>"
            "<p>The API is running. Open <a href='/docs'>/docs</a> for the interactive reference.</p>"
            "<p>Drop the Stitch HTML into <code>web/index.html</code> and it will be served here.</p>"
        )
