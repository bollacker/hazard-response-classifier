"""Tests for `DECISIONS.md` D-28's train-time gate (`VERIFICATION.md` IS-6):
a wholly-skipped Enablement hard-fails `fit`; a wholly-skipped Legitimization
warns but still produces a usable (enablement-only) artifact.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hazard_classifier.model import WhollySkippedEnablementError, fit

_ENABLEMENT_ONLY = frozenset({"prv"})
_N = 20
_HAZARDS = np.array(["hte"] * 10 + ["prv"] * 10)


def _make_fixture() -> tuple[pd.DataFrame, dict, dict]:
    rng = np.random.default_rng(0)
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


def test_wholly_skipped_enablement_hard_fails_with_no_classifier_returned() -> None:
    df, features, effective = _make_fixture()
    df = df.copy()
    df["enablement_value"] = "0"  # single-class across both hazards

    with pytest.raises(WhollySkippedEnablementError):
        fit(df, features, effective, _ENABLEMENT_ONLY)


def test_wholly_skipped_legitimization_warns_but_writes_a_usable_enablement_only_artifact() -> None:
    df, features, effective = _make_fixture()
    df = df.copy()
    df["legitimization_value"] = df["legitimization_value"].where(df["hazard"] == "prv", "1")  # single-class "1" for hte

    with pytest.warns(UserWarning, match="Legitimization"):
        classifier = fit(df, features, effective, _ENABLEMENT_ONLY)

    assert classifier.skipped_components == ["legitimization"]
    # Still a usable, enablement-only-workload artifact: Enablement cells for
    # both hazards are fit normally, unaffected by Legitimization's skip.
    assert classifier.cells[("enablement", "hte")].status == "fit"
    assert classifier.cells[("enablement", "prv")].status == "fit"
    assert classifier.cells[("legitimization", "hte")].status == "skipped"
    assert ("legitimization", "prv") not in classifier.cells  # D-18, unaffected by D-28


def test_wholly_skipped_legitimization_does_not_raise() -> None:
    df, features, effective = _make_fixture()
    df = df.copy()
    df["legitimization_value"] = df["legitimization_value"].where(df["hazard"] == "prv", "2")

    with pytest.warns(UserWarning):
        classifier = fit(df, features, effective, _ENABLEMENT_ONLY)
    assert classifier is not None
