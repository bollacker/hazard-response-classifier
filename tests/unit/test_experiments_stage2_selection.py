"""Tests for slice C's selection rule -- `scripts/run_stage2_sweep.py`'s
`_select`, which implements `PREREGISTRATION_LE_STRUCTURE.md` §4.

This is the function that decides what queue item 2 actually selects, so it
is the last place in this item where an untested branch is acceptable.

The load-bearing test here is
`test_a_two_head_structure_can_never_be_selected_even_when_it_ranks_first`.
§4's closing rule requires the selection to be "the highest-ranked candidate
that produces a genuine three-class distribution", and that property is
structural, not a label attached to R: every two-head variant on the ladder
inherits R's inability to emit one. A first version of this function ignored
the rule entirely and selected `S2` for the L target -- a structure with
exactly the defect that makes R ineligible.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

from run_stage2_sweep import _select  # noqa: E402


def _row(
    level,
    macro_f1,
    worst_class_f1,
    *,
    disqualified=False,
    excludes_zero=None,
    distribution=True,
):
    return {
        "level": level,
        "macro_f1": macro_f1,
        "worst_class_f1": worst_class_f1,
        "disqualified_worst_class_floor": disqualified,
        "produces_three_class_distribution": distribution,
        "bootstrap_vs_r": None if excludes_zero is None else {"excludes_zero": excludes_zero},
    }


def _r(macro_f1=0.50, worst=0.31):
    return _row("R", macro_f1, worst, distribution=False)


# --------------------------------------------------------------------------
# §4's closing rule -- the constraint the first implementation missed
# --------------------------------------------------------------------------


def test_a_two_head_structure_can_never_be_selected_even_when_it_ranks_first():
    """The real L-target shape. `S2` outranks R on macro-F1, but it decides
    by threshold and returns a one-hot row -- the same defect §2.2 excludes
    R for. The selection must fall to the best structure that actually emits
    a distribution, and must be reported as the null finding.
    """
    r = _r(macro_f1=0.4840, worst=0.3182)
    s2 = _row("S2", 0.4851, 0.2927, excludes_zero=False, distribution=False)
    l1 = _row("L1", 0.4336, 0.2667, distribution=True)
    l2 = _row("L2", 0.4199, 0.2162, disqualified=True, distribution=True)

    result = _select("L", r, [r, s2], [r, s2, l1, l2])

    assert result["outcome"] == "no_structure_beat_the_incumbent"
    assert result["selected"] == "L1"
    assert result["blocked_top_finalist"] == "S2"
    assert "S2" in result["excluded_no_three_class_distribution"]
    assert "R" in result["excluded_no_three_class_distribution"]
    assert "no structure that beats the incumbent" in result["note"]


def test_every_two_head_variant_is_excluded_not_just_r():
    """The property is structural. W2/W3/H1/H2/B1/P2/P3/S2 all keep R's L3
    loss, so none of them may be selected however well they score.
    """
    r = _r(macro_f1=0.40, worst=0.30)
    two_head = [
        _row(level, 0.90, 0.80, excludes_zero=True, distribution=False)
        for level in ("W2", "W3", "H1", "H2", "B1", "P2", "P3", "S2")
    ]
    l1 = _row("L1", 0.41, 0.26, distribution=True)

    result = _select("E", r, [r, two_head[-1]], [r, *two_head, l1])

    assert result["selected"] == "L1"
    assert set(result["excluded_no_three_class_distribution"]) == {
        "R", "W2", "W3", "H1", "H2", "B1", "P2", "P3", "S2",
    }


def test_no_eligible_candidate_when_every_distribution_producer_is_disqualified():
    r = _r()
    s2 = _row("S2", 0.52, 0.31, excludes_zero=False, distribution=False)
    l1 = _row("L1", 0.48, 0.10, disqualified=True, distribution=True)

    result = _select("E", r, [r, s2], [r, s2, l1])

    assert result["outcome"] == "no_eligible_candidate"
    assert result["selected"] is None
    assert "cannot be the answer" in result["note"]


# --------------------------------------------------------------------------
# The ordinary paths
# --------------------------------------------------------------------------


def test_composite_ranked_first_with_separation_is_selected_outright():
    r = _r(macro_f1=0.48, worst=0.30)
    composite = _row("L1+W3", 0.55, 0.34, distribution=True)
    runner_up = _row("L1", 0.50, 0.31, distribution=True)

    result = _select(
        "E",
        r,
        [r, composite],
        [r, composite, runner_up],
        separation={"excludes_zero": True, "comparator": "L1"},
    )

    assert result["outcome"] == "selected_outright"
    assert result["selected"] == "L1+W3"
    assert result["separated_from_next"] is True
    assert result["separation_comparator"] == "L1"


def test_composite_ranked_first_without_separation_says_so_plainly():
    """The real E-target shape: the composite tops the eligible ranking but
    its interval against R includes zero. Selected, but the report must not
    imply it was shown to beat R.
    """
    r = _r(macro_f1=0.5199, worst=0.3077)
    composite = _row("L1+W3", 0.5356, 0.3415, distribution=True)
    l1 = _row("L1", 0.5289, 0.3500, distribution=True)

    result = _select(
        "E",
        r,
        [r, composite],
        [r, composite, l1],
        separation={"excludes_zero": False, "comparator": "L1"},
    )

    assert result["outcome"] == "selected_without_separation"
    assert result["selected"] == "L1+W3"
    assert result["separated_from_next"] is False
    # The comparator must be the next-ranked *eligible* candidate, never R:
    # R can never be selected, so separating from it decides nothing.
    assert result["separation_comparator"] == "L1"
    assert "not because it was shown to beat the incumbent" in result["note"]


def test_separation_is_not_applicable_with_a_single_eligible_candidate():
    """The L-target shape: only one structure both survives the floor and
    produces a distribution, so there is no runner-up to separate from.
    That must read as 'not applicable', never as a passed or failed test.
    """
    r = _r(macro_f1=0.4840, worst=0.3182)
    s2 = _row("S2", 0.4851, 0.2927, distribution=False)
    l1 = _row("L1", 0.4336, 0.2667, distribution=True)

    result = _select("L", r, [r, s2], [r, s2, l1], separation=None)

    assert result["selected"] == "L1"
    assert result["separated_from_next"] is None
    assert result["separation_comparator"] is None


def test_separation_against_r_is_never_used_as_the_comparator():
    """Forcing function for the bug this replaced: an earlier version read
    the candidate's own `bootstrap_vs_r` and so reported separation against
    R. A row carrying a misleading `bootstrap_vs_r` must not influence the
    result when the caller supplies no separation.
    """
    r = _r(macro_f1=0.48, worst=0.30)
    composite = _row("L1+W3", 0.55, 0.34, excludes_zero=True, distribution=True)

    result = _select("E", r, [r, composite], [r, composite], separation=None)

    # bootstrap_vs_r says excludes_zero=True, but with no eligible runner-up
    # there is nothing to separate from -- it must not be read as outright.
    assert result["outcome"] != "selected_outright"
    assert result["separated_from_next"] is None


def test_r_outranking_everything_still_selects_the_best_distribution_producer():
    r = _r(macro_f1=0.60, worst=0.35)
    composite = _row("L1+W3", 0.50, 0.30, excludes_zero=False, distribution=True)

    result = _select("E", r, [r, composite], [r, composite])

    assert result["outcome"] == "no_structure_beat_the_incumbent"
    assert result["selected"] == "L1+W3"
    assert result["blocked_top_finalist"] == "R"


def test_disqualified_finalists_are_reported():
    r = _r(macro_f1=0.52, worst=0.31)
    composite = _row("L1+W3", 0.55, 0.10, disqualified=True, distribution=True)
    l1 = _row("L1", 0.40, 0.28, distribution=True)

    result = _select("E", r, [r, composite], [r, composite, l1])

    assert result["disqualified_worst_class_floor"] == ["L1+W3"]
    assert result["selected"] == "L1"


def test_selection_never_returns_r_itself():
    """§2.2, as an invariant rather than a branch: whatever the numbers, R
    must never come back as the selected structure.
    """
    for r_macro in (0.10, 0.50, 0.99):
        r = _r(macro_f1=r_macro, worst=0.40)
        composite = _row("L1+W3", 0.50, 0.30, excludes_zero=False, distribution=True)
        result = _select("E", r, [r, composite], [r, composite])
        assert result["selected"] != "R"
