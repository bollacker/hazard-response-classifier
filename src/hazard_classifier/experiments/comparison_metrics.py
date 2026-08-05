"""Slice A §4.3 -- metrics and uncertainty for the L/E structure comparison
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md`,
`docs/planning/PREREGISTRATION_LE_STRUCTURE.md` §3).

**Not `hazard_classifier.metrics`.** That module is the baseline's own
evaluation surface (exact accuracy, AUC, QWK, D-17's final-label rates). This
one exists only for the offline ablation ladder and computes what the
pre-registration's selection rule actually reads: per-class F1, macro-F1, and
worst-class F1, with a cluster bootstrap over prompt groups.

Two things the plan warns go wrong here, and both inflate confidence:

- **Resampling rows rather than groups** understates the interval, because
  rows sharing a prompt are correlated. Everything below resamples
  `prompt_group_id`, never rows.
- **Comparing two candidates' marginal intervals** is a strictly weaker test
  than the interval on their **paired difference**. The pre-registration §4
  step 3 requires the paired form -- the difference computed within each
  resample, on the same resampled groups. `paired_cluster_bootstrap` is the
  function selection reads; `cluster_bootstrap_interval` exists only for
  reporting a single candidate's own uncertainty (`SCIENCE.md` §Evidence and
  outputs, Estimability) and **must not** be used to decide separation.

L and E are computed by calling these on each target's own rows -- nothing
here knows which target it is looking at.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

N_CLASSES = 3

# Frozen for reproducibility. The pre-registration fixes 1000 resamples (§3);
# the seed is this harness's own choice, recorded so a rerun reproduces the
# same intervals rather than merely similar ones.
N_RESAMPLES = 1000
BOOTSTRAP_SEED = 20260804

# Pre-registration §3's screening threshold: a candidate whose lowest
# per-class F1 falls below this on either target is disqualified regardless
# of its macro score. It is deliberately low and is **not** a success
# criterion -- approved per-outcome criteria are the Standards team's to set
# (`STANDARDS_REQUEST.md` Ask B) and do not exist. Named here so slice C's
# selection rule reads the constant rather than retyping the number.
WORST_CLASS_F1_FLOOR = 0.25

MetricFn = Callable[[np.ndarray, np.ndarray], float]


class UnpairableComparisonError(ValueError):
    """Two candidates share no row both could score, so no paired difference
    exists. Under `DECISIONS.md` D-45 an unavailable cell is not a wrong
    answer, so the difference is undefined rather than zero."""


@dataclass(frozen=True)
class Predictions:
    """One candidate's decided labels, plus which rows it could score at all.

    `scored` is what keeps `DECISIONS.md` D-45 honest through the metrics
    layer: a hazard whose cell was unfittable is *unavailable*, not wrong.
    Its rows are excluded from the metric rather than counted as errors,
    which would invent a result D-45 exists to prevent.
    """

    labels: np.ndarray  # int, (n,) -- value at an unscored row is meaningless
    scored: np.ndarray  # bool, (n,)

    def __post_init__(self) -> None:
        if self.labels.shape != self.scored.shape:
            raise ValueError(
                f"labels {self.labels.shape} and scored {self.scored.shape} must be the same shape"
            )

    def __len__(self) -> int:
        return int(self.labels.shape[0])

    @classmethod
    def from_proba(cls, proba: np.ndarray, *, atol: float = 1e-6) -> "Predictions":
        """Decide labels by `argmax` over a candidate's `(n, 3)` output.

        An **all-NaN** row is an unscored row -- the `Candidate` protocol's
        one declared exception, used by `R` for a hazard whose cell was
        unfittable (D-45). A **partially** NaN row is a candidate bug, not an
        unavailability signal, and raises rather than being silently treated
        as either.

        Ties go to the lowest class index (`np.argmax`'s own rule) --
        arbitrary but deterministic, which is what reproducibility needs.
        """
        proba = np.asarray(proba, dtype=np.float64)
        if proba.ndim != 2 or proba.shape[1] != N_CLASSES:
            raise ValueError(f"expected an (n, {N_CLASSES}) probability array, got {proba.shape}")

        nan_counts = np.isnan(proba).sum(axis=1)
        partial = (nan_counts > 0) & (nan_counts < N_CLASSES)
        if partial.any():
            raise ValueError(
                f"{int(partial.sum())} row(s) are partially NaN. A candidate reports an "
                "unavailable cell as an all-NaN row (D-45); a partially NaN row is a bug."
            )

        scored = nan_counts == 0
        if scored.any():
            sums = proba[scored].sum(axis=1)
            if not np.allclose(sums, 1.0, atol=atol):
                worst = float(np.max(np.abs(sums - 1.0)))
                raise ValueError(
                    f"scored rows must sum to 1 (worst deviation {worst:.3g}); the "
                    "Candidate protocol requires a normalized three-class output"
                )

        labels = np.zeros(len(proba), dtype=np.int64)
        if scored.any():
            labels[scored] = np.argmax(proba[scored], axis=1)
        return cls(labels=labels, scored=scored)


@dataclass(frozen=True)
class ClassificationMetrics:
    """What the pre-registration §3 reads, plus the coverage it was computed
    over. `accuracy` is reported as a diagnostic only -- §3 is explicit that
    a single accuracy figure is not used at any point in selection, because
    the class balance makes a majority-class predictor look strong.
    """

    per_class_f1: tuple[float, float, float]
    macro_f1: float
    worst_class_f1: float
    accuracy: float
    n_scored: int
    n_total: int

    @property
    def coverage(self) -> float:
        return self.n_scored / self.n_total if self.n_total else 0.0

    def as_dict(self) -> dict:
        return {
            "per_class_f1": list(self.per_class_f1),
            "macro_f1": self.macro_f1,
            "worst_class_f1": self.worst_class_f1,
            "accuracy": self.accuracy,
            "n_scored": self.n_scored,
            "n_total": self.n_total,
            "coverage": self.coverage,
        }


@dataclass(frozen=True)
class PairedDifference:
    """A paired cluster-bootstrap interval on `metric(a) - metric(b)`.

    `excludes_zero` is precisely the pre-registration §4 step 3 test: the top
    candidate is selected outright only if this is `True` against the
    next-ranked candidate. When it is `False` the candidates are tied and
    §4.1's tie-break decides.
    """

    point_estimate: float
    ci_low: float
    ci_high: float
    ci_level: float
    n_resamples: int
    n_groups: int
    n_paired_rows: int

    @property
    def excludes_zero(self) -> bool:
        return self.ci_low > 0.0 or self.ci_high < 0.0

    def as_dict(self) -> dict:
        return {
            "point_estimate": self.point_estimate,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "ci_level": self.ci_level,
            "excludes_zero": self.excludes_zero,
            "n_resamples": self.n_resamples,
            "n_groups": self.n_groups,
            "n_paired_rows": self.n_paired_rows,
        }


@dataclass(frozen=True)
class BootstrapInterval:
    """A single candidate's own cluster-bootstrap interval.

    For **reporting** an uncertainty estimate alongside a point value
    (`SCIENCE.md` §Evidence and outputs, Estimability). Never for deciding
    separation between two candidates -- overlapping marginal intervals are
    a strictly weaker test than the paired difference, and the
    pre-registration requires the paired form.
    """

    point_estimate: float
    ci_low: float
    ci_high: float
    ci_level: float
    n_resamples: int
    n_groups: int

    def as_dict(self) -> dict:
        return {
            "point_estimate": self.point_estimate,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "ci_level": self.ci_level,
            "n_resamples": self.n_resamples,
            "n_groups": self.n_groups,
        }


def _validated_labels(values, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional, got shape {array.shape}")
    if array.dtype.kind == "f" and np.isnan(array).any():
        raise ValueError(f"{name} contains NaN; ground-truth labels must be present")
    array = array.astype(np.int64)
    if array.size and (array.min() < 0 or array.max() >= N_CLASSES):
        raise ValueError(f"{name} must be in {{0, 1, 2}}, got range [{array.min()}, {array.max()}]")
    return array


def confusion_matrix(y_true, y_pred) -> np.ndarray:
    """`(3, 3)` counts, `C[i, j] = #(true == i and predicted == j)`.

    Computed by `bincount` rather than by three nested comparisons so the
    bootstrap's thousands of recomputations stay cheap. Equivalence with
    sklearn is pinned by a test rather than assumed.
    """
    y_true = _validated_labels(y_true, "y_true")
    y_pred = _validated_labels(y_pred, "y_pred")
    if y_true.shape != y_pred.shape:
        raise ValueError(f"y_true {y_true.shape} and y_pred {y_pred.shape} must be the same shape")
    flat = np.bincount(N_CLASSES * y_true + y_pred, minlength=N_CLASSES * N_CLASSES)
    return flat.reshape(N_CLASSES, N_CLASSES)


def per_class_f1(y_true, y_pred) -> np.ndarray:
    """Per-class F1 over classes 0, 1, 2.

    A class the candidate never predicts but that has true instances scores
    **0**, not "undefined" -- matching sklearn's `zero_division=0`. That is
    the behavior the §3 worst-class floor depends on: a candidate that solves
    two classes by abandoning the third must score 0 on the abandoned one,
    or the floor screens nothing.
    """
    counts = confusion_matrix(y_true, y_pred).astype(np.float64)
    true_positive = np.diag(counts)
    predicted = counts.sum(axis=0)
    actual = counts.sum(axis=1)

    with np.errstate(invalid="ignore", divide="ignore"):
        precision = np.where(predicted > 0, true_positive / predicted, 0.0)
        recall = np.where(actual > 0, true_positive / actual, 0.0)
        denominator = precision + recall
        f1 = np.where(denominator > 0, 2 * precision * recall / denominator, 0.0)
    return f1


def macro_f1_score(y_true, y_pred) -> float:
    """The pre-registration §3 primary metric: the unweighted mean of the
    three per-class F1s. Macro-averaging is the direct encoding of
    `SCIENCE.md`'s requirement that all three outcomes be treated as equally
    important -- each class contributes equally regardless of frequency.
    """
    return float(per_class_f1(y_true, y_pred).mean())


def worst_class_f1_score(y_true, y_pred) -> float:
    """The §3 guard, and §4.1's first tie-break. Report this every time a
    macro is reported -- a good macro with a worst class at 0.26 has passed
    the floor and is still failing equal importance in substance.
    """
    return float(per_class_f1(y_true, y_pred).min())


def classification_metrics(y_true, predictions: Predictions) -> ClassificationMetrics:
    """Every §3 figure for one target, computed over the rows this candidate
    could actually score.

    **Coverage is reported, never silently absorbed** (`DECISIONS.md` D-67,
    carried by `PREREGISTRATION_LE_STRUCTURE.md` §3). Rows the candidate could
    not score are excluded rather than counted as errors (D-45), so a
    candidate with partial coverage is not being compared on the same rows as
    one with full coverage. That is a recorded departure from `SCIENCE.md`
    §Evidence and outputs' same-rows requirement, and `n_scored`/`n_total` is
    what keeps it visible in the numbers rather than hidden inside them. For a
    *comparison* between two candidates use `paired_cluster_bootstrap`, which
    restricts both sides to the rows they share.
    """
    y_true_all = _validated_labels(y_true, "y_true")
    if len(y_true_all) != len(predictions):
        raise ValueError(
            f"y_true has {len(y_true_all)} rows but predictions has {len(predictions)}"
        )

    scored = np.asarray(predictions.scored, dtype=bool)
    y_true_scored = y_true_all[scored]
    y_pred_scored = np.asarray(predictions.labels, dtype=np.int64)[scored]

    if len(y_true_scored) == 0:
        return ClassificationMetrics(
            per_class_f1=(0.0, 0.0, 0.0),
            macro_f1=0.0,
            worst_class_f1=0.0,
            accuracy=0.0,
            n_scored=0,
            n_total=len(y_true_all),
        )

    f1 = per_class_f1(y_true_scored, y_pred_scored)
    return ClassificationMetrics(
        per_class_f1=(float(f1[0]), float(f1[1]), float(f1[2])),
        macro_f1=float(f1.mean()),
        worst_class_f1=float(f1.min()),
        accuracy=float(np.mean(y_true_scored == y_pred_scored)),
        n_scored=int(len(y_true_scored)),
        n_total=int(len(y_true_all)),
    )


def group_row_indices(groups) -> tuple[np.ndarray, list[np.ndarray]]:
    """`(unique_groups, rows_per_group)` -- the clustering the bootstrap
    resamples over. Groups are sorted so the mapping is deterministic
    regardless of row order.
    """
    groups = np.asarray(groups)
    unique = np.unique(groups)
    return unique, [np.flatnonzero(groups == group) for group in unique]


def cluster_resample_indices(groups, rng: np.random.Generator) -> np.ndarray:
    """One cluster-bootstrap resample: draw `n_groups` **groups** with
    replacement and return the concatenated row indices they contribute.

    A group drawn twice contributes its rows twice -- that is the point of a
    cluster bootstrap, and it is why the resulting interval is wider (and
    honest) compared to resampling rows independently. Exposed rather than
    inlined so a test can assert directly that resampling happens in whole
    groups.
    """
    unique, rows_per_group = group_row_indices(groups)
    drawn = rng.integers(0, len(unique), size=len(unique))
    return np.concatenate([rows_per_group[i] for i in drawn]) if len(unique) else np.empty(0, dtype=np.int64)


def _percentile_interval(values: np.ndarray, ci_level: float) -> tuple[float, float]:
    tail = (1.0 - ci_level) / 2.0 * 100.0
    low, high = np.percentile(values, [tail, 100.0 - tail])
    return float(low), float(high)


def paired_cluster_bootstrap(
    y_true,
    predictions_a: Predictions,
    predictions_b: Predictions,
    groups,
    *,
    metric: MetricFn = macro_f1_score,
    n_resamples: int = N_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = 0.95,
) -> PairedDifference:
    """The interval the pre-registration §4 step 3 reads: `metric(a) - metric(b)`
    with the difference computed **within each resample, on the same
    resampled groups**.

    This is the paired form, and the pairing is the whole point. Computing
    two marginal intervals and checking whether they overlap is a strictly
    weaker test, and a bootstrap that draws independent resamples for `a` and
    `b` produces a non-degenerate interval even when `a` and `b` are the same
    candidate -- which is exactly what the self-comparison test in this
    module's tests forces.

    Both candidates are restricted to the rows **both** could score. A row
    only one of them scored has no difference to contribute (D-45: the other
    candidate did not get it wrong, it had nothing to say), and including it
    on one side only would compare two candidates on two different row sets.
    """
    y_true_all = _validated_labels(y_true, "y_true")
    groups_all = np.asarray(groups)
    for name, length in (
        ("predictions_a", len(predictions_a)),
        ("predictions_b", len(predictions_b)),
        ("groups", len(groups_all)),
    ):
        if length != len(y_true_all):
            raise ValueError(f"{name} has {length} rows but y_true has {len(y_true_all)}")

    paired = np.asarray(predictions_a.scored, dtype=bool) & np.asarray(
        predictions_b.scored, dtype=bool
    )
    if not paired.any():
        raise UnpairableComparisonError(
            "no row was scored by both candidates, so no paired difference is defined"
        )

    y_true_paired = y_true_all[paired]
    labels_a = np.asarray(predictions_a.labels, dtype=np.int64)[paired]
    labels_b = np.asarray(predictions_b.labels, dtype=np.int64)[paired]
    groups_paired = groups_all[paired]

    point_estimate = float(metric(y_true_paired, labels_a) - metric(y_true_paired, labels_b))

    rng = np.random.default_rng(seed)
    unique, rows_per_group = group_row_indices(groups_paired)
    differences = np.empty(n_resamples, dtype=np.float64)
    for b in range(n_resamples):
        drawn = rng.integers(0, len(unique), size=len(unique))
        index = np.concatenate([rows_per_group[i] for i in drawn])
        # Same `index` on both sides -- this single shared array is what makes
        # the difference paired rather than two independent estimates.
        differences[b] = metric(y_true_paired[index], labels_a[index]) - metric(
            y_true_paired[index], labels_b[index]
        )

    ci_low, ci_high = _percentile_interval(differences, ci_level)
    return PairedDifference(
        point_estimate=point_estimate,
        ci_low=ci_low,
        ci_high=ci_high,
        ci_level=ci_level,
        n_resamples=n_resamples,
        n_groups=int(len(unique)),
        n_paired_rows=int(paired.sum()),
    )


def cluster_bootstrap_interval(
    y_true,
    predictions: Predictions,
    groups,
    *,
    metric: MetricFn = macro_f1_score,
    n_resamples: int = N_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = 0.95,
) -> BootstrapInterval:
    """One candidate's own cluster-bootstrap interval, for **reporting** a
    point value with an uncertainty estimate (`SCIENCE.md` §Evidence and
    outputs, Estimability).

    **Not a separation test.** Two candidates' intervals from this function
    must never be compared to decide whether one beats the other -- use
    `paired_cluster_bootstrap`, per the pre-registration §4 step 3.
    """
    y_true_all = _validated_labels(y_true, "y_true")
    groups_all = np.asarray(groups)
    if len(predictions) != len(y_true_all) or len(groups_all) != len(y_true_all):
        raise ValueError("y_true, predictions, and groups must all have the same length")

    scored = np.asarray(predictions.scored, dtype=bool)
    if not scored.any():
        raise UnpairableComparisonError("this candidate scored no rows, so it has no interval")

    y_true_scored = y_true_all[scored]
    labels = np.asarray(predictions.labels, dtype=np.int64)[scored]
    groups_scored = groups_all[scored]

    point_estimate = float(metric(y_true_scored, labels))

    rng = np.random.default_rng(seed)
    unique, rows_per_group = group_row_indices(groups_scored)
    values = np.empty(n_resamples, dtype=np.float64)
    for b in range(n_resamples):
        drawn = rng.integers(0, len(unique), size=len(unique))
        index = np.concatenate([rows_per_group[i] for i in drawn])
        values[b] = metric(y_true_scored[index], labels[index])

    ci_low, ci_high = _percentile_interval(values, ci_level)
    return BootstrapInterval(
        point_estimate=point_estimate,
        ci_low=ci_low,
        ci_high=ci_high,
        ci_level=ci_level,
        n_resamples=n_resamples,
        n_groups=int(len(unique)),
    )
