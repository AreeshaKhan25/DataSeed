"""Tabular generation, a Gaussian copula fitted per table.

Why a copula rather than a GAN: it is deterministic under a seed, fits in
milliseconds, needs no GPU, and cannot silently fail to converge. Every step is
explainable, which matters more here than squeezing out the last point of fidelity.

The method:
  fit     x -> u = F(x) -> z = PPF(u), then estimate the covariance of Z
  sample  z ~ N(0, Sigma) -> u = CDF(z) -> x = F_inv(u)

F is the empirical marginal, so each column keeps its own shape exactly while
Sigma carries the cross-column correlation.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from faker import Faker
from scipy import stats

from .schema import Column, Table, coerce_to_schema
from .seeds import SeedFactory

# Clipping u away from {0, 1} is mandatory: PPF(0) is -inf and PPF(1) is +inf,
# and a single infinity poisons the whole covariance estimate.
_EPS = 1e-6

# Semantic types we generate from scratch rather than resampling. Resampling a
# real name or email would copy a real person's data into the output, which is
# the one thing this platform must never do.
_FAKER_MAP: dict[str, str] = {
    "person_name": "name",
    "email": "email",
    "phone": "phone_number",
    "address": "street_address",
    "city": "city",
    "country": "country",
    "postcode": "postcode",
    "company": "company",
    "iban": "iban",
    "url": "url",
    "national_id": "ssn",
    "free_text": "sentence",
    "sku": "sku",
}


def _ecdf_forward(values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Map observed values to uniform (0,1) via their empirical ranks.

    Ties are broken randomly rather than averaged, so that a heavily tied column
    still spreads across the unit interval instead of collapsing onto one point.
    """
    n = len(values)
    if n == 0:
        return np.array([])
    jitter = rng.random(n) * 1e-9
    ranks = stats.rankdata(values + jitter, method="ordinal")
    return (ranks - 0.5) / n


