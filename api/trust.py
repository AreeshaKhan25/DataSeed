"""The Trust Report — proof that the generated data is actually usable.

Four independent scores:

  Integrity  structural guarantees (keys, reconciliation). A hard gate.
  Fidelity   do the distributions match? KS for numerics, TVD for categories.
  Utility    TSTR. Train a model on synthetic data, test it on held-out REAL
             data, and compare against the same model trained on real data.
  Privacy    exact-match leakage, distance to closest record, and a membership
             inference attack.

The one rule that makes any of this honest: the generator used for the report is
refitted on the 70% training split alone. Fitting on all of the real data and
then scoring against part of it would leak, and every number would flatter us.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors

from .engine import fit_table, sample_table
from .schema import Table, coerce_to_schema
from .seeds import SeedFactory

# Columns that carry no signal and would only add noise to the ML metrics.
_SKIP_SEMANTICS = {
    "primary_key", "foreign_key", "identifier",
    "person_name", "email", "phone", "address", "url", "national_id",
    "iban", "free_text",
}


# --------------------------------------------------------------------------
# Shared encoding
# --------------------------------------------------------------------------

def _modelling_columns(table: Table, df: pd.DataFrame) -> list[str]:
    usable = []
    for column in table.columns:
        if column.name not in df.columns:
            continue
        if column.semantic in _SKIP_SEMANTICS:
            continue
        series = df[column.name].dropna()
        if series.empty or series.nunique() <= 1:
            continue
        if column.dtype == "str" and series.nunique() > 50:
            continue
        usable.append(column.name)
    return usable


def _encode(
    df: pd.DataFrame, table: Table, columns: list[str], categories: dict[str, list]
) -> pd.DataFrame:
    """Numeric matrix using category codes learned from the real data.

    Categories are fixed by the real data so that real and synthetic frames
    always land in the same space; an unseen synthetic category encodes to -1
    rather than shifting every other code.
    """
    out = pd.DataFrame(index=df.index)
    for name in columns:
        column = table.column(name)
        series = df[name]
        if column is None:
            continue
        if column.dtype in ("int", "float"):
            out[name] = pd.to_numeric(series, errors="coerce")
        elif column.dtype in ("date", "datetime"):
            out[name] = pd.to_datetime(series, errors="coerce").astype("int64") // 10**9
            out.loc[series.isna(), name] = np.nan
        else:
            lookup = {v: i for i, v in enumerate(categories.get(name, []))}
            out[name] = series.astype(str).map(lookup).fillna(-1).astype(float)
    return out.replace([np.inf, -np.inf], np.nan)


def _category_map(df: pd.DataFrame, table: Table, columns: list[str]) -> dict[str, list]:
    mapping: dict[str, list] = {}
    for name in columns:
        column = table.column(name)
        if column and column.dtype not in ("int", "float", "date", "datetime"):
            mapping[name] = sorted(df[name].dropna().astype(str).unique().tolist())
    return mapping


# --------------------------------------------------------------------------
# Fidelity
# --------------------------------------------------------------------------

def fidelity_scores(
    real: pd.DataFrame, synth: pd.DataFrame, table: Table, model: Any = None
) -> dict[str, Any]:
    """Per-column distribution match, plus correlation structure.

    Columns that are synthesised from scratch (names, emails, free text) are
    excluded rather than scored. We *want* those to differ from the source --
    that is the privacy guarantee -- so measuring their distributional distance
    would penalise the generator for doing its job.
    """
    per_column: list[dict[str, Any]] = []
    regenerated: list[str] = []
    modes = getattr(model, "models", {}) or {}

    for column in table.columns:
        name = column.name
        if name not in real.columns or name not in synth.columns:
            continue
        if column.semantic in ("primary_key", "foreign_key"):
            continue
        mode = getattr(modes.get(name), "mode", None)
        if mode in ("faker", "faker_text", "sequence", "foreign_key"):
            regenerated.append(name)
            continue

        real_vals = real[name].dropna()
        synth_vals = synth[name].dropna()
        if real_vals.empty or synth_vals.empty:
            continue

        if column.dtype in ("int", "float", "date", "datetime"):
            if column.dtype in ("date", "datetime"):
                r = pd.to_datetime(real_vals, errors="coerce").dropna().astype("int64").to_numpy()
                s = pd.to_datetime(synth_vals, errors="coerce").dropna().astype("int64").to_numpy()
            else:
                r = pd.to_numeric(real_vals, errors="coerce").dropna().to_numpy()
                s = pd.to_numeric(synth_vals, errors="coerce").dropna().to_numpy()
            if len(r) < 2 or len(s) < 2:
                continue
            distance = float(stats.ks_2samp(r, s).statistic)
            metric = "KS"
        else:
            r_freq = real_vals.astype(str).value_counts(normalize=True)
            s_freq = synth_vals.astype(str).value_counts(normalize=True)
            labels = r_freq.index.union(s_freq.index)
            distance = float(
                0.5 * np.abs(
                    r_freq.reindex(labels, fill_value=0.0).to_numpy()
                    - s_freq.reindex(labels, fill_value=0.0).to_numpy()
                ).sum()
            )
            metric = "TVD"

        per_column.append({
            "column": name,
            "metric": metric,
            "distance": round(distance, 4),
            "match": round(max(0.0, 1.0 - distance) * 100, 1),
        })

    column_score = float(np.mean([c["match"] for c in per_column])) if per_column else 0.0

    # Correlation structure: how far the synthetic correlation matrix drifts.
    numeric = [
        c.name for c in table.columns
        if c.dtype in ("int", "float")
        and c.semantic not in ("primary_key", "foreign_key")
        and c.name in real.columns and c.name in synth.columns
    ]
    correlation_score = 100.0
    correlation_delta = 0.0
    if len(numeric) >= 2:
        real_corr = real[numeric].apply(pd.to_numeric, errors="coerce").corr().to_numpy()
        synth_corr = synth[numeric].apply(pd.to_numeric, errors="coerce").corr().to_numpy()
        mask = ~(np.isnan(real_corr) | np.isnan(synth_corr))
        if mask.any():
            correlation_delta = float(np.abs(real_corr[mask] - synth_corr[mask]).mean())
            correlation_score = round(max(0.0, 1.0 - correlation_delta) * 100, 1)

    overall = round(0.75 * column_score + 0.25 * correlation_score, 1)
    return {
        "score": overall,
        "column_score": round(column_score, 1),
        "correlation_score": correlation_score,
        "correlation_delta": round(correlation_delta, 4),
        "columns": sorted(per_column, key=lambda c: c["match"]),
        "regenerated_columns": regenerated,
        "note": (
            f"{len(regenerated)} identity columns are regenerated from scratch and "
            "excluded from fidelity scoring by design."
        ) if regenerated else "",
    }


# --------------------------------------------------------------------------
# Utility — TSTR
# --------------------------------------------------------------------------

def _candidate_targets(
    table: Table, df: pd.DataFrame, columns: list[str]
) -> list[tuple[str, str]]:
    """Every column that could serve as a prediction target, best first.

    A low-cardinality integer (a 0/1 churn flag) is a classification target, not
    a regression one -- treating it as numeric produces a meaningless R2.
    """
    classification: list[tuple[str, int]] = []
    regression: list[str] = []

    for name in columns:
        column = table.column(name)
        if column is None:
            continue
        series = df[name].dropna()
        if series.empty:
            continue
        n = series.nunique()
        if column.dtype in ("date", "datetime"):
            continue
        if column.dtype in ("int", "float"):
            if column.dtype == "int" and 2 <= n <= 10:
                classification.append((name, n))
            elif series.notna().sum() > 30 and n > 10:
                regression.append(name)
        elif 2 <= n <= 10:
            classification.append((name, n))

    ordered = [(n, "classification") for n, _ in sorted(classification, key=lambda c: c[1])]
    ordered += [(n, "regression") for n in regression]
    return ordered


def _evaluate_target(
    x_train, y_train, x_synth, y_synth, x_test, y_test, task: str, seed: int
) -> dict[str, float] | None:
    """Train on real and on synthetic, score both on the same real holdout."""
    if task == "classification":
        shared = set(y_train.unique()) & set(y_synth.unique()) & set(y_test.unique())
        if len(shared) < 2:
            return None

        test_keep = y_test.isin(shared)
        if test_keep.sum() < 20:
            return None
        truth = y_test[test_keep]
        if truth.nunique() < 2:
            return None

        def score(x, y) -> float:
            keep = y.isin(shared)
            if keep.sum() < 20 or y[keep].nunique() < 2:
                return float("nan")
            model = HistGradientBoostingClassifier(
                max_iter=120, random_state=seed, early_stopping=False
            )
            model.fit(x[keep], y[keep])
            probabilities = model.predict_proba(x_test[test_keep])
            if len(shared) == 2:
                positive = sorted(shared)[1]
                index = list(model.classes_).index(positive)
                return float(roc_auc_score(
                    (truth == positive).astype(int), probabilities[:, index]
                ))
            return float(roc_auc_score(
                truth, probabilities, multi_class="ovr", average="macro"
            ))

        trtr, tstr, baseline, metric = score(x_train, y_train), score(x_synth, y_synth), 0.5, "ROC AUC"
    else:
        def score(x, y) -> float:
            model = HistGradientBoostingRegressor(
                max_iter=120, random_state=seed, early_stopping=False
            )
            model.fit(x, y)
            return float(r2_score(y_test, model.predict(x_test)))

        trtr, tstr, baseline, metric = score(x_train, y_train), score(x_synth, y_synth), 0.0, "R2"

    if np.isnan(trtr) or np.isnan(tstr):
        return None
    return {"trtr": trtr, "tstr": tstr, "baseline": baseline, "metric": metric}


def utility_score(
    train_real: pd.DataFrame,
    holdout_real: pd.DataFrame,
    synth: pd.DataFrame,
    table: Table,
    seed: int,
    target: str | None = None,
    conditioned_on: str | None = None,
) -> dict[str, Any]:
    """TSTR: train on synthetic, test on real. Compared against TRTR.

    The target is chosen by how well a model trained on the REAL data predicts
    it. Scoring against a target that even real data cannot predict produces a
    flattering ratio between two useless models, which is worse than no metric
    at all.
    """
    columns = _modelling_columns(table, train_real)
    if len(columns) < 2:
        return {"score": 0.0, "available": False,
                "reason": "Not enough modellable columns for a utility test."}

    if target and target in columns:
        column = table.column(target)
        is_small_int = (
            column is not None and column.dtype == "int"
            and train_real[target].dropna().nunique() <= 10
        )
        task = "regression" if (
            column and column.dtype in ("int", "float") and not is_small_int
        ) else "classification"
        candidates = [(target, task)]
    else:
        candidates = _candidate_targets(table, train_real, columns)

    if not candidates:
        return {"score": 0.0, "available": False,
                "reason": "No suitable target column for a utility test."}

    categories = _category_map(train_real, table, columns)
    encoded = {
        "train": _encode(train_real, table, columns, categories),
        "holdout": _encode(holdout_real, table, columns, categories),
        "synth": _encode(synth, table, columns, categories),
    }

    best: dict[str, Any] | None = None
    best_class: dict[str, Any] | None = None
    tried: list[dict[str, Any]] = []
    leaked: list[str] = []

    for name, task in candidates[:6]:
        features = [c for c in columns if c != name]
        if not features:
            continue

        def xy(key: str):
            frame = encoded[key]
            mask = frame[name].notna()
            if task == "classification":
                mask &= frame[name] >= 0
            if mask.sum() < 20:
                return None
            return frame.loc[mask, features], frame.loc[mask, name]

        parts = [xy(k) for k in ("train", "holdout", "synth")]
        if any(part is None for part in parts):
            continue
        (x_train, y_train), (x_test, y_test), (x_synth, y_synth) = parts

        outcome = _evaluate_target(
            x_train, y_train, x_synth, y_synth, x_test, y_test, task, seed
        )
        if outcome is None:
            continue

        lift = outcome["trtr"] - outcome["baseline"]
        tried.append({
            "target": name, "task": task, "trtr": round(outcome["trtr"], 4),
            "tstr": round(outcome["tstr"], 4), "lift": round(lift, 4),
        })

        # A near-perfect real-data score means some feature determines the
        # target outright (a derived column, or a date encoding the same fact).
        # Both models then score 1.0 and the ratio proves nothing.
        if outcome["trtr"] > 0.98:
            leaked.append(name)
            continue

        candidate = {**outcome, "target": name, "task": task,
                     "lift": lift, "features": len(features)}
        if best is None or lift > best["lift"]:
            best = candidate
        if task == "classification" and (best_class is None or lift > best_class["lift"]):
            best_class = candidate

    # Prefer a classification target when one is genuinely learnable: "can it
    # predict churn" is a claim a reviewer can weigh, "R2 on a numeric column"
    # is not.
    if best_class is not None and best_class["lift"] >= 0.05:
        best = best_class

    if best is None:
        return {
            "score": 0.0, "available": False, "candidates": tried,
            "reason": (
                f"Every candidate target ({', '.join(leaked)}) is determined outright by "
                "another column, so a utility ratio would prove nothing."
                if leaked else
                "No target could be evaluated on both real and synthetic data."
            ),
        }

    # If real data cannot predict the target either, the ratio is noise over
    # noise. Say so rather than printing a confident number.
    if best["lift"] < 0.03:
        return {
            "score": 0.0, "available": False, "target": best["target"],
            "trtr": round(best["trtr"], 4), "tstr": round(best["tstr"], 4),
            "candidates": tried,
            "reason": (
                f"No learnable signal in this table: even a model trained on real data "
                f"only reaches {best['trtr']:.3f} {best['metric']} on '{best['target']}'. "
                "A utility ratio here would be meaningless."
            ),
        }

    lift_synth = max(best["tstr"] - best["baseline"], 0.0)
    ratio = min(1.0, lift_synth / best["lift"])

    # If the generator conditioned on the same column we are predicting, the
    # headline score flatters itself: the model was built around exactly that
    # relationship. Report a second target it was NOT conditioned on, so the
    # claim can be checked rather than taken on trust.
    independent: dict[str, Any] | None = None
    if conditioned_on and best["target"] == conditioned_on:
        others = [
            t for t in tried
            if t["target"] != conditioned_on and t["lift"] >= 0.03 and t["trtr"] <= 0.98
        ]
        # Prefer a classification target: its lift is AUC over 0.5, which is
        # directly comparable to the headline number. A regression lift is an
        # R-squared and ranking the two against each other is meaningless.
        classification = [t for t in others if t["task"] == "classification"]
        pool = classification or others
        if pool:
            alt = max(pool, key=lambda t: t["lift"])
            alt_baseline = 0.5 if alt["task"] == "classification" else 0.0
            alt_lift_real = max(alt["trtr"] - alt_baseline, 1e-6)
            alt_lift_synth = max(alt["tstr"] - alt_baseline, 0.0)
            independent = {
                "target": alt["target"],
                "trtr": alt["trtr"],
                "tstr": alt["tstr"],
                "score": round(min(1.0, alt_lift_synth / alt_lift_real) * 100, 1),
            }

    return {
        "conditioned_on": conditioned_on,
        "independent_check": independent,
        "score": round(ratio * 100, 1),
        "available": True,
        "task": best["task"],
        "target": best["target"],
        "metric": best["metric"],
        "trtr": round(best["trtr"], 4),
        "tstr": round(best["tstr"], 4),
        "ratio": round(ratio, 4),
        "features": best["features"],
        "candidates": tried,
        "excluded_as_leaked": leaked,
        "explanation": (
            f"A model trained only on synthetic data reaches {round(ratio * 100)}% of one "
            f"trained on real data, both tested on the same held-out real records "
            f"(target: {best['target']}, {best['metric']})."
        ),
    }


# --------------------------------------------------------------------------
# Privacy
# --------------------------------------------------------------------------

def privacy_scores(
    train_real: pd.DataFrame,
    holdout_real: pd.DataFrame,
    synth: pd.DataFrame,
    table: Table,
    seed: int,
) -> dict[str, Any]:
    """Exact-match leakage, distance to closest record, membership inference."""
    compare = [
        c.name for c in table.columns
        if c.name in real_and_synth(train_real, synth)
        and c.semantic not in ("primary_key", "foreign_key")
    ]

    exact = 0
    if compare:
        real_keys = set(map(tuple, train_real[compare].astype(str).to_numpy()))
        synth_keys = list(map(tuple, synth[compare].astype(str).to_numpy()))
        exact = sum(1 for row in synth_keys if row in real_keys)

    columns = _modelling_columns(table, train_real)
    dcr: float | None = None
    baseline: float | None = None
    membership_auc: float | None = None

    if len(columns) >= 2:
        categories = _category_map(train_real, table, columns)
        real_enc = _encode(train_real, table, columns, categories)
        hold_enc = _encode(holdout_real, table, columns, categories)
        synth_enc = _encode(synth, table, columns, categories)

        # Min-max scale on the real data so every column contributes equally.
        low, high = real_enc.min(), real_enc.max()
        span = (high - low).replace(0, 1.0)

        def scale(frame: pd.DataFrame) -> np.ndarray:
            return ((frame - low) / span).fillna(0.5).to_numpy()

        real_matrix, synth_matrix, hold_matrix = scale(real_enc), scale(synth_enc), scale(hold_enc)

        if len(real_matrix) > 2 and len(synth_matrix) > 0:
            neighbours = NearestNeighbors(n_neighbors=1).fit(real_matrix)
            dcr = float(np.percentile(neighbours.kneighbors(synth_matrix)[0][:, 0], 5))

            # Real-to-real baseline, skipping each row's match with itself.
            self_nn = NearestNeighbors(n_neighbors=2).fit(real_matrix)
            baseline = float(np.percentile(self_nn.kneighbors(real_matrix)[0][:, 1], 5))

        # Membership inference: if training rows sit closer to the synthetic
        # data than unseen rows do, the generator memorised its training set.
        if len(synth_matrix) > 2 and len(hold_matrix) > 5 and len(real_matrix) > 5:
            to_synth = NearestNeighbors(n_neighbors=1).fit(synth_matrix)
            member_d = to_synth.kneighbors(real_matrix)[0][:, 0]
            outsider_d = to_synth.kneighbors(hold_matrix)[0][:, 0]
            labels = np.concatenate([np.ones(len(member_d)), np.zeros(len(outsider_d))])
            # Closer means more likely to be a member, hence the negation.
            scores = -np.concatenate([member_d, outsider_d])
            if len(set(labels)) == 2:
                membership_auc = float(roc_auc_score(labels, scores))

    score = 100.0
    if exact > 0:
        score -= min(60.0, 100.0 * exact / max(len(synth), 1) + 20.0)
    if dcr is not None and baseline is not None and baseline > 0:
        # Synthetic records should sit no closer to the training data than
        # training records sit to each other.
        ratio = dcr / baseline
        if ratio < 1.0:
            score -= min(25.0, (1.0 - ratio) * 50.0)
    if membership_auc is not None:
        score -= min(25.0, abs(membership_auc - 0.5) * 100.0)

    return {
        "score": round(max(0.0, score), 1),
        "exact_matches": exact,
        "exact_match_rate": round(exact / max(len(synth), 1), 6),
        "dcr": round(dcr, 4) if dcr is not None else None,
        "dcr_baseline": round(baseline, 4) if baseline is not None else None,
        "membership_auc": round(membership_auc, 4) if membership_auc is not None else None,
        "explanation": (
            "No synthetic record is a copy of a real one, and training records are "
            "no closer to the output than unseen records are."
            if exact == 0 else
            f"{exact} synthetic rows are identical to real records and must be resampled."
        ),
    }


def real_and_synth(real: pd.DataFrame, synth: pd.DataFrame) -> set[str]:
    return set(real.columns) & set(synth.columns)


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

def detection_auc(
    real: pd.DataFrame, synth: pd.DataFrame, table: Table, seed: int
) -> dict[str, Any]:
    """Can a classifier tell real from synthetic? 0.50 means it cannot."""
    columns = _modelling_columns(table, real)
    if len(columns) < 2:
        return {"auc": None, "available": False, "reason": "Not enough columns."}

    categories = _category_map(real, table, columns)
    n = min(len(real), len(synth))
    if n < 40:
        return {"auc": None, "available": False, "reason": "Not enough rows."}

    rng = np.random.default_rng(seed)
    real_sample = real.iloc[rng.choice(len(real), n, replace=False)]
    synth_sample = synth.iloc[rng.choice(len(synth), n, replace=False)]

    x = pd.concat([
        _encode(real_sample, table, columns, categories),
        _encode(synth_sample, table, columns, categories),
    ], ignore_index=True)
    y = np.concatenate([np.zeros(n), np.ones(n)])

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.3, random_state=seed, stratify=y
    )
    model = HistGradientBoostingClassifier(max_iter=120, random_state=seed, early_stopping=False)
    model.fit(x_train, y_train)
    auc = float(roc_auc_score(y_test, model.predict_proba(x_test)[:, 1]))

    return {
        "auc": round(auc, 4),
        "available": True,
        "score": round(max(0.0, 100.0 - abs(auc - 0.5) * 200.0), 1),
        "explanation": (
            f"A classifier separates real from synthetic at {auc:.2f} AUC. "
            "0.50 means the two are indistinguishable."
        ),
    }


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def build_trust_report(
    real: pd.DataFrame,
    table: Table,
    seeds: SeedFactory,
    *,
    target: str | None = None,
    integrity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run every check against a generator refitted on the training split only."""
    seed = seeds.seed
    real = coerce_to_schema(real, table)
    if len(real) < 40:
        return {
            "available": False,
            "reason": f"Need at least 40 rows to validate; got {len(real)}.",
        }

    train_real, holdout_real = train_test_split(real, test_size=0.3, random_state=seed)
    train_real = train_real.reset_index(drop=True)
    holdout_real = holdout_real.reset_index(drop=True)

    # The critical step: this generator never sees the holdout.
    audit_seeds = SeedFactory(seed)
    model = fit_table(table, train_real, audit_seeds)
    synth = sample_table(model, len(train_real), audit_seeds)

    fidelity = fidelity_scores(train_real, synth, table, model)
    utility = utility_score(
        train_real, holdout_real, synth, table, seed, target,
        conditioned_on=getattr(model, "condition_column", None),
    )
    privacy = privacy_scores(train_real, holdout_real, synth, table, seed)
    detection = detection_auc(train_real, synth, table, seed)

    integrity = integrity or {"passed": True, "score": 100.0}
    gates = {
        "integrity": bool(integrity.get("passed", True)),
        "no_exact_matches": privacy["exact_matches"] == 0,
        "fidelity_above_70": fidelity["score"] >= 70,
    }

    weights = {"integrity": 0.30, "fidelity": 0.25, "utility": 0.30, "privacy": 0.15}
    overall = (
        weights["integrity"] * float(integrity.get("score", 100.0))
        + weights["fidelity"] * fidelity["score"]
        + weights["utility"] * (utility["score"] if utility.get("available") else fidelity["score"])
        + weights["privacy"] * privacy["score"]
    )

    return {
        "available": True,
        "seed": seed,
        "table": table.name,
        "conditioned_on": getattr(model, "condition_column", None),
        "condition_strength": getattr(model, "condition_strength", 0.0),
        "rows_evaluated": len(train_real),
        "holdout_rows": len(holdout_real),
        "overall": round(overall, 1),
        "integrity": integrity,
        "fidelity": fidelity,
        "utility": utility,
        "privacy": privacy,
        "detection": detection,
        "gates": gates,
        "export_allowed": all(gates.values()),
    }
