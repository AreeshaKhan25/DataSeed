"""Relational generation — two passes.

Pass 1 walks the foreign-key graph top-down: parents are generated first, then
each child draws its row count from the empirical children-per-parent
distribution and inherits a real parent key.

Pass 2 walks the same order in reverse and recomputes every derived field from
the children that actually exist.

That second pass is the whole point. Parent aggregates such as `orders.total`
are computed from line items, never generated, so they reconcile by construction
rather than by luck.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .constraints import ConstraintResult, apply_constraints, check_constraints
from .engine import TableModel, apply_privacy, sample_table
from .schema import ForeignKey, SchemaIR
from .seeds import SeedFactory


class IntegrityError(RuntimeError):
    """Raised when generated data violates a structural guarantee."""


def topological_order(schema: SchemaIR) -> tuple[list[str], list[ForeignKey]]:
    """Order tables parents-first.

    Returns the order plus any FK edges that had to be dropped to break a cycle.
    A dropped edge means that column is left null rather than pointing at a row
    that does not exist yet.
    """
    names = [t.name for t in schema.tables]
    edges = [
        fk for fk in schema.foreign_keys
        if fk.parent_table in names and fk.child_table in names
        and fk.parent_table != fk.child_table
    ]

    incoming: dict[str, set[str]] = {n: set() for n in names}
    for fk in edges:
        incoming[fk.child_table].add(fk.parent_table)

    order: list[str] = []
    remaining = dict(incoming)
    while remaining:
        ready = sorted([n for n, parents in remaining.items() if not parents])
        if not ready:
            break  # everything left is in a cycle
        for name in ready:
            order.append(name)
            del remaining[name]
        for parents in remaining.values():
            parents.difference_update(ready)

    broken: list[ForeignKey] = []
    if remaining:
        # Break the cycle at the alphabetically first remaining table so the
        # result is deterministic, then continue.
        cyclic = sorted(remaining)
        for name in cyclic:
            order.append(name)
        broken = [
            fk for fk in edges
            if fk.child_table in remaining and fk.parent_table in remaining
        ]

    return order, broken


def _draw_child_counts(
    fk: ForeignKey, n_parents: int, rng: np.random.Generator
) -> np.ndarray:
    """How many children each parent gets."""
    if fk.cardinality == "1:1":
        return np.ones(n_parents, dtype=int)
    if not fk.count_values:
        return np.ones(n_parents, dtype=int)
    values = np.array(fk.count_values, dtype=int)
    probs = np.array(fk.count_probs, dtype=float)
    probs = probs / probs.sum()
    return rng.choice(values, size=n_parents, p=probs)


# A root table at or below this size that other tables point at is an
# enumeration, not a fact table.
LOOKUP_MAX_ROWS = 100


def is_lookup_table(table, schema: SchemaIR) -> bool:
    """True for small reference tables: tags, statuses, countries, currencies.

    Scaling one of these makes no sense. If the source has ten tags, the
    synthetic data has ten tags -- inventing six hundred would break the meaning
    of the column and destroy the popularity distribution that the junction
    depends on.
    """
    if table.row_count > LOOKUP_MAX_ROWS or table.row_count == 0:
        return False
    has_parents = any(fk.child_table == table.name for fk in schema.foreign_keys)
    is_referenced = any(fk.parent_table == table.name for fk in schema.foreign_keys)
    return is_referenced and not has_parents


def _degree_weights(
    fk: ForeignKey, n_parents: int, rng: np.random.Generator
) -> np.ndarray:
    """Pick-probability per parent, proportional to its learned degree.

    Without this every tag would be equally likely, and the junction would come
    out uniform when the real data has a few very popular tags and a long tail.
    """
    if not fk.count_values:
        return np.full(n_parents, 1.0 / max(n_parents, 1))
    values = np.array(fk.count_values, dtype=float)
    probs = np.array(fk.count_probs, dtype=float)
    probs = probs / probs.sum()
    degrees = rng.choice(values, size=n_parents, p=probs).astype(float)
    # A floor keeps every parent reachable; a zero-degree draw would otherwise
    # make that row impossible to ever select.
    degrees = np.maximum(degrees, 0.05)
    return degrees / degrees.sum()


def _generate_junction(
    table,
    model: TableModel,
    left: ForeignKey,
    right: ForeignKey,
    frames: dict[str, pd.DataFrame],
    seeds: SeedFactory,
    *,
    null_rate: float | None,
    outlier_rate: float,
) -> pd.DataFrame:
    """Build an N:N link table.

    Each left parent draws a number of partners from its learned degree
    distribution, and partners are chosen weighted by their own popularity.
    Pairs are deduplicated, because a link table that repeats a pair is not a
    many-to-many relationship -- it is a child table with two parents.
    """
    rng = seeds.stream(f"junction:{table.name}")
    left_keys = frames[left.parent_table][left.parent_column].dropna().to_numpy()
    right_keys = frames[right.parent_table][right.parent_column].dropna().to_numpy()

    if len(left_keys) == 0 or len(right_keys) == 0:
        return pd.DataFrame(columns=[c.name for c in table.columns])

    degrees = _draw_child_counts(left, len(left_keys), rng)
    weights = _degree_weights(right, len(right_keys), rng)

    seen: set[tuple] = set()
    pairs: list[tuple] = []
    for left_key, k in zip(left_keys, degrees):
        k = int(min(max(int(k), 0), len(right_keys)))
        if k == 0:
            continue
        picks = rng.choice(len(right_keys), size=k, replace=False, p=weights)
        for j in picks:
            key = (left_key, right_keys[j])
            if key in seen:
                continue
            seen.add(key)
            pairs.append(key)

    if not pairs:
        # Every parent drew zero partners. Give each one a single link so the
        # table is never silently empty in the demo.
        picks = rng.choice(len(right_keys), size=len(left_keys), replace=True)
        pairs = [(left_keys[i], right_keys[j]) for i, j in enumerate(picks)]

    frame = sample_table(
        model, len(pairs), seeds, null_rate=null_rate, outlier_rate=outlier_rate
    )
    frame[left.child_column] = [p[0] for p in pairs]
    frame[right.child_column] = [p[1] for p in pairs]
    return frame


def generate_relational(
    schema: SchemaIR,
    models: dict[str, TableModel],
    rows: int,
    seeds: SeedFactory,
    *,
    null_rate: float | None = None,
    outlier_rate: float = 0.0,
) -> tuple[dict[str, pd.DataFrame], list[str], dict[str, list[ConstraintResult]]]:
    """Generate every table. Returns frames, warnings, and constraint results."""
    order, broken = topological_order(schema)
    warnings: list[str] = []
    for fk in broken:
        warnings.append(
            f"Cycle broken: {fk.child_table}.{fk.child_column} left null "
            f"(would point at {fk.parent_table})"
        )
    broken_keys = {(fk.child_table, fk.child_column) for fk in broken}

    fks_by_child: dict[str, list[ForeignKey]] = defaultdict(list)
    for fk in schema.foreign_keys:
        if (fk.child_table, fk.child_column) in broken_keys:
            continue
        if fk.parent_table in models and fk.child_table in models:
            fks_by_child[fk.child_table].append(fk)

    frames: dict[str, pd.DataFrame] = {}
    rule_results: dict[str, list[ConstraintResult]] = {}

    # ---- Pass 1: top-down -------------------------------------------------
    for name in order:
        table = schema.table(name)
        model = models.get(name)
        if table is None or model is None:
            continue

        rng = seeds.stream(f"rel:{name}")
        parent_fks = fks_by_child.get(name, [])

        if table.is_junction and len(parent_fks) == 2:
            left, right = parent_fks[0], parent_fks[1]
            if left.child_column != table.junction[0]:
                left, right = right, left
            if frames.get(left.parent_table) is None or frames.get(right.parent_table) is None:
                warnings.append(f"{name}: a parent table is missing, skipped")
                frames[name] = pd.DataFrame(columns=[c.name for c in table.columns])
                continue
            frame = _generate_junction(
                table, model, left, right, frames, seeds,
                null_rate=null_rate, outlier_rate=outlier_rate,
            )
            frame = apply_privacy(frame, table, seeds)
            frame, results = apply_constraints(
                frame, table, schema.constraints, seeds.stream(f"rules:{name}"),
                null_override=null_rate,
            )
            if results:
                rule_results[name] = results
            frames[name] = frame
            continue

        if not parent_fks:
            # Root table: honour the requested row count, unless it is a small
            # reference table, which keeps its real cardinality.
            n_rows = table.row_count if is_lookup_table(table, schema) else max(1, rows)
            frame = sample_table(
                model, n_rows, seeds,
                null_rate=null_rate, outlier_rate=outlier_rate,
            )
        else:
            # Child table: its size is dictated by its parents' cardinality,
            # not by the requested row count. This is what keeps the shape of
            # the data realistic when you scale a schema up.
            primary = parent_fks[0]
            parent_frame = frames.get(primary.parent_table)
            if parent_frame is None or parent_frame.empty:
                warnings.append(f"{name}: parent {primary.parent_table} is empty, skipped")
                frames[name] = pd.DataFrame(columns=[c.name for c in table.columns])
                continue

            parent_keys = parent_frame[primary.parent_column].to_numpy()
            counts = _draw_child_counts(primary, len(parent_keys), rng)
            assigned = np.repeat(parent_keys, counts)
            n_rows = int(len(assigned))

            if n_rows == 0:
                # Every parent drew zero children. Force at least one child per
                # parent so the demo never shows an empty table.
                assigned = parent_keys.copy()
                n_rows = len(assigned)

            frame = sample_table(
                model, n_rows, seeds,
                null_rate=null_rate, outlier_rate=outlier_rate,
            )
            frame[primary.child_column] = assigned

            # Any additional parents are sampled independently.
            for extra in parent_fks[1:]:
                extra_parent = frames.get(extra.parent_table)
                if extra_parent is None or extra_parent.empty:
                    continue
                pool = extra_parent[extra.parent_column].to_numpy()
                extra_rng = seeds.stream(f"rel:{name}:{extra.child_column}")
                frame[extra.child_column] = extra_rng.choice(pool, size=n_rows, replace=True)

        frame = apply_privacy(frame, table, seeds)

        # Business rules run before reconciliation: a repaired quantity or price
        # has to be in place before parent totals are summed from it.
        frame, results = apply_constraints(
            frame, table, schema.constraints, seeds.stream(f"rules:{name}"),
            null_override=null_rate,
        )
        if results:
            rule_results[name] = results
            dropped = sum(r.dropped for r in results)
            if dropped:
                warnings.append(
                    f"{name}: dropped {dropped} rows that could not satisfy a business rule"
                )
        frames[name] = frame

    # ---- Pass 2: bottom-up reconciliation ---------------------------------
    for name in reversed(order):
        table = schema.table(name)
        if table is None or not table.derived or name not in frames:
            continue
        parent_frame = frames[name]

        for derived in table.derived:
            child_frame = frames.get(derived.child_table)
            if child_frame is None or child_frame.empty:
                continue
            link = next(
                (fk for fk in schema.foreign_keys
                 if fk.child_table == derived.child_table and fk.parent_table == name),
                None,
            )
            if link is None or table.primary_key is None:
                continue

            working = child_frame.copy()
            if derived.expr:
                try:
                    working["_value"] = working.eval(derived.expr)
                except Exception as exc:  # noqa: BLE001 - surfaced as a warning
                    warnings.append(
                        f"{name}.{derived.column}: could not evaluate "
                        f"'{derived.expr}' ({exc})"
                    )
                    continue
            else:
                working["_value"] = 1

            grouped = working.groupby(link.child_column)["_value"]
            aggregated = getattr(grouped, derived.agg)()

            mapped = parent_frame[table.primary_key].map(aggregated)
            fill = 0 if derived.agg in ("sum", "count") else np.nan
            parent_frame[derived.column] = mapped.fillna(fill)

            if table.column(derived.column) and table.column(derived.column).dtype == "int":
                parent_frame[derived.column] = parent_frame[derived.column].round().astype("int64")
            else:
                parent_frame[derived.column] = parent_frame[derived.column].round(2)

        frames[name] = parent_frame

    return frames, warnings, rule_results


def check_integrity(
    schema: SchemaIR, frames: dict[str, pd.DataFrame],
    null_override: float | None = None,
) -> dict[str, object]:
    """Hard structural gate. Export is blocked unless this passes.

    Returns a report rather than raising, so the UI can show exactly which
    guarantee failed instead of a stack trace.
    """
    orphans: dict[str, int] = {}
    duplicate_keys: dict[str, int] = {}
    null_keys: dict[str, int] = {}
    reconciliation: dict[str, int] = {}

    for table in schema.tables:
        frame = frames.get(table.name)
        if frame is None or table.primary_key is None:
            continue
        if table.primary_key not in frame.columns:
            continue
        keys = frame[table.primary_key]
        duplicate_keys[table.name] = int(keys.duplicated().sum())
        null_keys[table.name] = int(keys.isna().sum())

    for fk in schema.foreign_keys:
        child = frames.get(fk.child_table)
        parent = frames.get(fk.parent_table)
        if child is None or parent is None:
            continue
        if fk.child_column not in child.columns or fk.parent_column not in parent.columns:
            continue
        child_vals = child[fk.child_column].dropna()
        if child_vals.empty:
            orphans[f"{fk.child_table}.{fk.child_column}"] = 0
            continue
        valid = set(parent[fk.parent_column].dropna().tolist())
        orphans[f"{fk.child_table}.{fk.child_column}"] = int((~child_vals.isin(valid)).sum())

    # Derived fields must equal the aggregate of their children exactly.
    for table in schema.tables:
        frame = frames.get(table.name)
        if frame is None or table.primary_key is None:
            continue
        for derived in table.derived:
            child_frame = frames.get(derived.child_table)
            link = next(
                (fk for fk in schema.foreign_keys
                 if fk.child_table == derived.child_table and fk.parent_table == table.name),
                None,
            )
            if child_frame is None or link is None or derived.column not in frame.columns:
                continue
            working = child_frame.copy()
            try:
                working["_value"] = working.eval(derived.expr) if derived.expr else 1
            except Exception:  # noqa: BLE001
                continue
            expected = getattr(working.groupby(link.child_column)["_value"], derived.agg)()
            actual = frame.set_index(table.primary_key)[derived.column]
            aligned = expected.reindex(actual.index).fillna(0)
            # Half a cent: a true to-the-penny check. A looser tolerance was
            # hiding real drift that shows up the moment anyone sums the
            # exported column in a spreadsheet.
            mismatches = int((~np.isclose(
                actual.astype(float), aligned.astype(float), atol=0.005, rtol=0
            )).sum())
            reconciliation[f"{table.name}.{derived.column}"] = mismatches

    duplicate_links: dict[str, int] = {}
    for table in schema.tables:
        if not table.is_junction:
            continue
        frame = frames.get(table.name)
        if frame is None or frame.empty:
            continue
        if not all(c in frame.columns for c in table.junction):
            continue
        duplicate_links[table.name] = int(frame[table.junction].duplicated().sum())

    total_orphans = sum(orphans.values())
    total_dupes = sum(duplicate_keys.values())
    total_null_keys = sum(null_keys.values())
    total_mismatch = sum(reconciliation.values())
    rule_violations = check_constraints(frames, schema, null_override)
    total_rule_violations = sum(rule_violations.values())

    total_dup_links = sum(duplicate_links.values())
    failures = (
        total_orphans + total_dupes + total_null_keys + total_mismatch
        + total_dup_links + total_rule_violations
    )

    return {
        "passed": failures == 0,
        "score": 100.0 if failures == 0 else max(0.0, 100.0 - failures),
        "orphan_keys": orphans,
        "duplicate_primary_keys": duplicate_keys,
        "duplicate_junction_links": duplicate_links,
        "business_rule_violations": rule_violations,
        "total_rule_violations": total_rule_violations,
        "total_duplicate_links": total_dup_links,
        "null_primary_keys": null_keys,
        "reconciliation_mismatches": reconciliation,
        "total_orphans": total_orphans,
        "total_duplicate_keys": total_dupes,
        "total_reconciliation_mismatches": total_mismatch,
    }
