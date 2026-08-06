"""The production L/E fitter: a flat three-class multinomial softmax, fitted
per hazard (`docs/planning/PR5_EXECUTION_PLAN.md` §5).

This is [D-68](../../../docs/planning/DECISIONS.md#d-68)'s selected structure
-- `L1 · W1 · S1 · H3 · V1 · P1` -- moved out of
`experiments/candidates.py::MultinomialSoftmax` and into production, and it
is **the same estimator, parameter for parameter**. A different
regularization, a dropped `class_weight`, or a pooled fallback for a thin
cell is a *different model from the one that was selected*, however
reasonable it looks; changing any of them is a
`PREREGISTRATION_LE_STRUCTURE.md` §8 amendment, not a commit message
(`PR5_EXECUTION_PLAN.md` §5). `tests/unit/test_evaluator_training_multinomial.py`
pins the agreement against the experiment implementation numerically, which
is what makes "we shipped what was selected" a verified claim rather than a
stated one -- and is why `experiments/` is not deleted.

**Building it is not evidence it is good.** D-68 is a null result: no
candidate beat the incumbent, and on Legitimization the selected structure
scored *below* it (macro-F1 0.4336 vs 0.4840). It was selected because the
higher-scoring candidates are two-head structures that cannot emit the
three-class distribution `SCIENCE.md` §Legitimization/Enablement Scoring
require. Both models ship **not evaluated**.

**No live estimator survives a fit.** [D-37](../../../docs/planning/DECISIONS.md#d-37)
bars pickle and `joblib`, so a fitted cell here holds only plain NumPy
arrays -- coefficients, intercepts, and the per-cell standardization
statistics -- and scores with pure NumPy. `sklearn` appears in `fit` and
nowhere else, which is what lets slice B serialize a cell to `.npz` + JSON
directly rather than reaching inside an object it must not persist.

**The absent-class trap** (`PR5_EXECUTION_PLAN.md` §5). A per-hazard cell of
~42 rows can easily see only two of the three classes.
`LogisticRegression.classes_` then omits the third entirely -- and switches
to its binary parameterization, `coef_` of shape `(1, d)` rather than
`(3, d)`. Both are handled here by canonicalizing to a single `(d, 3)`
coefficient matrix plus a recorded `fitted_classes` set, and masking the
absent class's logit to `-inf` at score time so it reads exactly `0.0`. That
is honest -- the model cannot predict a class it never saw -- and it is a
**disclosure item**: a distribution with a hard zero is a property of the
data the cell was fitted on, not a calibrated probability.
"""

from __future__ import annotations

import dataclasses
import sys
from types import MappingProxyType
from typing import Literal, Mapping

import numpy as np
from sklearn.linear_model import LogisticRegression

from ...config import DEFAULT_SEED
from ..no_fixed_rules import assert_no_fixed_rule_import

__all__ = [
    "N_CLASSES",
    "SCALE_FLOOR",
    "ESTIMATOR_PARAMS",
    "Target",
    "MultinomialCell",
    "TargetModel",
    "fit_cell",
    "fit_target_model",
]

N_CLASSES = 3

# `heads.py`'s standardization convention (D-7), reproduced rather than
# imported: mean/std over the cell's own fit rows, with a near-constant
# column's scale floored to 1.0 so it never divides by ~zero.
SCALE_FLOOR = 1e-6

# D-68's estimator, exactly. `class_weight="balanced"` is the estimator's own
# balancing and is **not** the Weighting axis -- `W1` ("no class weighting")
# means uniform `sample_weight` on top of it, which is why no sample weights
# appear below at all. See D-68's "'No class weighting' is not literal" note.
ESTIMATOR_PARAMS: Mapping[str, object] = MappingProxyType(
    {
        "C": 1.0,
        "class_weight": "balanced",
        "solver": "lbfgs",
        "random_state": DEFAULT_SEED,
        "max_iter": 1000,
    }
)

Target = Literal["legitimization", "enablement"]


