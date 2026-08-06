"""Tests for the Release 1.1 fit against the frozen interim split
(`docs/planning/PR5_EXECUTION_PLAN.md` §5, slice A).

Three settled decisions are checked here as *behavior*, because each of them
fails silently if it is only written down:

- **[D-73](../../docs/planning/DECISIONS.md#d-73) — the fit half only.**
  `interim_data`'s split labels are `train`/`eval` while the
  pre-registration calls the same halves *fit*/*dev*, and mixing the
  vocabularies fits on the held-out rows with no error anywhere.
- **`PREREGISTRATION_LE_STRUCTURE.md` §1 — L excludes `prv` and `sxc_prn`.**
  `SCIENCE.md` phase A makes final L `N/A` there, so their L labels exist in
  the source and must go unused.
- **[D-45](../../docs/planning/DECISIONS.md#d-45) — unfittable is
  unavailable.** Nothing substitutes a pooled or neighbouring fit for a thin
  cell.

A stub embedding provider stands in for BGE: none of the above is a claim
about *vectors*, and the real encoder is exercised in
`tests/integration/test_le_training_real_bge.py`. The stub is deterministic
per text, so the fit is reproducible run to run.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np
import pytest

from hazard_classifier.config import DEFAULT_SEED, ENABLEMENT_ONLY_HAZARDS
from hazard_classifier.evaluator.components.embedding import MeanPooling
from hazard_classifier.evaluator.training.release import fit_release_models
from hazard_classifier.experiments.candidates import MultinomialSoftmax
from hazard_classifier.interim_data import legitimization_rows, load_interim

_DIM = 16


class _DeterministicStub:
    """A per-text pseudo-random vector. Not BGE, and not meant to be: what
    these tests assert is row selection, cell structure, and provenance.
    """

    name: ClassVar[str] = "deterministic_stub"
    version: ClassVar[str] = "1"

    def embed(self, texts) -> np.ndarray:
        if not texts:
            return np.zeros((0, _DIM), dtype=np.float32)
        seeds = [abs(hash(text)) % (2**31) for text in texts]
        return np.random.default_rng(seeds).normal(size=(len(texts), _DIM)).astype(np.float32)


@pytest.fixture(scope="module")
def models():
    """One fit for the whole module -- stages 1-7 over 635 rows is the cost
    here, and it is paid once rather than per assertion.
    """
    return fit_release_models(provider=_DeterministicStub(), pooling=MeanPooling())


@pytest.fixture(scope="module")
def fit_frame():
    return load_interim(split="train")


# --- D-73: the fit half, and only the fit half ---------------------------


def test_the_fit_uses_the_fit_half_only(models, fit_frame):
    """635 rows for E and 563 for L -- `PREREGISTRATION_LE_STRUCTURE.md` §1's
    own numbers, taken from the frame rather than from literals so the test
    tracks a re-frozen split.
    """
    assert models.enablement.n_fit_rows == len(fit_frame)
    assert models.legitimization.n_fit_rows == len(legitimization_rows(fit_frame))

    assert models.provenance.split_half == "train"
    assert models.provenance.split_role == "fit"


def test_no_dev_row_is_used(models):
    """The other half of D-73. If the dev slice were consumed by fitting,
    slice D's numbers would describe a different model than the one that
    ships.
    """
    dev = load_interim(split="eval")
    assert models.enablement.n_fit_rows + len(dev) == len(load_interim())


def test_the_dev_split_can_be_fitted_but_says_so(models):
    """`split` is a parameter so a diagnostic refit is expressible -- and
    **visible in the provenance**, which is the point. It is not a way to
    consume the dev slice quietly.
    """
    diagnostic = fit_release_models(
        split="eval", provider=_DeterministicStub(), pooling=MeanPooling()
    )
    assert diagnostic.provenance.split_half == "eval"
    assert diagnostic.provenance.split_role == "dev"
    assert diagnostic.enablement.n_fit_rows < models.enablement.n_fit_rows


def test_an_unknown_split_is_rejected():
    with pytest.raises(ValueError, match="split must be one of"):
        fit_release_models(split="fit", provider=_DeterministicStub(), pooling=MeanPooling())


# --- Row eligibility ------------------------------------------------------


def test_legitimization_excludes_the_enablement_only_hazards(models):
    """`SCIENCE.md` phase A makes final L `N/A` for `prv` and `sxc_prn`, so
    their L labels -- which do exist in the source -- go unused.
    """
    assert models.legitimization.supported_hazards.isdisjoint(ENABLEMENT_ONLY_HAZARDS)
    assert models.legitimization.unavailable_hazards.isdisjoint(ENABLEMENT_ONLY_HAZARDS)


def test_enablement_covers_every_hazard_in_the_fit_split(models, fit_frame):
    assert models.enablement.supported_hazards == frozenset(fit_frame["hazard"].unique())


def test_the_two_targets_are_separate_models(models):
    """`S1`: separate L and E models. Same hazard, different parameters --
    a shared parameterization is a different structure from the one D-68
    selected.
    """
    shared = models.legitimization.supported_hazards & models.enablement.supported_hazards
    assert shared
    hazard = sorted(shared)[0]
    assert not np.allclose(
        models.legitimization.cells[hazard].coef, models.enablement.cells[hazard].coef
    )


# --- D-45, and the per-hazard cell record §6 requires ---------------------


def test_every_fitted_cell_is_recorded_with_its_row_count_and_class_set(models):
    """`PREREGISTRATION_LE_STRUCTURE.md` §6's `H3` row: the artifact must
    record which `(target, hazard)` cells were fit. A cell that saw only two
    classes must say so, or a reloaded model silently mis-orders its columns.
    """
    for model in (models.legitimization, models.enablement):
        assert model.cells
        for hazard, cell in model.cells.items():
            assert cell.hazard == hazard
            assert cell.n_fit_rows > 0
            assert set(cell.fitted_classes) <= {0, 1, 2}
            assert cell.coef.shape == (model.n_features, 3)


def test_fitted_and_unavailable_cells_partition_the_hazards(models, fit_frame):
    """Nothing is substituted and nothing is silently dropped: every hazard a
    target had rows for is either fitted or explicitly unavailable.
    """
    e_hazards = frozenset(fit_frame["hazard"].unique())
    assert models.enablement.supported_hazards | models.enablement.unavailable_hazards == e_hazards

    l_hazards = frozenset(legitimization_rows(fit_frame)["hazard"].unique())
    assert (
        models.legitimization.supported_hazards | models.legitimization.unavailable_hazards
        == l_hazards
    )


def test_an_unavailable_hazard_scores_nan_rather_than_a_substituted_judgment(models):
    """`prv` has no L cell at all, by eligibility. Scoring it against the L
    model must be a refusal to answer, never an invented distribution.
    """
    X = np.zeros((3, models.legitimization.n_features))
    proba = models.legitimization.predict_proba(X, np.array(["prv"] * 3))
    assert np.isnan(proba).all()


# --- Agreement with the structure that was selected -----------------------


def test_the_release_fit_agrees_with_the_experiment_implementation(models, fit_frame):
    """The equivalence check on the real fit split's hazards and labels,
    rather than on a synthetic fixture: same rows, same features, same seed.
    """
    from hazard_classifier.evaluator.training.features import build_pipeline_features

    features = build_pipeline_features(
        fit_frame, provider=_DeterministicStub(), pooling=MeanPooling()
    )
    positions = [features.row_index()[str(uid)] for uid in fit_frame["prompt_uid"]]
    X = features.pooled[positions]
    y = fit_frame["enablement_value"].to_numpy(dtype=np.int64)
    hazards = features.hazards[positions]

    experiment = MultinomialSoftmax()
    experiment.fit(X, y, hazards)

    np.testing.assert_allclose(
        models.enablement.predict_proba(X, hazards),
        experiment.predict_proba(X, hazards),
        atol=1e-10,
    )


# --- Provenance -----------------------------------------------------------


def test_provenance_carries_what_reproduces_the_fit(models):
    """PR 5's exit criterion "runs reproduce results from locked model, rule,
    data, split, and metric versions" is met by this field set or it is not
    met (`PR5_EXECUTION_PLAN.md` §6). Slice B writes these into
    `manifest.json`.
    """
    provenance = models.provenance

    assert provenance.source_sha256 == (
        "8fdbec27dbcec27b0d2df4a1e3106f98e3e72d746bd0faa939f57e6a49922ddf"
    )
    assert provenance.split_version == "interim-v1"
    assert provenance.text_view == "working"  # D-72
    assert provenance.seed == DEFAULT_SEED
    assert provenance.pooling == "mean"
    assert provenance.embedding_provider == "deterministic_stub"
    assert dict(provenance.estimator)["solver"] == "lbfgs"
    assert dict(provenance.estimator)["class_weight"] == "balanced"


def test_no_interim_row_exhausts_so_none_is_excluded_from_fitting(models):
    """`scripts/probe_working_text_delta.py`'s headline finding, re-asserted
    where it would actually bite: nothing on this data is fitted on a row the
    evaluator could never score. The field exists because a future dataset
    could change that, not because this one does.
    """
    assert models.provenance.exhausted_excluded == ()
    assert models.provenance.n_feature_rows == models.enablement.n_fit_rows
