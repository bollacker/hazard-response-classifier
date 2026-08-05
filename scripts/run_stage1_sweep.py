#!/usr/bin/env python3
"""Run queue item 2 slice B's stage-1 ablation sweep and write
`docs/planning/item2_results/stage1.json`.

Context (`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` §5,
`docs/planning/PREREGISTRATION_LE_STRUCTURE.md` §2.3-§2.4). From the
reference structure `R`, this varies one axis at a time across its ten
non-reference levels (corrected 2026-08-04, §2.4's amendment: `L1, L2, W2,
W3, S2, H1, H2, B1, P2, P3`) and evaluates each against the frozen dev split,
per target (L, E) independently. Every candidate is fit on the `train` split
and scored on the `eval` split -- never the reverse, and never on rows either
split shares.

**Every number this script writes is a dev-set number**
(`DECISIONS.md` D-66): not a benchmark result, not a generalization estimate,
not reportable under `SCIENCE.md` §Evidence and outputs.

Run:  python scripts/run_stage1_sweep.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hazard_classifier.experiments.candidates import (  # noqa: E402
    JOINT_BUILDERS,
    STAGE1_BUILDERS,
    TwoHeadReference,
)
from hazard_classifier.experiments.comparison_metrics import (  # noqa: E402
    WORST_CLASS_F1_FLOOR,
    Predictions,
    classification_metrics,
    paired_cluster_bootstrap,
)
from hazard_classifier.experiments.features import embed_responses  # noqa: E402
from hazard_classifier.interim_data import (  # noqa: E402
    INTERIM_SPLIT,
    legitimization_rows,
    load_interim,
)

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "docs" / "planning" / "item2_results" / "stage1.json"

TARGETS = ("L", "E")
POOLING_LEVELS_USED_STANDALONE = ("P2", "P3")  # P1 is R's own default, used by every other level

# Which pre-registration §2.3 axis each non-reference level belongs to --
# for the "best level identified per axis" exit criterion. Purely
# informational triage feeding slice C's composite; not the selection rule.
AXIS_OF_LEVEL = {
    "L1": "Loss",
    "L2": "Loss",
    "W2": "Weighting",
    "W3": "Weighting",
    "S2": "Sharing",
    "H1": "Hazard-conditioning",
    "H2": "Hazard-conditioning",
    "B1": "Branching",
    "P2": "Pooling",
    "P3": "Pooling",
}


def _target_frames() -> dict[str, dict[str, object]]:
    train = load_interim(split="train")
    dev = load_interim(split="eval")
    return {
        "L": {
            "fit": legitimization_rows(train),
            "dev": legitimization_rows(dev),
            "y_col": "legitimization_value",
        },
        "E": {
            "fit": train,
            "dev": dev,
            "y_col": "enablement_value",
        },
    }


def _features_for(rows: pd.DataFrame, pooled: np.ndarray, row_index: dict[str, int]) -> np.ndarray:
    return pooled[[row_index[u] for u in rows["prompt_uid"]]]


def _record(
    level: str,
    target: str,
    metrics,
    unavailable_hazards,
    bootstrap_vs_r=None,
    marginal_bootstrap=None,
    produces_three_class_distribution=None,
) -> dict:
    payload = {
        "level": level,
        "target": target,
        "axis": AXIS_OF_LEVEL.get(level),  # None for R itself
        # PREREGISTRATION_LE_STRUCTURE.md §4's closing rule: only a candidate
        # producing a genuine three-class distribution may be *selected*.
        # Recorded per result so slice C enforces it from data rather than
        # re-deriving which structures qualify.
        "produces_three_class_distribution": produces_three_class_distribution,
        "n_scored": metrics.n_scored,
        "n_total": metrics.n_total,
        "coverage": metrics.coverage,
        "accuracy": metrics.accuracy,
        "per_class_f1": list(metrics.per_class_f1),
        "macro_f1": metrics.macro_f1,
        "worst_class_f1": metrics.worst_class_f1,
        "disqualified_worst_class_floor": metrics.worst_class_f1 < WORST_CLASS_F1_FLOOR,
        "unavailable_hazards": sorted(unavailable_hazards),
    }
    if bootstrap_vs_r is not None:
        payload["bootstrap_vs_r"] = bootstrap_vs_r.as_dict()
    if marginal_bootstrap is not None:
        payload["marginal_bootstrap"] = marginal_bootstrap.as_dict()
    return payload


def run_sweep(*, allow_download: bool, n_resamples: int) -> dict:
    from hazard_classifier.experiments.comparison_metrics import cluster_bootstrap_interval

    full = load_interim()  # every row, both splits -- one embedding pass over all of it
    embeddings = embed_responses(full, allow_download=allow_download)
    row_index = {rid: i for i, rid in enumerate(embeddings.row_ids)}
    pooled = {level: embeddings.pooled(level) for level in ("P1", "P2", "P3")}

    frames = _target_frames()
    fit_X = {t: _features_for(frames[t]["fit"], pooled["P1"], row_index) for t in TARGETS}
    dev_X = {t: _features_for(frames[t]["dev"], pooled["P1"], row_index) for t in TARGETS}
    fit_y = {t: frames[t]["fit"][frames[t]["y_col"]].to_numpy(dtype=np.int64) for t in TARGETS}
    dev_y = {t: frames[t]["dev"][frames[t]["y_col"]].to_numpy(dtype=np.int64) for t in TARGETS}
    fit_hazards = {t: frames[t]["fit"]["hazard"].to_numpy() for t in TARGETS}
    dev_hazards = {t: frames[t]["dev"]["hazard"].to_numpy() for t in TARGETS}
    dev_groups = {t: frames[t]["dev"]["prompt_group_id"].to_numpy() for t in TARGETS}

    results: list[dict] = []
    r_predictions: dict[str, Predictions] = {}

    print("Fitting R (reference) ...")
    for target in TARGETS:
        r = TwoHeadReference()
        r.fit(fit_X[target], fit_y[target], fit_hazards[target])
        proba = r.predict_proba(dev_X[target], dev_hazards[target])
        predictions = Predictions.from_proba(proba)
        r_predictions[target] = predictions
        metrics = classification_metrics(dev_y[target], predictions)
        marginal = cluster_bootstrap_interval(
            dev_y[target], predictions, dev_groups[target], n_resamples=n_resamples
        )
        results.append(
            _record(
                "R", target, metrics, r.unavailable_hazards,
                marginal_bootstrap=marginal,
                produces_three_class_distribution=r.produces_three_class_distribution,
            )
        )
        print(f"  R  {target}: macro_f1={metrics.macro_f1:.4f} worst={metrics.worst_class_f1:.4f}")

    print("Fitting per-target stage-1 candidates ...")
    for target in TARGETS:
        for level, builder in STAGE1_BUILDERS.items():
            candidate = builder()
            candidate.fit(fit_X[target], fit_y[target], fit_hazards[target])
            proba = candidate.predict_proba(dev_X[target], dev_hazards[target])
            predictions = Predictions.from_proba(proba)
            metrics = classification_metrics(dev_y[target], predictions)
            diff = paired_cluster_bootstrap(
                dev_y[target], predictions, r_predictions[target], dev_groups[target],
                n_resamples=n_resamples,
            )
            results.append(
                _record(
                    level, target, metrics, candidate.unavailable_hazards, bootstrap_vs_r=diff,
                    produces_three_class_distribution=candidate.produces_three_class_distribution,
                )
            )
            print(
                f"  {level:3s} {target}: macro_f1={metrics.macro_f1:.4f} worst={metrics.worst_class_f1:.4f} "
                f"vs_R_excludes_zero={diff.excludes_zero}"
            )

        for level in POOLING_LEVELS_USED_STANDALONE:
            X_fit = _features_for(frames[target]["fit"], pooled[level], row_index)
            X_dev = _features_for(frames[target]["dev"], pooled[level], row_index)
            candidate = TwoHeadReference()
            candidate.name = level
            candidate.fit(X_fit, fit_y[target], fit_hazards[target])
            proba = candidate.predict_proba(X_dev, dev_hazards[target])
            predictions = Predictions.from_proba(proba)
            metrics = classification_metrics(dev_y[target], predictions)
            diff = paired_cluster_bootstrap(
                dev_y[target], predictions, r_predictions[target], dev_groups[target],
                n_resamples=n_resamples,
            )
            results.append(
                _record(
                    level, target, metrics, candidate.unavailable_hazards, bootstrap_vs_r=diff,
                    produces_three_class_distribution=candidate.produces_three_class_distribution,
                )
            )
            print(
                f"  {level:3s} {target}: macro_f1={metrics.macro_f1:.4f} worst={metrics.worst_class_f1:.4f} "
                f"vs_R_excludes_zero={diff.excludes_zero}"
            )

    print("Fitting S2 (jointly across both targets) ...")
    s2 = JOINT_BUILDERS["S2"]()
    s2.fit(fit_X["L"], fit_y["L"], fit_hazards["L"], fit_X["E"], fit_y["E"], fit_hazards["E"])
    for target in TARGETS:
        view = s2.target_view(target)
        proba = view.predict_proba(dev_X[target], dev_hazards[target])
        predictions = Predictions.from_proba(proba)
        metrics = classification_metrics(dev_y[target], predictions)
        diff = paired_cluster_bootstrap(
            dev_y[target], predictions, r_predictions[target], dev_groups[target],
            n_resamples=n_resamples,
        )
        results.append(
            _record(
                "S2", target, metrics, s2.unavailable_hazards, bootstrap_vs_r=diff,
                produces_three_class_distribution=view.produces_three_class_distribution,
            )
        )
        print(
            f"  S2  {target}: macro_f1={metrics.macro_f1:.4f} worst={metrics.worst_class_f1:.4f} "
            f"vs_R_excludes_zero={diff.excludes_zero}"
        )

    # Informational triage feeding slice C's composite (§6) -- not a
    # selection. R has no axis of its own (its row is `axis: null`); it is
    # included as the baseline every real axis's level(s) must beat, not as
    # a pseudo-axis in its own right.
    best_level_per_axis: dict[str, dict[str, str]] = {t: {} for t in TARGETS}
    for target in TARGETS:
        by_axis: dict[str, list[dict]] = {}
        for row in results:
            if row["target"] != target or row["axis"] is None:
                continue
            by_axis.setdefault(row["axis"], []).append(row)
        r_row = next(r for r in results if r["target"] == target and r["level"] == "R")
        for axis, level_rows in by_axis.items():
            best = max(level_rows + [r_row], key=lambda r: r["macro_f1"])
            best_level_per_axis[target][axis] = best["level"]

    split_manifest = json.loads(INTERIM_SPLIT.read_text())

    return {
        "stage": "stage1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split_version": split_manifest["split_version"],
        "split_source_sha256": split_manifest["source_sha256"],
        "reference": "R",
        "worst_class_f1_floor": WORST_CLASS_F1_FLOOR,
        "bootstrap_resamples": n_resamples,
        "not_a_benchmark_result": (
            "Every number here is a dev-set number under DECISIONS.md D-66 -- "
            "not a benchmark result, not a generalization estimate, and not "
            "reportable under SCIENCE.md §Evidence and outputs."
        ),
        "best_level_per_axis": best_level_per_axis,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--allow-download", action="store_true",
        help="allow downloading the BGE model if not already cached (do this once, not per run)",
    )
    parser.add_argument(
        "--resamples", type=int, default=1000,
        help="bootstrap resamples per comparison (pre-registration default: 1000)",
    )
    args = parser.parse_args()

    manifest = run_sweep(allow_download=args.allow_download, n_resamples=args.resamples)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        display_path = args.out.relative_to(REPO)
    except ValueError:
        display_path = args.out
    print(f"\nwrote {display_path} ({len(manifest['results'])} results)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
