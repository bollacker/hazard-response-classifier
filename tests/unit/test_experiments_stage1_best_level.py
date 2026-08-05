"""Tests for `scripts/run_stage1_sweep.py`'s `best_level_per_axis` -- the
informational triage that names the stage-2 composite's per-axis
construction levels.

The load-bearing property: §3's worst-class floor carries its cross-target
scope here too (`PREREGISTRATION_LE_STRUCTURE.md` §8, 2026-08-05). A level
failing the floor on *either* target must not be named best-of-axis on
*either* -- otherwise the stage-2 composite could be built from a structure
the selection rule has already disqualified.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

from run_stage1_sweep import best_level_per_axis  # noqa: E402


def _row(level, target, axis, macro_f1, *, disqualified=False):
    return {
        "level": level,
        "target": target,
        "axis": axis,
        "macro_f1": macro_f1,
        "disqualified_worst_class_floor": disqualified,
    }


def test_best_level_wins_its_axis_when_it_beats_r():
    results = [
        _row("R", "L", None, 0.48),
        _row("R", "E", None, 0.52),
        _row("P2", "L", "Pooling", 0.50),
        _row("P2", "E", "Pooling", 0.54),
    ]
    best = best_level_per_axis(results)
    assert best["L"]["Pooling"] == "P2"
    assert best["E"]["Pooling"] == "P2"


def test_r_wins_an_axis_whose_levels_all_score_below_it():
    results = [
        _row("R", "L", None, 0.48),
        _row("R", "E", None, 0.52),
        _row("P2", "L", "Pooling", 0.40),
        _row("P2", "E", "Pooling", 0.41),
    ]
    best = best_level_per_axis(results)
    assert best["L"]["Pooling"] == "R"
    assert best["E"]["Pooling"] == "R"


def test_own_target_floor_failure_cannot_be_best_of_axis():
    results = [
        _row("R", "L", None, 0.48),
        _row("R", "E", None, 0.52),
        # Tops the axis on macro but fails the floor on this same target.
        _row("P2", "L", "Pooling", 0.55, disqualified=True),
        _row("P2", "E", "Pooling", 0.55, disqualified=True),
    ]
    best = best_level_per_axis(results)
    assert best["L"]["Pooling"] == "R"
    assert best["E"]["Pooling"] == "R"


def test_cross_target_floor_failure_cannot_be_best_of_axis_on_the_other_target():
    """The case the first implementation got wrong: P3 passes the floor on E
    and would top E's Pooling axis on macro-F1, but it fails the floor on L
    -- so under §3's 'on either target' scope it is disqualified on both,
    and must not seed E's composite either.
    """
    results = [
        _row("R", "L", None, 0.48),
        _row("R", "E", None, 0.52),
        _row("P3", "L", "Pooling", 0.45, disqualified=True),  # fails floor on L
        _row("P3", "E", "Pooling", 0.60, disqualified=False),  # tops E on macro
        _row("P2", "E", "Pooling", 0.53, disqualified=False),
        _row("P2", "L", "Pooling", 0.40, disqualified=False),
    ]
    best = best_level_per_axis(results)
    assert best["E"]["Pooling"] == "P2", "P3 is floor-failed on L, so excluded on E too"
    assert best["L"]["Pooling"] == "R"
