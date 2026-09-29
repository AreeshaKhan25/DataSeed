"""In-memory project and job registry.

Deliberately not a database. A hackathon demo does not need durable state, and
every extra moving part is another thing that can fail on stage. Restarting the
server clears everything and reseeds the demo project.

The source frames are held in memory because the trust report has to refit a
generator on a training split of the real data. They are never written to disk
and never leave the process.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .engine import TableModel
from .schema import SchemaIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Project:
    id: str
    name: str
    schema: SchemaIR
    sources: dict[str, pd.DataFrame] = field(default_factory=dict)
    models: dict[str, TableModel] = field(default_factory=dict)
    generated: dict[str, pd.DataFrame] = field(default_factory=dict)
    report: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    rule_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tables": [
                {
                    "name": t.name,
                    "columns": len(t.columns),
                    "source_rows": t.row_count,
                    "generated_rows": len(self.generated.get(t.name, [])),
                    "primary_key": t.primary_key,
                }
                for t in self.schema.tables
            ],
            "foreign_keys": len(self.schema.foreign_keys),
            "seed": self.schema.seed,
            "has_output": bool(self.generated),
            "has_report": self.report is not None,
            "scores": {
                "integrity": (self.report or {}).get("integrity", {}).get("score"),
                "fidelity": (self.report or {}).get("fidelity", {}).get("score"),
                "utility": (self.report or {}).get("utility", {}).get("score"),
                "privacy": (self.report or {}).get("privacy", {}).get("score"),
                "overall": (self.report or {}).get("overall"),
            } if self.report else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Job:
    id: str
    project_id: str
    kind: str
    status: str = "queued"  # queued | running | done | failed
    phase: str = "Queued"
    percent: int = 0
    message: str = ""
    error: dict[str, str] | None = None
    result: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None

    def advance(self, phase: str, percent: int, message: str = "") -> None:
        self.status = "running"
        self.phase = phase
        self.percent = max(0, min(100, percent))
        self.message = message

    def finish(self, **result: Any) -> None:
        self.status = "done"
        self.phase = "Complete"
        self.percent = 100
        self.result = result
        self.finished_at = _now()

    def fail(self, code: str, message: str, remedy: str) -> None:
        self.status = "failed"
        self.phase = "Failed"
        self.error = {"code": code, "message": message, "remedy": remedy}
        self.finished_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "project_id": self.project_id, "kind": self.kind,
            "status": self.status, "phase": self.phase, "percent": self.percent,
            "message": self.message, "error": self.error, "result": self.result,
            "started_at": self.started_at, "finished_at": self.finished_at,
        }


class Store:
    """Thread-safe because generation runs on a background worker."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()

    # -- projects ---------------------------------------------------------
    def create_project(
        self, name: str, schema: SchemaIR, sources: dict[str, pd.DataFrame]
    ) -> Project:
        project = Project(id=uuid.uuid4().hex[:12], name=name, schema=schema, sources=sources)
        with self._lock:
            self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        with self._lock:
            return self._projects.get(project_id)

    def list_projects(self) -> list[Project]:
        with self._lock:
            return sorted(self._projects.values(), key=lambda p: p.updated_at, reverse=True)

    def delete_project(self, project_id: str) -> bool:
        with self._lock:
            return self._projects.pop(project_id, None) is not None

    # -- jobs -------------------------------------------------------------
    def create_job(self, project_id: str, kind: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], project_id=project_id, kind=kind)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, project_id: str | None = None) -> list[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        if project_id:
            jobs = [j for j in jobs if j.project_id == project_id]
        return sorted(jobs, key=lambda j: j.started_at, reverse=True)


STORE = Store()
