"""Slice 0's headline exit criterion (`docs/planning/PR1_EXECUTION_PLAN.md`):
"the same inputs produce unchanged current text, features, scores,
probabilities, labels, and failures."

This reruns the exact `hrc-train` -> `hrc-evaluate` -> `hrc-predict` pipeline
`tests/golden/capture_baseline.py` used and asserts the result against the
committed goldens under `tests/golden/baseline/`. It must pass on unmodified
code today, and it must fail if any fitted parameter is perturbed by hand --
proven once, deliberately, in `test_a_perturbed_head_fails_parity` (named to
sort first only for readability when running verbosely; tests are otherwise
independent).

Needs network on first run only (BGE model download, cached after,
`DECISIONS.md` D-6) -- lives in `tests/integration/`, not `tests/unit/`, per
`PLAN.md` §8.1's "unit tests need no model download" rule.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from hazard_classifier.cli import evaluate, predict, train

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "golden" / "baseline"
SAMPLE_INPUT = Path(__file__).resolve().parents[2] / "examples" / "sample_input.csv"

# The one genuinely time-varying field (`cli/train.py` stamps it with
# `datetime.now(timezone.utc)`); every other manifest field is deterministic
# given the same input and code (DECISIONS.md D-6). Excluded from comparison
# here rather than worked around by making the test tolerant of other drift.
_MANIFEST_VOLATILE_FIELDS = {"training_timestamp"}


def _run_pipeline(output_dir: Path) -> None:
    artifact_dir = output_dir / "artifact"
    eval_dir = output_dir / "eval"
    predict_dir = output_dir / "predict"

    train.main(["--input", str(SAMPLE_INPUT), "--output-dir", str(artifact_dir)])
    evaluate.main(
        [
            "--model-dir", str(artifact_dir),
            "--input", str(SAMPLE_INPUT),
            "--output-dir", str(eval_dir),
        ]
    )
    predict.main(
        [
            "--model-dir", str(artifact_dir),
            "--input", str(SAMPLE_INPUT),
            "--output-dir", str(predict_dir),
        ]
    )


@pytest.fixture(scope="module")
def rerun_dir(tmp_path_factory) -> Path:
    output_dir = tmp_path_factory.mktemp("baseline_parity")
    _run_pipeline(output_dir)
    return output_dir


def test_thresholds_json_matches_golden(rerun_dir: Path) -> None:
    golden = json.loads((GOLDEN_DIR / "artifact" / "thresholds.json").read_text())
    rerun = json.loads((rerun_dir / "artifact" / "thresholds.json").read_text())
    assert rerun == golden


def test_rules_json_matches_golden(rerun_dir: Path) -> None:
    golden = json.loads((GOLDEN_DIR / "artifact" / "rules.json").read_text())
    rerun = json.loads((rerun_dir / "artifact" / "rules.json").read_text())
    assert rerun == golden


def test_manifest_json_matches_golden_modulo_timestamp(rerun_dir: Path) -> None:
    golden = json.loads((GOLDEN_DIR / "artifact" / "manifest.json").read_text())
    rerun = json.loads((rerun_dir / "artifact" / "manifest.json").read_text())
    for field in _MANIFEST_VOLATILE_FIELDS:
        golden.pop(field, None)
        rerun.pop(field, None)
    assert rerun == golden


def test_heads_npz_arrays_match_golden(rerun_dir: Path) -> None:
    # `.npz` is a zip and embeds per-entry timestamps even when the arrays
    # inside are identical (PR1_EXECUTION_PLAN.md's trap note) -- compare
    # the loaded arrays, never the file bytes.
    golden = np.load(GOLDEN_DIR / "artifact" / "heads.npz")
    rerun = np.load(rerun_dir / "artifact" / "heads.npz")
    assert set(rerun.files) == set(golden.files)
    for key in golden.files:
        np.testing.assert_array_equal(rerun[key], golden[key], err_msg=f"heads.npz key {key!r} differs")


@pytest.mark.parametrize("filename", ["metrics.json", "metrics.csv", "summary.txt"])
def test_eval_outputs_match_golden(rerun_dir: Path, filename: str) -> None:
    golden = (GOLDEN_DIR / "eval" / filename).read_text()
    rerun = (rerun_dir / "eval" / filename).read_text()
    assert rerun == golden


@pytest.mark.parametrize("filename", ["predictions.csv", "failures.csv"])
def test_predict_outputs_match_golden(rerun_dir: Path, filename: str) -> None:
    golden = (GOLDEN_DIR / "predict" / filename).read_text()
    rerun = (rerun_dir / "predict" / filename).read_text()
    assert rerun == golden


def test_a_perturbed_head_fails_parity(rerun_dir: Path) -> None:
    """Slice 0's exit criterion requires this parity check to actually be a
    forcing function, not a vacuous pass -- proven once, directly: hand-flip
    one float in a rerun artifact's `heads.npz` and confirm the array
    comparison this module relies on (same logic as
    `test_heads_npz_arrays_match_golden`) rejects it.
    """
    rerun = np.load(rerun_dir / "artifact" / "heads.npz")
    key = next(iter(rerun.files))
    perturbed = dict(rerun.items())
    perturbed[key] = perturbed[key] + 1.0

    golden = np.load(GOLDEN_DIR / "artifact" / "heads.npz")
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(perturbed[key], golden[key])
