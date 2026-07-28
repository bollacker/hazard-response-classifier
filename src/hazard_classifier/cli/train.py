"""`hrc-train` (`PLAN.md` §3): labeled CSV -> deployable model artifact.

Thin wrapper around already-built, already-tested logic:
`schema.load_csv` (validation) -> `embed.build_legacy_component_features`
(preprocess/embed/pool, D-35) -> `model.fit` -> `model.save`.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from pathlib import Path

from hazard_classifier import config
from hazard_classifier.embed import build_legacy_component_features
from hazard_classifier.model import WhollySkippedEnablementError, fit, save
from hazard_classifier.schema import SchemaError, load_csv

from ._common import add_allow_download_flag, fatal, warn_if_skipped_components


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hrc-train",
        description="Train a HazardResponseClassifier artifact from a labeled CSV (PLAN.md §3).",
    )
    parser.add_argument("--input", required=True, type=Path, help="Labeled training CSV (schema.py's train-mode columns).")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory to write the trained artifact to.")
    parser.add_argument(
        "--other-hazard-weight",
        type=float,
        default=0.25,
        help="Sample weight for non-target-hazard rows in each cell's fit (default: %(default)s).",
    )
    parser.add_argument(
        "--model-name",
        default=config.DEFAULT_EMBEDDING_MODEL_NAME,
        help="BGE model id to embed responses with (default: %(default)s).",
    )
    parser.add_argument(
        "--holdout-seed-fraction",
        type=float,
        default=0.0,
        help="Fraction of seed_prompt_id groups to reserve for hrc-evaluate's held-out "
        "measurement (default: %(default)s -- no holdout reserved, DECISIONS.md D-1).",
    )
    add_allow_download_flag(parser)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    try:
        df = load_csv(args.input, mode="train")
    except SchemaError as exc:
        fatal(f"hrc-train: {exc}")

    training_file_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
    training_hazard_counts = {str(k): int(v) for k, v in df["hazard"].value_counts().items()}

    print(f"Loaded {len(df)} rows, {df['hazard'].nunique()} hazards, from {args.input}")
    print(f"Preprocessing and embedding responses (model={args.model_name})...")
    component_features, component_effective, _ = build_legacy_component_features(
        df["prompt_text"].tolist(),
        df["response_text"].tolist(),
        df["hazard"].tolist(),
        model_name=args.model_name,
        allow_download=args.allow_download,
    )

    try:
        classifier = fit(
            df,
            component_features,
            component_effective,
            frozenset(config.ENABLEMENT_ONLY_HAZARDS),
            other_hazard_weight=args.other_hazard_weight,
            holdout_seed_fraction=args.holdout_seed_fraction,
            specialized_advice_hazards=frozenset(config.SPECIALIZED_ADVICE_HAZARDS),
            embedding_model_name=args.model_name,
        )
    except WhollySkippedEnablementError as exc:
        fatal(f"hrc-train: {exc}")

    save(
        classifier,
        args.output_dir,
        code_version=package_version("hazard-response-classifier"),
        hyperparameters={
            "other_hazard_weight": args.other_hazard_weight,
            "holdout_seed_fraction": args.holdout_seed_fraction,
            "model_name": args.model_name,
        },
        training_timestamp=datetime.now(timezone.utc).isoformat(),
        training_file_hash=training_file_hash,
        training_row_count=len(df),
        training_hazard_counts=training_hazard_counts,
    )

    print(f"Trained {len(classifier.trained_hazards)} hazards: {sorted(classifier.trained_hazards)}")
    if classifier.holdout_seed_prompt_ids:
        print(f"Reserved {len(classifier.holdout_seed_prompt_ids)} seed_prompt_id group(s) for holdout.")
    warn_if_skipped_components(classifier)
    print(f"Wrote artifact to {args.output_dir}")


if __name__ == "__main__":
    main()
