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

import pytest  # noqa: E402

from run_stage2_sweep import _apply_tie_break, _axes_varied_from_r, _select  # noqa: E402


def _row(
    level,
    macro_f1,
    worst_class_f1,
    *,
    disqualified=False,
    excludes_zero=None,
    distribution=True,
    params=100,
):
    return {
        "level": level,
        "macro_f1": macro_f1,
        "worst_class_f1": worst_class_f1,
        "disqualified_worst_class_floor": disqualified,
        "produces_three_class_distribution": distribution,
        "fitted_parameter_count": params,
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


def test_failed_separation_hands_the_decision_to_the_tiebreak_and_can_overturn_the_leader():
    """The real E-target shape, and §4 step 4's whole point: the composite
    leads on macro-F1 but is not separated from `L1`, so the two are tied
    and §4.1 decides. `L1` has the higher worst-class F1 (0.3500 vs 0.3415),
    so it wins -- the macro-F1 leader does **not** get selected by default.

    An earlier version returned the macro leader here, which pinned a
    violation of §4 step 4 with these exact numbers.
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

    assert result["outcome"] == "selected_by_tiebreak"
    assert result["selected"] == "L1", "§4.1 criterion 1 must overturn the macro-F1 leader"
    assert result["separated_from_next"] is False
    # The comparator must be the next-ranked *eligible* candidate, never R.
    assert result["separation_comparator"] == "L1"
    assert result["tie_break"]["decided_by"] == "higher_worst_class_f1"


def test_tiebreak_criterion_order_worst_class_then_params_then_closeness():
    r = _r()
    # 1: worst-class F1 decides.
    a = _row("A", 0.60, 0.30, params=10)
    b = _row("B", 0.55, 0.40, params=10)
    assert _apply_tie_break(a, b, r)["winner"]["level"] == "B"
    assert _apply_tie_break(a, b, r)["record"]["decided_by"] == "higher_worst_class_f1"

    # 2: worst-class tied -> fewer fitted parameters decides.
    a = _row("A", 0.60, 0.30, params=900)
    b = _row("B", 0.55, 0.30, params=10)
    out = _apply_tie_break(a, b, r)
    assert out["winner"]["level"] == "B"
    assert out["record"]["decided_by"] == "fewer_fitted_parameters"

    # 3: both tied -> closer to R decides (a stage-1 level varies 1 axis,
    #    the E composite varies 2).
    a = _row("L1+W3 (= E composite)", 0.60, 0.30, params=10)
    b = _row("L1", 0.55, 0.30, params=10)
    out = _apply_tie_break(a, b, r)
    assert out["winner"]["level"] == "L1"
    assert out["record"]["decided_by"] == "closer_to_r"


def test_tiebreak_fires_even_when_an_ineligible_structure_tops_the_finalists():
    """Forcing function for the §8 2026-08-05 amendment: §4 steps 3-4
    operate on the *eligible* ranking, wherever the never-selectable
    structures rank. Here R tops the finalist ranking (so the outcome is the
    null finding), the two eligible candidates are unseparated, and the
    runner-up has the higher worst-class F1 -- §4.1 must still decide, and
    must overturn the eligible macro-F1 leader.

    The previous implementation only applied §4.1 when the eligible leader
    also topped the finalists; with a strong-enough R it silently selected
    the unseparated macro leader by rank alone.
    """
    r = _r(macro_f1=0.60, worst=0.35)
    composite = _row("L1+W3 (= E composite)", 0.50, 0.28, distribution=True)
    l1 = _row("L1", 0.49, 0.34, distribution=True)

    result = _select(
        "E",
        r,
        [r, composite],
        [r, composite, l1],
        separation={"excludes_zero": False, "comparator": "L1"},
    )

    assert result["outcome"] == "no_structure_beat_the_incumbent"
    assert result["blocked_top_finalist"] == "R"
    assert result["selected"] == "L1", "§4.1 must decide regardless of where R ranks"
    assert result["tie_break"]["decided_by"] == "higher_worst_class_f1"
    assert result["separated_from_next"] is False


def test_two_eligible_candidates_without_a_separation_interval_is_refused():
    """§4 step 3 cannot be silently skipped: a caller that has two eligible
    candidates must supply the paired interval between them.
    """
    r = _r()
    a = _row("L1+W3 (= E composite)", 0.55, 0.34, distribution=True)
    b = _row("L1", 0.50, 0.31, distribution=True)

    with pytest.raises(ValueError, match="separation"):
        _select("E", r, [r, a], [r, a, b], separation=None)


def test_tiebreak_worst_class_f1_uses_a_tolerance_not_exact_float_equality():
    """A float-rounding difference (~1e-16) must not 'decide' criterion 1;
    it falls through to criterion 2, and the record says criterion 1 did
    not decide.
    """
    r = _r()
    a = _row("A", 0.60, 0.35, params=900)
    b = _row("B", 0.55, 0.35 + 1e-16, params=10)
    out = _apply_tie_break(a, b, r)
    assert out["record"]["decided_by"] == "fewer_fitted_parameters"
    assert out["winner"]["level"] == "B"
    assert out["record"]["criteria"][0]["decided"] is False

    # A genuinely meaningful difference still decides.
    a = _row("A", 0.60, 0.34)
    b = _row("B", 0.55, 0.35)
    out = _apply_tie_break(a, b, r)
    assert out["record"]["decided_by"] == "higher_worst_class_f1"
    assert out["winner"]["level"] == "B"


def test_tiebreak_records_a_missing_parameter_count_as_not_evaluable():
    """A `None` parameter count must not silently vanish: criterion 2 is
    recorded as not evaluable, and the decision falls to criterion 3.
    """
    r = _r()
    a = _row("L1+W3 (= E composite)", 0.60, 0.30, params=None)
    b = _row("L1", 0.55, 0.30, params=50)
    out = _apply_tie_break(a, b, r)
    criterion_2 = out["record"]["criteria"][1]
    assert criterion_2["criterion"] == "fewer_fitted_parameters"
    assert criterion_2["evaluable"] is False
    assert "not evaluable" in criterion_2["note"]
    # Falls through to criterion 3: L1 varies one axis, the composite two.
    assert out["record"]["decided_by"] == "closer_to_r"
    assert out["winner"]["level"] == "L1"


def test_axes_varied_from_r_raises_on_an_unknown_level():
    """A composite missing from `_COMPOSITE_AXES_VARIED` must fail loudly
    rather than silently counting as one axis (which could decide §4.1
    criterion 3 wrongly).
    """
    assert _axes_varied_from_r("R") == 0
    assert _axes_varied_from_r("L1") == 1
    assert _axes_varied_from_r("S2 (= L composite)") == 1
    assert _axes_varied_from_r("L1+W3 (= E composite)") == 2
    with pytest.raises(ValueError, match="unknown level"):
        _axes_varied_from_r("L1+W2+H1 (= future composite)")


def test_selection_record_carries_the_pool_with_its_numbers():
    """The ledger owes 'the rejected candidates with their numbers'; the
    selection record must be self-sufficient rather than a list of names to
    be joined against stage1.json by hand.
    """
    r = _r(macro_f1=0.4840, worst=0.3182)
    s2 = _row("S2", 0.4851, 0.2927, distribution=False)
    l1 = _row("L1", 0.4336, 0.2667, distribution=True)
    l2 = _row("L2", 0.4199, 0.2162, disqualified=True, distribution=True)

    result = _select("L", r, [r, s2], [r, s2, l1, l2])

    pool = {entry["level"]: entry for entry in result["pool"]}
    assert set(pool) == {"R", "S2", "L1", "L2"}
    assert pool["L2"]["disqualified_worst_class_floor"] is True
    assert pool["L2"]["eligible"] is False
    assert pool["S2"]["produces_three_class_distribution"] is False
    assert pool["L1"]["eligible"] is True
    assert pool["L1"]["macro_f1"] == 0.4336
    assert pool["L1"]["worst_class_f1"] == 0.2667
    # Ranked by macro-F1, descending.
    assert [e["level"] for e in result["pool"]] == ["S2", "R", "L1", "L2"]


def test_cross_target_floor_failure_is_distinguished_in_the_pool():
    r = _r()
    ok_here = _row("P3", 0.52, 0.30, distribution=False)  # passes floor on this target
    l1 = _row("L1", 0.50, 0.31, distribution=True)

    result = _select(
        "E", r, [r], [r, ok_here, l1], cross_target_disqualified=frozenset({"P3"})
    )

    pool = {entry["level"]: entry for entry in result["pool"]}
    assert pool["P3"]["disqualified_worst_class_floor"] is False
    assert pool["P3"]["disqualified_by_other_target_floor"] is True
    assert pool["P3"]["eligible"] is False


def test_tiebreak_exhausted_is_recorded_as_unresolved_not_as_a_decision():
    r = _r()
    a = _row("W2", 0.60, 0.30, params=10)
    b = _row("W3", 0.55, 0.30, params=10)  # both stage-1 levels: 1 axis each
    out = _apply_tie_break(a, b, r)
    assert out["record"]["decided_by"] == "exhausted_tie_break"
    assert "unresolved tie" in out["note"]


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
    # §4 step 3 with no runner-up is "not applicable", never "fails".
    assert "fails" not in result["note"]


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
