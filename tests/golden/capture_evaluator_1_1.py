"""Capture the golden Release 1.1 evaluator artifact
(`docs/planning/PR5_EXECUTION_PLAN.md` §6).

**This is a script, not a test.** Run it by hand to (re)capture
`tests/golden/evaluator_1_1/artifact`. It exists so tests have a 1.1 artifact
to *load and score with* without fitting one, which is what makes PR 5's
"fitting and scoring are independently testable" exit criterion reachable:
slice C's component tests get a loaded artifact and never fit, and slice A's
fitter tests fit and never load.

**The artifact this writes is a fixture, and says so.** It is fitted on
`examples/sample_input.csv` -- twelve synthetic rows over two hazards, the
same fixture the baseline golden artifact uses -- so its coefficients carry
no scientific meaning whatsoever and its `artifact_id` names it a fixture.
Nothing about it should ever be read as a model of anything. The real
Release 1.1 fit is `evaluator.training.release.fit_release_models`, over the
frozen interim split.

It is **768-dimensional and fitted with the real, non-mocked BGE encoder**,
deliberately: a stub-embedded fixture could not be scored by a test that uses
the real encoder, which is the test slice C most needs. Needs network on
first run only (the model is cached afterward, `DECISIONS.md` D-6).

Determinism: the estimator is seeded (`config.DEFAULT_SEED`) and D-6 pins
CPU-only, so a rerun against unmodified code reproduces every fitted
parameter exactly. Before committing a fresh capture, run it twice into
separate directories and diff -- excluding `manifest.json`'s `created_at`,
the one genuinely time-varying field, and comparing `.npz` by array rather
than by file bytes (`.npz` is a zip and embeds per-entry timestamps even when
the arrays inside are identical).

Run:  python tests/golden/capture_evaluator_1_1.py
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pandas as pd

from hazard_classifier.config import ENABLEMENT_ONLY_HAZARDS, SPECIALIZED_ADVICE_HAZARDS
from hazard_classifier.evaluator.artifact import write_artifact
from hazard_classifier.evaluator.components.integration import RuleSet
from hazard_classifier.evaluator.training.features import build_pipeline_features
from hazard_classifier.evaluator.training.provenance import FitProvenance
from hazard_classifier.evaluator.training.release import fit_models_from_features

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_INPUT = REPO_ROOT / "examples" / "sample_input.csv"

GOLDEN_DIR = Path(__file__).resolve().parent / "evaluator_1_1"
ARTIFACT_DIR = GOLDEN_DIR / "artifact"

ARTIFACT_ID = "golden-1.1-fixture"
ARTIFACT_VERSION = "0.0.1-fixture"


def capture(output_dir: Path = ARTIFACT_DIR) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)

    frame = pd.read_csv(SAMPLE_INPUT)
    features = build_pipeline_features(frame)

    provenance = FitProvenance(
        source_path=SAMPLE_INPUT.name,
        source_sha256=hashlib.sha256(SAMPLE_INPUT.read_bytes()).hexdigest(),
        # A fixture has no split: it is not a sample of anything, so there is
        # nothing held out from it. Saying "none"/"fixture" here is what stops
        # a reader from mistaking it for a fit that had a dev slice.
        split_path="none",
        split_version="none",
        split_half="all",
        split_role="fixture",
        text_view=features.text_view,
        embedding_provider=features.provider_name,
        embedding_provider_version=features.provider_version,
        embedding_model_name=features.provider_model_name,
        embedding_model_revision=features.provider_model_revision,
        pooling=features.pooling_name,
        seed=_seed(),
        estimator=_estimator(),
        components=features.components,
        n_feature_rows=len(features.prompt_uids),
        exhausted_excluded=tuple(
            (row.prompt_uid, row.hazard, row.exhausted_at) for row in features.exhausted_rows
        ),
    )

    models = fit_models_from_features(frame, features, provenance)

    return write_artifact(
        output_dir,
        models,
        artifact_id=ARTIFACT_ID,
        artifact_version=ARTIFACT_VERSION,
        rules=RuleSet(
            enablement_only_hazards=frozenset(ENABLEMENT_ONLY_HAZARDS),
            specialized_advice_hazards=frozenset(SPECIALIZED_ADVICE_HAZARDS),
        ),
    )


def _seed() -> int:
    from hazard_classifier.config import DEFAULT_SEED

    return DEFAULT_SEED


def _estimator() -> dict:
    from hazard_classifier.evaluator.training.multinomial import ESTIMATOR_PARAMS

    return dict(ESTIMATOR_PARAMS)


if __name__ == "__main__":
    path = capture()
    print(f"wrote {path.relative_to(REPO_ROOT)}")
