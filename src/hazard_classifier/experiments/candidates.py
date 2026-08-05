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
from types import ModuleType
from typing import Protocol

import numpy as np

from hazard_classifier.heads import BinaryHead, fit_binary_head
from hazard_classifier.rules import ordinal_prediction, optimize_ordinal_thresholds

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


_assert_no_fixed_rule_import(sys.modules[__name__])
