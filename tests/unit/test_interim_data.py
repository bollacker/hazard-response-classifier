"""Tests for `hazard_classifier.interim_data`, the single source of truth for
Release 1.1's interim dataset (`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md`
slice 0).

Numbers are asserted against the frozen manifest (`data/interim_split_v1.json`),
never hardcoded literals, so a re-frozen split keeps these tests honest instead
of silently going stale.
"""

from __future__ import annotations

import json

import pytest

from hazard_classifier import interim_data
from hazard_classifier.config import ENABLEMENT_ONLY_HAZARDS
from hazard_classifier.interim_data import (
    InterimDataError,
    legitimization_rows,
    load_interim,
    prompt_group_id,
)


def _manifest() -> dict:
    return json.loads(interim_data.INTERIM_SPLIT.read_text())


def test_load_interim_row_counts_match_the_frozen_manifest():
    manifest = _manifest()

    full = load_interim()
    train = load_interim(split="train")
    evalset = load_interim(split="eval")

    assert len(full) == manifest["source_rows"]
    assert len(train) == manifest["rows"]["train"]
    assert len(evalset) == manifest["rows"]["eval"]
    assert evalset["prompt_group_id"].nunique() == manifest["eval_group_count"]


def test_load_interim_split_column_matches_train_plus_eval():
    full = load_interim()
    assert set(full["split"].unique()) == {"train", "eval"}
    assert len(load_interim(split="train")) + len(load_interim(split="eval")) == len(full)


def test_every_hazard_appears_in_both_splits():
    full = load_interim()
    train_hazards = set(load_interim(split="train")["hazard"].unique())
    eval_hazards = set(load_interim(split="eval")["hazard"].unique())
    all_hazards = set(full["hazard"].unique())

    assert train_hazards == all_hazards
    assert eval_hazards == all_hazards


def test_all_three_l_and_e_classes_appear_in_eval():
    evalset = load_interim(split="eval")
    assert set(evalset["legitimization_value"].unique()) == {0, 1, 2}
    assert set(evalset["enablement_value"].unique()) == {0, 1, 2}


def test_no_prompt_group_id_appears_in_both_splits():
    train = load_interim(split="train")
    evalset = load_interim(split="eval")
    assert set(train["prompt_group_id"]) & set(evalset["prompt_group_id"]) == set()


def test_legitimization_rows_excludes_exactly_enablement_only_hazards():
    full = load_interim()
    manifest = _manifest()

    rows = legitimization_rows(full)

    assert len(rows) == manifest["source_rows"] - (full["hazard"].isin(ENABLEMENT_ONLY_HAZARDS)).sum()
    assert set(rows["hazard"].unique()) & ENABLEMENT_ONLY_HAZARDS == set()
    assert set(full["hazard"].unique()) - set(rows["hazard"].unique()) == ENABLEMENT_ONLY_HAZARDS


def test_prompt_group_id_is_stable_and_whitespace_insensitive():
    assert prompt_group_id("Tell me about X") == prompt_group_id("Tell me about X")
    assert prompt_group_id("Tell me   about X") == prompt_group_id("Tell me about X")
    assert prompt_group_id("Tell me about X") != prompt_group_id("Tell me about Y")


def test_a_tampered_source_file_raises_rather_than_silently_splitting_differently(
    tmp_path, monkeypatch
):
    tampered = tmp_path / "tampered.csv"
    tampered.write_text("prompt_uid,hazard,prompt_text\n1,hte,not the real data\n")
    monkeypatch.setattr(interim_data, "INTERIM_SOURCE", tampered)

    with pytest.raises(InterimDataError):
        load_interim()
