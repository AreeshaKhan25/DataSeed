"""Business rules — the third input the platform accepts.

A schema says what shape the data has. A business rule says what makes a row
*valid*: an order cannot ship before it was placed, a quantity is never
negative, a cancelled order has no payment date. Distributions alone cannot
express any of that, so a generator that only fits marginals will happily emit
data that no real system would ever produce.

Enforcement is **repair first, reject second**:

  1. Fix deterministically where the fix is unambiguous -- clamp to a range,
     recompute a derived value, reorder two dates.
  2. Drop only what cannot be repaired, count it, and report it.

Pure rejection sampling is the usual way these engines hang: a rule that is
rarely satisfied turns into an unbounded resample loop. Nothing here loops.
"""
from __future__ import annotations

import re
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from .schema import Constraint, OPERATORS, SchemaIR, Table

class ConstraintResult(BaseModel):
    id: str
    label: str
    kind: str
    violations_before: int = 0
    repaired: int = 0
    dropped: int = 0
    violations_after: int = 0
    note: str = ""


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------

def _violation_mask(frame: pd.DataFrame, c: Constraint) -> pd.Series:
    """Rows that break the rule. Missing columns mean nothing to check."""
    empty = pd.Series(False, index=frame.index)
    p = c.params

    if c.kind == "not_null":
        return frame[c.column].isna() if c.column in frame.columns else empty

    if c.column and c.column not in frame.columns:
        return empty

    if c.kind == "range":
        values = pd.to_numeric(frame[c.column], errors="coerce")
        bad = pd.Series(False, index=frame.index)
        if p.get("minimum") is not None:
            bad |= values < float(p["minimum"])
        if p.get("maximum") is not None:
            bad |= values > float(p["maximum"])
        return bad.fillna(False)

    if c.kind == "comparison":
        other = p.get("other_column")
        if not other or other not in frame.columns:
            return empty
        op = OPERATORS.get(p.get("operator", ">="))
        if op is None:
            return empty
        left, right = frame[c.column], frame[other]
        if left.dtype.kind == "M" or right.dtype.kind == "M":
            left = pd.to_datetime(left, errors="coerce")
            right = pd.to_datetime(right, errors="coerce")
        else:
            left = pd.to_numeric(left, errors="coerce")
            right = pd.to_numeric(right, errors="coerce")
        both = left.notna() & right.notna()
        return (both & ~op(left, right)).fillna(False)

    if c.kind == "computed":
        try:
            expected = frame.eval(str(p.get("expression", "")))
        except Exception:  # noqa: BLE001 - a bad expression is reported, not raised
            return empty
        actual = pd.to_numeric(frame[c.column], errors="coerce")
        expected = pd.to_numeric(pd.Series(expected, index=frame.index), errors="coerce")
        both = actual.notna() & expected.notna()
        tol = float(p.get("tolerance", 0.011))
        return (both & (actual - expected).abs().gt(tol)).fillna(False)

    if c.kind == "enum":
        allowed = {str(v) for v in p.get("allowed", [])}
        if not allowed:
            return empty
        values = frame[c.column]
        return (values.notna() & ~values.astype(str).isin(allowed)).fillna(False)

    if c.kind == "regex":
        pattern = str(p.get("pattern", ""))
        if not pattern:
            return empty
        values = frame[c.column]
        try:
            ok = values.astype(str).str.match(pattern, na=False)
        except re.error:
            return empty
        return (values.notna() & ~ok).fillna(False)

    if c.kind == "unique":
        return frame[c.column].duplicated(keep="first") & frame[c.column].notna()

    if c.kind == "conditional":
        when_col = p.get("when_column")
        if not when_col or when_col not in frame.columns:
            return empty
        op = OPERATORS.get(p.get("when_operator", "=="))
        if op is None:
            return empty
        triggered = op(frame[when_col].astype(str), str(p.get("when_value"))).fillna(False)
        target_null = frame[c.column].isna()
        return triggered & (target_null if not p.get("then_null", True) else ~target_null)

    return empty


def check_constraints(
    frames: dict[str, pd.DataFrame], schema: SchemaIR,
    null_override: float | None = None,
) -> dict[str, int]:
    """Violations per constraint, after generation. Feeds the integrity gate.

    Takes the same override as enforcement, so the gate never fails a run for
    breaking a rule it was deliberately told to relax.
    """
    out: dict[str, int] = {}
    for c in active_constraints(schema.constraints, null_override):
        frame = frames.get(c.table)
        if frame is None or frame.empty:
            continue
        out[f"{c.table}.{c.label()}"] = int(_violation_mask(frame, c).sum())
    return out


# --------------------------------------------------------------------------
# Repair
# --------------------------------------------------------------------------

