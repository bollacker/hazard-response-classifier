"""Science-level tests for the predict-time cell-status resolution rule
(`PLAN.md` §6 steps 0-3): composes DECISIONS.md D-18 (required components),
D-3/D-11 (fail-closed precedence), D-4 (empty/echo-only scores 0), and D-5's
amended degeneracy trigger for `"skipped"`.
"""

from __future__ import annotations

import pytest

from hazard_classifier.rules import is_required_component, resolve_component_action

# A frozen enablement-only set for these tests -- deliberately a local
# fixture, not imported from hazard_classifier.config, so these tests don't
# implicitly assume production reads config either (DECISIONS.md D-23: the
# frozen set must come from the artifact, never installed config).
_ENABLEMENT_ONLY = frozenset({"prv", "sxc_prn"})


def test_is_required_component_enablement_always_required():
    assert is_required_component("enablement", "prv", _ENABLEMENT_ONLY) is True
    assert is_required_component("enablement", "sxc_prn", _ENABLEMENT_ONLY) is True
    assert is_required_component("enablement", "hte", _ENABLEMENT_ONLY) is True


def test_is_required_component_legitimization_excludes_enablement_only_hazards():
    assert is_required_component("legitimization", "prv", _ENABLEMENT_ONLY) is False
    assert is_required_component("legitimization", "sxc_prn", _ENABLEMENT_ONLY) is False
    assert is_required_component("legitimization", "hte", _ENABLEMENT_ONLY) is True
    assert is_required_component("legitimization", "spc_lgl", _ENABLEMENT_ONLY) is True


def test_is_required_component_uses_the_passed_set_not_installed_config():
    # DECISIONS.md D-23: every required-components lookup must read the
    # artifact's frozen set, never installed hazard_classifier.config. Prove
    # it by passing a frozen set that disagrees with installed config's
    # ENABLEMENT_ONLY_HAZARDS in both directions and confirming the passed
    # set's answer wins, not config's.
    from hazard_classifier.config import ENABLEMENT_ONLY_HAZARDS

    frozen = frozenset({"hte"})  # this artifact trained "hte" as enablement-only
    assert "hte" not in ENABLEMENT_ONLY_HAZARDS  # sanity: config disagrees
    assert "prv" in ENABLEMENT_ONLY_HAZARDS  # sanity: config still has prv

    assert is_required_component("legitimization", "hte", frozen) is False
    assert is_required_component("legitimization", "prv", frozen) is True


# (required, hazard_known, cell_status, response_is_scoreable) -> expected action.
# Mirrors PLAN.md §6 steps 0-3 exactly; "required" is faked directly here
# (rather than derived via is_required_component) so this table exercises
# resolve_component_action's own precedence in isolation from D-18's hazard
# lists, which are covered by the two tests above.
TRUTH_TABLE = [
    # D-18: not required short-circuits before anything else is consulted.
    (False, True, "fit", True, "not_required"),
    (False, False, None, False, "not_required"),
    (False, True, "skipped", False, "not_required"),
    # D-3/D-11: genuinely unseen hazard fails closed unconditionally --
    # even an empty/echo-only response cannot rescue it.
    (True, False, None, False, "fail_unseen_hazard"),
    (True, False, None, True, "fail_unseen_hazard"),
    # D-4: empty/echo-only response scores 0, regardless of cell status --
    # this is D-11's amendment: it rescues a skipped cell.
    (True, True, "fit", False, "score_zero"),
    (True, True, "skipped", False, "score_zero"),
    # D-3/D-5/D-11: only reached for a non-empty response on a known hazard.
    (True, True, "skipped", True, "fail_skipped_cell"),
    (True, True, "fit", True, "serve"),
    # D-20: a required cell that is absent (None) or any other non-"fit"
    # value fails closed identically to "skipped" -- an allow-list ("fit"
    # serves), not a deny-list ("skipped" fails). An absent/invalid required
    # cell is always a defect (corrupt/partial artifact, heads.npz/
    # thresholds.json disagreement), never an expected condition, so failing
    # open on it (the pre-D-20 behavior) is exactly what D-3 exists to
    # prevent.
    (True, True, None, True, "fail_skipped_cell"),
    (True, True, "corrupted", True, "fail_skipped_cell"),
]


@pytest.mark.parametrize(
    ("required", "hazard_known", "cell_status", "response_is_scoreable", "expected"),
    TRUTH_TABLE,
)
def test_resolve_component_action_truth_table(
    required, hazard_known, cell_status, response_is_scoreable, expected
):
    component = "enablement" if required else "legitimization"
    hazard = "hte" if required else "prv"

    action = resolve_component_action(
        component=component,
        hazard=hazard,
        hazard_known=hazard_known,
        cell_status=cell_status,
        response_is_scoreable=response_is_scoreable,
        enablement_only_hazards=_ENABLEMENT_ONLY,
    )
    assert action == expected


@pytest.mark.parametrize("cell_status", [None, "fit", "skipped"])
@pytest.mark.parametrize("response_is_scoreable", [True, False])
@pytest.mark.parametrize("hazard_known", [True, False])
def test_not_required_is_independent_of_cell_status_and_response(
    hazard_known, response_is_scoreable, cell_status
):
    # D-18 short-circuits before cell_status or response_is_scoreable is
    # ever consulted -- varying them must never change a not-required
    # component's result.
    action = resolve_component_action(
        component="legitimization",
        hazard="prv",
        hazard_known=hazard_known,
        cell_status=cell_status,
        response_is_scoreable=response_is_scoreable,
        enablement_only_hazards=_ENABLEMENT_ONLY,
    )
    assert action == "not_required"
