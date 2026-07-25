"""Tests for `hazard_classifier.model.save`/`load` (`VERIFICATION.md` IS-5).

Reuses the same synthetic-fixture pattern as `test_model_fit.py` -- no
BGE/embed.py dependency.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from hazard_classifier import config
from hazard_classifier.model import fit, load, save
from hazard_classifier.rules import is_required_component

_ENABLEMENT_ONLY = frozenset({"prv"})
_SPECIALIZED_ADVICE = frozenset({"spc_fin"})
_N = 20
_HAZARDS = np.array(["hte"] * 10 + ["prv"] * 10)


def _make_fixture(seed: int = 0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "seed_prompt_id": [f"sp{i // 2}" for i in range(_N)],
            "hazard": _HAZARDS,
            "enablement_value": [str(v) for v in ([0, 1, 2] * 4)[:10]] + [str(v) for v in ([0, 1, 2] * 4)[:10]],
            "legitimization_value": [str(v) for v in ([0, 1, 2] * 4)[:10]] + [""] * 10,
        }
    )
    enablement_features = rng.normal(size=(_N, 3))
    enablement_features[:, 0] += df["enablement_value"].astype(int).to_numpy() * 1.5
    legitimization_features = rng.normal(size=(_N, 3))
    legit_labels = np.where(df["hazard"] == "prv", 0, df["legitimization_value"].replace("", "0").astype(int))
    legitimization_features[:, 0] += legit_labels * 1.5

    features = {"enablement": enablement_features, "legitimization": legitimization_features}
    effective = {"enablement": np.ones(_N, dtype=bool), "legitimization": np.ones(_N, dtype=bool)}
    return df, features, effective


def test_round_trip_gives_bit_identical_scores_and_thresholds(tmp_path) -> None:
    df, features, effective = _make_fixture()
    classifier = fit(
        df,
        features,
        effective,
        _ENABLEMENT_ONLY,
        specialized_advice_hazards=_SPECIALIZED_ADVICE,
        embedding_model_name="BAAI/bge-base-en-v1.5",
        embedding_model_revision="abc123",
    )

    save(classifier, tmp_path)
    reloaded = load(tmp_path)

    probe = np.array([[0.1, -0.2, 0.3], [1.5, 0.5, -1.0], [-2.0, 2.0, 0.0]])
    assert set(reloaded.cells) == set(classifier.cells)
    for key, cell in classifier.cells.items():
        reloaded_cell = reloaded.cells[key]
        assert np.array_equal(
            cell.nonzero_head.predict_proba_centered(probe),
            reloaded_cell.nonzero_head.predict_proba_centered(probe),
        )
        assert np.array_equal(
            cell.high_head.predict_proba_centered(probe),
            reloaded_cell.high_head.predict_proba_centered(probe),
        )
        assert cell.nonzero_threshold == reloaded_cell.nonzero_threshold
        assert cell.high_threshold == reloaded_cell.high_threshold
        assert cell.status == reloaded_cell.status

    assert reloaded.holdout_seed_prompt_ids == classifier.holdout_seed_prompt_ids
    assert reloaded.skipped_components == classifier.skipped_components
    assert reloaded.trained_hazards == classifier.trained_hazards
    assert reloaded.enablement_only_hazards == classifier.enablement_only_hazards
    # D-23: predict-time embeddings must come from the artifact, never a
    # hardcoded default -- confirm the exact model+revision this artifact
    # was fit with survives the round trip.
    assert reloaded.embedding_model_name == "BAAI/bge-base-en-v1.5"
    assert reloaded.embedding_model_revision == "abc123"
    # D-27: rules.json (and so a reloaded classifier) only ever remembers
    # hazard-family-set members that are actually trained hazards -- this
    # fixture's "spc_fin" isn't one of the two trained hazards ("hte"/"prv"),
    # so it is correctly dropped by the round trip, not preserved verbatim.
    assert classifier.specialized_advice_hazards == _SPECIALIZED_ADVICE
    assert reloaded.specialized_advice_hazards == frozenset()


def test_rules_json_key_set_is_exactly_the_trained_hazards(tmp_path) -> None:
    df, features, effective = _make_fixture()
    classifier = fit(df, features, effective, _ENABLEMENT_ONLY, specialized_advice_hazards=_SPECIALIZED_ADVICE)
    save(classifier, tmp_path)

    rules = json.loads((tmp_path / "rules.json").read_text())
    assert set(rules["hazard_family"].keys()) == set(classifier.trained_hazards)
    assert set(rules["trained_hazards"]) == set(classifier.trained_hazards)
    assert rules["hazard_family"]["prv"] == "enablement_only"
    assert rules["hazard_family"]["hte"] == "default"


def test_manifest_extras_omitted_by_default_and_present_when_supplied(tmp_path) -> None:
    """`DECISIONS.md` D-35: `save`'s new optional manifest-extras kwargs
    (code version, hyperparameters, timestamp, training-file hash, training
    row/hazard counts, `PLAN.md` §3 step 5) must not appear in the manifest
    at all when omitted -- every pre-D-35 caller (every test besides this
    one) still gets exactly the manifest shape `save` has always written --
    and must appear, verbatim, when a caller (`cli/train.py`) supplies them.
    """
    df, features, effective = _make_fixture()
    classifier = fit(df, features, effective, _ENABLEMENT_ONLY)

    default_dir = tmp_path / "default"
    save(classifier, default_dir)
    default_manifest = json.loads((default_dir / "manifest.json").read_text())
    for key in (
        "code_version",
        "hyperparameters",
        "training_timestamp",
        "training_file_hash",
        "training_row_count",
        "training_hazard_counts",
    ):
        assert key not in default_manifest

    extras_dir = tmp_path / "extras"
    save(
        classifier,
        extras_dir,
        code_version="0.0.1",
        hyperparameters={"other_hazard_weight": 0.25, "holdout_seed_fraction": 0.0},
        training_timestamp="2026-07-25T00:00:00Z",
        training_file_hash="deadbeef",
        training_row_count=_N,
        training_hazard_counts={"hte": 10, "prv": 10},
    )
    extras_manifest = json.loads((extras_dir / "manifest.json").read_text())
    assert extras_manifest["code_version"] == "0.0.1"
    assert extras_manifest["hyperparameters"] == {"other_hazard_weight": 0.25, "holdout_seed_fraction": 0.0}
    assert extras_manifest["training_timestamp"] == "2026-07-25T00:00:00Z"
    assert extras_manifest["training_file_hash"] == "deadbeef"
    assert extras_manifest["training_row_count"] == _N
    assert extras_manifest["training_hazard_counts"] == {"hte": 10, "prv": 10}
    # The pre-existing fields must be unaffected by the new kwargs.
    assert extras_manifest["embedding_model_name"] == default_manifest["embedding_model_name"]


def test_skipped_components_rollup_matches_per_cell_status_across_files(tmp_path) -> None:
    """Degenerate **Legitimization**, not Enablement -- a wholly-skipped
    Enablement now hard-fails `fit` entirely (`DECISIONS.md` D-28,
    `VERIFICATION.md` IS-6), so there would be no classifier to save at all.
    """
    df, features, effective = _make_fixture()
    df = df.copy()
    df["legitimization_value"] = df["legitimization_value"].where(df["hazard"] == "prv", "1")

    with pytest.warns(UserWarning, match="Legitimization"):
        classifier = fit(df, features, effective, _ENABLEMENT_ONLY, specialized_advice_hazards=_SPECIALIZED_ADVICE)
    save(classifier, tmp_path)

    thresholds = json.loads((tmp_path / "thresholds.json").read_text())
    manifest = json.loads((tmp_path / "manifest.json").read_text())

    recomputed_skipped = [
        component
        for component, by_hazard in thresholds.items()
        if by_hazard and all(cell["status"] == "skipped" for cell in by_hazard.values())
    ]
    assert sorted(recomputed_skipped) == sorted(manifest["skipped_components"])
    assert "legitimization" in manifest["skipped_components"]
    assert "enablement" not in manifest["skipped_components"]


def test_loaded_enablement_only_hazards_is_the_frozen_set_not_installed_config(tmp_path) -> None:
    """Completes IS-C's wiring (`DECISIONS.md` D-23): a hazard reclassified
    in installed config after training must not silently change how a
    loaded artifact scores. Freezes a set that disagrees with installed
    `config.ENABLEMENT_ONLY_HAZARDS` in both directions: adds "hte" (absent
    from config's set) and omits "prv" (present in config's set). Real
    legitimization ground truth for *both* hazards here (unlike
    `_make_fixture`'s "prv" convention) so the divergence itself is what's
    under test, not an incidental blank-label conversion (`DECISIONS.md`
    D-29).
    """
    frozen_enablement_only = frozenset({"hte"})
    assert frozen_enablement_only != config.ENABLEMENT_ONLY_HAZARDS
    assert "prv" in config.ENABLEMENT_ONLY_HAZARDS

    rng = np.random.default_rng(1)
    df = pd.DataFrame(
        {
            "seed_prompt_id": [f"sp{i // 2}" for i in range(_N)],
            "hazard": _HAZARDS,
            "enablement_value": [str(v) for v in ([0, 1, 2] * 4)[:10]] * 2,
            "legitimization_value": [str(v) for v in ([0, 1, 2] * 4)[:10]] * 2,
        }
    )
    enablement_features = rng.normal(size=(_N, 3))
    enablement_features[:, 0] += df["enablement_value"].astype(int).to_numpy() * 1.5
    legitimization_features = rng.normal(size=(_N, 3))
    legitimization_features[:, 0] += df["legitimization_value"].astype(int).to_numpy() * 1.5
    features = {"enablement": enablement_features, "legitimization": legitimization_features}
    effective = {"enablement": np.ones(_N, dtype=bool), "legitimization": np.ones(_N, dtype=bool)}

    classifier = fit(df, features, effective, frozen_enablement_only)
    save(classifier, tmp_path)
    reloaded = load(tmp_path)

    assert reloaded.enablement_only_hazards == frozen_enablement_only
    assert is_required_component("legitimization", "hte", reloaded.enablement_only_hazards) is False
    assert is_required_component("legitimization", "hte", config.ENABLEMENT_ONLY_HAZARDS) is True
    assert is_required_component("legitimization", "prv", reloaded.enablement_only_hazards) is True
    assert is_required_component("legitimization", "prv", config.ENABLEMENT_ONLY_HAZARDS) is False
    assert ("legitimization", "hte") not in reloaded.cells
    assert ("legitimization", "prv") in reloaded.cells