def _repair(
    frame: pd.DataFrame, c: Constraint, mask: pd.Series, rng: np.random.Generator
) -> tuple[pd.DataFrame, int, str]:
    """Fix what can be fixed in place. Returns (frame, repaired_count, note)."""
    p = c.params
    count = int(mask.sum())
    if count == 0:
        return frame, 0, ""

    if c.kind == "range":
        values = pd.to_numeric(frame[c.column], errors="coerce")
        lo = float(p["minimum"]) if p.get("minimum") is not None else None
        hi = float(p["maximum"]) if p.get("maximum") is not None else None
        frame.loc[mask, c.column] = values[mask].clip(lower=lo, upper=hi)
        return frame, count, "clamped to range"

    if c.kind == "computed":
        try:
            expected = frame.eval(str(p["expression"]))
        except Exception:  # noqa: BLE001
            return frame, 0, "expression could not be evaluated"
        frame.loc[mask, c.column] = pd.Series(expected, index=frame.index)[mask].round(2)
        return frame, count, "recomputed from its inputs"

    if c.kind == "comparison":
        other = p["other_column"]
        op = p.get("operator", ">=")
        left, right = frame[c.column], frame[other]
        if left.dtype.kind == "M" or right.dtype.kind == "M":
            # Dates out of order: mirror the gap rather than collapse them onto
            # the same day, so the interval distribution survives.
            left_d = pd.to_datetime(left, errors="coerce")
            right_d = pd.to_datetime(right, errors="coerce")
            gap = (right_d - left_d).abs()
            if op in (">=", ">"):
                frame.loc[mask, c.column] = (right_d + gap)[mask]
            else:
                frame.loc[mask, c.column] = (right_d - gap)[mask]
        else:
            left_n = pd.to_numeric(left, errors="coerce")
            right_n = pd.to_numeric(right, errors="coerce")
            frame.loc[mask, c.column] = right_n[mask]
            if op == ">":
                frame.loc[mask, c.column] = right_n[mask] + 1
            elif op == "<":
                frame.loc[mask, c.column] = right_n[mask] - 1
        return frame, count, "reordered against its partner column"

    if c.kind == "enum":
        allowed = list(p.get("allowed", []))
        if not allowed:
            return frame, 0, "no allowed values given"
        weights = p.get("weights")
        probs = None
        if weights and len(weights) == len(allowed):
            probs = np.array(weights, dtype=float)
            probs = probs / probs.sum()
        frame.loc[mask, c.column] = rng.choice(allowed, size=count, p=probs)
        return frame, count, "replaced with an allowed value"

    if c.kind == "not_null":
        pool = frame.loc[~mask, c.column].dropna()
        if pool.empty:
            return frame, 0, "no non-null value available to fill with"
        frame.loc[mask, c.column] = rng.choice(pool.to_numpy(), size=count)
        return frame, count, "filled from the column's own distribution"

    if c.kind == "unique":
        series = frame[c.column]
        if pd.api.types.is_numeric_dtype(series):
            highest = pd.to_numeric(series, errors="coerce").max()
            start = int(highest) + 1 if pd.notna(highest) else 1
            frame.loc[mask, c.column] = np.arange(start, start + count)
        else:
            frame.loc[mask, c.column] = [
                f"{v}-{i + 1}" for i, v in enumerate(series[mask].astype(str))
            ]
        return frame, count, "redrawn from unused values"

    if c.kind == "conditional":
        if p.get("then_null", True):
            frame.loc[mask, c.column] = None
            return frame, count, "cleared where the condition applies"
        pool = frame.loc[~mask, c.column].dropna()
        if pool.empty:
            return frame, 0, "no value available to fill with"
        frame.loc[mask, c.column] = rng.choice(pool.to_numpy(), size=count)
        return frame, count, "filled where the condition applies"

    # regex has no general repair: a pattern says what is valid, never how to
    # construct it. Those rows are dropped and counted.
    return frame, 0, ""


def active_constraints(
    constraints: list[Constraint], null_override: float | None = None
) -> list[Constraint]:
    """The rules actually enforced for a run.

    An explicit null rate is a deliberate instruction -- the user is asking for
    missing values so they can test how their system handles them. A `not_null`
    rule the platform *inferred* from the sample must not silently undo that;
    otherwise the preview shows nulls and the output has none. A rule the user
    or the AI wrote is kept, because that one was asked for on purpose.
    """
    if not null_override:
        return [c for c in constraints if c.enabled]
    return [
        c for c in constraints
        if c.enabled and not (c.kind == "not_null" and c.source == "inferred")
    ]


def apply_constraints(
    frame: pd.DataFrame,
    table: Table,
    constraints: list[Constraint],
    rng: np.random.Generator,
    *,
    null_override: float | None = None,
) -> tuple[pd.DataFrame, list[ConstraintResult]]:
    """Enforce every rule for one table. Repairs first, drops only if it must."""
    results: list[ConstraintResult] = []
    active = active_constraints(constraints, null_override)
    relevant = [c for c in active if c.table == table.name]
    if not relevant or frame.empty:
        return frame, results

    for c in relevant:
        mask = _violation_mask(frame, c)
        before = int(mask.sum())
        result = ConstraintResult(id=c.id, label=c.label(), kind=c.kind,
                                  violations_before=before)

        if before:
            frame, repaired, note = _repair(frame, c, mask, rng)
            result.repaired = repaired
            result.note = note

            remaining = _violation_mask(frame, c)
            if remaining.any():
                # Unrepairable. Dropping is the honest outcome: the row cannot
                # be made valid, so it must not appear in the output.
                result.dropped = int(remaining.sum())
                frame = frame.loc[~remaining].reset_index(drop=True)

        result.violations_after = int(_violation_mask(frame, c).sum())
        results.append(result)

    return frame, results


