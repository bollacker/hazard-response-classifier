"""Shared argparse pieces and error handling for the three CLIs
(`DECISIONS.md` D-35) -- kept here once rather than duplicated per command.
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn


def add_allow_download_flag(parser: argparse.ArgumentParser) -> None:
    """`PLAN.md` §3/§5/§6: every CLI is offline by default (no BGE weight
    download); `--allow-download` opts in. Identical across all three, so
    added here once rather than three separately-worded `add_argument` calls.
    """
    parser.add_argument(
        "--allow-download",
        action="store_true",
        default=False,
        help="Allow downloading BGE model weights not already cached (default: offline only).",
    )


def fatal(message: str) -> NoReturn:
    """Print a clean, single-line error to stderr and exit(1) -- used for
    expected domain errors (`SchemaError`, `WhollySkippedEnablementError`,
    `BlankGroundTruthError`) so a user sees a plain message instead of a
    raw Python traceback for a condition the code already has a name for.
    """
    print(message, file=sys.stderr)
    raise SystemExit(1)


def warn_if_skipped_components(classifier) -> None:
    """`PLAN.md` §5/§6's load-time up-front warning (`DECISIONS.md` D-28):
    if any component is wholly skipped, name it and which hazard families
    it makes unscoreable. A skipped Legitimization leaves only
    enablement-only hazards fully scoreable; a skipped Enablement would
    have hard-failed at train time (`WhollySkippedEnablementError`), so a
    loaded artifact should never actually have one here -- handled
    defensively, not because it's expected to fire.

    Warn-and-continue only, never raises: affected rows still route to
    `hrc-predict`'s failures output / `hrc-evaluate`'s excluded-row count
    per row, as D-28 requires.
    """
    for component in classifier.skipped_components:
        if component == "legitimization":
            print(
                "WARNING: this artifact's Legitimization component is wholly skipped "
                "(DECISIONS.md D-28) -- only enablement-only hazards "
                f"({sorted(classifier.enablement_only_hazards)}) have a usable score for "
                "every hazard; every other hazard's Legitimization score will fail closed.",
                file=sys.stderr,
            )
        else:
            print(
                f"WARNING: this artifact's {component} component is wholly skipped "
                "(DECISIONS.md D-28) -- this should never happen for enablement (a "
                "wholly-skipped Enablement hard-fails at train time), so this artifact "
                "may be corrupt or hand-edited.",
                file=sys.stderr,
            )
