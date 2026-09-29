"""Export formats.

Everything returns bytes plus a media type and filename, so the route layer
stays a one-liner and adding a format never touches the API.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from .schema import SchemaIR, frame_to_records

# Postgres-flavoured types. Chosen over a generic dialect because the deck
# promises a "relational DB dump" and a restore has to actually work.
_SQL_TYPES = {
    "int": "BIGINT", "float": "DOUBLE PRECISION", "str": "TEXT",
    "bool": "BOOLEAN", "date": "DATE", "datetime": "TIMESTAMP",
}


class ExportError(RuntimeError):
    def __init__(self, code: str, message: str, remedy: str) -> None:
        super().__init__(message)
        self.code, self.message, self.remedy = code, message, remedy


def available_formats() -> list[dict[str, Any]]:
    formats = [
        {"id": "csv", "label": "CSV (zip)", "media": "application/zip"},
        {"id": "json", "label": "JSON", "media": "application/json"},
        {"id": "sql", "label": "SQL dump", "media": "application/sql"},
        {"id": "excel", "label": "Excel workbook", "media": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ]
    try:
        import pyarrow  # noqa: F401
        formats.insert(2, {"id": "parquet", "label": "Parquet (zip)", "media": "application/zip"})
    except ImportError:
        pass
    return formats


def _sql_literal(value: Any) -> str:
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "NULL"
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float, np.integer, np.floating)):
        return repr(float(value)) if isinstance(value, (float, np.floating)) else str(int(value))
    if isinstance(value, pd.Timestamp):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"
    return "'" + str(value).replace("'", "''") + "'"


def to_sql(
    frames: dict[str, pd.DataFrame], schema: SchemaIR, *, batch: int = 500
) -> bytes:
    """A restorable Postgres dump: DDL, data, then constraints.

    Foreign keys are added at the end rather than inline so the file restores in
    any table order. If the referential integrity is wrong, the restore fails
    loudly -- which is the point.
    """
    from .relational import topological_order

    out = io.StringIO()
    out.write("-- DataSeed synthetic data export\n")
    out.write(f"-- generated {datetime.utcnow().isoformat(timespec='seconds')}Z\n")
    out.write(f"-- project {schema.name} | seed {schema.seed}\n")
    out.write("-- Reproduce exactly: POST /projects/{id}/generate with this seed.\n\n")
    out.write("BEGIN;\n\n")

    order, _ = topological_order(schema)
    ordered = [n for n in order if n in frames] + [n for n in frames if n not in order]

    for name in reversed(ordered):
        out.write(f'DROP TABLE IF EXISTS "{name}" CASCADE;\n')
    out.write("\n")

    for name in ordered:
        table = schema.table(name)
        frame = frames[name]
        if table is None:
            continue
        columns = []
        for column in table.columns:
            sql_type = _SQL_TYPES.get(column.dtype, "TEXT")
            parts = [f'  "{column.name}" {sql_type}']
            if column.name == table.primary_key:
                parts.append("PRIMARY KEY")
            elif column.unique:
                parts.append("UNIQUE")
            columns.append(" ".join(parts))
        out.write(f'CREATE TABLE "{name}" (\n' + ",\n".join(columns) + "\n);\n\n")

    for name in ordered:
        frame = frames[name]
        if frame.empty:
            continue
        column_list = ", ".join(f'"{c}"' for c in frame.columns)
        records = frame.to_dict(orient="records")
        for start in range(0, len(records), batch):
            chunk = records[start:start + batch]
            out.write(f'INSERT INTO "{name}" ({column_list}) VALUES\n')
            rows = [
                "  (" + ", ".join(_sql_literal(row[c]) for c in frame.columns) + ")"
                for row in chunk
            ]
            out.write(",\n".join(rows) + ";\n")
        out.write("\n")

    for fk in schema.foreign_keys:
        if fk.child_table not in frames or fk.parent_table not in frames:
            continue
        out.write(
            f'ALTER TABLE "{fk.child_table}" ADD CONSTRAINT '
            f'"fk_{fk.child_table}_{fk.child_column}" FOREIGN KEY ("{fk.child_column}") '
            f'REFERENCES "{fk.parent_table}" ("{fk.parent_column}");\n'
        )

    out.write("\nCOMMIT;\n")
    return out.getvalue().encode("utf-8")


def to_csv_zip(frames: dict[str, pd.DataFrame], schema: SchemaIR, extras: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, frame in frames.items():
            archive.writestr(f"{name}.csv", frame.to_csv(index=False))
        for filename, content in extras.items():
            archive.writestr(filename, content)
    return buffer.getvalue()


def to_parquet_zip(frames: dict[str, pd.DataFrame], extras: dict[str, str]) -> bytes:
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        raise ExportError(
            "parquet_unavailable",
            "Parquet export needs the pyarrow package.",
            "Run `pip install pyarrow`, or export as CSV or Parquet's alternative formats.",
        ) from exc

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, frame in frames.items():
            table_buffer = io.BytesIO()
            frame.to_parquet(table_buffer, index=False)
            archive.writestr(f"{name}.parquet", table_buffer.getvalue())
        for filename, content in extras.items():
            archive.writestr(filename, content)
    return buffer.getvalue()


def to_json(frames: dict[str, pd.DataFrame], schema: SchemaIR, report: Any) -> bytes:
    payload = {
        "project": schema.name,
        "seed": schema.seed,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "tables": {name: frame_to_records(frame) for name, frame in frames.items()},
        "row_counts": {name: len(frame) for name, frame in frames.items()},
        "trust_report": report,
    }
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


def to_excel(frames: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for name, frame in frames.items():
                frame.to_excel(writer, sheet_name=name[:31], index=False)
    except ImportError as exc:
        raise ExportError(
            "excel_unavailable",
            "Excel export needs the openpyxl package.",
            "Run `pip install openpyxl`, or export as CSV instead.",
        ) from exc
    return buffer.getvalue()


def build_export(
    fmt: str,
    frames: dict[str, pd.DataFrame],
    schema: SchemaIR,
    report: Any = None,
    *,
    include_schema: bool = True,
    include_report: bool = True,
) -> tuple[bytes, str, str]:
    """Return (payload, media_type, filename)."""
    if not frames:
        raise ExportError(
            "no_output",
            "This project has not generated any data yet.",
            "Run a generation first, then export.",
        )

    extras: dict[str, str] = {}
    if include_schema:
        extras["schema.json"] = schema.model_dump_json(indent=2)
    if include_report and report:
        extras["trust_report.json"] = json.dumps(report, indent=2, default=str)

    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    base = f"{schema.name}-{stamp}"

    if fmt == "csv":
        return to_csv_zip(frames, schema, extras), "application/zip", f"{base}-csv.zip"
    if fmt == "parquet":
        return to_parquet_zip(frames, extras), "application/zip", f"{base}-parquet.zip"
    if fmt == "json":
        return to_json(frames, schema, report), "application/json", f"{base}.json"
    if fmt == "sql":
        return to_sql(frames, schema), "application/sql", f"{base}.sql"
    if fmt == "excel":
        return (
            to_excel(frames),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"{base}.xlsx",
        )

    raise ExportError(
        "unknown_format",
        f"'{fmt}' is not a supported export format.",
        "Choose one of: " + ", ".join(f["id"] for f in available_formats()),
    )
