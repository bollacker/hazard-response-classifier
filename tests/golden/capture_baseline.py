"""Slice 0 (`docs/planning/PR1_EXECUTION_PLAN.md`): capture today's baseline
outputs so PR 1's refactor has something concrete to prove parity against.

**This is a script, not a test.** Run it by hand to (re)capture
`tests/golden/baseline/`; `tests/integration/test_baseline_parity.py` is the
test that reruns the same pipeline and asserts byte/array-equality against
what this script wrote. Only rerun this script -- and recommit the result --
when a change is *deliberately* changing baseline output; running it to make
a failing parity test pass would defeat the point of slice 0.

Runs `hrc-train` -> `hrc-evaluate` -> `hrc-predict` (in-process, via each
CLI's own `main(argv)`, not a subprocess) against `examples/sample_input.csv`
and the real, non-mocked BGE model. Needs network on first run only (the
model is cached by `sentence-transformers` afterward, `DECISIONS.md` D-6).

Determinism: `heads.py`'s `LogisticRegression` uses `config.DEFAULT_SEED`,
and D-6 pins CPU-only, so a rerun against unmodified code and the same input
must reproduce every fitted parameter exactly. Before committing a fresh
capture, run this script twice into separate directories and diff (excluding
`manifest.json`'s `training_timestamp`, the one genuinely time-varying field,
and comparing `heads.npz` by array rather than by file bytes -- `.npz` is a
zip and embeds per-entry timestamps even when the arrays inside are
identical).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hazard_classifier.cli import evaluate, predict, train

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_INPUT = REPO_ROOT / "examples" / "sample_input.csv"

BASELINE_DIR = Path(__file__).resolve().parent / "baseline"
ARTIFACT_DIR = BASELINE_DIR / "artifact"
EVAL_DIR = BASELINE_DIR / "eval"
PREDICT_DIR = BASELINE_DIR / "predict"


def capture(output_dir: Path = BASELINE_DIR) -> None:
    """Run the full baseline pipeline, writing every output under
    `output_dir`. Defaults to the committed golden location; pass a scratch
    directory to capture into for a determinism diff without touching the
    committed goldens.
    """
    artifact_dir = output_dir / "artifact"
    eval_dir = output_dir / "eval"
    predict_dir = output_dir / "predict"

    if output_dir.exists():
        shutil.rmtree(output_dir)

    train.main(
        [
            "--input", str(SAMPLE_INPUT),
            "--output-dir", str(artifact_dir),
        ]
    )
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


if __name__ == "__main__":
    capture()
    print(f"Captured baseline outputs under {BASELINE_DIR}")
