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
structure significantly beat `R` on either target, and both targets select
`L1`.** L selects `L1` purely as the best qualifying structure while scoring
*below* `R`. On E the `L1+W3` composite led on macro-F1 but §4 step 3's
paired interval against the next-ranked *eligible* candidate (`L1` -- the
comparator is never `R`) did not exclude zero, so §4 step 4 applies and
§4.1 criterion 1 (higher worst-class F1, 0.3500 vs 0.3415) selects `L1`.

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

from hazard_classifier.experiments.candidates import (  # noqa: E402
    STAGE1_BUILDERS,
    STAGE1_LEVELS,
    MultinomialSoftmax,
)
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
    fitted_parameter_count=None,
    axis=None,
) -> dict:
    return {
        "level": level,
        "target": target,
        # A stage-1 ladder concept: the single §2.3 axis this level varies.
        # `None` for a composite that varies more than one (the E composite);
        # the L composite inherits "Sharing" because it *is* stage 1's S2.
        "axis": axis,
        # Must be carried on stage-2 rows too: §4's closing rule reads it,
        # and a missing value is treated as "does not qualify", which would
        # silently exclude a composite that does.
        "produces_three_class_distribution": produces_three_class_distribution,
        # §4.1's second tie-break criterion.
        "fitted_parameter_count": fitted_parameter_count,
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


# How many of §2.3's axes each stage-2 composite moves off R's own level.
# Stage-1 levels are not listed: each varies exactly one axis by
# construction (§2.3, "One axis varies at a time from R").
_COMPOSITE_AXES_VARIED = {
    # L's composite keeps R's level on every axis but Sharing.
    "S2 (= L composite)": 1,
    # E's composite moves Loss (L1) and Weighting (W3).
    "L1+W3 (= E composite)": 2,
}


def _axes_varied_from_r(level: str) -> int:
    """§4.1's third criterion, "closer to the reference R", made countable:
    how many of §2.3's axes this structure moves off R's own level. Every
    stage-1 level varies exactly one by construction; a stage-2 composite
    varies as many as its definition names.

    **Raises on any level it does not recognize** rather than guessing. A
    silent default of 1 was the trap here: a future composite missing from
    `_COMPOSITE_AXES_VARIED` would be scored as varying a single axis and
    could wrongly win criterion 3 against a candidate that genuinely does.
    """
    if level == "R":
        return 0
    composite = _COMPOSITE_AXES_VARIED.get(level)
    if composite is not None:
        return composite
    if level in STAGE1_LEVELS:
        return 1  # every stage-1 ladder level varies exactly one axis from R
    raise ValueError(
        f"unknown level {level!r}: not R, not a stage-1 ladder level, and not in "
        "_COMPOSITE_AXES_VARIED. Add any new composite to that table explicitly -- "
        "a silent default here could decide §4.1 criterion 3 wrongly."
    )


# §4.1 criterion 1 compares two floats produced by the same metrics pipeline.
# Exact `!=` would let a difference on the order of float rounding (~1e-16)
# "decide" the tie-break; any difference at or below this tolerance is treated
# as a genuine tie and falls through to criterion 2. Far below any difference
# that could be meaningful on a ≤224-row dev slice (where one row moves an F1
# by ~1e-3), and far above accumulated float noise.
_WORST_F1_TIE_TOLERANCE = 1e-9


def _apply_tie_break(top: dict, runner_up: dict, r_row: dict) -> dict:
    """`PREREGISTRATION_LE_STRUCTURE.md` §4.1, in order:
    1. higher worst-class F1, 2. fewer fitted parameters, 3. closer to R.

    Returns the winner and a record of which criterion decided, so the
    result is auditable rather than asserted. Criteria are consulted in
    order and stop at the first that separates them. A criterion that cannot
    be evaluated (a missing parameter count) is recorded as not evaluable
    rather than silently skipped.
    """
    criteria = []

    a, b = top["worst_class_f1"], runner_up["worst_class_f1"]
    decided = abs(a - b) > _WORST_F1_TIE_TOLERANCE
    criteria.append(
        {
            "criterion": "higher_worst_class_f1",
            "top": a,
            "runner_up": b,
            "tolerance": _WORST_F1_TIE_TOLERANCE,
            "decided": decided,
        }
    )
    if decided:
        winner = top if a > b else runner_up
        return {
            "winner": winner,
            "record": {"decided_by": "higher_worst_class_f1", "criteria": criteria},
            "note": (
                f"§4.1 criterion 1 (higher worst-class F1) decides: "
                f"{winner['level']} has {max(a, b):.4f} against {min(a, b):.4f}."
            ),
        }

    a, b = top.get("fitted_parameter_count"), runner_up.get("fitted_parameter_count")
    evaluable = a is not None and b is not None
    entry = {
        "criterion": "fewer_fitted_parameters",
        "top": a,
        "runner_up": b,
        "evaluable": evaluable,
        "decided": bool(evaluable and a != b),
    }
    if not evaluable:
        entry["note"] = (
            "not evaluable: at least one candidate has no recorded "
            "fitted_parameter_count -- criterion skipped, not decided"
        )
    criteria.append(entry)
    if evaluable and a != b:
        winner = top if a < b else runner_up
        return {
            "winner": winner,
            "record": {"decided_by": "fewer_fitted_parameters", "criteria": criteria},
            "note": (
                f"§4.1 criterion 1 tied; criterion 2 (fewer fitted parameters) decides: "
                f"{winner['level']} has {min(a, b)} against {max(a, b)}."
            ),
        }

    a, b = _axes_varied_from_r(top["level"]), _axes_varied_from_r(runner_up["level"])
    criteria.append({"criterion": "closer_to_r", "top": a, "runner_up": b, "decided": a != b})
    if a != b:
        winner = top if a < b else runner_up
        return {
            "winner": winner,
            "record": {"decided_by": "closer_to_r", "criteria": criteria},
            "note": (
                f"§4.1 criteria 1 and 2 tied; criterion 3 (closer to R) decides: "
                f"{winner['level']} varies {min(a, b)} axis/axes from R against {max(a, b)}."
            ),
        }

    return {
        "winner": top,
        "record": {"decided_by": "exhausted_tie_break", "criteria": criteria},
        "note": (
            "§4.1's three criteria are all tied; the macro-F1 leader stands by default. "
            "The pre-registration defines no fourth criterion, so this is recorded as an "
            "unresolved tie rather than a decision."
        ),
    }


def _select(
    target: str,
    r_row: dict,
    finalists: list[dict],
    eligible_pool: list[dict],
    separation: dict | None = None,
    cross_target_disqualified: frozenset[str] = frozenset(),
) -> dict:
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
    # §3's floor is written "below 0.25 **on either target**", so a level
    # failing it on one target is disqualified on both -- even though §4 is
    # otherwise applied per target. The two clauses pull in different
    # directions; the literal wording of §3 is taken, which is also the
    # conservative choice (it disqualifies strictly more). Recorded in §8.
    # `cross_target_disqualified` carries the levels failing on the *other*
    # target; a level failing on this one is already flagged in its own row.
    def _disqualified(row: dict) -> bool:
        return bool(row["disqualified_worst_class_floor"]) or row["level"] in cross_target_disqualified

    ranked_finalists = sorted(
        [row for row in finalists if not _disqualified(row)],
        key=lambda row: row["macro_f1"],
        reverse=True,
    )
    disqualified = [row["level"] for row in finalists if _disqualified(row)]

    # §4 steps 1-2 over the *eligible* pool: survives the floor AND produces
    # a genuine three-class distribution. Both conditions, not either.
    eligible = sorted(
        [
            row
            for row in eligible_pool
            if not _disqualified(row)
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
    pool_disqualified = sorted({row["level"] for row in eligible_pool if _disqualified(row)})

    # The numbers themselves, per pool candidate, so this record is
    # self-sufficient for the ledger entry ("the rejected candidates with
    # their numbers") without a reader having to join stage1.json by hand.
    pool_records = [
        {
            "level": row["level"],
            "macro_f1": row["macro_f1"],
            "per_class_f1": row.get("per_class_f1"),
            "worst_class_f1": row["worst_class_f1"],
            "fitted_parameter_count": row.get("fitted_parameter_count"),
            "produces_three_class_distribution": row.get("produces_three_class_distribution"),
            "disqualified_worst_class_floor": bool(row["disqualified_worst_class_floor"]),
            "disqualified_by_other_target_floor": (
                row["level"] in cross_target_disqualified
                and not row["disqualified_worst_class_floor"]
            ),
            "eligible": (
                not _disqualified(row)
                and row.get("produces_three_class_distribution") is True
            ),
        }
        for row in sorted(eligible_pool, key=lambda r: r["macro_f1"], reverse=True)
    ]

    base = {
        "disqualified_worst_class_floor": disqualified,
        "pool_disqualified_worst_class_floor": pool_disqualified,
        "excluded_no_three_class_distribution": excluded_no_distribution,
        "finalists_ranked": [row["level"] for row in ranked_finalists],
        "eligible_ranked": [row["level"] for row in eligible],
        "pool": pool_records,
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

    # §4 step 3: separation of the top candidate against **the next-ranked
    # candidate**. The comparator must be the next-ranked *eligible*
    # candidate, not R.
    #
    # Getting this wrong is subtle and was wrong here once: an earlier
    # version read `selected["bootstrap_vs_r"]`, testing separation against
    # R -- a structure that can never be selected. Step 3 exists to decide
    # whether the winner is distinguishable from the runner-up it was
    # actually chosen over, and the runner-up is whatever would have been
    # selected instead. On the E target that is `L1` (0.5289), not R.
    #
    # `separation` is supplied by the caller because computing it needs
    # row-level predictions for both candidates, which this pure function
    # does not have. `None` means "not applicable" -- there was no second
    # eligible candidate to separate from -- and is therefore refused when a
    # second eligible candidate exists, so steps 3-4 can never be silently
    # skipped by an incomplete caller.
    if len(eligible) > 1 and separation is None:
        raise ValueError(
            "more than one eligible candidate exists, so §4 step 3 needs the paired "
            "separation interval between the top two -- the caller must supply "
            "`separation`; omitting it would silently skip steps 3-4"
        )

    separated = None if separation is None else bool(separation["excludes_zero"])
    separation_comparator = None if separation is None else separation.get("comparator")

    # §4 steps 2-4 operate on the *eligible* ranking, wherever the
    # never-selectable structures happen to rank (`PREREGISTRATION_LE_STRUCTURE.md`
    # §8, 2026-08-05: "an unseparated lead on macro-F1 is not evidence", and
    # the runner-up is whatever would have been selected instead -- both
    # statements are indifferent to where R or a two-head composite ranks).
    # So the tie-break fires whenever separation between the top two
    # eligible candidates fails, in *every* branch below -- an earlier
    # version applied it only when the eligible leader also topped the
    # finalist ranking, which made §4.1's applicability depend on the rank
    # of a structure that can never be selected.
    tie_break = None
    selected = eligible[0]
    if separated is False and len(eligible) > 1:
        tie_break = _apply_tie_break(eligible[0], eligible[1], r_row)
        selected = tie_break["winner"]

    top_finalist = ranked_finalists[0] if ranked_finalists else None
    finalist_won = top_finalist is not None and top_finalist["level"] == eligible[0]["level"]

    common = {
        "separated_from_next": separated,
        "separation_comparator": separation_comparator,
        "separation_interval": separation,
    }
    if tie_break is not None:
        common["tie_break"] = tie_break["record"]

    if finalist_won and separated:
        return {
            **base,
            "outcome": "selected_outright",
            "selected": selected["level"],
            **common,
            "note": (
                f"{selected['level']} ranked first among eligible candidates and its "
                f"paired bootstrap interval against the next-ranked eligible candidate "
                f"({separation_comparator}) excludes zero -- selected outright."
            ),
        }

    if finalist_won:
        # §4 step 4: "If separation fails, the candidates are tied and §4.1
        # decides." Ranking first by macro-F1 does NOT settle it -- macro-F1
        # produced the ranking, and step 4 exists precisely because an
        # unseparated lead on that metric is not evidence. Applying §4.1's
        # criteria in order can, and here does, overturn the macro-F1 leader.
        if tie_break is not None:
            return {
                **base,
                "outcome": "selected_by_tiebreak",
                "selected": selected["level"],
                **common,
                "note": (
                    f"{eligible[0]['level']} led on macro-F1 but was not significantly "
                    f"separated from {separation_comparator} (§4 step 3 fails), so the two "
                    f"are tied and §4.1 decides. {tie_break['note']} Selected: "
                    f"{selected['level']}."
                ),
            }

        return {
            **base,
            "outcome": "selected_without_separation",
            "selected": selected["level"],
            **common,
            "note": (
                f"{selected['level']} is the only eligible candidate, so §4 step 3 has no "
                f"runner-up to test separation against and step 4's tie-break has nothing "
                f"to weigh it against. It is selected because it is the only structure that "
                f"both survives the floor and produces a genuine three-class distribution "
                f"-- not because it was shown to beat the incumbent."
            ),
        }

    # The candidate that topped the finalists could not be selected -- it
    # does not emit a distribution. This is the null result §4 describes.
    # §4 steps 3-4 still applied among the eligible candidates above, so
    # `selected` may be §4.1's winner rather than the eligible macro leader.
    blocked = top_finalist["level"] if top_finalist is not None else "(none)"
    if tie_break is not None:
        chosen_clause = (
            f"Among the candidates that do produce one, {eligible[0]['level']} led on "
            f"macro-F1 but was not significantly separated from {separation_comparator} "
            f"(§4 step 3 fails), so §4.1 decides. {tie_break['note']} Selected: "
            f"{selected['level']} (macro-F1 {selected['macro_f1']:.4f} vs R's "
            f"{r_row['macro_f1']:.4f})."
        )
    else:
        chosen_clause = (
            f"The selection is therefore the highest-ranked candidate that does produce "
            f"one: {selected['level']} (macro-F1 {selected['macro_f1']:.4f} vs R's "
            f"{r_row['macro_f1']:.4f})."
        )
    return {
        **base,
        "outcome": "no_structure_beat_the_incumbent",
        "selected": selected["level"],
        **common,
        "blocked_top_finalist": blocked,
        "note": (
            f"The highest-ranked finalist ({blocked}) cannot be selected: like R, it "
            f"decides by threshold and returns a one-hot row rather than the genuine "
            f"three-class distribution `SCIENCE.md` requires (§2.2, §4's closing rule). "
            f"{chosen_clause} **The ablation found no structure that beats the "
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
    # reproduces stage 1's R exactly -- enforced by the assert immediately
    # below, which is the actual check (there is no separate test for it).
    from hazard_classifier.experiments.candidates import TwoHeadReference

    r = TwoHeadReference()
    r.fit(fit_X["E"], fit_y["E"], fit_hazards["E"])
    r_predictions_e = Predictions.from_proba(r.predict_proba(dev_X["E"], dev_hazards["E"]))
    r_metrics_e = classification_metrics(dev_y["E"], r_predictions_e)
    assert abs(r_metrics_e.macro_f1 - r_e["macro_f1"]) < 1e-9, (
        "refit R does not match stage1.json's R -- fitting is not reproducing stage 1"
    )

    composite_predictions_e = predictions
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
        fitted_parameter_count=candidate.fitted_parameter_count(),
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

    # Row-level predictions for the candidates §4 step 3 may need to compare.
    # Only distribution-producing stage-1 levels can ever be the top or
    # next-ranked *eligible* candidate, so only those are rebuilt. Refitting
    # is deterministic and recomputes an already-counted stage-1
    # configuration -- it adds nothing to the §2.4 budget -- and each refit
    # is asserted against stage 1's own recorded macro-F1 so a silent
    # divergence cannot pass unnoticed.
    eligible_predictions: dict[tuple[str, str], Predictions] = {
        ("L1+W3 (= E composite)", "E"): composite_predictions_e,
    }
    for target in TARGETS:
        for level, builder in STAGE1_BUILDERS.items():
            probe = builder()
            if not probe.produces_three_class_distribution:
                continue
            recorded = stage1_by_key[(level, target)]
            if recorded["disqualified_worst_class_floor"]:
                continue  # cannot be top or next-ranked eligible
            probe.fit(fit_X[target], fit_y[target], fit_hazards[target])
            preds = Predictions.from_proba(probe.predict_proba(dev_X[target], dev_hazards[target]))
            got = classification_metrics(dev_y[target], preds).macro_f1
            assert abs(got - recorded["macro_f1"]) < 1e-9, (
                f"refit {level}/{target} macro-F1 {got} != stage1's {recorded['macro_f1']} "
                "-- fitting is not reproducing stage 1"
            )
            eligible_predictions[(level, target)] = preds

    # Levels failing §3's floor on *any* target -- see `_select`'s note on
    # the "on either target" wording.
    floor_failures_any_target = frozenset(
        row["level"] for row in stage1["results"] if row["disqualified_worst_class_floor"]
    ) | frozenset(
        composites[t]["level"] for t in TARGETS if composites[t]["disqualified_worst_class_floor"]
    )

    selections = {}
    for target in TARGETS:
        r_row = stage1_by_key[("R", target)]
        # The pool §4's closing rule ranks over: every candidate evaluated
        # in this item for this target -- stage 1's ladder plus stage 2's
        # composite -- not just stage 2's finalists.
        pool = [row for row in stage1["results"] if row["target"] == target]
        pool = pool + [composites[target]]

        # §4 step 3's comparator: the next-ranked *eligible* candidate.
        eligible_ranked = sorted(
            [
                row
                for row in pool
                if not row["disqualified_worst_class_floor"]
                and row["level"] not in floor_failures_any_target
                and row.get("produces_three_class_distribution") is True
            ],
            key=lambda row: row["macro_f1"],
            reverse=True,
        )
        separation = None
        if len(eligible_ranked) > 1:
            top_level, next_level = eligible_ranked[0]["level"], eligible_ranked[1]["level"]
            top_preds = eligible_predictions[(top_level, target)]
            next_preds = eligible_predictions[(next_level, target)]
            diff_sep = paired_cluster_bootstrap(
                dev_y[target], top_preds, next_preds, dev_groups[target], n_resamples=n_resamples
            )
            separation = {**diff_sep.as_dict(), "comparator": next_level, "top": top_level}
            print(
                f"  separation[{target}]: {top_level} vs {next_level} -> "
                f"excludes_zero={diff_sep.excludes_zero}"
            )
        else:
            print(f"  separation[{target}]: not applicable (only one eligible candidate)")

        selections[target] = _select(
            target,
            r_row,
            [r_row, composites[target]],
            pool,
            separation=separation,
            cross_target_disqualified=floor_failures_any_target,
        )
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
        "worst_class_floor_applied_across_targets": True,
        "worst_class_floor_scope_note": (
            "§3's floor is written 'below 0.25 on either target', so a level failing "
            "it on one target is disqualified on both, even though §4 is otherwise "
            "applied per target. The literal (and more conservative) reading is used; "
            "see PREREGISTRATION_LE_STRUCTURE.md §8. On this data it changes nothing -- "
            "the only floor-failing distribution-producer (L2) fails on both targets."
        ),
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
