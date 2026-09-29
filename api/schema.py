"""Schema IR, the single object every engine reads.

Nothing downstream of the profiler ever touches the uploaded file again.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

DType = Literal["int", "float", "str", "bool", "date", "datetime"]
Privacy = Literal["passthrough", "mask", "hash", "noise", "synthesize"]
PII = Literal["none", "quasi", "direct"]

# Semantic detection patterns, applied to the column NAME first and then to
# sample VALUES. Deliberately conservative: a wrong guess here is visible to the
# user in the schema editor, but a false positive on PII is worse than a miss.
# Order matters: the first pattern that matches wins, so the identifying
# patterns must come before the broader geographic ones. `national_id` contains
# "nation", and classifying a government ID as a country would drop it from
# direct PII to quasi, which is the difference between regenerating it and
# treating it as a low risk attribute.
_NAME_PATTERNS: list[tuple[str, str]] = [
    (r"e?mail", "email"),
    (r"(phone|mobile|tel)", "phone"),
    (r"(ssn|nin|national_?id|nationalid|tax_?id|passport|nhs_?number)", "national_id"),
    (r"(iban|account_?no|account_?number|sort_?code|card_?number)", "iban"),
    (r"(first_?name|last_?name|full_?name|customer_?name|^name$)", "person_name"),
    (r"(address|street|addr)", "address"),
    (r"(city|town)", "city"),
    (r"(country|nationality)", "country"),
    (r"(zip|postal|post_?code)", "postcode"),
    (r"(company|organisation|organization|employer)", "company"),
    (r"(sku|product_?code|item_?code)", "sku"),
    (r"(price|amount|total|balance|cost|salary|revenue|fee)", "currency"),
    (r"(url|website|link)", "url"),
    (r"(lat|latitude)", "latitude"),
    (r"(lon|lng|longitude)", "longitude"),
    (r"(notes?|comment|description|summary|review|feedback|body|text)", "free_text"),
    (r"_id$|^id$", "identifier"),
]

_VALUE_PATTERNS: list[tuple[str, str]] = [
    (r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", "email"),
    (r"^https?://", "url"),
    (r"^\+?[\d\s().-]{7,}$", "phone"),
]

_DIRECT_PII = {"email", "phone", "person_name", "address", "national_id", "iban"}
_QUASI_PII = {"city", "country", "postcode", "company", "free_text", "latitude", "longitude"}


class ColumnStats(BaseModel):
    """Everything the generator needs. The source rows are never kept."""

    count: int = 0
    null_rate: float = 0.0
    # numeric / datetime
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    std: float | None = None
    # categorical
    categories: list[str] = Field(default_factory=list)
    frequencies: list[float] = Field(default_factory=list)
    n_unique: int = 0
    is_constant: bool = False


class Column(BaseModel):
    name: str
    dtype: DType = "str"
    semantic: str = "unknown"
    nullable: bool = False
    null_rate: float = 0.0
    unique: bool = False
    pii: PII = "none"
    privacy: Privacy = "synthesize"
    ai_inferred: bool = False
    stats: ColumnStats = Field(default_factory=ColumnStats)
    sample: str | None = None


class DerivedField(BaseModel):
    """A parent column computed from its children after generation.

    `agg` is applied to `expr` evaluated per child row. This is why parent
    aggregates reconcile: they are never generated, only computed.
    """

    column: str
    child_table: str
    agg: Literal["sum", "count", "mean", "max", "min"] = "sum"
    expr: str | None = None  # pandas eval expression over the child frame


class Table(BaseModel):
    name: str
    columns: list[Column] = Field(default_factory=list)
    primary_key: str | None = None
    row_count: int = 0
    derived: list[DerivedField] = Field(default_factory=list)
    # Set when the table is a link table joining two parents many-to-many.
    # Holds the two foreign-key column names, in order.
    junction: list[str] = Field(default_factory=list)

    @property
    def is_junction(self) -> bool:
        return len(self.junction) == 2

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


class ForeignKey(BaseModel):
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    cardinality: Literal["1:1", "1:N", "N:N"] = "1:N"
    # empirical children-per-parent distribution, as counts -> probability
    count_values: list[int] = Field(default_factory=list)
    count_probs: list[float] = Field(default_factory=list)
    nullable: bool = False
    ai_inferred: bool = False


Kind = Literal[
    "range",        # column stays within [minimum, maximum]
    "comparison",   # column <op> other_column
    "computed",     # column = <expression over other columns>
    "enum",         # column drawn from a fixed set
    "regex",        # column matches a pattern
    "not_null",     # column is never missing
    "unique",       # column has no repeats
    "conditional",  # when <col> <op> <value>, then <target> is null / not null
    "offset",       # column = another column plus an observed gap
]

OPERATORS: dict[str, Any] = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class Constraint(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    table: str
    kind: Kind
    column: str = ""
    enabled: bool = True
    description: str = ""
    source: Literal["inferred", "user", "ai"] = "user"
    params: dict[str, Any] = Field(default_factory=dict)

    def label(self) -> str:
        if self.description:
            return self.description
        p = self.params
        if self.kind == "range":
            lo, hi = p.get("minimum"), p.get("maximum")
            if lo is not None and hi is not None:
                return f"{self.column} between {lo:g} and {hi:g}"
            if lo is not None:
                return f"{self.column} at least {lo:g}"
            return f"{self.column} at most {hi:g}" if hi is not None else self.column
        if self.kind == "comparison":
            return f"{self.column} {p.get('operator', '>=')} {p.get('other_column', '')}"
        if self.kind == "computed":
            return f"{self.column} = {p.get('expression', '')}"
        if self.kind == "enum":
            return f"{self.column} in {{{', '.join(map(str, p.get('allowed', [])[:4]))}…}}"
        if self.kind == "regex":
            return f"{self.column} matches {p.get('pattern', '')}"
        if self.kind == "not_null":
            return f"{self.column} is never null"
        if self.kind == "unique":
            return f"{self.column} has no duplicates"
        if self.kind == "conditional":
            return (
                f"when {p.get('when_column')} {p.get('when_operator', '==')} "
                f"{p.get('when_value')}, {self.column} is "
                f"{'null' if p.get('then_null', True) else 'set'}"
            )
        return self.kind


class SchemaIR(BaseModel):
    name: str = "project"
    tables: list[Table] = Field(default_factory=list)
    foreign_keys: list[ForeignKey] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    seed: int = 42
    locale: str = "en_US"

    def table(self, name: str) -> Table | None:
        return next((t for t in self.tables if t.name == name), None)


# --------------------------------------------------------------------------
# Profiling
# --------------------------------------------------------------------------

def _infer_semantic(name: str, series: pd.Series, dtype: DType) -> str:
    lowered = name.lower()
    for pattern, semantic in _NAME_PATTERNS:
        if re.search(pattern, lowered):
            # a name-based "currency" guess only holds for numerics
            if semantic == "currency" and dtype not in ("int", "float"):
                continue
            if semantic == "identifier" and dtype == "str":
                return "identifier"
            return semantic

    if dtype == "str":
        sample = series.dropna().astype(str).head(20)
        for pattern, semantic in _VALUE_PATTERNS:
            if len(sample) and sample.str.match(pattern, case=False).mean() > 0.8:
                return semantic
        if series.nunique(dropna=True) <= max(20, int(0.05 * max(len(series), 1))):
            return "category"
        if sample.str.len().mean() > 40 if len(sample) else False:
            return "free_text"
    if dtype in ("date", "datetime"):
        return "date"
    if dtype in ("int", "float"):
        return "numeric"
    return "unknown"


def _infer_dtype(series: pd.Series) -> tuple[DType, pd.Series]:
    """Return the IR dtype plus the series coerced to it."""
    if pd.api.types.is_bool_dtype(series):
        return "bool", series
    if pd.api.types.is_integer_dtype(series):
        return "int", series
    if pd.api.types.is_float_dtype(series):
        return "float", series
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime", series

    non_null = series.dropna()
    if non_null.empty:
        return "str", series

    # numeric-looking strings
    coerced = pd.to_numeric(non_null, errors="coerce")
    if coerced.notna().mean() > 0.95:
        full = pd.to_numeric(series, errors="coerce")
        if (coerced.dropna() % 1 == 0).all():
            return "int", full
        return "float", full

    # date-looking strings. `format="mixed"` keeps pandas from warning on
    # heterogeneous input, and errors="coerce" means a stray value can't throw.
    try:
        parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        parsed = pd.Series([pd.NaT] * len(non_null), index=non_null.index)
    if parsed.notna().mean() > 0.9:
        full = pd.to_datetime(series, errors="coerce", format="mixed")
        has_time = bool((full.dt.hour.fillna(0) != 0).any() or (full.dt.minute.fillna(0) != 0).any())
        return ("datetime" if has_time else "date"), full

    return "str", series


def _profile_column(name: str, series: pd.Series) -> Column:
    dtype, coerced = _infer_dtype(series)
    total = len(coerced)
    null_rate = float(coerced.isna().mean()) if total else 0.0
    non_null = coerced.dropna()

    stats = ColumnStats(
        count=total,
        null_rate=round(null_rate, 4),
        n_unique=int(non_null.nunique()) if len(non_null) else 0,
        is_constant=bool(len(non_null) and non_null.nunique() == 1),
    )

    if dtype in ("int", "float"):
        stats.minimum = float(non_null.min()) if len(non_null) else None
        stats.maximum = float(non_null.max()) if len(non_null) else None
        stats.mean = float(non_null.mean()) if len(non_null) else None
        stats.std = float(non_null.std(ddof=0)) if len(non_null) > 1 else 0.0
    elif dtype in ("date", "datetime"):
        as_int = non_null.astype("int64") // 10**9 if len(non_null) else pd.Series(dtype="int64")
        stats.minimum = float(as_int.min()) if len(as_int) else None
        stats.maximum = float(as_int.max()) if len(as_int) else None
        stats.mean = float(as_int.mean()) if len(as_int) else None
        stats.std = float(as_int.std(ddof=0)) if len(as_int) > 1 else 0.0
    else:
        counts = non_null.astype(str).value_counts(normalize=True)
        # Cap the category list so a high-cardinality free-text column doesn't
        # blow up the IR. Anything beyond the cap is regenerated, not sampled.
        top = counts.head(200)
        stats.categories = [str(v) for v in top.index]
        stats.frequencies = [float(v) for v in top.to_numpy()]

    semantic = _infer_semantic(name, non_null if len(non_null) else series, dtype)
    is_unique = bool(total and len(non_null) == total and stats.n_unique == total)

    pii: PII = "none"
    if semantic in _DIRECT_PII:
        pii = "direct"
    elif semantic in _QUASI_PII:
        pii = "quasi"

    sample: str | None = None
    if len(non_null):
        raw = non_null.iloc[0]
        sample = raw.strftime("%Y-%m-%d") if isinstance(raw, pd.Timestamp) else str(raw)

    return Column(
        name=name,
        dtype=dtype,
        semantic=semantic,
        nullable=null_rate > 0,
        null_rate=round(null_rate, 4),
        unique=is_unique,
        pii=pii,
        privacy="synthesize",
        stats=stats,
        sample=sample,
    )


def profile_table(name: str, df: pd.DataFrame) -> Table:
    """Build a Table IR from a DataFrame. The frame itself is not retained."""
    columns = [_profile_column(str(c), df[c]) for c in df.columns]

    primary_key = None
    for col in columns:
        lowered = col.name.lower()
        if col.unique and (lowered == "id" or lowered.endswith("_id")):
            primary_key = col.name
            break
    if primary_key is None:
        primary_key = next((c.name for c in columns if c.unique), None)

    return Table(name=name, columns=columns, primary_key=primary_key, row_count=len(df))


def detect_foreign_keys(
    tables: dict[str, pd.DataFrame], schema: SchemaIR
) -> list[ForeignKey]:
    """Heuristic FK detection: name match plus value containment.

    A column is a FK when it is named like a parent's PK and its values are
    mostly contained in that parent's PK values. Both tests must pass, which
    keeps unrelated same-named columns from being linked.
    """
    found: list[ForeignKey] = []
    pks = {
        t.name: t.primary_key
        for t in schema.tables
        if t.primary_key is not None
    }

    for child_name, child_df in tables.items():
        for col in child_df.columns:
            col_str = str(col)
            for parent_name, parent_pk in pks.items():
                if parent_name == child_name or parent_pk is None:
                    continue
                if col_str != parent_pk:
                    continue
                if parent_pk not in tables[parent_name].columns:
                    continue

                child_vals = child_df[col].dropna()
                parent_vals = set(tables[parent_name][parent_pk].dropna().tolist())
                if not len(child_vals) or not parent_vals:
                    continue
                containment = float(child_vals.isin(parent_vals).mean())
                if containment < 0.9:
                    continue

                counts = child_vals.value_counts()
                # every parent that has zero children still shapes the distribution
                zero_children = max(0, len(parent_vals) - len(counts))
                hist = counts.value_counts().to_dict()
                if zero_children:
                    hist[0] = hist.get(0, 0) + zero_children

                values = sorted(int(k) for k in hist)
                total = float(sum(hist.values()))
                probs = [hist[v] / total for v in values]

                child_tbl = schema.table(child_name)
                is_unique = bool(
                    child_tbl
                    and (c := child_tbl.column(col_str))
                    and c.unique
                )

                found.append(
                    ForeignKey(
                        child_table=child_name,
                        child_column=col_str,
                        parent_table=parent_name,
                        parent_column=parent_pk,
                        cardinality="1:1" if is_unique else "1:N",
                        count_values=values,
                        count_probs=probs,
                    )
                )
                break

    return found


def detect_junctions(
    frames: dict[str, pd.DataFrame], schema: SchemaIR
) -> None:
    """Mark link tables, and re-label their edges as N:N.

    A junction table is recognised by shape rather than by name: it carries
    exactly two foreign keys to different parents, and the PAIR of them is
    unique. That pair-uniqueness is the definition of a many-to-many link --
    without it the table is just a child with two parents.
    """
    for table in schema.tables:
        edges = [fk for fk in schema.foreign_keys if fk.child_table == table.name]
        if len(edges) != 2:
            continue
        left, right = edges
        if left.parent_table == right.parent_table:
            continue

        frame = frames.get(table.name)
        if frame is None or frame.empty:
            continue
        if left.child_column not in frame.columns or right.child_column not in frame.columns:
            continue

        pair = frame[[left.child_column, right.child_column]].dropna()
        if pair.empty or pair.duplicated().any():
            continue  # repeated pairs mean this is not a link table

        table.junction = [left.child_column, right.child_column]
        left.cardinality = "N:N"
        right.cardinality = "N:N"

        # The right-hand degree distribution (parents per B) is needed to
        # reproduce how popular each B is, so compute it in both directions.
        for edge, other in ((left, right), (right, left)):
            counts = frame[edge.child_column].value_counts()
            parent_frame = frames.get(edge.parent_table)
            if parent_frame is None or edge.parent_column not in parent_frame.columns:
                continue
            total_parents = parent_frame[edge.parent_column].nunique()
            hist = counts.value_counts().to_dict()
            missing = max(0, total_parents - len(counts))
            if missing:
                hist[0] = hist.get(0, 0) + missing
            values = sorted(int(k) for k in hist)
            total = float(sum(hist.values())) or 1.0
            edge.count_values = values
            edge.count_probs = [hist[v] / total for v in values]
            del other


def build_schema(
    frames: dict[str, pd.DataFrame], name: str = "project", seed: int = 42
) -> SchemaIR:
    schema = SchemaIR(name=name, seed=seed)
    schema.tables = [profile_table(tname, df) for tname, df in frames.items()]
    schema.foreign_keys = detect_foreign_keys(frames, schema)
    detect_junctions(frames, schema)

    # A FK column is structural, not data: it must not be sampled by the
    # tabular engine, and it is not PII.
    for fk in schema.foreign_keys:
        tbl = schema.table(fk.child_table)
        if tbl and (col := tbl.column(fk.child_column)):
            col.semantic = "foreign_key"
            col.pii = "none"
            col.privacy = "passthrough"

    for tbl in schema.tables:
        if tbl.primary_key and (col := tbl.column(tbl.primary_key)):
            col.semantic = "primary_key"
            col.pii = "none"
            col.privacy = "passthrough"

    return schema


def infer_derived_fields(frames: dict[str, pd.DataFrame], schema: SchemaIR) -> None:
    """Propose parent aggregates that should be computed from children.

    Looks for a parent column that reads like a total next to a child table with
    quantity and price columns, and checks that the numbers actually add up in
    the source data before claiming the relationship. Guessing wrong here would
    silently overwrite a real column during reconciliation.
    """
    for fk in schema.foreign_keys:
        parent = schema.table(fk.parent_table)
        child = schema.table(fk.child_table)
        if parent is None or child is None:
            continue
        if fk.parent_table not in frames or fk.child_table not in frames:
            continue
        if parent.derived:
            continue

        child_frame = frames[fk.child_table]
        parent_frame = frames[fk.parent_table]

        quantity = next(
            (c.name for c in child.columns
             if c.name.lower() in ("qty", "quantity", "units") and c.dtype in ("int", "float")),
            None,
        )
        price = next(
            (c.name for c in child.columns
             if c.dtype in ("int", "float")
             and any(k in c.name.lower() for k in ("price", "rate", "cost"))
             and "total" not in c.name.lower()),
            None,
        )
        totals = [
            c.name for c in parent.columns
            if c.dtype in ("int", "float")
            and any(k in c.name.lower() for k in ("total", "amount", "value", "sum"))
        ]
        counts = [
            c.name for c in parent.columns
            if c.dtype == "int"
            and any(k in c.name.lower() for k in ("item_count", "items", "line_count", "n_items"))
        ]

        if quantity and price and totals and parent.primary_key:
            expr = f"{quantity} * {price}"
            try:
                expected = (
                    child_frame.eval(expr)
                    .groupby(child_frame[fk.child_column]).sum().round(2)
                )
                actual = parent_frame.set_index(parent.primary_key)[totals[0]]
                aligned = expected.reindex(actual.index).fillna(0.0)
                agreement = float(
                    np.isclose(actual.astype(float), aligned.astype(float), atol=0.02).mean()
                )
            except Exception:  # noqa: BLE001 - a bad guess just means no derived field
                agreement = 0.0

            if agreement > 0.95:
                parent.derived.append(
                    DerivedField(column=totals[0], child_table=fk.child_table,
                                 agg="sum", expr=expr)
                )
                for name in counts:
                    parent.derived.append(
                        DerivedField(column=name, child_table=fk.child_table, agg="count")
                    )


def coerce_to_schema(df: pd.DataFrame, table: Table) -> pd.DataFrame:
    """Cast a raw frame to the dtypes the IR declares.

    The profiler infers types from string input, so every later stage must see
    the coerced form. Doing this in one place is what stops "it worked in the
    profiler but crashed in the engine" bugs.
    """
    out = pd.DataFrame(index=df.index)
    for column in table.columns:
        if column.name not in df.columns:
            out[column.name] = pd.Series([None] * len(df), index=df.index)
            continue
        series = df[column.name]
        if column.dtype in ("int", "float"):
            out[column.name] = pd.to_numeric(series, errors="coerce")
        elif column.dtype in ("date", "datetime"):
            try:
                out[column.name] = pd.to_datetime(series, errors="coerce", format="mixed")
            except (ValueError, TypeError):
                out[column.name] = pd.to_datetime(series, errors="coerce")
        elif column.dtype == "bool":
            out[column.name] = series.astype("boolean")
        else:
            out[column.name] = series.astype("object")
    return out


def json_safe(value: Any) -> Any:
    """Convert numpy/pandas scalars into something json.dumps accepts."""
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if (np.isnan(value) or np.isinf(value)) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S") if value.time() != pd.Timestamp(0).time() else value.strftime("%Y-%m-%d")
    if value is pd.NaT:
        return None
    return value


def frame_to_records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    subset = df.head(limit) if limit is not None else df
    return [
        {str(k): json_safe(v) for k, v in row.items()}
        for row in subset.to_dict(orient="records")
    ]