def _ecdf_inverse(sorted_values: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Map uniforms back to values by interpolating the empirical quantiles."""
    if len(sorted_values) == 0:
        return np.zeros(len(u))
    if len(sorted_values) == 1:
        return np.full(len(u), sorted_values[0])
    positions = np.linspace(0.0, 1.0, len(sorted_values))
    return np.interp(u, positions, sorted_values)


def _decimal_places(series: pd.Series, cap: int = 6) -> int | None:
    """How many decimals the source actually uses.

    A currency column is quoted to the cent, so its synthetic counterpart must
    be too -- otherwise `qty * unit_price` stops landing on a round figure and
    every total downstream drifts by fractions of a penny.
    """
    sample = series.dropna().astype(float).head(2000)
    if sample.empty:
        return None
    seen = 0
    for value in sample:
        text = f"{value:.10f}".rstrip("0")
        places = len(text.split(".")[1]) if "." in text else 0
        seen = max(seen, places)
        if seen >= cap:
            return cap
    return seen


def _nearest_psd(matrix: np.ndarray) -> np.ndarray:
    """Force a correlation matrix to be positive semi-definite.

    Near-duplicate columns produce a singular matrix that Cholesky rejects.
    Clipping the eigenvalues and renormalising is the cheapest reliable fix.
    """
    matrix = (matrix + matrix.T) / 2.0
    eigvals, eigvecs = np.linalg.eigh(matrix)
    eigvals = np.clip(eigvals, 1e-6, None)
    rebuilt = eigvecs @ np.diag(eigvals) @ eigvecs.T
    diag = np.sqrt(np.clip(np.diag(rebuilt), 1e-12, None))
    rebuilt = rebuilt / np.outer(diag, diag)
    np.fill_diagonal(rebuilt, 1.0)
    return rebuilt


class ColumnModel:
    """How one column is produced. Exactly one mode is active."""

    __slots__ = (
        "column", "mode", "sorted_values", "categories", "cum_bounds",
        "constant", "faker_provider", "forbidden", "decimals",
    )

    def __init__(self, column: Column) -> None:
        self.column = column
        self.mode: str = "constant"
        self.sorted_values: np.ndarray = np.array([])
        self.categories: list[Any] = []
        self.cum_bounds: np.ndarray = np.array([])
        self.constant: Any = None
        self.faker_provider: str | None = None
        # Hashes (never values) of the source entries for this column, so a
        # coincidental Faker collision with a real person can be rejected
        # without the model retaining any real data.
        self.forbidden: set[str] = set()
        # Decimal places observed in the source. Money is quoted to the cent;
        # emitting 44.665593 breaks every downstream sum and is visible the
        # moment anyone opens the CSV in a spreadsheet.
        self.decimals: int | None = None

    @property
    def in_copula(self) -> bool:
        return self.mode in ("numeric", "datetime", "categorical")


class TableModel:
    """A fitted generator for one table.

    A single copula has one covariance matrix for the whole table, so it can
    only express relationships that hold globally. When a categorical column
    genuinely partitions the data -- premium customers behave differently from
    standard ones -- the global fit averages those groups together and the
    dependence washes out.

    `condition_column` switches on a mixture instead: one copula per group, and
    sampling draws the group first. Each sub-model is itself an ordinary
    TableModel with no further nesting.
    """

    def __init__(self, table: Table) -> None:
        self.table = table
        self.models: dict[str, ColumnModel] = {}
        self.copula_columns: list[str] = []
        self.correlation: np.ndarray = np.eye(0)
        self.fitted_rows: int = 0
        self.condition_column: str | None = None
        self.condition_values: list[Any] = []
        self.condition_probs: list[float] = []
        self.groups: dict[Any, "TableModel"] = {}
        self.condition_strength: float = 0.0


def _resolve_mode(column: Column, series: pd.Series) -> str:
    """Decide how a column is produced. Order matters."""
    if column.semantic == "primary_key":
        return "sequence"
    if column.semantic == "foreign_key":
        return "foreign_key"

    non_null = series.dropna()
    if non_null.empty:
        return "null"
    if non_null.nunique() == 1:
        return "constant"

    # Direct PII and free text are always synthesised from scratch, never
    # resampled, regardless of cardinality.
    if column.pii == "direct" or column.semantic in ("free_text",):
        if column.semantic in _FAKER_MAP:
            return "faker"

    if column.dtype == "int" and non_null.nunique() <= 20:
        # A 0/1 flag or a small ordinal is a category wearing a number's
        # clothing. Running it through the continuous path would let the
        # rank transform spread two values across the whole real line.
        return "categorical"
    if column.dtype in ("int", "float"):
        return "numeric"
    if column.dtype in ("date", "datetime"):
        return "datetime"
    if column.dtype == "bool":
        return "categorical"

    # Strings: resampling a small set of labels ("Premium", "shipped") is safe
    # and preserves the real distribution. A high-cardinality string column is
    # effectively an identifier, so it gets faked instead of copied.
    unique_ratio = non_null.nunique() / len(non_null)
    if non_null.nunique() <= 200 and unique_ratio < 0.5:
        return "categorical"
    if column.semantic in _FAKER_MAP:
        return "faker"
    return "faker_text"


# A group needs enough rows for its own covariance estimate to mean anything.
_OTHER = object()   # pooled remainder: categories too rare to fit alone
MIN_GROUP_ROWS = 60
# Below this dependence, splitting costs more in estimation noise than it buys.
MIN_CONDITION_STRENGTH = 0.06


def _correlation_ratio(labels: np.ndarray, values: np.ndarray) -> float:
    """eta-squared: the share of a numeric column's variance explained by a
    categorical one. 0 means the groups are indistinguishable, 1 means the
    group determines the value.
    """
    keep = ~pd.isna(values)
    labels, values = labels[keep], values[keep].astype(float)
    if len(values) < 8:
        return 0.0
    total_var = values.var()
    if total_var <= 0:
        return 0.0
    grand = values.mean()
    between = 0.0
    for group in pd.unique(labels):
        member = values[labels == group]
        if len(member) == 0:
            continue
        between += len(member) * (member.mean() - grand) ** 2
    return float(min(1.0, between / (total_var * len(values))))


def select_condition_column(table: Table, df: pd.DataFrame) -> tuple[str | None, float]:
    """Pick the categorical column that best explains the rest of the table.

    Chosen purely from the data by a generic criterion, before anything knows
    what a downstream model might be asked to predict. That ordering matters:
    picking the column because it happens to be an evaluation target would be
    tuning the generator to its own score.
    """
    if len(df) < MIN_GROUP_ROWS * 2:
        return None, 0.0

    numeric = [
        c.name for c in table.columns
        if c.dtype in ("int", "float", "date", "datetime")
        and c.semantic not in ("primary_key", "foreign_key")
        and c.name in df.columns
        and df[c.name].notna().sum() > 20
        and df[c.name].dropna().nunique() > 20
    ]
    if not numeric:
        return None, 0.0

    best: tuple[str | None, float] = (None, 0.0)
    for column in table.columns:
        if column.semantic in ("primary_key", "foreign_key") or column.pii == "direct":
            continue
        if column.name not in df.columns:
            continue
        series = df[column.name]
        is_categorical = (
            column.dtype in ("str", "bool")
            or (column.dtype == "int" and series.dropna().nunique() <= 20)
        )
        if not is_categorical:
            continue

        counts = series.value_counts(dropna=True)
        if not 2 <= len(counts) <= 8 or counts.min() < MIN_GROUP_ROWS:
            continue

        labels = series.to_numpy()
        scores = []
        for target in numeric:
            values = df[target]
            if values.dtype.kind == "M":
                values = values.astype("int64").where(values.notna())
            scores.append(_correlation_ratio(labels, values.to_numpy()))
        strength = float(np.mean(scores)) if scores else 0.0
        if strength > best[1]:
            best = (column.name, strength)

    if best[0] is None or best[1] < MIN_CONDITION_STRENGTH:
        return None, best[1]
    return best


def fit_table(
    table: Table,
    df: pd.DataFrame,
    seeds: SeedFactory,
    *,
    conditional: bool = True,
    condition_column: str | None = None,
) -> TableModel:
    """Fit marginals and a correlation matrix. The frame is not retained."""
    df = coerce_to_schema(df, table)
    model = TableModel(table)
    model.fitted_rows = len(df)
    rng = seeds.stream(f"fit:{table.name}")

    z_columns: dict[str, np.ndarray] = {}

    for column in table.columns:
        series = df[column.name] if column.name in df.columns else pd.Series(dtype="object")
        cm = ColumnModel(column)
        cm.mode = _resolve_mode(column, series)
        non_null = series.dropna()

        if cm.mode == "constant":
            cm.constant = non_null.iloc[0] if len(non_null) else None

        elif cm.mode in ("faker", "faker_text"):
            cm.faker_provider = _FAKER_MAP.get(column.semantic, "")
            if not cm.faker_provider:
                # No known semantic, so match the shape of what is there. A
                # product title of three words should not come back as a single
                # dictionary word, which is what a fixed fallback produces.
                words = non_null.astype(str).str.split().str.len()
                typical = float(words.median()) if len(words) else 1.0
                if typical >= 5:
                    cm.faker_provider = "sentence"
                elif typical >= 2:
                    cm.faker_provider = "catch_phrase"
                else:
                    cm.faker_provider = "word"
            cm.forbidden = {_fingerprint(v) for v in non_null.astype(str)}

        elif cm.mode == "numeric":
            values = non_null.astype(float).to_numpy()
            cm.sorted_values = np.sort(values)
            cm.decimals = _decimal_places(non_null)
            z_columns[column.name] = stats.norm.ppf(
                np.clip(_ecdf_forward(values, rng), _EPS, 1 - _EPS)
            )

        elif cm.mode == "datetime":
            values = (non_null.astype("int64") // 10**9).astype(float).to_numpy()
            cm.sorted_values = np.sort(values)
            z_columns[column.name] = stats.norm.ppf(
                np.clip(_ecdf_forward(values, rng), _EPS, 1 - _EPS)
            )

        elif cm.mode == "categorical":
            freqs = non_null.value_counts(normalize=True)
            cm.categories = list(freqs.index)
            cm.cum_bounds = np.cumsum(freqs.to_numpy())
            cm.cum_bounds[-1] = 1.0

            # Place each observation uniformly inside its category's slice of
            # [0,1]. That is what lets a categorical column participate in the
            # correlation matrix alongside the numerics.
            lower = np.concatenate([[0.0], cm.cum_bounds[:-1]])
            index_of = {cat: i for i, cat in enumerate(cm.categories)}
            idx = non_null.map(index_of).to_numpy()
            u = lower[idx] + rng.random(len(idx)) * (cm.cum_bounds[idx] - lower[idx])
            z_columns[column.name] = stats.norm.ppf(np.clip(u, _EPS, 1 - _EPS))

        model.models[column.name] = cm

    # Correlation over the copula columns only. Rows with any missing value are
    # dropped for this estimate; nulls are re-applied after sampling.
    names = [n for n in z_columns if len(z_columns[n]) == len(df)]
    if len(names) >= 2:
        matrix = np.column_stack([z_columns[n] for n in names])
        keep = ~np.isnan(matrix).any(axis=1)
        matrix = matrix[keep]
        if len(matrix) > 2:
            corr = np.corrcoef(matrix, rowvar=False)
            corr = np.nan_to_num(corr, nan=0.0)
            model.correlation = _nearest_psd(corr)
            model.copula_columns = names
    elif len(names) == 1:
        model.copula_columns = names
        model.correlation = np.eye(1)

    # -- conditional mixture ------------------------------------------------
    if conditional:
        chosen, strength = (
            (condition_column, 1.0) if condition_column
            else select_condition_column(table, df)
        )
        if chosen and chosen in df.columns:
            counts = df[chosen].value_counts(dropna=True)
            viable = counts[counts >= MIN_GROUP_ROWS]
            if len(viable) >= 2:
                model.condition_column = chosen
                model.condition_strength = round(strength, 4)
                total = float(counts.sum())
                model.condition_values = [v for v in viable.index]
                model.condition_probs = [float(counts[v] / total) for v in viable.index]

                for value in model.condition_values:
                    subset = df[df[chosen] == value]
                    # conditional=False: one level of mixture, never a tree.
                    group = fit_table(table, subset, seeds, conditional=False)
                    # A group only sees its own rows, so its collision guard
                    # would only know its own values -- and could emit a real
                    # name belonging to a different group. Give every sub-model
                    # the whole table's fingerprints.
                    for name, cm in group.models.items():
                        parent_cm = model.models.get(name)
                        if parent_cm is not None and parent_cm.forbidden:
                            cm.forbidden = parent_cm.forbidden
                    model.groups[value] = group

                # Rows in groups too small to fit keep the global model, so the
                # rare categories are still represented rather than dropped.
                leftover = float(1.0 - sum(model.condition_probs))
                if leftover > 1e-9:
                    model.condition_values.append(_OTHER)
                    model.condition_probs.append(leftover)
                    model.groups[_OTHER] = fit_table(table, df, seeds, conditional=False)

    return model


def _fingerprint(value: str) -> str:
    """A short, one-way marker for a source value.

    The model keeps these instead of the values themselves, so it can refuse to
    emit a real record without ever being able to reconstruct one.
    """
    import hashlib

    return hashlib.sha256(value.strip().lower().encode()).hexdigest()[:16]


def _faker_values_safe(
    provider: str, n: int, faker: Faker, forbidden: set[str]
) -> list[Any]:
    """Generate n values, none of which appear in the source data.

    Faker draws from a finite pool, so on a large table it will eventually
    reproduce a real name or email by chance. Left unchecked that is a genuine
    privacy leak, and the trust report would correctly fail the run.
    """
    values = _faker_values(provider, n, faker)
    if not forbidden:
        return values

    for index, value in enumerate(values):
        attempts = 0
        while _fingerprint(str(value)) in forbidden and attempts < 12:
            value = _faker_values(provider, 1, faker)[0]
            attempts += 1
        if _fingerprint(str(value)) in forbidden:
            # Exhausted the pool: perturb deterministically rather than give up.
            value = f"{value} {faker.random_int(100, 999)}"
        values[index] = value
    return values


def _faker_values(provider: str, n: int, faker: Faker) -> list[Any]:
    if provider == "catch_phrase":
        return [faker.catch_phrase() for _ in range(n)]
    if provider == "sentence":
        return [faker.sentence(nb_words=8) for _ in range(n)]
    if provider == "sku":
        return [f"SKU-{faker.random_int(10000, 99999)}" for _ in range(n)]
    method = getattr(faker, provider, None)
    if method is None:
        return [faker.word() for _ in range(n)]
    return [method() for _ in range(n)]


def _sample_core(
    model: TableModel,
    rows: int,
    rng: np.random.Generator,
    faker: Faker,
    pk_start: int,
) -> pd.DataFrame:
    """Draw rows from a single (unconditioned) copula fit.

    No null or outlier injection here -- those run once on the assembled frame
    so a mixture does not apply them per group.
    """
    table = model.table
    out: dict[str, Any] = {}

    # One correlated normal draw drives every copula column at once.
    u_matrix: dict[str, np.ndarray] = {}
    if model.copula_columns:
        k = len(model.copula_columns)
        corr = model.correlation if model.correlation.shape == (k, k) else np.eye(k)
        z = rng.multivariate_normal(np.zeros(k), corr, size=rows, method="cholesky")
        u = stats.norm.cdf(z)
        for i, name in enumerate(model.copula_columns):
            u_matrix[name] = np.clip(u[:, i], _EPS, 1 - _EPS)

    for column in table.columns:
        cm = model.models[column.name]
        name = column.name

        if cm.mode == "sequence":
            out[name] = np.arange(pk_start, pk_start + rows)

        elif cm.mode == "foreign_key":
            # Filled in by the relational engine. Kept as a typed placeholder so
            # column order and dtype survive.
            out[name] = np.full(rows, np.nan)

        elif cm.mode == "null":
            out[name] = np.full(rows, np.nan)

        elif cm.mode == "constant":
            out[name] = [cm.constant] * rows

        elif cm.mode in ("faker", "faker_text"):
            out[name] = _faker_values_safe(
                cm.faker_provider or "word", rows, faker, cm.forbidden
            )

        elif cm.mode == "numeric":
            u = u_matrix.get(name, rng.random(rows))
            values = _ecdf_inverse(cm.sorted_values, u)
            if column.dtype == "int":
                values = np.rint(values)
            elif cm.decimals is not None:
                values = np.round(values, cm.decimals)
            out[name] = values

        elif cm.mode == "datetime":
            u = u_matrix.get(name, rng.random(rows))
            epoch = _ecdf_inverse(cm.sorted_values, u)
            values = pd.to_datetime(np.rint(epoch), unit="s")
            if column.dtype == "date":
                # The source had no time component, so neither can the output.
                # Interpolating between two dates otherwise lands mid-day and
                # a "date" column starts emitting timestamps.
                values = values.normalize()
            out[name] = values

        elif cm.mode == "categorical":
            u = u_matrix.get(name, rng.random(rows))
            idx = np.searchsorted(cm.cum_bounds, u, side="left")
            idx = np.clip(idx, 0, len(cm.categories) - 1)
            out[name] = [cm.categories[i] for i in idx]

        else:  # pragma: no cover - every mode is handled above
            out[name] = [None] * rows

    return pd.DataFrame(out, columns=[c.name for c in table.columns])


def sample_table(
    model: TableModel,
    rows: int,
    seeds: SeedFactory,
    *,
    null_rate: float | None = None,
    outlier_rate: float = 0.0,
    pk_start: int = 1,
) -> pd.DataFrame:
    """Draw `rows` synthetic rows from a fitted TableModel.

    With a conditioning column, the group is drawn first and the rest of the row
    comes from that group's own copula. That is what preserves relationships a
    single global covariance matrix averages away.
    """
    table = model.table
    rng = seeds.stream(f"sample:{table.name}")
    faker = Faker(["en_US"])
    faker.seed_instance(int(rng.integers(0, 2**31 - 1)))

    if model.condition_column and model.groups:
        probs = np.array(model.condition_probs, dtype=float)
        probs = probs / probs.sum()
        counts = rng.multinomial(rows, probs)

        frames = []
        for value, n in zip(model.condition_values, counts):
            if n <= 0:
                continue
            sub = model.groups.get(value)
            if sub is None:
                continue
            frames.append(_sample_core(sub, int(n), rng, faker, 1))

        if frames:
            df = pd.concat(frames, ignore_index=True)
            # Groups are generated in blocks; shuffle so the output is not
            # sorted by the conditioning column.
            df = df.iloc[rng.permutation(len(df))].reset_index(drop=True)
            # Sequence columns must be reassigned across the whole frame, or
            # each group would restart the counter and duplicate keys.
            for column in table.columns:
                if model.models[column.name].mode == "sequence":
                    df[column.name] = np.arange(pk_start, pk_start + len(df))
        else:
            df = _sample_core(model, rows, rng, faker, pk_start)
    else:
        df = _sample_core(model, rows, rng, faker, pk_start)

    df = _enforce_unique(df, table, model)
    df = _inject_outliers(df, table, model, rng, outlier_rate)
    df = _inject_nulls(df, table, model, rng, null_rate)
    return df


def _enforce_unique(
    df: pd.DataFrame, table: Table, model: TableModel
) -> pd.DataFrame:
    """Make columns the profiler found to be unique actually unique.

    Faker draws from a finite pool and a categorical resamples by definition, so
    a column that held a distinct value on every source row will otherwise come
    back with duplicates. A reference or code column that repeats breaks any
    downstream join that assumed it was a key.
    """
    for column in table.columns:
        if not column.unique or column.name not in df.columns:
            continue
        mode = getattr(model.models.get(column.name), "mode", None)
        if mode in ("sequence", "foreign_key", "null", "constant"):
            continue

        series = df[column.name]
        duplicated = series.duplicated(keep="first") & series.notna()
        if not duplicated.any():
            continue

        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            highest = numeric.max()
            start = int(highest) + 1 if pd.notna(highest) else 1
            df.loc[duplicated, column.name] = np.arange(start, start + int(duplicated.sum()))
        else:
            # Suffix rather than regenerate, so the value keeps its shape and
            # stays recognisable as the same kind of code.
            df.loc[duplicated, column.name] = [
                f"{value}-{i + 1}" for i, value in enumerate(series[duplicated].astype(str))
            ]
    return df


def _inject_outliers(
    df: pd.DataFrame,
    table: Table,
    model: TableModel,
    rng: np.random.Generator,
    rate: float,
) -> pd.DataFrame:
    """Push a few numeric values past the observed range.

    Edge cases are the reason engineers want synthetic data at all, so this is a
    feature rather than noise. Outliers stay on the correct side of zero for
    currency columns to avoid producing nonsense negatives.
    """
    if rate <= 0:
        return df
    for column in table.columns:
        cm = model.models[column.name]
        if cm.mode != "numeric" or len(cm.sorted_values) == 0:
            continue
        n_out = int(len(df) * rate)
        if n_out < 1:
            continue
        idx = rng.choice(len(df), size=n_out, replace=False)
        low, high = cm.sorted_values[0], cm.sorted_values[-1]
        spread = max(high - low, 1.0)
        multipliers = rng.uniform(1.5, 3.0, size=n_out)
        values = high + spread * (multipliers - 1.0)
        if column.dtype == "int":
            values = np.rint(values)
        df.loc[df.index[idx], column.name] = values
    return df


def _inject_nulls(
    df: pd.DataFrame,
    table: Table,
    model: TableModel,
    rng: np.random.Generator,
    override: float | None,
) -> pd.DataFrame:
    """Re-apply missingness. Keys are never nulled."""
    for column in table.columns:
        cm = model.models[column.name]
        if cm.mode in ("sequence", "foreign_key", "null"):
            continue
        rate = column.null_rate if override is None else override
        if rate <= 0:
            continue
        mask = rng.random(len(df)) < rate
        if mask.any():
            df.loc[mask, column.name] = None
    return df


def apply_privacy(df: pd.DataFrame, table: Table, seeds: SeedFactory) -> pd.DataFrame:
    """Apply per-column privacy modes after generation.

    `synthesize` and `passthrough` are no-ops here: the values are already
    synthetic. `mask`, `hash` and `noise` transform them further.
    """
    import hashlib

    rng = seeds.stream(f"privacy:{table.name}")
    for column in table.columns:
        if column.name not in df.columns:
            continue
        values = df[column.name]

        if column.privacy == "hash":
            df[column.name] = [
                None if pd.isna(v)
                else hashlib.sha256(str(v).encode()).hexdigest()[:16]
                for v in values
            ]

        elif column.privacy == "mask":
            masked = []
            for v in values:
                if pd.isna(v):
                    masked.append(None)
                    continue
                text = str(v)
                if "@" in text:
                    local, _, domain = text.partition("@")
                    masked.append(f"{local[:1]}{'*' * max(len(local) - 1, 2)}@{domain}")
                elif len(text) <= 2:
                    masked.append("*" * len(text))
                else:
                    masked.append(f"{text[:1]}{'*' * (len(text) - 2)}{text[-1:]}")
            df[column.name] = masked

        elif column.privacy == "noise" and column.dtype in ("int", "float"):
            std = column.stats.std or 0.0
            if std > 0:
                noise = rng.normal(0, std * 0.05, size=len(df))
                shifted = pd.to_numeric(values, errors="coerce") + noise
                if column.dtype == "int":
                    shifted = np.rint(shifted)
                df[column.name] = shifted

    return df