@dataclasses.dataclass(frozen=True)
class MultinomialCell:
    """One fitted `(target, hazard)` cell, as plain arrays.

    `coef` is `(n_features, 3)` and `intercept` is `(3,)` --
    `PREREGISTRATION_LE_STRUCTURE.md` §6's payload shape for the multinomial
    row, so slice B's writer serializes these two arrays as they stand.
    Columns are indexed by **class label** (0, 1, 2), never by whatever order
    the estimator happened to produce.

    `fitted_classes` is the subset of `(0, 1, 2)` the cell's fit rows
    actually contained. A class outside it has a zero coefficient column
    *and* is masked out of the softmax -- the zero column alone would not do
    it, since `exp(0) == 1` is not a zero probability.
    """

    hazard: str
    mean: np.ndarray  # (n_features,)
    scale: np.ndarray  # (n_features,)
    coef: np.ndarray  # (n_features, 3)
    intercept: np.ndarray  # (3,)
    fitted_classes: tuple[int, ...]
    n_fit_rows: int

    def __post_init__(self) -> None:
        n_features = int(self.coef.shape[0])
        if self.coef.shape != (n_features, N_CLASSES):
            raise ValueError(f"coef must be (n_features, {N_CLASSES}), got {self.coef.shape}")
        if self.intercept.shape != (N_CLASSES,):
            raise ValueError(f"intercept must be ({N_CLASSES},), got {self.intercept.shape}")
        if self.mean.shape != (n_features,) or self.scale.shape != (n_features,):
            raise ValueError(
                f"mean/scale must be (n_features,) = ({n_features},), got "
                f"{self.mean.shape}/{self.scale.shape}"
            )
        if not self.fitted_classes:
            raise ValueError("a fitted cell must record at least one fitted class")
        if any(c not in range(N_CLASSES) for c in self.fitted_classes):
            raise ValueError(f"fitted_classes must be a subset of {tuple(range(N_CLASSES))}")

    @property
    def n_features(self) -> int:
        return int(self.coef.shape[0])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """`(n, 3)`, every row summing to 1, columns indexed by class label.

        Pure NumPy: standardize with this cell's own statistics, take the
        softmax of `z @ coef + intercept`, and give a class the cell never
        saw exactly `0.0` rather than the `exp(0) == 1` its zero coefficient
        column would otherwise contribute.
        """
        z = (np.asarray(X, dtype=np.float64) - self.mean) / self.scale
        logits = z @ self.coef + self.intercept

        absent = [c for c in range(N_CLASSES) if c not in self.fitted_classes]
        if absent:
            logits = logits.copy()
            logits[:, absent] = -np.inf

        shifted = logits - logits.max(axis=1, keepdims=True)
        exponentiated = np.exp(shifted)
        return exponentiated / exponentiated.sum(axis=1, keepdims=True)


@dataclasses.dataclass(frozen=True)
class TargetModel:
    """One target's fitted model: a `MultinomialCell` per hazard that could
    be fitted, and an explicit record of the hazards that could not.

    **`unavailable_hazards` is not an error list to be papered over**
    ([D-45](../../../docs/planning/DECISIONS.md#d-45)): a cell with fewer
    than two present classes is *unavailable*, never substituted by a pooled
    or neighbouring fit. `predict_proba` returns `NaN` for such a row, which
    slice C's scoring component turns into a per-hazard `ComponentError` and
    the integrator's phase D turns into a per-hazard failure -- never a
    uniform distribution and never an invented judgment.

    `supported_hazards` is what the artifact's frozen supported set is built
    from ([D-57](../../../docs/planning/DECISIONS.md#d-57)): exactly the
    hazards with a fitted cell.
    """

    target: Target
    cells: Mapping[str, MultinomialCell]
    unavailable_hazards: frozenset[str]
    n_features: int
    n_fit_rows: int

    def __post_init__(self) -> None:
        # Read-only, matching `record.py`'s convention for a dict-shaped
        # field on a frozen dataclass: `replace()` copies shallowly, so
        # without this a caller could add a cell to a "frozen" model.
        object.__setattr__(self, "cells", MappingProxyType(dict(self.cells)))
        overlap = set(self.cells) & set(self.unavailable_hazards)
        if overlap:
            raise ValueError(
                f"hazards {sorted(overlap)} are recorded as both fitted and unavailable"
            )

    @property
    def supported_hazards(self) -> frozenset[str]:
        return frozenset(self.cells)

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        """`(n, 3)`. A row whose hazard has no fitted cell -- unavailable at
        fit time, or never seen at fit time at all -- is `NaN`, never zero
        and never a substitute (D-45). A caller must treat a `NaN` row as
        "this model cannot score this hazard".
        """
        X = np.asarray(X, dtype=np.float64)
        hazards = np.asarray(hazards)
        out = np.full((len(X), N_CLASSES), np.nan, dtype=np.float64)

        for hazard in set(hazards.tolist()):
            cell = self.cells.get(hazard)
            if cell is None:
                continue
            mask = hazards == hazard
            out[mask] = cell.predict_proba(X[mask])

        return out


