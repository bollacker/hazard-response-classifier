"""Tests for `hazard_classifier.cli._common` (`DECISIONS.md` D-35) --
`fatal` and `warn_if_skipped_components`, tested directly rather than only
indirectly through a full CLI run, since neither needs argparse or a real
fitted classifier to exercise.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hazard_classifier.cli._common import fatal, warn_if_skipped_components


def test_fatal_prints_message_to_stderr_and_exits_1(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        fatal("boom")

    assert exc_info.value.code == 1
    assert "boom" in capsys.readouterr().err


def test_warn_if_skipped_components_is_silent_when_none_skipped(capsys) -> None:
    classifier = SimpleNamespace(skipped_components=[], enablement_only_hazards=frozenset())

    warn_if_skipped_components(classifier)

    assert capsys.readouterr().err == ""


def test_warn_if_skipped_components_names_legitimization_and_the_still_usable_hazards(capsys) -> None:
    classifier = SimpleNamespace(
        skipped_components=["legitimization"], enablement_only_hazards=frozenset({"prv", "sxc_prn"})
    )

    warn_if_skipped_components(classifier)

    err = capsys.readouterr().err
    assert "Legitimization" in err
    assert "prv" in err and "sxc_prn" in err


def test_warn_if_skipped_components_handles_enablement_defensively(capsys) -> None:
    """`DECISIONS.md` D-28: a wholly-skipped Enablement should have
    hard-failed at train time (`WhollySkippedEnablementError`), so a loaded
    artifact should never actually reach this branch -- exercised anyway
    since the function must not crash if it somehow does.
    """
    classifier = SimpleNamespace(skipped_components=["enablement"], enablement_only_hazards=frozenset())

    warn_if_skipped_components(classifier)

    assert "enablement" in capsys.readouterr().err
