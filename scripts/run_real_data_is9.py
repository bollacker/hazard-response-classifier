"""IS-9 real-data run against a non-toy labeled dataset (`VERIFICATION.md` IS-9).

**This is not the toy-parity confirmation IS-9 was originally scoped as.**
The original claim -- frozen-fit metrics match `security-evaluator`'s
published reference numbers (`PLAN.md` SS8.2) -- needs the toy's own raw
CSVs (`neyman_review_queue.csv`, `batch_*_key.csv`), which are excluded from
that repo and are not this file. This script instead runs the full, real
pipeline (`preprocess/*` -> `embed.py` -> `fit` -> `evaluate_rows`) against a
genuinely different real labeled dataset, to get a real held-out generalization
read -- a materially different but still valuable confirmation that the
implementation works end-to-end on real data, not synthetic fixtures.

Input CSV must have: prompt_uid, hazard, prompt_text, response_text,
enablement_value, legitimization_value, is_safe_ground_truth. `seed_prompt_id`
is derived here from `seed_prompt_text` (identical text -> identical
synthetic id) if the input doesn't already have `seed_prompt_id` -- every
seed_prompt_text in the source dataset this was built for maps to exactly one
hazard, confirmed by direct inspection, so this grouping is a faithful stand-in
for D-1's holdout unit.

Usage:
    python scripts/run_real_data_is9.py <path-to-csv> [--holdout-fraction 0.2]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hazard_classifier import config, schema
from hazard_classifier.embed import embed_sentences, enablement_keep_mask, pool_response_vector
from hazard_classifier.model import evaluate_rows, fit
from hazard_classifier.preprocess import decode, segment
from hazard_classifier.preprocess.flags import (
    disclaimer_label,
    later_authored_continuation,
    prompt_repetition_features,
)


def _derive_seed_prompt_id(df: pd.DataFrame) -> pd.Series:
    if "seed_prompt_id" in df.columns:
        return df["seed_prompt_id"].astype(str)
    if "seed_prompt_text" not in df.columns:
        raise SystemExit("Input has neither seed_prompt_id nor seed_prompt_text; cannot derive groups.")
    unique_texts = sorted(df["seed_prompt_text"].unique())
    text_to_id = {text: f"seed_{i:03d}" for i, text in enumerate(unique_texts)}
    mixed = df.groupby("seed_prompt_text")["hazard"].nunique()
    if (mixed > 1).any():
        bad = mixed[mixed > 1].index.tolist()
        raise SystemExit(f"seed_prompt_text groups spanning >1 hazard, cannot derive ids safely: {bad}")
    return df["seed_prompt_text"].map(text_to_id)


def _preprocess_row(prompt_text: str, response_text: str):
    context = "\n\n".join([prompt_text, response_text])
    prompt_readable = str(decode.best_readable_view(prompt_text, prompt_text)["review_text"])
    response_readable = str(decode.best_readable_view(response_text, context)["review_text"])
    segments = segment.segment_text(response_readable, max_chars=420, stride=210)

    texts, is_repeat, has_later = [], [], []
    disclaimer_count = 0
    for piece in segments:
        repetition = prompt_repetition_features(piece.text, prompt_readable, piece.start, piece.end)
        is_prompt_repetition = float(repetition["prompt_repetition_probability"]) >= 0.5
        has_later_authored = is_prompt_repetition and later_authored_continuation(piece.text, prompt_readable)
        texts.append(piece.text)
        is_repeat.append(is_prompt_repetition)
        has_later.append(has_later_authored)
        has_disclaimer, _ = disclaimer_label(piece.text)
        if has_disclaimer:
            disclaimer_count += 1
    return texts, is_repeat, has_later, disclaimer_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--holdout-fraction", type=float, default=0.2)
    parser.add_argument("--allow-download", action="store_true", default=True)
    parser.add_argument("--out", type=Path, default=Path("scripts/is9_real_data_metrics.json"))
    args = parser.parse_args()

    raw = pd.read_csv(args.csv_path, dtype=str, keep_default_na=False)
    raw["seed_prompt_id"] = _derive_seed_prompt_id(raw)

    tmp_path = args.csv_path.with_name(args.csv_path.stem + "__with_seed_prompt_id.csv")
    raw.to_csv(tmp_path, index=False)
    print(f"Wrote derived CSV (added seed_prompt_id) to {tmp_path}")

    df = schema.load_csv(tmp_path, mode="train")
    print(f"Loaded and schema-validated {len(df)} rows, {df['seed_prompt_id'].nunique()} seed groups, "
          f"{df['hazard'].nunique()} hazards.")

    n = len(df)
    all_segment_texts: list[str] = []
    row_segment_ranges: list[tuple[int, int]] = []
    row_is_repeat: list[list[bool]] = []
    row_has_later: list[list[bool]] = []
    row_disclaimer_count = np.zeros(n, dtype=np.int64)

    for i, (prompt_text, response_text) in enumerate(zip(df["prompt_text"], df["response_text"])):
        texts, is_repeat, has_later, disclaimer_count = _preprocess_row(prompt_text, response_text)
        start = len(all_segment_texts)
        all_segment_texts.extend(texts)
        row_segment_ranges.append((start, len(all_segment_texts)))
        row_is_repeat.append(is_repeat)
        row_has_later.append(has_later)
        row_disclaimer_count[i] = disclaimer_count
        if (i + 1) % 100 == 0:
            print(f"  preprocessed {i + 1}/{n} rows ({len(all_segment_texts)} segments so far)")

    print(f"Embedding {len(all_segment_texts)} segments in one batched BGE call "
          f"(first run downloads the model, ~0.4GB)...")
    all_embeddings = embed_sentences(all_segment_texts, allow_download=args.allow_download)
    print(f"Embeddings shape: {all_embeddings.shape}")

    enablement_features = np.zeros((n, 768), dtype=np.float32)
    legitimization_features = np.zeros((n, 768), dtype=np.float32)
    enablement_effective = np.zeros(n, dtype=bool)
    legitimization_effective = np.zeros(n, dtype=bool)

    for i, (start, end) in enumerate(row_segment_ranges):
        row_embeddings = all_embeddings[start:end]
        is_repeat = np.array(row_is_repeat[i], dtype=bool)
        has_later = np.array(row_has_later[i], dtype=bool)

        keep_all = np.ones(len(row_embeddings), dtype=bool)
        legit_vec, legit_eff = pool_response_vector(row_embeddings, keep_all)
        legitimization_features[i] = legit_vec
        legitimization_effective[i] = legit_eff

        keep_enablement = enablement_keep_mask(is_repeat, has_later) if len(row_embeddings) else keep_all
        enable_vec, enable_eff = pool_response_vector(row_embeddings, keep_enablement)
        enablement_features[i] = enable_vec
        enablement_effective[i] = enable_eff

    print(f"Enablement effective: {enablement_effective.sum()}/{n}; "
          f"Legitimization effective: {legitimization_effective.sum()}/{n}")

    component_features = {"enablement": enablement_features, "legitimization": legitimization_features}
    component_effective = {"enablement": enablement_effective, "legitimization": legitimization_effective}

    classifier = fit(
        df,
        component_features,
        component_effective,
        frozenset(config.ENABLEMENT_ONLY_HAZARDS),
        holdout_seed_fraction=args.holdout_fraction,
        seed=config.DEFAULT_SEED,
        specialized_advice_hazards=frozenset(config.SPECIALIZED_ADVICE_HAZARDS),
    )
    print(f"Fit complete. Trained hazards: {sorted(classifier.trained_hazards)}")
    print(f"Held-out seed groups: {len(classifier.holdout_seed_prompt_ids)}/{df['seed_prompt_id'].nunique()}")
    print(f"Skipped components: {classifier.skipped_components}")

    report = evaluate_rows(df, component_features, component_effective, row_disclaimer_count, classifier)

    args.out.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(f"\nWrote metrics report to {args.out}\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
