"""`hrc-predict` (`PLAN.md` §6): score brand-new responses -- no labels, no
retraining.

Thin wrapper around already-built, already-tested logic: `model.load`
(artifact) -> `schema.load_csv` (validation) ->
`embed.build_component_features` (preprocess/embed/pool, D-35) ->
`model.predict_rows` -> `model.to_predictions_frame`/`to_failures_frame`.
Uses `predict_rows`, not `HazardResponseClassifier.score`, so this CLI's
feature-building step is identical to `hrc-train`'s/`hrc-evaluate`'s
(D-35) -- one shared pipeline, not a fourth copy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from hazard_classifier.embed import build_component_features
from hazard_classifier.model import predict_rows, load, to_failures_frame, to_predictions_frame
from hazard_classifier.schema import SchemaError, load_csv

from ._common import add_allow_download_flag, fatal, warn_if_skipped_components


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hrc-predict",
        description="Score new responses with a trained HazardResponseClassifier artifact (PLAN.md §6).",
    )
    parser.add_argument("--model-dir", required=True, type=Path, help="Artifact directory hrc-train wrote.")
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="CSV to score (schema.py's predict-mode columns; ground-truth columns optional/ignored, D-24).",
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path, help="Directory to write predictions.csv/failures.csv to."
    )
    add_allow_download_flag(parser)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    try:
        classifier = load(args.model_dir)
    except FileNotFoundError as exc:
        fatal(f"hrc-predict: could not load artifact from {args.model_dir}: {exc}")
    warn_if_skipped_components(classifier)

    try:
        df = load_csv(args.input, mode="predict")
    except SchemaError as exc:
        fatal(f"hrc-predict: {exc}")

    print(f"Loaded {len(df)} rows from {args.input}")
    print(f"Preprocessing and embedding responses (model={classifier.embedding_model_name})...")
    component_features, component_effective, disclaimer_sentence_count = build_component_features(
        df["prompt_text"].tolist(),
        df["response_text"].tolist(),
        model_name=classifier.embedding_model_name,
        revision=classifier.embedding_model_revision,
        allow_download=args.allow_download,
    )

    predictions, failures = predict_rows(
        df, component_features, component_effective, disclaimer_sentence_count, classifier
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    to_predictions_frame(predictions).to_csv(args.output_dir / "predictions.csv", index=False)
    to_failures_frame(failures).to_csv(args.output_dir / "failures.csv", index=False)

    print(f"{len(predictions)} scored, {len(failures)} failed (of {len(df)} total rows)")
    print(f"Wrote predictions.csv and failures.csv to {args.output_dir}")


if __name__ == "__main__":
    main()
