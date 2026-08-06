#!/usr/bin/env python3
"""Fit Release 1.1's L and E models and write the 1.1 evaluator artifact
(`docs/planning/PR5_EXECUTION_PLAN.md` §5, §6).

This is the one command that produces the shipped model. It fits
[D-68](../docs/planning/DECISIONS.md#d-68)'s structure on
[D-72](../docs/planning/DECISIONS.md#d-72)'s pipeline working text over
[D-73](../docs/planning/DECISIONS.md#d-73)'s fit half, and writes the
artifact `ARCHITECTURE.md` §10 and `PREREGISTRATION_LE_STRUCTURE.md` §6
specify.

**Nothing this produces is evaluated.** Both models are reported *not
evaluated* (`SCIENCE.md` §Legitimization Scoring, §Enablement Scoring) --
approved per-outcome criteria do not exist, the labels are out-of-version
([D-63](../docs/planning/DECISIONS.md#d-63)), coverage is attacked-prompt
only ([D-65](../docs/planning/DECISIONS.md#d-65)), and D-68 is a **null
result**: no candidate beat the incumbent, and on Legitimization the selected
structure scored below it. Building it is not evidence it is good. The
manifest says so in its own `not_evaluated` field, so a consumer that never
reads this docstring still meets the statement.

Costs one real BGE pass over the fit split (~2.5 minutes on CPU for 635
rows). Needs the model already cached locally (`--allow-download` once,
otherwise offline per D-6).

Run:  python scripts/build_release_artifact.py
      python scripts/build_release_artifact.py --output-dir artifacts/le_v2
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hazard_classifier.config import (  # noqa: E402
    ENABLEMENT_ONLY_HAZARDS,
    SPECIALIZED_ADVICE_HAZARDS,
)
from hazard_classifier.evaluator.artifact import write_artifact  # noqa: E402
from hazard_classifier.evaluator.components.integration import RuleSet  # noqa: E402
from hazard_classifier.evaluator.training.release import fit_release_models  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
# `artifacts/` is gitignored -- a fitted artifact is a build output, and
# whether one ships is PR 6's promotion decision (D-58), not this script's.
DEFAULT_OUT = REPO / "artifacts" / "release_1_1_le"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--artifact-id", default="release-1.1-le")
    parser.add_argument("--artifact-version", default="1")
    parser.add_argument(
        "--split",
        default="train",
        choices=("train", "eval"),
        help="D-73: the shipped artifact is the fit half ('train'). 'eval' is a "
        "diagnostic refit and is recorded as such in the manifest.",
    )
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="allow downloading the BGE model if not already cached (do this once)",
    )
    args = parser.parse_args()

    print(f"fitting on the {args.split!r} split (one BGE pass, a few minutes) ...")
    models = fit_release_models(split=args.split, allow_download=args.allow_download)

    write_artifact(
        args.output_dir,
        models,
        artifact_id=args.artifact_id,
        artifact_version=args.artifact_version,
        # The frozen rule constants and the rule version come from the
        # `RuleSet` itself, never a literal typed here that could drift from
        # it -- the same discipline `evaluator/profile.py` applies.
        rules=RuleSet(
            enablement_only_hazards=frozenset(ENABLEMENT_ONLY_HAZARDS),
            specialized_advice_hazards=frozenset(SPECIALIZED_ADVICE_HAZARDS),
        ),
    )

    provenance = models.provenance
    print()
    print(f"wrote {args.output_dir}")
    print(
        f"  split         {provenance.split_half} ({provenance.split_role}), "
        f"{provenance.split_version}"
    )
    print(f"  text view     {provenance.text_view}")
    print(f"  feature rows  {provenance.n_feature_rows} "
          f"(excluded as exhausted: {len(provenance.exhausted_excluded)})")
    for name, model in (("L", models.legitimization), ("E", models.enablement)):
        print(
            f"  {name}: {model.n_fit_rows} rows, {len(model.cells)} fitted cells, "
            f"unavailable {sorted(model.unavailable_hazards) or 'none'}"
        )
    print()
    print("Both models are NOT EVALUATED (SCIENCE.md §Legitimization/Enablement Scoring);")
    print("D-68's selection is a null result. Building it is not evidence it is good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
