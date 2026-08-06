"""Tests for the production L/E fitter
(`docs/planning/PR5_EXECUTION_PLAN.md` §5, slice A).

Fitting is tested here **with no pipeline and no record** -- PR 5's exit
criterion is that fitting and scoring are independently testable, and this
half of it takes synthetic feature matrices only.

The load-bearing test in this file is the equivalence check against
`experiments.candidates.MultinomialSoftmax`: it is what makes "we shipped the
structure that was selected" a verified claim rather than a stated one
([D-68](../../docs/planning/DECISIONS.md#d-68)), and it is why the
comparison harness is not deleted.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from hazard_classifier.config import DEFAULT_SEED
from hazard_classifier.evaluator import no_fixed_rules
from hazard_classifier.evaluator.training import multinomial
from hazard_classifier.evaluator.training.multinomial import (
    ESTIMATOR_PARAMS,
    N_CLASSES,
    MultinomialCell,
    fit_cell,
    fit_target_model,
)
from hazard_classifier.experiments.candidates import MultinomialSoftmax

TRAINING_PACKAGE_DIR = Path(multinomial.__file__).resolve().parent


def _synthetic_data(rng, n_per_hazard=60):
    """Three hazards, each a case the per-hazard fit must handle:

    - `hte`  -- all three classes present, real signal (the ordinary cell);
    - `vcr`  -- only classes {0, 2} present (the absent-class trap: sklearn
                drops the column *and* switches to its binary form);
    - `prv`  -- single-class, so D-45 makes it unavailable.
    """
    hazards = np.array(
        (["hte"] * n_per_hazard) + (["vcr"] * n_per_hazard) + (["prv"] * n_per_hazard)
    )
    y_hte = rng.integers(0, 3, size=n_per_hazard)
    y_vcr = rng.choice([0, 2], size=n_per_hazard)
    y_prv = np.zeros(n_per_hazard, dtype=np.int64)
    y = np.concatenate([y_hte, y_vcr, y_prv]).astype(np.int64)

    signal = np.where(y == 0, -1.5, np.where(y == 1, 0.0, 1.5))
    X = rng.normal(size=(len(y), 6))
    X[:, 0] += signal
    return X, y, hazards


# --- The estimator is D-68's, parameter for parameter ---------------------


def test_estimator_parameters_are_the_selected_ones():
    """A different regularization or a dropped `class_weight` is a different
    model from the one that was selected (`PR5_EXECUTION_PLAN.md` §5). Pinned
    here so a change has to be deliberate.
    """
    assert dict(ESTIMATOR_PARAMS) == {
        "C": 1.0,
        "class_weight": "balanced",
        "solver": "lbfgs",
        "random_state": DEFAULT_SEED,
        "max_iter": 1000,
    }


def test_production_fitter_agrees_with_the_experiment_implementation():
    """The equivalence test `PR5_EXECUTION_PLAN.md` §5 requires: same rows,
    same features, same seed, agreeing to floating-point tolerance.
    """
    rng = np.random.default_rng(20260805)
    X, y, hazards = _synthetic_data(rng)

    experiment = MultinomialSoftmax()
    experiment.fit(X, y, hazards)
    expected = experiment.predict_proba(X, hazards)

    production = fit_target_model(X, y, hazards, target="enablement")
    actual = production.predict_proba(X, hazards)

    assert production.unavailable_hazards == experiment.unavailable_hazards

    fitted = ~np.isnan(expected).any(axis=1)
    assert fitted.any(), "the fixture must contain fittable cells for this test to mean anything"
    np.testing.assert_allclose(actual[fitted], expected[fitted], rtol=0, atol=1e-12)
    assert np.isnan(actual[~fitted]).all()


def test_equivalence_holds_on_a_cell_with_all_three_classes_and_on_a_two_class_cell():
    """The two sklearn parameterizations `_canonical_parameters` reconciles,
    checked separately so a regression in either is not masked by the other.
    """
    rng = np.random.default_rng(11)
    X = rng.normal(size=(90, 5))

    for classes in ([0, 1, 2], [0, 2], [1, 2]):
        y = np.array([classes[i % len(classes)] for i in range(90)], dtype=np.int64)

        estimator = LogisticRegression(**ESTIMATOR_PARAMS)
        mean, scale = X.mean(axis=0), X.std(axis=0)
        estimator.fit((X - mean) / scale, y)

        cell = fit_cell("hte", X, y)
        assert cell is not None

        actual = cell.predict_proba(X)
        expected = estimator.predict_proba((X - mean) / scale)
        # sklearn returns one column per class it saw; the production cell
        # always returns three, columns indexed by class label.
        np.testing.assert_allclose(actual[:, list(classes)], expected, atol=1e-12)
        absent = [c for c in range(N_CLASSES) if c not in classes]
        assert (actual[:, absent] == 0.0).all()


# --- The payload shape the artifact needs ---------------------------------


def test_a_fitted_cell_holds_arrays_not_a_live_estimator():
    """D-37 bars pickle and `joblib`, so slice B must be able to serialize a
    cell as `.npz` + JSON. Nothing here may be an sklearn object.
    """
    rng = np.random.default_rng(3)
    X, y, hazards = _synthetic_data(rng)
    model = fit_target_model(X, y, hazards, target="legitimization")

    cell = model.cells["hte"]
    for field in (cell.mean, cell.scale, cell.coef, cell.intercept):
        assert isinstance(field, np.ndarray)
    assert not any(
        isinstance(value, LogisticRegression) for value in vars(cell).values()
    ), "a fitted cell must not hold a live estimator (D-37)"


def test_coefficient_payload_matches_the_preregistration_shape():
    """`PREREGISTRATION_LE_STRUCTURE.md` §6's multinomial row: coefficient
    matrix `(n_features, 3)` plus intercept `(3,)`, class order recorded.
    """
    rng = np.random.default_rng(4)
    X, y, hazards = _synthetic_data(rng)
    model = fit_target_model(X, y, hazards, target="enablement")

    cell = model.cells["hte"]
    assert cell.coef.shape == (X.shape[1], N_CLASSES)
    assert cell.intercept.shape == (N_CLASSES,)
    assert cell.fitted_classes == (0, 1, 2)
    assert model.n_features == X.shape[1]


def test_cell_rejects_a_payload_of_the_wrong_shape():
    with pytest.raises(ValueError):
        MultinomialCell(
            hazard="hte",
            mean=np.zeros(4),
            scale=np.ones(4),
            coef=np.zeros((4, 2)),  # two classes, not three
            intercept=np.zeros(N_CLASSES),
            fitted_classes=(0, 1),
            n_fit_rows=10,
        )


# --- D-45: unfittable is unavailable, never substituted -------------------


def test_a_single_class_cell_is_unavailable_not_substituted():
    rng = np.random.default_rng(5)
    X, y, hazards = _synthetic_data(rng)
    model = fit_target_model(X, y, hazards, target="enablement")

    assert model.unavailable_hazards == frozenset({"prv"})
    assert "prv" not in model.cells
    assert model.supported_hazards == frozenset({"hte", "vcr"})

    proba = model.predict_proba(X, hazards)
    assert np.isnan(proba[hazards == "prv"]).all(), "D-45: never a substitute value"


def test_a_hazard_never_seen_at_fit_time_is_nan_not_a_crash():
    rng = np.random.default_rng(6)
    X, y, hazards = _synthetic_data(rng)
    model = fit_target_model(X, y, hazards, target="enablement")

    unseen_X = rng.normal(size=(4, X.shape[1]))
    proba = model.predict_proba(unseen_X, np.array(["ipv"] * 4))
    assert np.isnan(proba).all()


def test_fit_cell_returns_none_for_a_single_class_cell():
    x = np.random.default_rng(7).normal(size=(20, 3))
    assert fit_cell("prv", x, np.zeros(20, dtype=np.int64)) is None


def test_a_target_model_cannot_record_a_hazard_as_both_fitted_and_unavailable():
    rng = np.random.default_rng(8)
    X, y, hazards = _synthetic_data(rng)
    model = fit_target_model(X, y, hazards, target="enablement")

    with pytest.raises(ValueError, match="both fitted and unavailable"):
        multinomial.TargetModel(
            target="enablement",
            cells=model.cells,
            unavailable_hazards=frozenset({"hte"}),
            n_features=model.n_features,
            n_fit_rows=model.n_fit_rows,
        )


# --- The absent class reads zero, and says why ----------------------------


def test_a_class_absent_from_a_cell_gets_exactly_zero_probability():
    """The model cannot predict a class it never saw. A hard zero is honest
    and is a slice D disclosure item -- what it must never be is `exp(0) == 1`
    leaking in from an unmasked zero coefficient column.
    """
    rng = np.random.default_rng(9)
    X, y, hazards = _synthetic_data(rng)
    model = fit_target_model(X, y, hazards, target="enablement")

    cell = model.cells["vcr"]
    assert cell.fitted_classes == (0, 2)

    proba = cell.predict_proba(X[hazards == "vcr"])
    assert (proba[:, 1] == 0.0).all()
    np.testing.assert_allclose(proba.sum(axis=1), 1.0)


def test_every_scored_row_is_a_well_formed_distribution():
    rng = np.random.default_rng(10)
    X, y, hazards = _synthetic_data(rng)
    model = fit_target_model(X, y, hazards, target="legitimization")

    proba = model.predict_proba(X, hazards)
    scored = ~np.isnan(proba).any(axis=1)
    assert (proba[scored] >= 0.0).all()
    np.testing.assert_allclose(proba[scored].sum(axis=1), 1.0)


def test_fitting_is_deterministic():
    rng = np.random.default_rng(12)
    X, y, hazards = _synthetic_data(rng)

    first = fit_target_model(X, y, hazards, target="enablement").predict_proba(X, hazards)
    second = fit_target_model(X, y, hazards, target="enablement").predict_proba(X, hazards)
    np.testing.assert_array_equal(np.nan_to_num(first, nan=-1.0), np.nan_to_num(second, nan=-1.0))


def test_fitting_on_zero_rows_raises():
    with pytest.raises(ValueError, match="zero rows"):
        fit_target_model(
            np.zeros((0, 3)), np.zeros(0, dtype=np.int64), np.array([]), target="enablement"
        )


# --- The fixed-rule guard, carried into production ------------------------


def test_the_fitter_asserts_it_applies_no_fixed_rule():
    """`PREREGISTRATION_LE_STRUCTURE.md` §2.1, made checkable by running the
    code rather than by trusting a docstring
    (`experiments/candidates.py::_assert_no_fixed_rule_import`'s mechanism,
    carried into production per `PR5_EXECUTION_PLAN.md` §5).
    """
    from hazard_classifier.evaluator.training import release

    for module in (multinomial, release):
        no_fixed_rules.assert_no_fixed_rule_import(module)


@pytest.mark.parametrize(
    "source",
    [
        "from ..components.integration import RuleSet\n",  # the natural spelling here
        "from hazard_classifier.evaluator.components import integration\n",
        "import hazard_classifier.evaluator.components.integration\n",
    ],
)
def test_the_guard_catches_every_spelling_of_the_forbidden_import(tmp_path, source):
    """The `experiments/` original compared `ImportFrom.module` verbatim,
    which would miss `from ..components.integration import RuleSet` -- the
    natural spelling inside this package, and therefore the one the guard
    most needs to catch.

    The offender is a real file on disk, so `inspect.getsource` reads it the
    same way it reads a production module; nothing is patched.
    """
    path = tmp_path / "_offender.py"
    path.write_text(source, encoding="utf-8")

    offender = type(sys)("hazard_classifier.evaluator.training._offender")
    offender.__package__ = "hazard_classifier.evaluator.training"
    offender.__file__ = str(path)

    with pytest.raises(no_fixed_rules.FixedRuleImportError, match="fixed rules"):
        no_fixed_rules.assert_no_fixed_rule_import(offender)


def test_the_guard_passes_a_module_that_imports_no_fixed_rule(tmp_path):
    """The other half of the claim: the guard is not trivially true."""
    path = tmp_path / "_innocent.py"
    path.write_text("from ..components.embedding import MeanPooling\n", encoding="utf-8")

    innocent = type(sys)("hazard_classifier.evaluator.training._innocent")
    innocent.__package__ = "hazard_classifier.evaluator.training"
    innocent.__file__ = str(path)

    no_fixed_rules.assert_no_fixed_rule_import(innocent)


@pytest.mark.parametrize(
    "path",
    sorted(TRAINING_PACKAGE_DIR.glob("*.py")),
    ids=lambda p: p.name,
)
def test_no_training_module_imports_the_fixed_rule_module(path):
    """The same claim checked statically over the whole package, so a module
    that forgets to call the guard on itself is still caught.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        names = no_fixed_rules._imported_module_names(
            node, "hazard_classifier.evaluator.training"
        )
        assert not (names & no_fixed_rules.FORBIDDEN_FIXED_RULE_IMPORTS), (
            f"{path.name} imports SCIENCE.md's fixed rules"
        )


def test_the_fitter_does_not_extend_the_baseline_model_module():
    """D-48: `model.py` is shared with the baseline and keeps writing
    `heads.npz`/`thresholds.json` for it. The 1.1 fitter is a new module, and
    a `from ...model import ...` here would be the first step back toward
    "just adding a multinomial branch" to `save`/`load`.
    """
    for path in TRAINING_PACKAGE_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = no_fixed_rules._imported_module_names(
                node, "hazard_classifier.evaluator.training"
            )
            assert "hazard_classifier.model" not in names, f"{path.name} imports the baseline model"
