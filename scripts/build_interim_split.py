#!/usr/bin/env python3
"""Build Release 1.1's frozen, versioned interim train/evaluation split.

Context (`docs/planning/DECISIONS.md` D-63 through D-66). The Standards team's
fixed dataset is not arriving. Release 1.1 instead uses the **Jailbreak v1.0
human ground truth** already in this repository as an out-of-version interim
dataset, so the pipeline can be built and exercised end to end and re-run when
real data appears.

What this script does and does not do:

- It does **not** synthesize labels. Every `legitimization_value` and
  `enablement_value` is a human judgment already present in the source CSV.
  The only thing constructed here is the *split*.
- It groups on **normalized prompt text**, not `seed_prompt_id` (D-64). The
  source has 30 seed prompts and each maps to exactly one hazard, so a
  seed-grouped holdout must place an entire hazard on one side. Grouping on
  prompt text gives 180 groups, 11 per hazard, and keeps every hazard and
  every L/E class on both sides.
- It is deterministic: groups are sorted before selection and the RNG is
  seeded, so the same source file always produces the same split.

Run:  python scripts/build_interim_split.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hazard_classifier.interim_data import prompt_group_id  # noqa: E402
from hazard_classifier.schema import normalize_hazard  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    REPO / "data" / "jb_1.0_1003_ground_truth_items_for_riki_eval__with_seed_prompt_id.csv"
)
DEFAULT_OUT = REPO / "data" / "interim_split_v1.json"

# Frozen. Changing either changes the split and therefore the split version.
SPLIT_SEED = 20260804
EVAL_FRACTION = 0.25
SPLIT_VERSION = "interim-v1"


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_split(source: pathlib.Path) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(source)
    frame["hazard"] = frame["hazard"].map(normalize_hazard)
    # Single implementation shared with every consumer -- hazard_classifier.interim_data.
    frame["prompt_group_id"] = frame["prompt_text"].map(prompt_group_id)

    rng = np.random.default_rng(SPLIT_SEED)
    eval_groups: set[str] = set()

    # Stratified by hazard so every hazard appears on both sides. Groups are
    # sorted before permutation -- pandas group order is not a contract.
    for hazard in sorted(frame["hazard"].unique()):
        groups = sorted(frame.loc[frame["hazard"] == hazard, "prompt_group_id"].unique())
        take = max(1, round(EVAL_FRACTION * len(groups)))
        eval_groups.update(rng.permutation(groups)[:take].tolist())

    frame["split"] = np.where(frame["prompt_group_id"].isin(eval_groups), "eval", "train")

    manifest = {
        "split_version": SPLIT_VERSION,
        "source_file": source.name,
        "source_sha256": _sha256_file(source),
        "source_rows": int(len(frame)),
        "split_seed": SPLIT_SEED,
        "eval_fraction": EVAL_FRACTION,
        "group_key": "sha256(whitespace-normalized prompt_text)[:16]",
        "group_count": int(frame["prompt_group_id"].nunique()),
        "eval_group_count": len(eval_groups),
        "eval_group_ids": sorted(eval_groups),
        "rows": {
            "train": int((frame["split"] == "train").sum()),
            "eval": int((frame["split"] == "eval").sum()),
        },
    }
    return frame, manifest


def verify(frame: pd.DataFrame) -> list[str]:
    """Properties the split must have. Returned as a list of failures so the
    caller reports all of them rather than the first.
    """
    failures = []
    train, evalset = frame[frame.split == "train"], frame[frame.split == "eval"]

    overlap = set(train.prompt_group_id) & set(evalset.prompt_group_id)
    if overlap:
        failures.append(f"prompt-group overlap between train and eval: {len(overlap)} groups")

    all_hazards = set(frame.hazard.unique())
    for name, part in (("train", train), ("eval", evalset)):
        missing = all_hazards - set(part.hazard.unique())
        if missing:
            failures.append(f"{name} is missing hazards: {sorted(missing)}")

    for column, label in (("legitimization_value", "L"), ("enablement_value", "E")):
        present = set(evalset[column].dropna().astype(int).unique())
        missing = {0, 1, 2} - present
        if missing:
            failures.append(f"eval is missing {label} classes: {sorted(missing)}")

    return failures


def summarize(frame: pd.DataFrame) -> str:
    evalset = frame[frame.split == "eval"]
    lines = [
        f"rows        train={int((frame.split=='train').sum()):4d}  eval={len(evalset):4d}",
        f"groups      total={frame.prompt_group_id.nunique():4d}  "
        f"eval={evalset.prompt_group_id.nunique():4d}",
        "",
        "eval L classes  " + "  ".join(
            f"L{k}={int(v)}" for k, v in evalset.legitimization_value.value_counts().sort_index().items()
        ),
        "eval E classes  " + "  ".join(
            f"E{k}={int(v)}" for k, v in evalset.enablement_value.value_counts().sort_index().items()
        ),
        "",
        "eval rows per hazard:",
    ]
    counts = evalset.hazard.value_counts().sort_index()
    lines += [f"  {h:<10} {int(n)}" for h, n in counts.items()]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild and compare against the existing manifest instead of writing",
    )
    args = parser.parse_args()

    frame, manifest = build_split(args.source)

    failures = verify(frame)
    if failures:
        print("SPLIT VERIFICATION FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    if args.check:
        existing = json.loads(args.out.read_text())
        if existing != manifest:
            print("MANIFEST DRIFT: rebuilt split does not match the frozen one", file=sys.stderr)
            return 1
        print("split reproduces the frozen manifest exactly")
        return 0

    args.out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {args.out.relative_to(REPO)}\n")
    print(summarize(frame))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
