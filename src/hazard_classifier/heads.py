"""`BinaryHead`: standardize + logistic + centering (`PLAN.md` §2.3, §3 step 4).

Ported from the toy's `standardize_train_test`/`fit_binary_head_weighted`
(`run_bge_hazard_weighted_heads.py` L70-110; `scoring_common.py`'s
`logit`/`sigmoid`/`centered_probability`, L412-423). Each ordinal component
(0/1/2) is modeled as two of these binary heads ("nonzero": score > 0,
"high": score == 2) -- assembling the two per `(component, hazard)` cell,
enumerating cells, and applying the D-1/D-4/D-5/D-18 exclusions that decide
*which* rows a given call gets is `model.py`'s `fit` (§3 step 4, a later
slice, IS-4): this module only fits and serves a single already-filtered,
already-weighted head, and has no notion of hazard identity at all.

**Refactor (`PLAN.md` §2.3):** the toy threads `train_x`/`test_x` in and out
of free functions and recomputes standardization/centering by hand at every
call site. This module replaces that with one small object holding
`{mean, scale, coef, intercept, center_mean}` (D-7) plus a
`predict_proba_centered` method, so a fitted head is a single serializable
value rather than five parallel arrays a caller must keep straight.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.linear_model import LogisticRegression

from hazard_classifier.config import DEFAULT_SEED

_LOGIT_CLIP = 1e-6
_SCALE_FLOOR = 1e-6

Status = Literal["fit", "skipped"]


class UnavailableOperationError(RuntimeError):
    """`DECISIONS.md` D-45 (superseding D-5): a `"skipped"` head was never
    fit, so it has no probability to serve and no substitute is invented for
    it. Reaching this means a caller bypassed the `status` check that D-3 and
    D-11 require at predict time (`rules.resolve_component_action`), so it is
    a programming error rather than a data condition -- raising is what makes
    the fail-closed guarantee testable instead of merely documented.
    """


def logit(p: np.ndarray | float) -> np.ndarray:
    """Ported from the toy's `logit` (`scoring_common.py` L412-413): clips to
    `[1e-6, 1-1e-6]` first so `0`/`1` probabilities never produce `+/-inf`.
    """
    clipped = np.clip(np.asarray(p, dtype=np.float64), _LOGIT_CLIP, 1 - _LOGIT_CLIP)
    return np.log(clipped / (1 - clipped))


def sigmoid(x: np.ndarray | float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=np.float64)))


def centered_probability(probability: np.ndarray | float, center_mean: float) -> np.ndarray:
    """Ported verbatim from the toy's `centered_probability`
    (`scoring_common.py` L420-423): recenter a probability relative to the
    training split's own mean so runs/folds are comparable.
    """
    return sigmoid(logit(probability) - float(logit(center_mean)))


def _standardize_mean_scale(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Ported from the toy's `standardize_train_test`
    (`run_bge_hazard_weighted_heads.py` L70-78): unweighted mean/std over
    every row of `x` (D-7 -- exactly the rows the caller passes in, no
    hazard-weighting, no per-hazard filtering done here), scale floored at
    `1e-6` to `1.0` so a constant feature column never divides by ~zero.
    """
    x64 = np.asarray(x, dtype=np.float64)
    mean = x64.mean(axis=0)
    scale = x64.std(axis=0)
    scale = np.where(scale < _SCALE_FLOOR, 1.0, scale)
    return mean, scale


def _raw_proba(x: np.ndarray, mean: np.ndarray, scale: np.ndarray, coef: np.ndarray, intercept: float) -> np.ndarray:
    z = (np.asarray(x, dtype=np.float64) - mean) / scale
    return sigmoid(z @ coef + intercept)


