"""`hrc-evaluate` (`PLAN.md` §5): measure a trained artifact against a
labeled CSV -- no retraining.

Thin wrapper around already-built, already-tested logic: `model.load`
(artifact) -> `schema.load_csv` (validation) ->
`embed.build_component_features` (preprocess/embed/pool, D-35) ->
`model.evaluate_rows` -> `metrics.flatten_metrics_report`/`render_summary`
(D-35) for the file outputs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from hazard_classifier.embed import build_component_features
from hazard_classifier.metrics import flatten_metrics_report, render_summary
from hazard_classifier.model import BlankGroundTruthError, evaluate_rows, load
from hazard_classifier.schema import SchemaError, load_csv

from ._common import add_allow_download_flag, fatal, warn_if_skipped_components


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hrc-evaluate",
        description="Measure a trained HazardResponseClassifier artifact against a labeled CSV (PLAN.md §5).",
    )
    parser.add_argument("--model-dir", required=True, type=Path, help="Artifact directory hrc-train wrote.")
    parser.add_argument("--input", required=True, type=Path, help="Labeled evaluation CSV (schema.py's evaluate-mode columns).")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory to write metrics.json/metrics.csv/summary.txt to.")
    add_allow_download_flag(parser)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    try:
        classifier = load(args.model_dir)
    except FileNotFoundError as exc:
        fatal(f"hrc-evaluate: could not load artifact from {args.model_dir}: {exc}")
    warn_if_skipped_components(classifier)

    try:
        df = load_csv(args.input, mode="evaluate")
    except SchemaError as exc:
        fatal(f"hrc-evaluate: {exc}")

    print(f"Loaded {len(df)} rows from {args.input}")
    print(f"Preprocessing and embedding responses (model={classifier.embedding_model_name})...")
    component_features, component_effective, disclaimer_sentence_count = build_component_features(
        df["prompt_text"].tolist(),
        df["response_text"].tolist(),
        model_name=classifier.embedding_model_name,
        revision=classifier.embedding_model_revision,
        allow_download=args.allow_download,
    )

    try:
        report = evaluate_rows(df, component_features, component_effective, disclaimer_sentence_count, classifier)
    except BlankGroundTruthError as exc:
        fatal(f"hrc-evaluate: {exc}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    pd.DataFrame(flatten_metrics_report(report)).to_csv(args.output_dir / "metrics.csv", index=False)
    summary = render_summary(report)
    (args.output_dir / "summary.txt").write_text(summary)

    print()
    print(summary, end="")
    print(f"Wrote metrics.json, metrics.csv, and summary.txt to {args.output_dir}")


if __name__ == "__main__":
    main()
