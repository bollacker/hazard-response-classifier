"""Tests for the Release 1.1 evaluator artifact
(`docs/planning/PR5_EXECUTION_PLAN.md` §6, slice B; `ARCHITECTURE.md` §10;
`PREREGISTRATION_LE_STRUCTURE.md` §6).

**A load-what-you-saved test belongs here, not in PR 6.** Round-tripping is
PR 6's exit criterion, but deferring the reader's test to PR 6 would mean
shipping a writer with no reader -- so the identity these tests turn on is
that a loaded artifact **scores identically** to the model that was written,
not merely that the files parse.

The other three claims checked here are all things that fail *silently*:
no `thresholds.json` (D-68's structure has no thresholds, so an empty one
would be a lie about the model), no pickle anywhere (D-37), and
`rules.json`'s supported hazard set matching the fitted cells exactly
(D-57 makes `hazard_scope` default to it).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest

from hazard_classifier.evaluator import artifact as artifact_module
from hazard_classifier.evaluator.artifact import (
    ARTIFACT_FORMAT,
    ArtifactError,
    is_evaluator_artifact,
    load_artifact,
    write_artifact,
)
from hazard_classifier.evaluator.components.integration import RuleSet
from hazard_classifier.evaluator.training.multinomial import fit_target_model
from hazard_classifier.evaluator.training.provenance import (
    ComponentRecord,
    FitProvenance,
    LEModels,
)

GOLDEN_ARTIFACT = Path(__file__).resolve().parents[1] / "golden" / "evaluator_1_1" / "artifact"
EVALUATOR_PACKAGE_DIR = Path(artifact_module.__file__).resolve().parent

_RULES = RuleSet(
    enablement_only_hazards=frozenset({"prv", "sxc_prn"}),
    specialized_advice_hazards=frozenset({"spc_hlt"}),
)


def _synthetic_models(rng=None, *, n_features=6):
    """Two hazards for E and one for L, mirroring the real shape: `prv` is
    enablement-only, so it has an E cell and no L cell at all.
    """
    rng = rng or np.random.default_rng(20260806)
    n = 60
    hazards_e = np.array(["hte"] * n + ["prv"] * n)
    y_e = np.concatenate([rng.integers(0, 3, size=n), rng.integers(0, 3, size=n)]).astype(np.int64)
    X_e = rng.normal(size=(2 * n, n_features))
    X_e[:, 0] += np.where(y_e == 0, -1.5, np.where(y_e == 1, 0.0, 1.5))

    hte = hazards_e == "hte"

    return LEModels(
        legitimization=fit_target_model(
            X_e[hte], y_e[hte], hazards_e[hte], target="legitimization"
        ),
        enablement=fit_target_model(X_e, y_e, hazards_e, target="enablement"),
        provenance=_provenance(),
    )


def _provenance() -> FitProvenance:
    return FitProvenance(
        source_path="jb_1.0.csv",
        source_sha256="0" * 64,
        split_path="interim_split_v1.json",
        split_version="interim-v1",
        split_half="train",
        split_role="fit",
        text_view="working",
        embedding_provider="stub",
        embedding_provider_version="1",
        embedding_model_name="stub/model",
        embedding_model_revision=None,
        pooling="mean",
        seed=20260628,
        estimator={"C": 1.0, "class_weight": "balanced", "solver": "lbfgs", "max_iter": 1000},
        components=(
            ComponentRecord("decoding", "baseline_best_readable_view", "1", "partial"),
            ComponentRecord("refusal_detection", "placeholder", "1", "placeholder"),
        ),
        n_feature_rows=120,
        exhausted_excluded=(("pu9", "hte", "prompt_repetition"),),
    )


def _write(tmp_path, models=None):
    models = models or _synthetic_models()
    write_artifact(
        tmp_path / "artifact",
        models,
        artifact_id="test-artifact",
        artifact_version="1",
        rules=_RULES,
    )
    return models, tmp_path / "artifact"


# --- The round trip -------------------------------------------------------


def test_a_loaded_artifact_scores_identically_to_the_model_that_was_written(tmp_path):
    """The exit criterion, and the only form of it that means anything: not
    that the files parse, but that the reconstructed pure-NumPy scorer gives
    the same distributions.
    """
    models, directory = _write(tmp_path)
    loaded = load_artifact(directory)

    rng = np.random.default_rng(1)
    X = rng.normal(size=(40, models.enablement.n_features))
    hazards = np.array(["hte", "prv"] * 20)

    for target in ("legitimization", "enablement"):
        before = getattr(models, target).predict_proba(X, hazards)
        after = getattr(loaded.models, target).predict_proba(X, hazards)
        np.testing.assert_array_equal(
            np.nan_to_num(before, nan=-1.0), np.nan_to_num(after, nan=-1.0)
        )


def test_the_round_trip_preserves_every_cell_array_exactly(tmp_path):
    models, directory = _write(tmp_path)
    loaded = load_artifact(directory)

    for target in ("legitimization", "enablement"):
        original = getattr(models, target)
        restored = getattr(loaded.models, target)
        assert restored.cells.keys() == original.cells.keys()
        assert restored.unavailable_hazards == original.unavailable_hazards
        assert restored.n_features == original.n_features
        assert restored.n_fit_rows == original.n_fit_rows
        for hazard, cell in original.cells.items():
            other = restored.cells[hazard]
            for field in ("coef", "intercept", "mean", "scale"):
                np.testing.assert_array_equal(getattr(other, field), getattr(cell, field))
            assert other.fitted_classes == cell.fitted_classes
            assert other.n_fit_rows == cell.n_fit_rows


def test_the_round_trip_preserves_the_training_provenance(tmp_path):
    """PR 5's exit criterion "runs reproduce results from locked model, rule,
    data, split, and metric versions" is met by this field set surviving the
    artifact or it is not met.
    """
    models, directory = _write(tmp_path)
    assert load_artifact(directory).models.provenance == models.provenance


def test_the_manifest_carries_the_full_provenance_set(tmp_path):
    _, directory = _write(tmp_path)
    manifest = json.loads((directory / "manifest.json").read_text())

    assert manifest["format"] == ARTIFACT_FORMAT
    assert manifest["artifact_id"] == "test-artifact"
    assert manifest["rule_version"] == _RULES.version
    assert manifest["embedding"]["pooling"] == "mean"
    assert manifest["training"]["split_half"] == "train"
    assert manifest["training"]["split_role"] == "fit"
    assert manifest["training"]["text_view"] == "working"
    assert manifest["training"]["source_sha256"] == "0" * 64
    assert manifest["training"]["split_version"] == "interim-v1"
    assert manifest["training"]["seed"] == 20260628
    assert "not evaluated" in manifest["not_evaluated"].lower()


def test_the_manifest_records_the_components_that_produced_the_training_text(tmp_path):
    """`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5: "a re-fit is owed whenever any of
    them is built." Recording the stages here is what makes that checkable
    against a later run rather than remembered.
    """
    _, directory = _write(tmp_path)
    components = json.loads((directory / "manifest.json").read_text())["components"]

    by_stage = {record["stage"]: record for record in components}
    assert by_stage["refusal_detection"]["maturity"] == "placeholder"
    assert by_stage["decoding"]["implementation"] == "baseline_best_readable_view"


# --- What must not be in the artifact ------------------------------------


def test_no_thresholds_file_is_written(tmp_path):
    """`PREREGISTRATION_LE_STRUCTURE.md` §6 retains `thresholds.json` only for
    `L3`. A multinomial decides by argmax; an empty thresholds file would be
    wrong, not harmless.
    """
    _, directory = _write(tmp_path)
    assert not (directory / "thresholds.json").exists()
    assert sorted(p.name for p in directory.iterdir()) == ["manifest.json", "model", "rules.json"]


def test_an_artifact_carrying_thresholds_is_rejected_by_name(tmp_path):
    _, directory = _write(tmp_path)
    (directory / "thresholds.json").write_text("{}")

    with pytest.raises(ArtifactError, match="thresholds"):
        load_artifact(directory)


def test_the_model_payload_loads_with_pickle_disabled(tmp_path):
    """D-37: no pickle, no `joblib`. `np.load` with `allow_pickle=False`
    raises on an object array, so this is a real check rather than a
    restatement of the default.
    """
    _, directory = _write(tmp_path)
    for name in ("legitimization.npz", "enablement.npz"):
        with np.load(directory / "model" / name, allow_pickle=False) as data:
            for key in data.files:
                assert data[key].dtype != object


def test_no_evaluator_module_imports_pickle_or_joblib():
    """The other half of D-37, checked statically: a reader that never
    unpickles is a property of the code, not of one artifact.
    """
    banned = {"pickle", "joblib", "cPickle", "dill"}
    paths = list(EVALUATOR_PACKAGE_DIR.rglob("*.py"))
    assert paths

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {(node.module or "").split(".")[0]}
            else:
                continue
            assert not (names & banned), f"{path.name} imports {sorted(names & banned)} (D-37)"


# --- rules.json and the supported hazard set ------------------------------


def test_the_supported_set_is_exactly_the_hazards_with_a_fitted_cell(tmp_path):
    """D-57 makes `hazard_scope` default to this set, so a hazard listed
    without a cell would fail every one of its rows at scoring time, and a
    hazard omitted despite having one would be silently unscoreable.
    """
    models, directory = _write(tmp_path)
    rules = json.loads((directory / "rules.json").read_text())

    assert frozenset(rules["supported_hazards"]) == models.supported_hazards
    # `prv` has an E cell and no L cell -- the union, not the intersection.
    assert set(rules["supported_hazards"]) == {"hte", "prv"}


def test_a_supported_set_that_disagrees_with_the_cells_is_rejected(tmp_path):
    _, directory = _write(tmp_path)
    rules_path = directory / "rules.json"
    rules = json.loads(rules_path.read_text())
    rules["supported_hazards"].append("vcr")
    rules_path.write_text(json.dumps(rules))

    with pytest.raises(ArtifactError, match="supported hazards"):
        load_artifact(directory)


def test_rules_json_carries_the_frozen_constants_and_the_families(tmp_path):
    """D-23: serve time reads hazard families from the artifact, never
    installed config.
    """
    _, directory = _write(tmp_path)
    loaded = load_artifact(directory)

    assert loaded.rules.enablement_only_hazards == _RULES.enablement_only_hazards
    assert loaded.rules.specialized_advice_hazards == _RULES.specialized_advice_hazards
    assert loaded.rules.hazard_family == {"hte": "default", "prv": "enablement_only"}
    assert loaded.rules.rule_version == _RULES.version


def test_the_family_sets_are_not_narrowed_to_the_supported_hazards(tmp_path):
    """`sxc_prn` has no cell in this fixture, but it is still an
    enablement-only hazard. Narrowing the frozen constants would
    reclassify it as `default` -- the one family whose L/E table requires a
    Legitimization judgment.
    """
    _, directory = _write(tmp_path)
    rules = json.loads((directory / "rules.json").read_text())
    assert "sxc_prn" in rules["enablement_only_hazards"]
    assert "sxc_prn" not in rules["supported_hazards"]


# --- Structural failures --------------------------------------------------


def test_a_baseline_artifact_is_not_mistaken_for_a_1_1_artifact():
    baseline = Path(__file__).resolve().parents[1] / "golden" / "baseline" / "artifact"
    assert baseline.exists()
    assert not is_evaluator_artifact(baseline)

    with pytest.raises(ArtifactError, match="format"):
        load_artifact(baseline)


def test_is_evaluator_artifact_recognizes_one(tmp_path):
    _, directory = _write(tmp_path)
    assert is_evaluator_artifact(directory)
    assert not is_evaluator_artifact(tmp_path / "nowhere")


def test_a_missing_required_file_is_named(tmp_path):
    _, directory = _write(tmp_path)
    (directory / "rules.json").unlink()

    with pytest.raises(ArtifactError, match="rules.json"):
        load_artifact(directory)


def test_an_index_naming_a_cell_the_payload_lacks_is_rejected(tmp_path):
    _, directory = _write(tmp_path)
    cells_path = directory / "model" / "cells.json"
    cells = json.loads(cells_path.read_text())
    cells["targets"]["enablement"]["cells"]["vcr"] = {"fitted_classes": [0, 1], "n_fit_rows": 4}
    cells_path.write_text(json.dumps(cells))

    with pytest.raises(ArtifactError, match="no array"):
        load_artifact(directory)


def test_writing_a_model_with_no_fitted_cell_anywhere_is_refused(tmp_path):
    single_class = np.zeros(20, dtype=np.int64)
    X = np.random.default_rng(2).normal(size=(20, 4))
    hazards = np.array(["prv"] * 20)
    empty = fit_target_model(X, single_class, hazards, target="enablement")
    models = LEModels(legitimization=empty, enablement=empty, provenance=_provenance())

    with pytest.raises(ArtifactError, match="no fitted cell"):
        write_artifact(
            tmp_path / "a", models, artifact_id="x", artifact_version="1", rules=_RULES
        )


def test_a_target_with_no_cells_still_round_trips(tmp_path):
    """Legitimization can legitimately have nothing fitted -- every eligible
    hazard unavailable (D-45) -- while Enablement still ships. That must be a
    loadable artifact, not a crash.
    """
    models = _synthetic_models()
    empty_l = fit_target_model(
        np.random.default_rng(3).normal(size=(20, models.enablement.n_features)),
        np.zeros(20, dtype=np.int64),
        np.array(["hte"] * 20),
        target="legitimization",
    )
    models = LEModels(
        legitimization=empty_l, enablement=models.enablement, provenance=models.provenance
    )

    write_artifact(
        tmp_path / "a", models, artifact_id="x", artifact_version="1", rules=_RULES
    )
    loaded = load_artifact(tmp_path / "a")

    assert loaded.models.legitimization.cells == {}
    assert loaded.models.legitimization.unavailable_hazards == frozenset({"hte"})
    assert loaded.rules.supported_hazards == frozenset({"hte", "prv"})


# --- The committed golden fixture ----------------------------------------


def test_the_golden_1_1_artifact_loads_and_scores():
    """What makes "fitting and scoring are independently testable" reachable:
    slice C's component tests get this, and never fit.
    """
    loaded = load_artifact(GOLDEN_ARTIFACT)

    assert loaded.artifact_id == "golden-1.1-fixture"
    assert loaded.rules.supported_hazards == frozenset({"hte", "prv"})
    assert loaded.models.enablement.n_features == 768
    assert loaded.models.legitimization.supported_hazards == frozenset({"hte"})
    assert loaded.models.enablement.supported_hazards == frozenset({"hte", "prv"})

    rng = np.random.default_rng(4)
    X = rng.normal(size=(5, 768))
    proba = loaded.models.enablement.predict_proba(X, np.array(["hte"] * 5))
    assert proba.shape == (5, 3)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0)

    # `prv` is enablement-only: L has no cell for it, and asking is a refusal
    # to answer rather than a substituted judgment (D-45, SCIENCE.md phase A).
    assert np.isnan(
        loaded.models.legitimization.predict_proba(X, np.array(["prv"] * 5))
    ).all()


def test_the_golden_fixture_says_it_is_a_fixture():
    """Its coefficients are fitted on twelve synthetic rows and mean nothing.
    Anything that reads it must be able to tell.
    """
    loaded = load_artifact(GOLDEN_ARTIFACT)
    assert "fixture" in loaded.artifact_id
    assert loaded.models.provenance.split_role == "fixture"
    assert loaded.models.provenance.split_version == "none"