@dataclass(frozen=True)
class BinaryHead:
    """One binary head. When `status == "skipped"` the training labels were
    single-class, so no logistic fit was possible: `coef`, `intercept`, and
    `center_mean` are all `None` and this head serves nothing (D-45,
    superseding D-5's constant-probability substitute). `mean`/`scale` are
    still present because standardization is computed before the degeneracy
    check and describes the training features regardless.

    The *decision* of whether a whole component's `(component, hazard)` cells
    should therefore be marked skipped in the artifact is `model.py`'s, not
    this object's; `status` here only records what happened to *this* fit
    call.
    """

    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray | None
    intercept: float | None
    center_mean: float | None
    status: Status

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        """Raw (uncentered) `P(y=1)` for each row of `x`.

        Raises `UnavailableOperationError` on a `"skipped"` head (D-45).
        """
        if self.status == "skipped":
            raise UnavailableOperationError(
                "This head was never fit (status='skipped'): its training label was "
                "single-class, so DECISIONS.md D-45 leaves the operation unavailable "
                "rather than substituting a constant probability. Predict-time code "
                "must check the cell's status first (D-3, D-11) -- reaching this "
                "means that check was bypassed."
            )
        x = np.asarray(x, dtype=np.float64)
        return _raw_proba(x, self.mean, self.scale, self.coef, self.intercept)

    def predict_proba_centered(self, x: np.ndarray) -> np.ndarray:
        """`P(y=1)`, recentered relative to this head's own training mean
        (`self.center_mean`) via `centered_probability`.

        Raises `UnavailableOperationError` on a `"skipped"` head (D-45), via
        `predict_proba`.
        """
        probability = self.predict_proba(x)
        assert self.center_mean is not None  # guaranteed by the status check above
        return centered_probability(probability, self.center_mean)

    def to_arrays(self) -> dict[str, np.ndarray]:
        """A dict of plain numpy arrays suitable for `np.savez` (§4
        `heads.npz`). A `"skipped"` head writes only `mean`/`scale`/`status`
        (D-45) -- there are no fitted parameters to record, and no substitute
        is invented to fill the gap. `from_arrays` dispatches on `status`
        first and never looks for the absent keys.
        """
        arrays = {
            "mean": self.mean,
            "scale": self.scale,
            "status": np.asarray([self.status]),
        }
        if self.status == "skipped":
            return arrays
        return {
            **arrays,
            "coef": np.asarray(self.coef, dtype=np.float64),
            "intercept": np.asarray([self.intercept], dtype=np.float64),
            "center_mean": np.asarray([self.center_mean], dtype=np.float64),
        }

    @classmethod
    def from_arrays(cls, arrays: dict[str, np.ndarray]) -> "BinaryHead":
        status = str(arrays["status"][0])
        is_skipped = status == "skipped"
        return cls(
            mean=np.asarray(arrays["mean"], dtype=np.float64),
            scale=np.asarray(arrays["scale"], dtype=np.float64),
            coef=None if is_skipped else np.asarray(arrays["coef"], dtype=np.float64),
            intercept=None if is_skipped else float(arrays["intercept"][0]),
            center_mean=None if is_skipped else float(arrays["center_mean"][0]),
            status=status,  # type: ignore[arg-type]
        )

    @staticmethod
    def array_fields(status: str) -> tuple[str, ...]:
        """Which `heads.npz` field names exist for a head of this `status`.
        `model.py`'s `load` rebuilds `heads.npz` keys from `thresholds.json`'s
        cell list, so it needs this without having the head yet (D-45 made
        the field set status-dependent).
        """
        if status == "skipped":
            return ("mean", "scale", "status")
        return ("mean", "scale", "coef", "intercept", "center_mean", "status")


def fit_binary_head(
    x: np.ndarray,
    y: np.ndarray,
    sample_weight: np.ndarray,
    *,
    seed: int = DEFAULT_SEED,
) -> BinaryHead:
    """Fit one binary head (D-7/D-45/§3 step 4), ported from the toy's
    `fit_binary_head_weighted` (`run_bge_hazard_weighted_heads.py` L81-110).

    `x`/`y`/`sample_weight` must already reflect every exclusion that applies
    to this component/head-type call: D-1's holdout-seed rows, D-4's
    empty/echo-only rows, and (for Legitimization, D-7/D-18) enablement-only
    hazard rows. This function has no `hazard` parameter and inspects no
    hazard identity -- it only ever sees already-filtered, already-weighted
    arrays, so it cannot itself apply, skip, or special-case any of those
    exclusions; that responsibility belongs entirely to the caller
    (`model.py`'s `fit`, IS-4).

    **Note on `center_mean`'s inputs (not a behavior change, a self-
    consistency choice):** the toy computes `center_mean` from
    `model.predict_proba(z_train)` (sklearn's own code path) but later serves
    predictions through a materially identical, independently-recomputed
    formula. This function instead computes the training probabilities used
    for `center_mean` via `BinaryHead.predict_proba` itself (the exact same
    call path serving will use later), so a head's own `center_mean` is
    always definitionally consistent with what `predict_proba_centered`
    would report if called on that same training data -- avoiding a
    dual-implementation drift risk the toy's structure did not have to worry
    about (it never serialized a head and re-loaded it days later).
    """
    x = np.asarray(x, dtype=np.float64)
    y_int = np.asarray(y, dtype=np.int64)
    sample_weight = np.asarray(sample_weight, dtype=np.float64)

    mean, scale = _standardize_mean_scale(x)

    if len(set(int(value) for value in y_int)) < 2:
        # DECISIONS.md D-45 (superseding D-5): a single-class label cannot be
        # fit, so the operation is marked unavailable. D-5 substituted the
        # label's own weighted mean as a constant probability here; that value
        # was serialized and then refused at every predict path that could
        # have read it, so it only ever made an unavailable head look fitted.
        # `mean`/`scale` are kept -- they describe the training features and
        # were computed before this check.
        return BinaryHead(
            mean=mean,
            scale=scale,
            coef=None,
            intercept=None,
            center_mean=None,
            status="skipped",
        )

    z = (x - mean) / scale
    model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        solver="liblinear",
        random_state=seed,
        max_iter=1000,
    )
    model.fit(z, y_int, sample_weight=sample_weight)
    coef = model.coef_[0].astype(np.float64)
    intercept = float(model.intercept_[0])

    train_prob = _raw_proba(x, mean, scale, coef, intercept)
    center_mean = float(np.average(train_prob, weights=sample_weight))

    return BinaryHead(
        mean=mean,
        scale=scale,
        coef=coef,
        intercept=intercept,
        center_mean=center_mean,
        status="fit",
    )
