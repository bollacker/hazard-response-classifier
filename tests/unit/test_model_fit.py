"""Tests for `hazard_classifier.model.fit` (`VERIFICATION.md` IS-4).

Synthetic fixtures only -- no BGE/embed.py dependency (`PLAN.md` §8.1: unit
tests need no model download). `component_features`/`component_effective`
stand in for a not-yet-built `embed.py`'s pooled output.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from hazard_classifier.model import choose_holdout_seed_prompts, fit

_ENABLEMENT_ONLY = frozenset({"prv"})
_N = 20
_HAZARDS = np.array(["hte"] * 10 + ["prv"] * 10)


def _make_fixture(seed: int = 0) -> tuple[pd.DataFrame, dict[str, np.ndarray], dict[str, np.ndarray]]:
    rng = np.random.default_rng(seed)

    df = pd.DataFrame(
        {
            "seed_prompt_id": [f"sp{i // 2}" for i in range(_N)],
            "hazard": _HAZARDS,
            # Mixed 0/1/2 labels for both hazards, non-degenerate.
            "enablement_value": ([str(v) for v in ([0, 1, 2] * 4)[:10]] + [str(v) for v in ([0, 1, 2] * 4)[:10]]),
            # Real legitimization ground truth for "hte"; blank for "prv"
            # (enablement-only, D-18) -- never read since those rows are
            # filtered out of legitimization's row set before conversion.
            "legitimization_value": (
                [str(v) for v in ([0, 1, 2] * 4)[:10]] + [""] * 10
            ),
        }
    )

    enablement_features = rng.normal(size=(_N, 3))
    # Nudge features to correlate with the label so LogisticRegression
    # converges to a real (non-degenerate) fit rather than noise.
    enablement_labels = df["enablement_value"].astype(int).to_numpy()
    enablement_features[:, 0] += enablement_labels * 1.5
    legitimization_features = rng.normal(size=(_N, 3))
    legitimization_labels = np.where(
        df["hazard"] == "prv", 0, df["legitimization_value"].replace("", "0").astype(int)
    )
    legitimization_features[:, 0] += legitimization_labels * 1.5

    component_features = {
        "enablement": enablement_features,
        "legitimization": legitimization_features,
    }
    component_effective = {
        "enablement": np.ones(_N, dtype=bool),
        "legitimization": np.ones(_N, dtype=bool),
    }
    return df, component_features, component_effective


def test_default_holdout_fraction_is_zero_and_records_empty_list() -> None:
    df, features, effective = _make_fixture()
    classifier = fit(df, features, effective, _ENABLEMENT_ONLY)
    assert classifier.holdout_seed_prompt_ids == []


def test_holdout_seed_prompts_are_recorded_and_never_influence_the_fit() -> None:
    df, features, effective = _make_fixture()
    classifier = fit(df, features, effective, _ENABLEMENT_ONLY, holdout_seed_fraction=0.5, seed=7)

    all_seed_ids = set(df["seed_prompt_id"])
    assert classifier.holdout_seed_prompt_ids
    assert set(classifier.holdout_seed_prompt_ids) <= all_seed_ids

    # Forcing function: corrupt the ground-truth labels and features for
    # *only* the held-out rows, then refit. If holdout rows are genuinely
    # excluded from the fit (D-1), corrupting them must not change a single
    # fitted parameter.
    holdout_mask = df["seed_prompt_id"].isin(classifier.holdout_seed_prompt_ids).to_numpy()
    assert holdout_mask.any()

    corrupted_df = df.copy()
    corrupted_df.loc[holdout_mask, "enablement_value"] = "2"
    corrupted_df.loc[holdout_mask, "legitimization_value"] = corrupted_df.loc[
        holdout_mask, "legitimization_value"
    ].where(corrupted_df.loc[holdout_mask, "hazard"] == "prv", "2")
    corrupted_features = copy.deepcopy(features)
    for component in ("enablement", "legitimization"):
        corrupted_features[component][holdout_mask] = 999.0

    reclassifier = fit(
        corrupted_df, corrupted_features, effective, _ENABLEMENT_ONLY, holdout_seed_fraction=0.5, seed=7
    )

    for key in classifier.cells:
        original = classifier.cells[key]
        corrupted = reclassifier.cells[key]
        assert np.array_equal(original.nonzero_head.mean, corrupted.nonzero_head.mean)
        assert np.array_equal(original.nonzero_head.coef, corrupted.nonzero_head.coef)
        assert original.nonzero_threshold == corrupted.nonzero_threshold
        assert original.high_threshold == corrupted.high_threshold


def test_single_class_labels_mark_every_cell_of_that_component_skipped() -> None:
    """D-5's per-cell skip marking, isolated from D-28's train-time gate
    (`VERIFICATION.md` IS-6, `tests/unit/test_model_train_gate.py`) -- a
    wholly-skipped **Enablement** now hard-fails `fit` entirely (D-28), so
    this test uses Legitimization (single-class across the one hazard for
    which it's required, D-18) to observe D-5's marking mechanism on its own,
    without D-28's stricter Enablement gate intervening.
    """
    df, features, effective = _make_fixture()
    df = df.copy()
    # "hte" is the only hazard Legitimization is required for here ("prv" is
    # enablement-only, D-18); make its label single-class.
    df["legitimization_value"] = df["legitimization_value"].where(df["hazard"] == "prv", "1")

    with pytest.warns(UserWarning, match="Legitimization"):
        classifier = fit(df, features, effective, _ENABLEMENT_ONLY)

    legitimization_cells = [key for key in classifier.cells if key[0] == "legitimization"]
    assert legitimization_cells
    assert all(classifier.cells[key].status == "skipped" for key in legitimization_cells)
    assert "legitimization" in classifier.skipped_components
    assert "enablement" not in classifier.skipped_components


def test_enablement_only_hazard_has_no_legitimization_cell() -> None:
    df, features, effective = _make_fixture()
    classifier = fit(df, features, effective, _ENABLEMENT_ONLY)

    assert ("legitimization", "prv") not in classifier.cells
    assert ("enablement", "prv") in classifier.cells
    assert ("legitimization", "hte") in classifier.cells


def test_mean_scale_identical_across_hazards_within_a_component_through_the_full_fit() -> None:
    """D-7, confirmed at the `fit()` integration level (not just `heads.py`
    in isolation): every hazard cell of a component must share the same
    `mean`/`scale`.
    """
    df, features, effective = _make_fixture()
    classifier = fit(df, features, effective, _ENABLEMENT_ONLY)

    enablement_cells = [classifier.cells[key] for key in classifier.cells if key[0] == "enablement"]
    assert len(enablement_cells) >= 2
    first = enablement_cells[0]
    for other in enablement_cells[1:]:
        assert np.array_equal(first.nonzero_head.mean, other.nonzero_head.mean)
        assert np.array_equal(first.nonzero_head.scale, other.nonzero_head.scale)


def test_choose_holdout_seed_prompts_is_deterministic_and_respects_zero_fraction() -> None:
    ids = pd.Series([f"sp{i}" for i in range(20)])
    assert choose_holdout_seed_prompts(ids, 0.0) == set()
    assert choose_holdout_seed_prompts(ids, 0.0, seed=123) == set()

    first = choose_holdout_seed_prompts(ids, 0.3, seed=42)
    second = choose_holdout_seed_prompts(ids, 0.3, seed=42)
    assert first == second
    assert first
    assert first <= set(ids)
