"""CLI smoke test for `hrc-train` (`PLAN.md` §8.1: "CLI smoke tests on
examples/sample_input.csv ... with the BGE call mocked/stubbed so unit
tests need no model download").

Monkeypatches `hazard_classifier.embed.embed_sentences` (the one real
network/model call `build_component_features` makes, D-35) with a
deterministic fake, so this test needs no network and no torch inference.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from hazard_classifier import embed
from hazard_classifier.cli.train import main

_SAMPLE_INPUT = Path(__file__).resolve().parents[2] / "examples" / "sample_input.csv"


def _fake_embed_sentences(sentences, **kwargs):
    rng = np.random.default_rng(0)
    return rng.normal(size=(len(sentences), embed.EMBEDDING_DIM)).astype(np.float32)


def test_hrc_train_writes_a_loadable_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    output_dir = tmp_path / "model"

    main(["--input", str(_SAMPLE_INPUT), "--output-dir", str(output_dir)])

    assert (output_dir / "heads.npz").exists()
    assert (output_dir / "thresholds.json").exists()
    assert (output_dir / "rules.json").exists()
    assert (output_dir / "manifest.json").exists()

    rules = json.loads((output_dir / "rules.json").read_text())
    assert set(rules["trained_hazards"]) == {"hte", "prv"}
    assert rules["hazard_family"]["prv"] == "enablement_only"

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["training_row_count"] == 12
    assert manifest["training_hazard_counts"] == {"hte": 6, "prv": 6}
    assert manifest["code_version"]
    assert manifest["training_file_hash"]
    assert manifest["training_timestamp"]
    assert manifest["hyperparameters"]["other_hazard_weight"] == 0.25
    assert manifest["holdout_seed_prompt_ids"] == []

    # Round-trips through model.load() cleanly -- proves the artifact isn't
    # just present on disk, but actually loadable by the rest of the system.
    from hazard_classifier.model import load

    reloaded = load(output_dir)
    assert set(reloaded.trained_hazards) == {"hte", "prv"}


def test_hrc_train_holdout_seed_fraction_is_recorded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    output_dir = tmp_path / "model"

    main(
        [
            "--input",
            str(_SAMPLE_INPUT),
            "--output-dir",
            str(output_dir),
            "--holdout-seed-fraction",
            "0.5",
        ]
    )

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert len(manifest["holdout_seed_prompt_ids"]) > 0
    assert manifest["hyperparameters"]["holdout_seed_fraction"] == 0.5


def test_hrc_train_fatal_on_schema_error(tmp_path, monkeypatch, capsys) -> None:
    """A CSV missing a required column (schema.py's `SchemaError`) must exit
    cleanly with a stderr message, not a raw traceback -- `_common.fatal`'s
    whole purpose.
    """
    monkeypatch.setattr(embed, "embed_sentences", _fake_embed_sentences)
    bad_input = tmp_path / "missing_hazard_column.csv"
    bad_input.write_text(
        "seed_prompt_id,prompt_uid,prompt_text,response_text,enablement_value,"
        "legitimization_value,is_safe_ground_truth\n"
        "sp0,pu0,prompt,response,0,0,safe\n"
    )

    with pytest.raises(SystemExit) as exc_info:
        main(["--input", str(bad_input), "--output-dir", str(tmp_path / "model")])

    assert exc_info.value.code == 1
    # A clean, single message on stderr -- not a raw traceback.
    assert "hrc-train" in capsys.readouterr().err
