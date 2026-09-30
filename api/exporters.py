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

from .schema import SchemaIR, Table, frame_to_records

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
    """The formats this installation can actually produce, right now.

    Parquet was guarded by an import check and Excel was not, so a deployment
    without openpyxl still advertised "Excel workbook". The interface builds its
    format list from this, so it offered a choice that answered with an error,
    and because the download is an ordinary link the browser saved that error as
    the file. Never advertise what cannot be delivered.
    """
    formats = [
        {"id": "csv", "label": "CSV (zip)", "media": "application/zip"},
        {"id": "json", "label": "JSON", "media": "application/json"},
        {"id": "sql", "label": "SQL dump", "media": "application/sql"},
    ]
    try:
        import pyarrow  # noqa: F401
        formats.insert(2, {"id": "parquet", "label": "Parquet (zip)", "media": "application/zip"})
    except ImportError:
        pass
    try:
        import openpyxl  # noqa: F401
        formats.append({
            "id": "excel",
            "label": "Excel workbook",
            "media": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
    except ImportError:
        pass
    return formats


def clean_frame_for_export(frame: pd.DataFrame, table: Table | None = None) -> pd.DataFrame:
    """Format integers, dates, floats, and strings cleanly before output.

    Prevents floating point artifacts (e.g. 12.0 for integer IDs), unformatted
    timestamps, or raw string representations in exported CSV/SQL/Excel.
    """
    clean = frame.copy()
    if table:
        for col_def in table.columns:
            col = col_def.name
            if col not in clean.columns:
                continue
            if col_def.dtype == "int":
                s = pd.to_numeric(clean[col], errors="coerce")
                if not s.isnull().any():
                    clean[col] = s.astype("int64")
                else:
                    clean[col] = s.astype("Int64")
            elif col_def.dtype == "float":
                clean[col] = pd.to_numeric(clean[col], errors="coerce").round(2)
            elif col_def.dtype in ("date", "datetime"):
                clean[col] = pd.to_datetime(clean[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").fillna("")
            elif col_def.dtype == "bool":
                clean[col] = clean[col].astype("boolean")
    else:
        for col in clean.columns:
            if pd.api.types.is_float_dtype(clean[col]):
                # If all non-null floats are integers, convert to int
                non_null = clean[col].dropna()
                if not non_null.empty and (non_null % 1 == 0).all():
                    clean[col] = clean[col].astype("Int64")

    return clean


def _sql_literal(value: Any) -> str:
    if value is None or pd.isna(value) or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return "NULL"
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if float(value).is_integer():
            return str(int(value))
        return repr(float(value))
    if isinstance(value, pd.Timestamp):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"
    return "'" + str(value).replace("'", "''") + "'"


def to_sql(
    frames: dict[str, pd.DataFrame], schema: SchemaIR, *, batch: int = 500
) -> bytes:
    """A restorable Postgres dump: DDL, data, then constraints."""
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

    # Clean frames to eliminate garbage values, float IDs, or precision overflow
    cleaned_frames = {
        name: clean_frame_for_export(frame, schema.table(name))
        for name, frame in frames.items()
    }

    extras: dict[str, str] = {}
    if include_schema:
        extras["schema.json"] = schema.model_dump_json(indent=2)
    if include_report and report:
        extras["trust_report.json"] = json.dumps(report, indent=2, default=str)

    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    base = f"{schema.name}-{stamp}"

    if fmt == "csv":
        return to_csv_zip(cleaned_frames, schema, extras), "application/zip", f"{base}-csv.zip"
    if fmt == "parquet":
        return to_parquet_zip(cleaned_frames, extras), "application/zip", f"{base}-parquet.zip"
    if fmt == "json":
        return to_json(cleaned_frames, schema, report), "application/json", f"{base}.json"
    if fmt == "sql":
        return to_sql(cleaned_frames, schema), "application/sql", f"{base}.sql"
    if fmt == "excel":
        return (
            to_excel(cleaned_frames),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"{base}.xlsx",
        )

    raise ExportError(
        "unknown_format",
        f"'{fmt}' is not a supported export format.",
        "Choose one of: " + ", ".join(f["id"] for f in available_formats()),
    )