# --------------------------------------------------------------------------
# Inference — business rules learned from the sample
# --------------------------------------------------------------------------

def infer_constraints(frames: dict[str, pd.DataFrame], schema: SchemaIR) -> list[Constraint]:
    """Read obvious rules straight off the source data.

    Everything proposed here is something the sample demonstrates without
    exception -- a column that is never negative, a date that never precedes
    another, a category that never takes an unlisted value. A rule that the real
    data already breaks is not a rule, so nothing is proposed unless it holds on
    every observed row.
    """
    found: list[Constraint] = []

    for table in schema.tables:
        frame = frames.get(table.name)
        if frame is None or frame.empty:
            continue

        for column in table.columns:
            if column.name not in frame.columns:
                continue
            if column.semantic in ("primary_key", "foreign_key"):
                continue
            series = frame[column.name].dropna()
            if series.empty:
                continue

            if column.dtype in ("int", "float"):
                values = pd.to_numeric(series, errors="coerce").dropna()
                if values.empty:
                    continue
                if values.min() >= 0:
                    found.append(Constraint(
                        table=table.name, kind="range", column=column.name,
                        source="inferred",
                        description=f"{column.name} is never negative",
                        params={"minimum": 0.0},
                    ))
                if column.semantic == "currency" and values.max() > 0:
                    # A generous ceiling: catches runaway outliers without
                    # clipping the genuine tail.
                    found.append(Constraint(
                        table=table.name, kind="range", column=column.name,
                        source="inferred",
                        description=f"{column.name} stays within a plausible ceiling",
                        params={"maximum": float(values.max()) * 10},
                    ))

            elif column.semantic == "category" or (
                column.dtype == "str" and series.nunique() <= 25
            ):
                allowed = sorted(series.astype(str).unique().tolist())
                freqs = series.astype(str).value_counts(normalize=True)
                found.append(Constraint(
                    table=table.name, kind="enum", column=column.name,
                    source="inferred",
                    description=f"{column.name} only takes known values",
                    params={
                        "allowed": allowed,
                        "weights": [float(freqs[v]) for v in allowed],
                    },
                ))

            if not column.nullable and column.null_rate == 0:
                found.append(Constraint(
                    table=table.name, kind="not_null", column=column.name,
                    source="inferred",
                    description=f"{column.name} is always present",
                ))

        # Arithmetic a column already satisfies: line_total = qty * unit_price.
        # The copula fits every column independently, so without this the three
        # are internally inconsistent even though each one looks right alone.
        numeric = [
            c.name for c in table.columns
            if c.dtype in ("int", "float")
            and c.semantic not in ("primary_key", "foreign_key")
            and c.name in frame.columns
            and frame[c.name].notna().sum() > 20
        ]
        for target in numeric:
            values = pd.to_numeric(frame[target], errors="coerce")
            found_expr = None
            for left in numeric:
                if left == target:
                    continue
                for right in numeric:
                    if right in (target, left) or right < left:
                        continue
                    a = pd.to_numeric(frame[left], errors="coerce")
                    b = pd.to_numeric(frame[right], errors="coerce")
                    usable = values.notna() & a.notna() & b.notna()
                    if usable.sum() < 20:
                        continue
                    for op, expr in (("*", f"{left} * {right}"), ("+", f"{left} + {right}")):
                        candidate = (a * b) if op == "*" else (a + b)
                        if np.isclose(
                            values[usable], candidate[usable], atol=0.005, rtol=0
                        ).all():
                            found_expr = expr
                            break
                    if found_expr:
                        break
                if found_expr:
                    break
            if found_expr:
                found.append(Constraint(
                    table=table.name, kind="computed", column=target,
                    source="inferred",
                    description=f"{target} equals {found_expr}",
                    params={"expression": found_expr, "tolerance": 0.005},
                ))

        # Date ordering between every pair of date columns that never inverts.
        date_columns = [
            c.name for c in table.columns
            if c.dtype in ("date", "datetime") and c.name in frame.columns
        ]
        for i, first in enumerate(date_columns):
            for second in date_columns[i + 1:]:
                a = pd.to_datetime(frame[first], errors="coerce")
                b = pd.to_datetime(frame[second], errors="coerce")
                both = a.notna() & b.notna()
                if both.sum() < 20:
                    continue
                if (b[both] >= a[both]).all():
                    found.append(Constraint(
                        table=table.name, kind="comparison", column=second,
                        source="inferred",
                        description=f"{second} never precedes {first}",
                        params={"operator": ">=", "other_column": first},
                    ))
                elif (a[both] >= b[both]).all():
                    found.append(Constraint(
                        table=table.name, kind="comparison", column=first,
                        source="inferred",
                        description=f"{first} never precedes {second}",
                        params={"operator": ">=", "other_column": second},
                    ))

    return found