def fit_cell(hazard: str, x: np.ndarray, y: np.ndarray) -> MultinomialCell | None:
    """Fit one `(target, hazard)` cell, or return `None` if it is unavailable.

    Unavailable means fewer than two classes present in `y` -- D-45's rule,
    re-implemented here because per-hazard cells force it. Nothing is
    substituted for such a cell and nothing about it is guessed.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)

    if len(set(y.tolist())) < 2:
        return None

    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale = np.where(scale < SCALE_FLOOR, 1.0, scale)
    z = (x - mean) / scale

    estimator = LogisticRegression(**ESTIMATOR_PARAMS)
    # `W1` -- uniform sample weights, written out rather than left to
    # sklearn's `None` default so the Weighting level D-68 selected is
    # visible in the code that implements it. The two are equivalent, and
    # the equivalence test against `experiments/` pins that they stay so.
    estimator.fit(z, y, sample_weight=np.ones(len(y), dtype=np.float64))

    coef, intercept = _canonical_parameters(estimator)
    return MultinomialCell(
        hazard=hazard,
        mean=mean,
        scale=scale,
        coef=coef,
        intercept=intercept,
        fitted_classes=tuple(int(c) for c in estimator.classes_),
        n_fit_rows=int(len(y)),
    )


def _canonical_parameters(estimator: LogisticRegression) -> tuple[np.ndarray, np.ndarray]:
    """`sklearn`'s two parameterizations, reduced to one `(n_features, 3)`
    coefficient matrix plus a `(3,)` intercept, indexed by class label.

    With all three classes present, `lbfgs` fits a multinomial softmax:
    `coef_` is `(3, d)` and `predict_proba` is exactly
    `softmax(X @ coef_.T + intercept_)`. With two classes present it fits the
    binary form instead -- `coef_` is `(1, d)` and `predict_proba` is
    `[1 - sigmoid(d), sigmoid(d)]`. Those are the same distribution written
    two ways: setting the lower class's logit row to zero and the higher
    class's to `coef_[0]` makes the softmax reproduce the sigmoid pair (to
    ~1e-16, verified in the unit tests). Canonicalizing here means score time
    has exactly one formula.
    """
    classes = [int(c) for c in estimator.classes_]
    n_features = int(estimator.coef_.shape[1])
    coef = np.zeros((n_features, N_CLASSES), dtype=np.float64)
    intercept = np.zeros(N_CLASSES, dtype=np.float64)

    if len(classes) == 2:
        # Binary form: the reference class keeps the zero row it was
        # initialized with, and the other carries the whole log-odds.
        higher = classes[1]
        coef[:, higher] = np.asarray(estimator.coef_[0], dtype=np.float64)
        intercept[higher] = float(estimator.intercept_[0])
        return coef, intercept

    for column, cls in enumerate(classes):
        coef[:, cls] = np.asarray(estimator.coef_[column], dtype=np.float64)
        intercept[cls] = float(estimator.intercept_[column])
    return coef, intercept


def fit_target_model(
    X: np.ndarray, y: np.ndarray, hazards: np.ndarray, *, target: Target
) -> TargetModel:
    """Fit one target's per-hazard cells.

    `X`/`y`/`hazards` must already be the correct eligibility subset for
    `target` -- `interim_data.legitimization_rows` for Legitimization, every
    row for Enablement. This function applies no `SCIENCE.md` rule and
    inspects no hazard family; which rows a target gets is the caller's
    (`release.py`'s), matching `heads.fit_binary_head`'s own division of
    responsibility in the baseline.
    """
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)
    hazards = np.asarray(hazards)

    if not (len(X) == len(y) == len(hazards)):
        raise ValueError(
            f"X ({len(X)}), y ({len(y)}) and hazards ({len(hazards)}) must be the same length"
        )
    if len(X) == 0:
        raise ValueError(f"cannot fit the {target} model on zero rows")

    cells: dict[str, MultinomialCell] = {}
    unavailable: set[str] = set()
    for hazard in sorted(set(hazards.tolist())):
        mask = hazards == hazard
        cell = fit_cell(hazard, X[mask], y[mask])
        if cell is None:
            unavailable.add(hazard)
            continue
        cells[hazard] = cell

    return TargetModel(
        target=target,
        cells=cells,
        unavailable_hazards=frozenset(unavailable),
        n_features=int(X.shape[1]),
        n_fit_rows=int(len(X)),
    )


assert_no_fixed_rule_import(sys.modules[__name__])
