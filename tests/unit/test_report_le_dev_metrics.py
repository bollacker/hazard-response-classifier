"""Tests for the two parts of PR 5 slice D's report that carry a judgment
rather than a number (`docs/planning/PR5_EXECUTION_PLAN.md` §8).

`scripts/report_le_dev_metrics.py` is mostly a driver, and this project does
not unit-test drivers. Two things in it are not driving:

- **`_describe_outcomes`** writes prose *from* the figures, so that the
  report's reading of its own table cannot drift from the table on a re-run.
  Prose generated from data is still a claim, and a claim gets a test.
- **the degeneracy threshold** decides which per-hazard intervals are marked
  as not readable as uncertainty at all. Getting that backwards would leave
  the report inviting exactly the misreading it exists to prevent — a narrow
  interval taken for a precise one.

The metric functions themselves are tested in
`test_experiments_comparison_metrics.py`; the bootstrap they run through was
already tested there before this slice.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "report_le_dev_metrics.py"


def _load_script():
    """`scripts/` is a directory of scripts, not an importable package -- the
    same reason `tests/golden/capture_baseline.py` is run by path.
    """
    spec = importlib.util.spec_from_file_location("report_le_dev_metrics", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


report = _load_script()


def _interval(point: float) -> dict:
    return {"point_estimate": point, "ci_low": max(0.0, point - 0.1), "ci_high": point + 0.1}


def _block(outcomes, prefix="L") -> dict:
    return {
        "outcome_prefix": prefix,
        "per_outcome": [
            {
                "class": index,
                "support": support,
                "predicted": support,
                "precision": _interval(precision),
                "recall": _interval(recall),
                "f1": _interval(2 * precision * recall / (precision + recall)),
            }
            for index, (support, precision, recall) in enumerate(outcomes)
        ],
    }


def test_it_names_the_outcome_with_the_lowest_recall():
    """Lowest *recall*, not lowest F1: the question the report is answering
    is "which outcome does the model fail to find", and a class can have a
    middling F1 built from high precision and almost no recall.
    """
    block = _block([(100, 0.7, 0.8), (50, 0.4, 0.5), (45, 0.9, 0.2)])
    text = "\n".join(report._describe_outcomes(block))

    assert "L2 is the outcome the model finds least often" in text
    # 45 true rows at recall 0.2 -> about 9 found.
    assert "roughly 9 are labelled L2" in text


def test_it_says_which_way_the_asymmetry_runs():
    """F1 alone cannot distinguish under-claiming from over-claiming, which is
    the whole reason precision and recall are reported separately.
    """
    under = "\n".join(report._describe_outcomes(_block([(100, 0.7, 0.8), (45, 0.9, 0.2)])))
    assert "under-claims" in under
    assert "over-claims" not in under

    over = "\n".join(report._describe_outcomes(_block([(100, 0.7, 0.8), (45, 0.2, 0.9)])))
    assert "over-claims" in over
    assert "under-claims" not in over


def test_it_never_says_whether_the_numbers_are_good():
    """The report describes; approved criteria would judge, and there are
    none. A generated sentence is the easiest place for a quality claim to
    slip in unnoticed.
    """
    text = "\n".join(report._describe_outcomes(_block([(100, 0.7, 0.8), (45, 0.9, 0.2)])))

    assert "not a verdict" in text
    for word in ("good", "poor", "strong", "weak", "acceptable performance", "accurate enough"):
        assert word not in text.lower().replace("whether it is acceptable", "")


def test_the_prefix_follows_the_target():
    assert "E1" in "\n".join(
        report._describe_outcomes(_block([(100, 0.7, 0.8), (45, 0.9, 0.2)], prefix="E"))
    )


@pytest.mark.parametrize("n_groups,expected", [(1, True), (3, True), (9, True), (10, False), (48, False)])
def test_the_degeneracy_threshold_marks_small_group_counts(n_groups, expected):
    """The threshold itself, pinned so the marking cannot silently invert.
    With 3 groups a cluster bootstrap has ten distinct resamples in
    existence, so its "interval" is an enumeration, not an estimate.
    """
    assert (n_groups < report.MIN_GROUPS_FOR_A_MEANINGFUL_INTERVAL) is expected


def test_the_not_evaluated_statement_names_all_four_bounds():
    """It is the sentence that governs every figure in the report, so it must
    carry the data's limits rather than a bare disclaimer.
    """
    statement = report.NOT_EVALUATED
    assert "NOT EVALUATED" in statement
    for decision in ("D-66", "D-63", "D-65", "D-68"):
        assert decision in statement


def test_the_uncertainty_method_states_the_method_not_just_the_number():
    """`SCIENCE.md` §Evidence and outputs (Estimability) requires the method
    alongside the estimate, not only the interval.
    """
    method = report.UNCERTAINTY_METHOD
    assert "prompt_group_id" in method
    assert "groups rather than" in method  # groups, not rows
    assert "1000 resamples" in method
    assert "seed" in method
