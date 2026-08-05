"""Slice A §4.2 -- the candidate interface every L/E structure implements,
plus the reference structure `R`
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md`,
`docs/planning/PREREGISTRATION_LE_STRUCTURE.md` §2.2).

One protocol every candidate implements, so the stage 1/2 ladder (slices B/C)
is a loop over `Candidate` instances rather than twelve bespoke scripts. Two
constraints from the pre-registration are enforced here rather than trusted:

- **No candidate may apply a `SCIENCE.md` fixed rule** (pre-registration
  §2.1). Applicability, phase C, and the L/E-to-result tables belong to final
  integration; a candidate that reads hazard family to decide an *outcome*
  (rather than to condition a *feature*, which `H2`/`H3` are permitted to do)
  is disqualified. Enforced below by `_assert_no_fixed_rule_import`, a real
  assertion run at import time against this module's own source -- not a
  comment -- so a future candidate module that imports the fixed-rule module
  fails loudly instead of silently drifting into scope this comparison must
  not touch.
- **Linear on frozen embeddings only** (pre-registration §2.1). Every
  candidate's `fit`/`predict_proba` take an already-embedded feature matrix,
  never text -- there is no encoder object anywhere in this module, so
  nothing here can fine-tune one.
"""

from __future__ import annotations

import ast
import inspect
import sys
from collections.abc import Callable
from types import ModuleType
from typing import Literal, Protocol

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from statsmodels.miscmodels.ordinal_model import OrderedModel

from hazard_classifier.config import DEFAULT_SEED
from hazard_classifier.heads import BinaryHead, fit_binary_head
from hazard_classifier.rules import ordinal_prediction, optimize_ordinal_thresholds

_N_CLASSES = 3

# SCIENCE.md's fixed rules -- applicability (phase A), the disclaimer
# modifier (phase C), the L/E-to-result tables, and the rollup -- live only
# in final integration. A candidate structure must never import the module
# that carries them.
_FORBIDDEN_FIXED_RULE_IMPORTS = frozenset(
    {
        "hazard_classifier.evaluator.components.integration",
    }
)


