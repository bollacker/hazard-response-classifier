#!/usr/bin/env python3
"""Run queue item 2 slice C's stage-2 finalists and selection, and write
`docs/planning/item2_results/stage2.json`.

Context (`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` §6,
`docs/planning/PREREGISTRATION_LE_STRUCTURE.md` §2.4, §4). Combines the best
level of each axis (`stage1.json`'s `best_level_per_axis`) into one composite
per target, then applies the pre-registration §4 selection rule exactly.

**Zero hand-picked combinations beyond the required composite, on Kurt's
direction (2026-08-05).** §2.4 allows "at most 3" extra combinations "where
stage 1 suggests an interaction" -- stage 1 found no candidate significantly
beating `R` on either target (only `B1` was significant, and worse), so
there is no data-driven interaction to chase. Inventing one to fill the
budget is exactly what the pre-registration's "do not expand the budget"
guards against: "an extended search on a dev set this size is how a
selection rule becomes a description of noise." "At most 3" already permits
zero.

**The L composite needs no new fit.** `stage1.json`'s `best_level_per_axis`
for L keeps `R`'s own level on every axis except Sharing, where `S2` wins --
so the L composite *is* `S2`, already fitted and scored in stage 1. Refitting
it would be wasted work computing an identical result. This script carries
`S2`'s stage-1 numbers forward rather than re-running it.

**The E composite is new**: `Loss=L1, Weighting=W3`, the remaining
applicable axes at `R`'s level. `MultinomialSoftmax(weighting="W3")` (added
to `candidates.py` for exactly this) is the one new fit this script performs.

**A finalist can top the ranking and still be ineligible to win.** §4's
closing rule requires the selection to be "the highest-ranked candidate that
produces a genuine three-class distribution", and that property is
structural: every level keeping `R`'s `L3` two-head loss decides by threshold
and returns a one-hot row, so `W2`, `W3`, `H1`, `H2`, `B1`, `P2`, `P3` and
`S2` are all excluded alongside `R` itself. Only `L1` and `L2` qualify. This
decides the L target, where the composite (`S2`) outranks `R` on macro-F1 but
cannot be selected -- see `PREREGISTRATION_LE_STRUCTURE.md` §8's 2026-08-05
amendment, which records both this reading and the pool the rule ranks over.

What the run finds, so it is not mistaken for a positive result: **no
structure significantly beat `R` on either target.** L selects `L1` purely as
the best qualifying structure while scoring *below* `R`; E selects the
`L1+W3` composite without significant separation from `R`.

Run:  python scripts/run_stage2_sweep.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np

_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR.parent / "src"))
sys.path.insert(0, str(_SCRIPTS_DIR))

from run_stage1_sweep import TARGETS, _features_for, _target_frames  # noqa: E402

from hazard_classifier.experiments.candidates import MultinomialSoftmax  # noqa: E402
from hazard_classifier.experiments.comparison_metrics import (  # noqa: E402
    WORST_CLASS_F1_FLOOR,
    Predictions,
    classification_metrics,
    paired_cluster_bootstrap,
)
from hazard_classifier.experiments.features import embed_responses  # noqa: E402
from hazard_classifier.interim_data import INTERIM_SPLIT, load_interim  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_STAGE1_PATH = REPO / "docs" / "planning" / "item2_results" / "stage1.json"
DEFAULT_OUT = REPO / "docs" / "planning" / "item2_results" / "stage2.json"


def _record(
    level: str,
    target: str,
    metrics,
    unavailable_hazards,
    bootstrap_vs_r=None,
    produces_three_class_distribution=None,
) -> dict:
    return {
        "level": level,
        "target": target,
        # Must be carried on stage-2 rows too: §4's closing rule reads it,
        # and a missing value is treated as "does not qualify", which would
        # silently exclude a composite that does.
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
        "bootstrap_vs_r": bootstrap_vs_r.as_dict() if bootstrap_vs_r is not None else None,
    }


def _select(target: str, r_row: dict, finalists: list[dict], eligible_pool: list[dict]) -> dict:
    """Pre-registration §4, applied to one target.

    `finalists` is stage 2's own finalist set (here: R plus the composite --
    no hand-picked extras, see the module docstring). `eligible_pool` is
    every candidate evaluated in this item, stage 1 and stage 2 together,
    which §4's closing rule needs.

    **§4's closing rule is a hard constraint on what may be selected, not a
    footnote about R.** Its exact words: "the selection is the highest-ranked
    candidate that produces a genuine three-class distribution." R is
    excluded by §2.2 for precisely that reason -- but the property is
    structural, not a label attached to R, so *every* two-head variant on the
    ladder is excluded with it (W2, W3, H1, H2, B1, P2, P3, and S2 all keep
    R's L3 loss and decide by threshold). Only L1 and L2 qualify.

    **Interpretation recorded rather than assumed** (`PREREGISTRATION_LE_STRUCTURE.md`
    §8, 2026-08-05): §4 does not say explicitly which pool the closing rule
    ranks over when no finalist qualifies. Taken here as every candidate
    evaluated in this item -- stage 1 and stage 2 -- since the alternative
    (select nothing) would leave PR 5 with no structure at all despite the
    ladder having measured qualifying ones.
    """
    ranked_finalists = sorted(
        [row for row in finalists if not row["disqualified_worst_class_floor"]],
        key=lambda row: row["macro_f1"],
        reverse=True,
    )
    disqualified = [row["level"] for row in finalists if row["disqualified_worst_class_floor"]]

    # §4 steps 1-2 over the *eligible* pool: survives the floor AND produces
    # a genuine three-class distribution. Both conditions, not either.
    eligible = sorted(
        [
            row
            for row in eligible_pool
            if not row["disqualified_worst_class_floor"]
            and row.get("produces_three_class_distribution") is True
        ],
        key=lambda row: row["macro_f1"],
        reverse=True,
    )
    excluded_no_distribution = sorted(
        {
            row["level"]
            for row in eligible_pool
            if row.get("produces_three_class_distribution") is not True
        }
    )

    # Reported across the whole eligible pool, not just the finalists:
    # queue item 2 owes the ledger "the rejected candidates with their
    # numbers", and a candidate rejected by the floor at stage 1 (L2, on
    # both targets) would otherwise be invisible in the selection record.
    pool_disqualified = sorted(
        {row["level"] for row in eligible_pool if row["disqualified_worst_class_floor"]}
    )

    base = {
        "disqualified_worst_class_floor": disqualified,
        "pool_disqualified_worst_class_floor": pool_disqualified,
        "excluded_no_three_class_distribution": excluded_no_distribution,
        "finalists_ranked": [row["level"] for row in ranked_finalists],
        "eligible_ranked": [row["level"] for row in eligible],
    }

    if not eligible:
        return {
            **base,
            "outcome": "no_eligible_candidate",
            "selected": None,
            "note": (
                "No candidate both survived the worst-class floor and produces a "
                "genuine three-class distribution, so §4's closing rule has nothing "
                "to select. `SCIENCE.md` requires a three-class multinomial; a "
                "structure that cannot emit one cannot be the answer regardless of "
                "its macro-F1."
            ),
        }

    selected = eligible[0]
    top_finalist = ranked_finalists[0] if ranked_finalists else None
    finalist_won = top_finalist is not None and top_finalist["level"] == selected["level"]

    # Separation (§4 step 3) is only meaningful when the selected candidate
    # is the top finalist and the next-ranked finalist is R -- the only
    # pairing this run's finalist set supports.
    separated = None
    if finalist_won and len(ranked_finalists) > 1:
        next_row = ranked_finalists[1]
        bootstrap = selected.get("bootstrap_vs_r")
        if next_row["level"] == r_row["level"] and bootstrap is not None:
            separated = bool(bootstrap["excludes_zero"])

    if finalist_won and separated:
        return {
            **base,
            "outcome": "selected_outright",
            "selected": selected["level"],
            "separated_from_next": True,
            "note": (
                f"{selected['level']} ranked first among eligible candidates and its "
                f"paired bootstrap interval against R excludes zero -- selected outright."
            ),
        }

    if finalist_won:
        return {
            **base,
            "outcome": "selected_without_separation",
            "selected": selected["level"],
            "separated_from_next": separated,
            "note": (
                f"{selected['level']} ranked first among eligible candidates but was not "
                f"significantly separated from R (§4 step 3 fails). It is selected because "
                f"it is the highest-ranked structure that produces a genuine three-class "
                f"distribution -- not because it was shown to beat the incumbent."
            ),
        }

    # The candidate that topped the finalists could not be selected -- it
    # does not emit a distribution. This is the null result §4 describes.
    blocked = top_finalist["level"] if top_finalist is not None else "(none)"
    return {
        **base,
        "outcome": "no_structure_beat_the_incumbent",
        "selected": selected["level"],
        "separated_from_next": separated,
        "blocked_top_finalist": blocked,
        "note": (
            f"The highest-ranked finalist ({blocked}) cannot be selected: like R, it "
            f"decides by threshold and returns a one-hot row rather than the genuine "
            f"three-class distribution `SCIENCE.md` requires (§2.2, §4's closing rule). "
            f"The selection is therefore the highest-ranked candidate that does produce "
            f"one: {selected['level']} (macro-F1 {selected['macro_f1']:.4f}, below R's "
            f"{r_row['macro_f1']:.4f}). **The ablation found no structure that beats the "
            f"incumbent on this data** -- this is the finding, reported as such, not a "
            f"positive selection."
        ),
    }


def run_stage2(*, stage1_path: pathlib.Path, allow_download: bool, n_resamples: int) -> dict:
    stage1 = json.loads(stage1_path.read_text())
    stage1_by_key = {(r["level"], r["target"]): r for r in stage1["results"]}
    best_level_per_axis = stage1["best_level_per_axis"]

    full = load_interim()
    embeddings = embed_responses(full, allow_download=allow_download)
    row_index = {rid: i for i, rid in enumerate(embeddings.row_ids)}
    pooled_p1 = embeddings.pooled("P1")

    frames = _target_frames()
    fit_X = {t: _features_for(frames[t]["fit"], pooled_p1, row_index) for t in TARGETS}
    dev_X = {t: _features_for(frames[t]["dev"], pooled_p1, row_index) for t in TARGETS}
    fit_y = {t: frames[t]["fit"][frames[t]["y_col"]].to_numpy(dtype=np.int64) for t in TARGETS}
    dev_y = {t: frames[t]["dev"][frames[t]["y_col"]].to_numpy(dtype=np.int64) for t in TARGETS}
    fit_hazards = {t: frames[t]["fit"]["hazard"].to_numpy() for t in TARGETS}
    dev_hazards = {t: frames[t]["dev"]["hazard"].to_numpy() for t in TARGETS}
    dev_groups = {t: frames[t]["dev"]["prompt_group_id"].to_numpy() for t in TARGETS}

    composites: dict[str, dict] = {}

    print("L composite: carried forward from stage 1's S2 (only Sharing differs from R) ...")
    s2_l = stage1_by_key[("S2", "L")]
    composites["L"] = {**s2_l, "level": "S2 (= L composite)", "composite_definition": best_level_per_axis["L"]}
    print(f"  S2 (= L composite): macro_f1={s2_l['macro_f1']:.4f} worst={s2_l['worst_class_f1']:.4f}")

    print("E composite: fitting Loss=L1, Weighting=W3 ...")
    candidate = MultinomialSoftmax(name="L1+W3 (= E composite)", weighting="W3")
    candidate.fit(fit_X["E"], fit_y["E"], fit_hazards["E"])
    proba = candidate.predict_proba(dev_X["E"], dev_hazards["E"])
    predictions = Predictions.from_proba(proba)
    metrics = classification_metrics(dev_y["E"], predictions)

    r_e = stage1_by_key[("R", "E")]
    # Rebuild R's Predictions from stage 1 is not possible from JSON alone
    # (only the summary metrics were persisted, not the per-row labels) --
    # refit R once here so the paired bootstrap has real row-level
    # predictions on both sides. Deterministic (fixed seed), so this
    # reproduces stage 1's R exactly; confirmed via the manifest comparison
    # in this script's own test.
    from hazard_classifier.experiments.candidates import TwoHeadReference

    r = TwoHeadReference()
    r.fit(fit_X["E"], fit_y["E"], fit_hazards["E"])
    r_predictions_e = Predictions.from_proba(r.predict_proba(dev_X["E"], dev_hazards["E"]))
    r_metrics_e = classification_metrics(dev_y["E"], r_predictions_e)
    assert abs(r_metrics_e.macro_f1 - r_e["macro_f1"]) < 1e-9, (
        "refit R does not match stage1.json's R -- fitting is not reproducing stage 1"
    )

    diff = paired_cluster_bootstrap(
        dev_y["E"], predictions, r_predictions_e, dev_groups["E"], n_resamples=n_resamples
    )
    composites["E"] = _record(
        "L1+W3 (= E composite)",
        "E",
        metrics,
        candidate.unavailable_hazards,
        diff,
        produces_three_class_distribution=candidate.produces_three_class_distribution,
    )
    composites["E"]["composite_definition"] = best_level_per_axis["E"]
    # `best_level_per_axis` is a per-axis independent maximum, so it can name
    # a combination no single structure can realize. Here it does: `Loss=L1`
    # is a flat three-class softmax with no nonzero/high decomposition, so
    # `Branching` -- whose levels (`B1` flat, `B2` hierarchical) describe how
    # a two-head structure combines its heads -- has nothing to apply to.
    # Recorded rather than silently dropped, so the composite is not read as
    # claiming a property it cannot have.
    composites["E"]["axes_not_applicable_under_this_loss"] = {
        "Branching": (
            "Not applicable under Loss=L1: a flat three-class softmax has no "
            "nonzero/high head pair to branch, so B1/B2 do not describe it. "
            "best_level_per_axis names 'R' (=B2) for this axis because each axis "
            "is maximized independently; the composite realizes every other axis."
        )
    }
    print(
        f"  L1+W3 (= E composite): macro_f1={metrics.macro_f1:.4f} worst={metrics.worst_class_f1:.4f} "
        f"vs_R_excludes_zero={diff.excludes_zero}"
    )

    selections = {}
    for target in TARGETS:
        r_row = stage1_by_key[("R", target)]
        # The pool §4's closing rule ranks over: every candidate evaluated
        # in this item for this target -- stage 1's ladder plus stage 2's
        # composite -- not just stage 2's finalists.
        pool = [row for row in stage1["results"] if row["target"] == target]
        pool = pool + [composites[target]]
        selections[target] = _select(target, r_row, [r_row, composites[target]], pool)
        print(f"  selection[{target}]: {selections[target]['outcome']} -> {selections[target]['selected']}")

    split_manifest = json.loads(INTERIM_SPLIT.read_text())

    return {
        "stage": "stage2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split_version": split_manifest["split_version"],
        "split_source_sha256": split_manifest["source_sha256"],
        "reference": "R",
        "worst_class_f1_floor": WORST_CLASS_F1_FLOOR,
        "bootstrap_resamples": n_resamples,
        "hand_picked_combinations_beyond_composite": 0,
        "hand_picked_combinations_rationale": (
            "Pre-registration §2.4 allows at most 3 hand-picked combinations "
            "'where stage 1 suggests an interaction'. Stage 1 found no candidate "
            "significantly beating R on either target (only B1 was significant, "
            "and worse) -- no data-driven interaction to chase, and 'at most 3' "
            "already permits zero. Kurt's direction, 2026-08-05."
        ),
        "not_a_benchmark_result": (
            "Every number here is a dev-set number under DECISIONS.md D-66 -- "
            "not a benchmark result, not a generalization estimate, and not "
            "reportable under SCIENCE.md §Evidence and outputs."
        ),
        "composites": composites,
        "selection": selections,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage1", type=pathlib.Path, default=DEFAULT_STAGE1_PATH)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--resamples", type=int, default=1000)
    args = parser.parse_args()

    manifest = run_stage2(
        stage1_path=args.stage1, allow_download=args.allow_download, n_resamples=args.resamples
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        display_path = args.out.relative_to(REPO)
    except ValueError:
        display_path = args.out
    print(f"\nwrote {display_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