def _assert_no_fixed_rule_import(module: ModuleType) -> None:
    """Parses `module`'s own source and raises if it imports a module named
    in `_FORBIDDEN_FIXED_RULE_IMPORTS`. Any module defining a `Candidate`
    implementation should call this on itself at import time (see the bottom
    of this file), so the pre-registration §2.1 constraint is checked by
    running the code, not by trusting a docstring.
    """
    source = inspect.getsource(module)
    tree = ast.parse(source, filename=getattr(module, "__file__", "<candidate module>"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            imported = {base} | ({f"{base}.{alias.name}" for alias in node.names} if base else set())
        else:
            continue
        hit = imported & _FORBIDDEN_FIXED_RULE_IMPORTS
        if hit:
            raise AssertionError(
                f"{module.__name__} imports {sorted(hit)}, which carries SCIENCE.md's "
                "fixed rules (applicability, phase C, L/E-to-result tables). Candidate "
                "structures must not apply those -- they belong to final integration "
                "only (pre-registration §2.1)."
            )


class Candidate(Protocol):
    """One L/E structure under comparison. `fit`/`predict_proba` see an
    already-pooled, already-embedded feature matrix (`features.pool_sentences`)
    and the row's hazard code -- never text, never a `SCIENCE.md` fixed rule.
    """

    name: str

    # Whether this structure emits a genuine three-class multinomial, or
    # merely a one-hot indicator of a decided label.
    #
    # **This is a selection constraint, not a cosmetic label.**
    # `PREREGISTRATION_LE_STRUCTURE.md` §4's closing rule is that the
    # selection must be "the highest-ranked candidate that produces a genuine
    # three-class distribution", and §2.2 excludes `R` for precisely this
    # reason: `SCIENCE.md` §Legitimization/Enablement Scoring require a
    # three-class multinomial that two thresholded binary heads structurally
    # cannot produce (`ARCHITECTURE.md` §4 -- the obvious derivation is
    # unsafe because `p_high > p_nonzero` is reachable).
    #
    # The property is **not** unique to `R`: every two-head structure on the
    # ladder inherits it, including the Weighting, Hazard-conditioning,
    # Branching, Pooling and Sharing variants, which vary one axis from `R`
    # while keeping its `L3` loss. §6's payload table is the same
    # distinction seen from the artifact side -- `thresholds.json` is
    # retained only for `L3`, and "every other candidate decides by `argmax`
    # over the distribution".
    produces_three_class_distribution: bool

    def fit(self, X: np.ndarray, y: np.ndarray, hazards: np.ndarray) -> None:
        """Fit on `X` (n, d), ordinal labels `y` (n,) in `{0, 1, 2}`, and
        `hazards` (n,) hazard codes. Rows must already be the correct
        eligibility subset for this target (`interim_data.legitimization_rows`
        for L; every row for E) -- this method does not filter by hazard
        family itself.
        """
        ...

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        """Returns `(n, 3)`. For every implementation except `R` (below),
        every row sums to 1. `R` is the pre-registration's one declared
        exception: a hazard whose cell was unfittable at `fit` time
        (`DECISIONS.md` D-45) returns `NaN` for that row rather than
        inventing a distribution -- callers must treat a `NaN` row as "this
        candidate could not score this hazard," never as zero.
        """
        ...


class MajorityClassBaseline:
    """A degenerate candidate that always predicts the most frequent training
    class, ignoring features entirely.

    **Not a ladder candidate, never eligible for selection, and kept out of
    `stage1.json`'s candidate list** (Kurt, 2026-08-04; recorded in
    `PREREGISTRATION_LE_STRUCTURE.md` §8 as a restatement of §2.3 rather than
    a new decision). The pre-registration §2.3 fixes the ladder's levels and
    none may be added without an amendment; this is a *diagnostic anchor*. It
    may be reported as a reference line, clearly marked as not a candidate.
    Its whole purpose is
    that its scores are known in advance from the class balance alone
    (§3: accuracy 0.569 on L, 0.636 on E, worst-class F1 = 0), so a harness
    that reproduces them is computing what it claims to compute.

    It is also the thing the §3 metric choice exists to reject: a candidate
    with a respectable accuracy and a worst-class F1 of exactly zero, useless
    on the two classes that matter.
    """

    name = "majority_class"
    # One-hot on the majority class -- not a distribution, and not a
    # ladder candidate either (see the class docstring).
    produces_three_class_distribution = False

    def __init__(self) -> None:
        self.majority_class: int | None = None

    def fit(self, X: np.ndarray, y: np.ndarray, hazards: np.ndarray) -> None:
        y = np.asarray(y, dtype=np.int64)
        if y.size == 0:
            raise ValueError("cannot fit a majority class on zero rows")
        self.majority_class = int(np.bincount(y, minlength=3).argmax())

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        if self.majority_class is None:
            raise RuntimeError("fit must be called before predict_proba")
        out = np.zeros((len(np.asarray(X)), 3), dtype=np.float64)
        out[:, self.majority_class] = 1.0
        return out


class TwoHeadReference:
    """`R` -- pre-registration §2.2's reference structure: two thresholded
    binary heads fitted per hazard, mean-pooled BGE representation, no class
    weighting, decisions made by an optimized threshold pair. This wraps the
    baseline's own per-cell mechanism (`heads.fit_binary_head`,
    `rules.optimize_ordinal_thresholds`) rather than reimplementing it, so
    `R` measures the actual incumbent the ladder is meant to improve on.

    `R` cannot be the final selection (pre-registration §2.2): two binary
    heads do not produce a genuine three-class multinomial. It exists on the
    ladder as the reference point every candidate is measured against.

    **"No class weighting" (`W1` = R) means uniform `sample_weight`** passed
    to `fit_binary_head`, distinct from `LogisticRegression`'s own internal
    `class_weight="balanced"` inside `fit_binary_head` -- that is an existing
    baseline mechanism this candidate inherits unchanged, not part of the
    Weighting axis stage 1 varies (`W2`/`W3`, slice B).
    """

    name = "R"
    # Two thresholded binary heads decide a label; the returned row is a
    # one-hot indicator, never a calibrated three-class distribution.
    # This is exactly why §2.2 excludes R from being the final selection.
    produces_three_class_distribution = False

    def __init__(self) -> None:
        self._cells: dict[str, tuple[BinaryHead, BinaryHead, float, float]] = {}
        self.unavailable_hazards: frozenset[str] = frozenset()

    def fit(self, X: np.ndarray, y: np.ndarray, hazards: np.ndarray) -> None:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        hazards = np.asarray(hazards)

        cells: dict[str, tuple[BinaryHead, BinaryHead, float, float]] = {}
        unavailable: set[str] = set()
        for hazard in sorted(set(hazards.tolist())):
            mask = hazards == hazard
            x_h, y_h = X[mask], y[mask]
            weights = np.ones(len(y_h), dtype=np.float64)

            nonzero_head = fit_binary_head(x_h, (y_h > 0).astype(np.int64), weights)
            high_head = fit_binary_head(x_h, (y_h == 2).astype(np.int64), weights)

            if nonzero_head.status == "skipped" or high_head.status == "skipped":
                # DECISIONS.md D-45: unfittable is unavailable, never
                # substituted -- record it and move on rather than crash the
                # ladder or invent a threshold pair for a head that has none.
                unavailable.add(hazard)
                continue

            centered_nonzero = nonzero_head.predict_proba_centered(x_h)
            centered_high = high_head.predict_proba_centered(x_h)
            nonzero_threshold, high_threshold, _ = optimize_ordinal_thresholds(
                y_h, centered_nonzero, centered_high
            )
            cells[hazard] = (nonzero_head, high_head, nonzero_threshold, high_threshold)

        self._cells = cells
        self.unavailable_hazards = frozenset(unavailable)

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        hazards = np.asarray(hazards)
        out = np.full((len(X), 3), np.nan, dtype=np.float64)

        for hazard in set(hazards.tolist()):
            cell = self._cells.get(hazard)
            if cell is None:
                # Unavailable at fit time (D-45), or never seen at fit time
                # at all -- both are "R cannot score this," not zero.
                continue
            nonzero_head, high_head, nonzero_threshold, high_threshold = cell
            mask = hazards == hazard
            x_h = X[mask]
            centered_nonzero = nonzero_head.predict_proba_centered(x_h)
            centered_high = high_head.predict_proba_centered(x_h)
            labels = ordinal_prediction(centered_nonzero, centered_high, nonzero_threshold, high_threshold)

            # R decides by threshold, not by a calibrated distribution
            # (ARCHITECTURE.md §4: the obvious probability derivation is not
            # safe, since p_high > p_nonzero is reachable). One-hot on the
            # decided label satisfies the (n, 3)-summing-to-1 interface
            # without inventing a continuous value D-45 would forbid.
            one_hot = np.zeros((len(labels), 3), dtype=np.float64)
            one_hot[np.arange(len(labels)), labels] = 1.0
            out[mask] = one_hot

        return out


_WeightingLevel = Literal["W1", "W2", "W3"]
_HazardConditioningLevel = Literal["H1", "H2", "H3"]
_BranchingLevel = Literal["B1", "B2"]


def _inverse_frequency_weights(y: np.ndarray) -> np.ndarray:
    """Per-row weight `1 / count(that row's class)`, counted **within `y`
    itself**. The standard inverse-class-frequency formula -- it already
    equalizes each present class's total weight contribution
    (`count * 1/count == 1` for every class with at least one row), which is
    the formula both `W2` and `W3` below share. What differs between them is
    the *population the counts are taken over*, not the formula -- see
    `TwoHeadFamily`'s docstring.
    """
    y = np.asarray(y, dtype=np.int64)
    counts = np.bincount(y, minlength=_N_CLASSES).astype(np.float64)
    weights = np.zeros(len(y), dtype=np.float64)
    present = counts[y] > 0
    weights[present] = 1.0 / counts[y[present]]
    return weights


def _ungated_prediction(
    centered_nonzero: np.ndarray,
    centered_high: np.ndarray,
    nonzero_threshold: float,
    high_threshold: float,
) -> np.ndarray:
    """`B1`'s flat, ungated combination: predicting `2` depends only on the
    high head crossing its own threshold, independent of whether the nonzero
    head also crossed. `rules.py`'s own docstring names this exact
    unconditional rule as what D-9/D-10 replaced with a monotonicity gate
    ("can predict '2' for a row that didn't even predict '>= 1' -- a
    non-monotone result"). It exists here, and only here, because the
    pre-registration's Branching axis names it as a comparison level -- `R`'s
    `B2` gate in `rules.ordinal_prediction` is untouched by this candidate.
    """
    nonzero = np.asarray(centered_nonzero, dtype=np.float64)
    high = np.asarray(centered_high, dtype=np.float64)
    out = np.zeros(len(nonzero), dtype=np.int8)
    out[nonzero >= nonzero_threshold] = 1
    out[high >= high_threshold] = 2  # unconditional -- the defining difference from B2
    return out


def _optimize_ungated_thresholds(
    y: np.ndarray, centered_nonzero: np.ndarray, centered_high: np.ndarray
) -> tuple[float, float]:
    """Grid-search `(nonzero_threshold, high_threshold)` for the ungated
    `B1` rule: maximize exact accuracy, ties broken by within-one accuracy,
    then lower MAE, then closeness to 0.5 -- same 91x91 grid and tie-break
    shape as `rules.optimize_ordinal_thresholds`, applied to
    `_ungated_prediction` instead of `rules.ordinal_prediction`.

    **Deliberately drops QWK from the key**, unlike `rules.
    optimize_ordinal_thresholds`. That function's weighted-kappa math is
    written and tested against the gated combination rule; re-deriving the
    equivalent expected-value formula for the ungated rule under time
    pressure, with no independent implementation to check it against, is a
    real place to introduce a silent sign or weighting error -- more risk
    than this candidate's own ranking needs, since stage 1's actual selection
    metric is the pre-registration's macro-F1 (`comparison_metrics.py`),
    computed independently of whatever criterion picked these thresholds.
    """
    grid = np.linspace(0.05, 0.95, 91)
    nonzero_thresholds = np.repeat(grid, len(grid))
    high_thresholds = np.tile(grid, len(grid))
    y_int = np.asarray(y, dtype=np.int64)

    nonzero = np.asarray(centered_nonzero, dtype=np.float64)[None, :]
    high = np.asarray(centered_high, dtype=np.float64)[None, :]
    crossed_nonzero = nonzero >= nonzero_thresholds[:, None]
    crossed_high = high >= high_thresholds[:, None]
    pred_grid = np.where(crossed_high, 2, np.where(crossed_nonzero, 1, 0)).astype(np.int8)

    abs_error = np.abs(pred_grid.astype(np.int64) - y_int[None, :])
    exact = np.mean(pred_grid == y_int[None, :], axis=1)
    within_one = np.mean(abs_error <= 1, axis=1)
    mae = np.mean(abs_error, axis=1)

    best_key: tuple[float, float, float, float, float] | None = None
    best_thresholds = (0.5, 0.5)
    for index, (nonzero_threshold, high_threshold) in enumerate(
        zip(nonzero_thresholds, high_thresholds)
    ):
        key = (
            float(exact[index]),
            float(within_one[index]),
            -float(mae[index]),
            -abs(float(nonzero_threshold) - 0.5),
            -abs(float(high_threshold) - 0.5),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_thresholds = (float(nonzero_threshold), float(high_threshold))
    return best_thresholds


class TwoHeadFamily:
    """A generalized two-head structure spanning the pre-registration's
    Weighting, Hazard-conditioning, and Branching axes -- `W2`, `W3`, `H1`,
    `H2`, and `B1` are each one instance of this class with exactly one axis
    moved off `R`'s level; every other axis stays at `R`'s own level (`W1`,
    `H3`, `B2`), matching §2.3's "one axis varies at a time from `R`."

    Deliberately a **separate class from `TwoHeadReference`**, not a
    generalization of it -- `R` is already tested and is the ladder's fixed
    reference point; adding knobs to its internals would be touching
    already-verified code for no reason a bug fix would require.

    **Weighting (`W2` vs `W3`) -- the interpretive call this class makes,
    stated so it can be checked rather than discovered.** Both share the
    inverse-frequency formula (`_inverse_frequency_weights`); the
    pre-registration's own text does not say what population the frequencies
    are taken over, so this class distinguishes them by *scope*:

    - `W2` ("inverse-frequency class weights") -- a **global** statistic:
      class counts taken once over the whole target's fit population (every
      hazard pooled), then applied per row regardless of which hazard's
      local fit that row lands in.
    - `W3` ("explicit equal-per-class weights") -- a **local**, deliberately
      imposed equalization: class counts taken fresh within whichever
      population is actually being fit (for the `H3` default, each hazard's
      own local counts) -- "explicit" in the sense that it is computed
      directly against the specific population being equalized, not
      inherited from a global statistic.

    Pooling (`P2`/`P3`) needs no class here at all -- it is `R`'s own
    mechanism (or this class's, at its `R`-equivalent configuration) fit on a
    differently-pooled feature matrix (`features.SentenceEmbeddings.pooled`),
    a harness-level choice about which `X` to pass in, not a model-level one.
    """

    # Every level this class spans (W2, W3, H1, H2, B1) varies one axis from
    # R while keeping its L3 two-head loss, so all of them decide by
    # threshold and return a one-hot row -- ineligible for selection under
    # §4's closing rule, exactly as R is.
    produces_three_class_distribution = False

    def __init__(
        self,
        name: str,
        *,
        weighting: _WeightingLevel = "W1",
        hazard_conditioning: _HazardConditioningLevel = "H3",
        branching: _BranchingLevel = "B2",
    ) -> None:
        self.name = name
        self.weighting = weighting
        self.hazard_conditioning = hazard_conditioning
        self.branching = branching
        self._cells: dict[str, tuple[BinaryHead, BinaryHead, float, float]] = {}
        self._hazard_vocabulary: tuple[str, ...] = ()
        self.unavailable_hazards: frozenset[str] = frozenset()
        # Only meaningful for hazard_conditioning in {"H1", "H2"}: whether
        # the single pooled cell itself was fit at all (D-45). "H3" instead
        # tracks per-hazard availability in `unavailable_hazards`, matching
        # `TwoHeadReference`.
        self._pooled_unavailable = False

    def _one_hot(self, hazards: np.ndarray) -> np.ndarray:
        vocabulary_index = {hazard: i for i, hazard in enumerate(self._hazard_vocabulary)}
        onehot = np.zeros((len(hazards), len(self._hazard_vocabulary)), dtype=np.float64)
        for row, hazard in enumerate(hazards):
            column = vocabulary_index.get(hazard)
            if column is not None:
                onehot[row, column] = 1.0
        return onehot

    def _features(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        if self.hazard_conditioning != "H2":
            return X
        return np.concatenate([X, self._one_hot(hazards)], axis=1)

    def fit(self, X: np.ndarray, y: np.ndarray, hazards: np.ndarray) -> None:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        hazards = np.asarray(hazards)

        if self.hazard_conditioning == "H2":
            self._hazard_vocabulary = tuple(sorted(set(hazards.tolist())))

        global_class_counts = None
        if self.weighting == "W2":
            global_class_counts = np.bincount(y, minlength=_N_CLASSES).astype(np.float64)

        if self.hazard_conditioning == "H3":
            cell_keys: list[str] = sorted(set(hazards.tolist()))
            cell_masks = {key: hazards == key for key in cell_keys}
        else:
            cell_keys = ["__pooled__"]
            cell_masks = {"__pooled__": np.ones(len(y), dtype=bool)}

        X_features = self._features(X, hazards)

        cells: dict[str, tuple[BinaryHead, BinaryHead, float, float]] = {}
        unavailable: set[str] = set()
        for key in cell_keys:
            mask = cell_masks[key]
            x_cell, y_cell = X_features[mask], y[mask]

            if self.weighting == "W1":
                weights = np.ones(len(y_cell), dtype=np.float64)
            elif self.weighting == "W2":
                assert global_class_counts is not None
                weights = np.zeros(len(y_cell), dtype=np.float64)
                present = global_class_counts[y_cell] > 0
                weights[present] = 1.0 / global_class_counts[y_cell[present]]
            else:  # "W3"
                weights = _inverse_frequency_weights(y_cell)

            nonzero_head = fit_binary_head(x_cell, (y_cell > 0).astype(np.int64), weights)
            high_head = fit_binary_head(x_cell, (y_cell == 2).astype(np.int64), weights)

            if nonzero_head.status == "skipped" or high_head.status == "skipped":
                # DECISIONS.md D-45: unfittable is unavailable, never
                # substituted -- same principle as TwoHeadReference, applied
                # to whichever cell shape this configuration uses.
                if key == "__pooled__":
                    self._pooled_unavailable = True
                else:
                    unavailable.add(key)
                continue

            centered_nonzero = nonzero_head.predict_proba_centered(x_cell)
            centered_high = high_head.predict_proba_centered(x_cell)
            if self.branching == "B2":
                nonzero_threshold, high_threshold, _ = optimize_ordinal_thresholds(
                    y_cell, centered_nonzero, centered_high
                )
            else:  # "B1"
                nonzero_threshold, high_threshold = _optimize_ungated_thresholds(
                    y_cell, centered_nonzero, centered_high
                )

            cells[key] = (nonzero_head, high_head, nonzero_threshold, high_threshold)

        self._cells = cells
        self.unavailable_hazards = frozenset(unavailable)

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        hazards = np.asarray(hazards)
        out = np.full((len(X), _N_CLASSES), np.nan, dtype=np.float64)

        if self.hazard_conditioning == "H3":
            row_groups = {h: (hazards == h) for h in set(hazards.tolist())}
        elif self.hazard_conditioning == "H2":
            # A hazard absent from the fit vocabulary has no honest one-hot
            # placement -- exclude those rows even if the pooled cell itself
            # is available.
            known = np.isin(hazards, np.asarray(self._hazard_vocabulary))
            row_groups = {"__pooled__": known}
        else:  # "H1"
            row_groups = {"__pooled__": np.ones(len(hazards), dtype=bool)}

        for key, row_mask in row_groups.items():
            if not row_mask.any():
                continue
            if key == "__pooled__" and self._pooled_unavailable:
                continue
            cell = self._cells.get(key)
            if cell is None:
                continue
            nonzero_head, high_head, nonzero_threshold, high_threshold = cell

            x_rows = self._features(X[row_mask], hazards[row_mask])
            centered_nonzero = nonzero_head.predict_proba_centered(x_rows)
            centered_high = high_head.predict_proba_centered(x_rows)
            if self.branching == "B2":
                labels = ordinal_prediction(
                    centered_nonzero, centered_high, nonzero_threshold, high_threshold
                )
            else:
                labels = _ungated_prediction(
                    centered_nonzero, centered_high, nonzero_threshold, high_threshold
                )

            one_hot = np.zeros((len(labels), _N_CLASSES), dtype=np.float64)
            one_hot[np.arange(len(labels)), labels] = 1.0
            out[row_mask] = one_hot

        return out


class MultinomialSoftmax:
    """`L1` -- flat three-class softmax cross-entropy, fitted per hazard
    (Hazard-conditioning held at `R`'s own `H3` level, since this candidate
    varies only the Loss axis by default). A genuinely different model from
    the two-head family, not a `TwoHeadFamily` configuration: there is no
    nonzero/high decomposition here, so it does not belong alongside
    `W2/W3/H1/H2/B1`.

    Standardizes features the way `heads.py` does (D-7's convention:
    mean/std over the fit rows, scale floored so a constant column never
    divides by ~zero), so this candidate sits on the same numerical footing
    as every two-head variant it is compared against.

    **`weighting` -- added for slice C's stage-2 composites, not part of
    `L1`'s own stage-1 definition.** `L1` on the ladder proper is always
    `weighting="W1"` (the default, uniform); `weighting="W3"` is what lets
    this class serve as the `Loss=L1, Weighting=W3` composite stage 1's
    `best_level_per_axis` names for the E target, reusing `TwoHeadFamily`'s
    own `_inverse_frequency_weights` (local, per-hazard-cell) for the same
    reason that function documents there: consistency of what `W3` means
    everywhere it appears on the ladder, not a second, independent
    definition.
    """

    # A genuine softmax over three classes -- one of only two structures on
    # the ladder (with L2) that satisfies §4's closing requirement.
    produces_three_class_distribution = True

    def __init__(self, *, name: str = "L1", weighting: _WeightingLevel = "W1") -> None:
        self.name = name
        self.weighting = weighting
        self._cells: dict[str, tuple[np.ndarray, np.ndarray, LogisticRegression]] = {}
        self.unavailable_hazards: frozenset[str] = frozenset()

    def fit(self, X: np.ndarray, y: np.ndarray, hazards: np.ndarray) -> None:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        hazards = np.asarray(hazards)

        cells: dict[str, tuple[np.ndarray, np.ndarray, LogisticRegression]] = {}
        unavailable: set[str] = set()
        for hazard in sorted(set(hazards.tolist())):
            mask = hazards == hazard
            x_h, y_h = X[mask], y[mask]

            if len(set(y_h.tolist())) < 2:
                # Same D-45 principle as R/TwoHeadFamily: a single-class
                # cell cannot be fit, so it is unavailable, not substituted.
                unavailable.add(hazard)
                continue

            mean = x_h.mean(axis=0)
            scale = x_h.std(axis=0)
            scale = np.where(scale < 1e-6, 1.0, scale)
            z = (x_h - mean) / scale

            sample_weight = (
                np.ones(len(y_h), dtype=np.float64)
                if self.weighting == "W1"
                else _inverse_frequency_weights(y_h)
            )

            model = LogisticRegression(
                C=1.0,
                class_weight="balanced",
                solver="lbfgs",
                random_state=DEFAULT_SEED,
                max_iter=1000,
            )
            model.fit(z, y_h, sample_weight=sample_weight)
            cells[hazard] = (mean, scale, model)

        self._cells = cells
        self.unavailable_hazards = frozenset(unavailable)

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        hazards = np.asarray(hazards)
        out = np.full((len(X), _N_CLASSES), np.nan, dtype=np.float64)

        for hazard in set(hazards.tolist()):
            cell = self._cells.get(hazard)
            if cell is None:
                continue
            mean, scale, model = cell
            mask = hazards == hazard
            z = (X[mask] - mean) / scale
            proba = model.predict_proba(z)

            # LogisticRegression's `classes_` omits a class entirely if it
            # never appeared in y_h, even though y_h had >= 2 classes overall
            # (e.g. only {0, 2} present, ~42 rows/hazard makes this plausible)
            # -- place columns by class label, never assume classes_ == [0,1,2]
            # positionally. The omitted class then reads 0, which is honest:
            # this candidate never predicts a class it never saw.
            full = np.zeros((len(z), _N_CLASSES), dtype=np.float64)
            for column, cls in enumerate(model.classes_):
                full[:, int(cls)] = proba[:, column]
            out[mask] = full

        return out


def _l2_pca_components(n_rows: int, n_features: int) -> int:
    """How many principal components `OrdinalCumulativeLink` reduces to
    before fitting, given a cell of `n_rows` rows and `n_features` frozen
    embedding dimensions.

    **Why this exists, found while testing this candidate against the real
    interim data, not assumed in advance.** Unlike every other candidate
    here, `statsmodels.miscmodels.ordinal_model.OrderedModel` has no built-in
    regularization -- and fitting it directly on 768-dimensional BGE vectors
    against a ~42-124-row per-hazard cell (`PREREGISTRATION_LE_STRUCTURE.md`
    §2.3's own "roughly 42 rows per hazard" note) is a severely
    underdetermined MLE. Confirmed two failure modes by hand before writing
    this: the model's own constructor can raise `ValueError` outright on a
    rank-deficient design matrix, and even where it "converges" it can hit
    exact in-sample separation (silent, severe overfitting a downstream
    dev-set number would not visibly flag as such).

    This formula was chosen empirically against every real `(target, hazard)`
    cell in the interim dataset -- all 28 converge with no Hessian-inversion
    warning and no perfect in-sample accuracy under it; `k=10` alone already
    produced both failure modes on the smallest, most class-imbalanced real
    cell (`cse`, 49 rows, class counts 35/5/9). It scales with `n_rows` so a
    larger cell (e.g. `hte`, 124 rows) gets more components, floored at 2 so
    a very small cell still gets a fittable model, and capped by
    `n_features` so a low-dimensional input (a unit test's synthetic fixture)
    is never asked for more components than it has.
    """
    return max(2, min(10, n_rows // 10, n_features))


class OrdinalCumulativeLink:
    """`L2` -- ordinal cumulative-link (proportional odds), fitted per hazard
    (Hazard-conditioning held at `R`'s own `H3` level; this candidate varies
    only the Loss axis, matching `MultinomialSoftmax`'s own scoping).

    Uses `statsmodels.miscmodels.ordinal_model.OrderedModel` (`distr="logit"`)
    -- a genuine MLE proportional-odds fit, not a hand-rolled one. Chosen
    over `mord` (last released 2017, effectively unmaintained) specifically
    because this candidate feeds a comparison that selects the structure a
    safety classifier ships with: an actively-maintained, widely-used
    implementation is worth the dependency over an implementation this
    session would have no trusted reference to validate against
    (see `PREREGISTRATION_LE_STRUCTURE.md` §8's 2026-08-04 amendment).

    Standardizes features the way `heads.py`/`MultinomialSoftmax` do (D-7's
    convention), then reduces to `_l2_pca_components` principal components
    and standardizes again -- see that function's docstring for why the PCA
    step exists at all: `OrderedModel` has no regularization of its own, and
    this candidate's frozen 768-dim BGE input is otherwise underdetermined
    against a per-hazard cell this small.
    """

    name = "L2"
    # Cumulative-link MLE emits genuine per-class probabilities.
    produces_three_class_distribution = True

    def __init__(self) -> None:
        self._cells: dict[str, tuple[np.ndarray, np.ndarray, PCA, np.ndarray, object, np.ndarray]] = {}
        self.unavailable_hazards: frozenset[str] = frozenset()

    def _reduce(
        self, x: np.ndarray, mean: np.ndarray, scale: np.ndarray, pca: PCA, component_scale: np.ndarray
    ) -> np.ndarray:
        z = (x - mean) / scale
        return pca.transform(z) / component_scale

    def fit(self, X: np.ndarray, y: np.ndarray, hazards: np.ndarray) -> None:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        hazards = np.asarray(hazards)

        cells: dict[str, tuple[np.ndarray, np.ndarray, PCA, np.ndarray, object, np.ndarray]] = {}
        unavailable: set[str] = set()
        for hazard in sorted(set(hazards.tolist())):
            mask = hazards == hazard
            x_h, y_h = X[mask], y[mask]

            if len(set(y_h.tolist())) < 2:
                # Same D-45 principle as every other candidate: a
                # single-class cell has nothing to fit.
                unavailable.add(hazard)
                continue

            mean = x_h.mean(axis=0)
            scale = x_h.std(axis=0)
            scale = np.where(scale < 1e-6, 1.0, scale)
            z = (x_h - mean) / scale

            n_components = _l2_pca_components(len(y_h), z.shape[1])
            pca = PCA(n_components=n_components, random_state=DEFAULT_SEED)
            z_pca = pca.fit_transform(z)
            component_scale = z_pca.std(axis=0)
            component_scale = np.where(component_scale < 1e-6, 1.0, component_scale)
            z_reduced = z_pca / component_scale

            try:
                model = OrderedModel(y_h, z_reduced, distr="logit")
                result = model.fit(method="bfgs", disp=False, maxiter=500)
            except (ValueError, np.linalg.LinAlgError):
                # A genuine fit failure -- unavailable, not a crashed ladder.
                # `OrderedModel`'s constructor itself can raise on a
                # rank-deficient design matrix (confirmed by hand), which is
                # why the try wraps construction too, not only `.fit()`.
                unavailable.add(hazard)
                continue

            if not result.mle_retvals.get("converged", False):
                # An unconverged MLE is not a fit D-45 would recognize as
                # available -- its parameters do not reflect a genuine
                # optimum, so serving them would be exactly the kind of
                # "looks fitted, isn't" case D-45 exists to rule out.
                unavailable.add(hazard)
                continue

            cells[hazard] = (mean, scale, pca, component_scale, result, np.asarray(model.labels))

        self._cells = cells
        self.unavailable_hazards = frozenset(unavailable)

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        hazards = np.asarray(hazards)
        out = np.full((len(X), _N_CLASSES), np.nan, dtype=np.float64)

        for hazard in set(hazards.tolist()):
            cell = self._cells.get(hazard)
            if cell is None:
                continue
            mean, scale, pca, component_scale, result, labels = cell
            mask = hazards == hazard
            z_reduced = self._reduce(X[mask], mean, scale, pca, component_scale)
            proba = np.asarray(result.predict(z_reduced))

            # OrderedModel drops a class entirely (fewer output columns, not
            # a zero column) if it never appeared in y_h -- placed by
            # `model.labels`, confirmed by hand, the same trap
            # MultinomialSoftmax's own `classes_` handling guards against.
            full = np.zeros((len(z_reduced), _N_CLASSES), dtype=np.float64)
            for column, cls in enumerate(labels):
                full[:, int(cls)] = proba[:, column]
            out[mask] = full

        return out


class JointCandidate(Protocol):
    """A candidate whose L and E fits are not independent (§2.3's Sharing
    axis, `S2`). Everything else in this module fits each target separately,
    matching the pre-registration §4's "applied per target (L and E
    independently)" comparison procedure -- `S2` is the one level that needs
    to see both targets' data at once to be meaningful at all, so it gets its
    own fit signature rather than forcing `Candidate.fit`'s single-target
    shape to accommodate it.

    **Extended alongside `Candidate`, not in place of it.** Every
    already-built, already-tested single-target candidate (`TwoHeadReference`,
    `TwoHeadFamily`, `MultinomialSoftmax`, `OrdinalCumulativeLink`) is
    untouched and still conforms to `Candidate` exactly as slice A left it.

    After `fit`, `target_view("L")`/`target_view("E")` hand back an ordinary
    `Candidate`-conforming object for that target, so nothing downstream
    (`comparison_metrics.py`, a stage-1/2 driver) needs to know a candidate
    was jointly fit -- it is handed something that already looks like every
    other candidate it compares against.
    """

    name: str

    def fit(
        self,
        X_l: np.ndarray,
        y_l: np.ndarray,
        hazards_l: np.ndarray,
        X_e: np.ndarray,
        y_e: np.ndarray,
        hazards_e: np.ndarray,
    ) -> None: ...

    def target_view(self, target: Literal["L", "E"]) -> "Candidate": ...


class _JointTargetView:
    """`Candidate`-protocol view of one target of an already-fitted
    `JointCandidate`. `fit` is intentionally unusable here -- fitting only
    ever happens on the joint object, once, across both targets at once; a
    caller that tries to fit this view directly has misunderstood what it
    is, and this raises rather than silently doing nothing.
    """

    def __init__(
        self,
        name: str,
        predict_fn: Callable[[np.ndarray, np.ndarray], np.ndarray],
        *,
        produces_three_class_distribution: bool,
    ) -> None:
        self.name = name
        self._predict_fn = predict_fn
        # Propagated from the joint candidate rather than defaulted: a view
        # must never claim a distribution property its own model does not have.
        self.produces_three_class_distribution = produces_three_class_distribution

    def fit(self, X: np.ndarray, y: np.ndarray, hazards: np.ndarray) -> None:
        raise RuntimeError(
            f"{self.name} is a target_view() of a JointCandidate -- fit the joint "
            "candidate itself (on both targets at once), not this view."
        )

    def predict_proba(self, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        return self._predict_fn(X, hazards)


class SharedTwoHeadJoint:
    """`S2` -- one shared parameterization with two output blocks. Every
    other axis stays at `R`'s level (`W1` uniform weighting, `H3` per-hazard,
    `B2` gated branching); Sharing is the only one this candidate moves.

    **What "shared" means here, stated explicitly since the pre-registration
    gives no formula** (same footing as `TwoHeadFamily`'s `W2`/`W3` note).
    Per hazard, **one** nonzero head and **one** high head
    (`heads.fit_binary_head`) are fit on the rows of **both** targets
    pooled together -- L's rows contribute their own L-derived nonzero/high
    binary labels, E's rows contribute their own E-derived ones, uniform
    weight across the pool. That single head pair is the shared
    parameterization. The **two output blocks** are the decision layer on
    top of it: L and E each get their own independently
    `rules.optimize_ordinal_thresholds`-optimized threshold pair, applied to
    that *same* shared head's `predict_proba_centered` output, restricted to
    that target's own rows.

    This is a genuinely cheaper structure than `R`, not just a differently
    labeled one: 15 hazards' worth of heads fit **once**, instead of `R`'s
    15 x 2 = 30 (a full set per target) -- directly exercising §4.1's
    fewer-fitted-parameters tie-break criterion, not only the Sharing axis's
    name.

    A hazard with no rows at all for one target (Privacy and Sexual Content
    have none for L -- `interim_data.legitimization_rows` excludes them
    entirely) has nothing to optimize a threshold pair against for that
    target: that target's `target_view` reports the hazard unavailable,
    while the shared head still serves the other target normally.
    """

    name = "S2"
    # S2 varies only the Sharing axis from R and keeps its L3 two-head
    # loss, so it inherits R's defect: the shared head pair still decides
    # by threshold and still returns a one-hot row. It is a legitimate
    # candidate to *measure* and an ineligible one to *select*.
    produces_three_class_distribution = False

    def __init__(self) -> None:
        self._heads: dict[str, tuple[BinaryHead, BinaryHead]] = {}
        self._thresholds: dict[str, dict[str, tuple[float, float]]] = {"L": {}, "E": {}}
        # A hazard here means the *shared head itself* was unfittable
        # (D-45) -- both targets lose it. A hazard absent from one target's
        # `_thresholds[target]` but present in `_heads` means that target
        # simply had no rows for it (Privacy/Sexual Content under L), a
        # different reason with the same NaN-row effect.
        self.unavailable_hazards: frozenset[str] = frozenset()

    def fit(
        self,
        X_l: np.ndarray,
        y_l: np.ndarray,
        hazards_l: np.ndarray,
        X_e: np.ndarray,
        y_e: np.ndarray,
        hazards_e: np.ndarray,
    ) -> None:
        X_l = np.asarray(X_l, dtype=np.float64)
        y_l = np.asarray(y_l, dtype=np.int64)
        hazards_l = np.asarray(hazards_l)
        X_e = np.asarray(X_e, dtype=np.float64)
        y_e = np.asarray(y_e, dtype=np.int64)
        hazards_e = np.asarray(hazards_e)

        all_hazards = sorted(set(hazards_l.tolist()) | set(hazards_e.tolist()))

        heads: dict[str, tuple[BinaryHead, BinaryHead]] = {}
        thresholds: dict[str, dict[str, tuple[float, float]]] = {"L": {}, "E": {}}
        unavailable: set[str] = set()

        for hazard in all_hazards:
            mask_l = hazards_l == hazard
            mask_e = hazards_e == hazard
            x_pool = np.concatenate([X_l[mask_l], X_e[mask_e]], axis=0)
            y_pool = np.concatenate([y_l[mask_l], y_e[mask_e]], axis=0)
            weights = np.ones(len(y_pool), dtype=np.float64)  # W1, held at R's level

            nonzero_head = fit_binary_head(x_pool, (y_pool > 0).astype(np.int64), weights)
            high_head = fit_binary_head(x_pool, (y_pool == 2).astype(np.int64), weights)

            if nonzero_head.status == "skipped" or high_head.status == "skipped":
                # DECISIONS.md D-45: the shared head is unavailable, so
                # neither target can be scored for this hazard at all.
                unavailable.add(hazard)
                continue

            heads[hazard] = (nonzero_head, high_head)

            for target, x_target, y_target in (
                ("L", X_l[mask_l], y_l[mask_l]),
                ("E", X_e[mask_e], y_e[mask_e]),
            ):
                if len(y_target) == 0:
                    continue  # this target has no rows for this hazard at all
                centered_nonzero = nonzero_head.predict_proba_centered(x_target)
                centered_high = high_head.predict_proba_centered(x_target)
                nonzero_threshold, high_threshold, _ = optimize_ordinal_thresholds(
                    y_target, centered_nonzero, centered_high
                )
                thresholds[target][hazard] = (nonzero_threshold, high_threshold)

        self._heads = heads
        self._thresholds = thresholds
        self.unavailable_hazards = frozenset(unavailable)

    def _predict(self, target: str, X: np.ndarray, hazards: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        hazards = np.asarray(hazards)
        out = np.full((len(X), _N_CLASSES), np.nan, dtype=np.float64)

        for hazard in set(hazards.tolist()):
            heads_cell = self._heads.get(hazard)
            thresholds_cell = self._thresholds[target].get(hazard)
            if heads_cell is None or thresholds_cell is None:
                continue
            nonzero_head, high_head = heads_cell
            nonzero_threshold, high_threshold = thresholds_cell
            mask = hazards == hazard
            x_h = X[mask]
            centered_nonzero = nonzero_head.predict_proba_centered(x_h)
            centered_high = high_head.predict_proba_centered(x_h)
            labels = ordinal_prediction(centered_nonzero, centered_high, nonzero_threshold, high_threshold)
            one_hot = np.zeros((len(labels), _N_CLASSES), dtype=np.float64)
            one_hot[np.arange(len(labels)), labels] = 1.0
            out[mask] = one_hot

        return out

    def target_view(self, target: Literal["L", "E"]) -> "Candidate":
        if target not in ("L", "E"):
            raise ValueError(f"target must be 'L' or 'E', got {target!r}")
        return _JointTargetView(
            f"S2[{target}]",
            lambda X, hazards: self._predict(target, X, hazards),
            produces_three_class_distribution=self.produces_three_class_distribution,
        )


# Stage 1's ten non-reference levels (PREREGISTRATION_LE_STRUCTURE.md §2.4,
# corrected 2026-08-04). `P2`/`P3` are not builder entries -- see
# `TwoHeadFamily`'s docstring; they are `TwoHeadReference` fit on
# `features.SentenceEmbeddings.pooled("P2"/"P3")` instead of `"P1"`, a
# harness-level input choice with no candidate-level code of its own.
STAGE1_BUILDERS: dict[str, Callable[[], object]] = {
    "L1": lambda: MultinomialSoftmax(),
    "L2": lambda: OrdinalCumulativeLink(),
    "W2": lambda: TwoHeadFamily("W2", weighting="W2"),
    "W3": lambda: TwoHeadFamily("W3", weighting="W3"),
    "H1": lambda: TwoHeadFamily("H1", hazard_conditioning="H1"),
    "H2": lambda: TwoHeadFamily("H2", hazard_conditioning="H2"),
    "B1": lambda: TwoHeadFamily("B1", branching="B1"),
}

# `S2` is fit jointly across both targets (`JointCandidate`), not per target
# -- it does not fit `STAGE1_BUILDERS`' per-target shape, so it is its own
# registry. A stage-1 driver builds it once, then reads
# `target_view("L")`/`target_view("E")` as the L and E entries for the
# Sharing axis.
JOINT_BUILDERS: dict[str, Callable[[], JointCandidate]] = {
    "S2": lambda: SharedTwoHeadJoint(),
}

# All ten of §2.4's non-reference levels are now accounted for: eight in
# STAGE1_BUILDERS, S2 in JOINT_BUILDERS, P2/P3 needing no candidate-level
# code (TwoHeadReference re-fit on differently-pooled features).
STAGE1_LEVELS: tuple[str, ...] = (
    "L1", "L2", "W2", "W3", "S2", "H1", "H2", "B1", "P2", "P3"
)


_assert_no_fixed_rule_import(sys.modules[__name__])
