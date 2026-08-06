"""Stage 7: disclaimer detection (`docs/ARCHITECTURE.md` §7 row 7 and §7.2,
§5; `docs/SCIENCE.md` §Disclaimer detection). Wraps the baseline's
`preprocess/flags.py` disclaimer patterns -- **three of the four**, per
`ARCHITECTURE.md` §7.2 (`docs/planning/DECISIONS.md` D-70) -- and publishes
the stripped variant as `named["disclaimer_stripped"]` rather than removing
it from `working`.

**Why this component is `partial`**, all three reasons (`ARCHITECTURE.md`
§7.2, which carries them because §7's table has room only for a pointer):

1. It does not remove disclaimer text from `working`. `SCIENCE.md`'s
   success criterion requires removal; 1.1 publishes the stripped view
   alongside instead, while the comparison that would settle which view the
   models should read stays deferred (D-55). `working` is left intact
   deliberately -- that is an open empirical question (C-4), to be settled
   on fixed human-labeled data, not decided here.
2. Two `SCIENCE.md` qualifying forms are unimplemented: risk warnings (see
   the exclusion below), and `spc_ele`'s link to an official source, which
   no inherited pattern implements at all.
3. **Precision is unmeasured and unmeasurable in 1.1** -- no human
   disclaimer labels exist anywhere. D-70's figures are dev-set-class
   numbers on out-of-version labels (D-63, D-66) and support no quality
   claim in either direction.

The residual risk has a direction worth stating: phase C is
one-directional, so a false positive here can only move a Specialized
Advice row toward non-violating -- it hides a violation rather than
inventing one.
"""

from __future__ import annotations

import dataclasses
import re
from typing import ClassVar

from hazard_classifier.preprocess.flags import DISCLAIMER_PATTERNS

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord

_WHITESPACE_RE = re.compile(r"\s+")

# `ARCHITECTURE.md` §7.2, locked as `docs/planning/DECISIONS.md` D-70. The
# 1.1 component selects a subset of the shared baseline patterns **by
# name**; it never edits `DISCLAIMER_PATTERNS`, which the baseline still
# scores with in full and unchanged (D-48). This mirrors what
# `repetition.py` does for stage 4's two exact paths (§7.1).
RELEASE_1_1_PATTERN_NAMES = (
    "professional_referral",
    "uncertainty_warning",
    "verify_or_check",
)

# **Excluded: `safety_warning`.** It matches bare risk vocabulary -- `risk`,
# `harm`, `safety`, `unsafe`, `danger` -- anywhere in a response, with no
# disclaimer context required. `SCIENCE.md`'s "warns about risks" qualifying
# form describes a *disclaimer*, not any mention of risk, so the pattern
# does not implement the form it appears to serve. This is §7.1's reasoning
# applied to a second component. The measurement is D-70's and is
# reproducible via `scripts/probe_disclaimer_scope.py`: on 217 Specialized
# Advice rows it nearly doubles the flag rate (46 -> 88) while the rows it
# alone adds show no enrichment in human L0 over rows nothing flags, all
# eleven rows where it alone changes a result are false positives on
# inspection, and its apparent signal comes from refusals explaining
# themselves in risk vocabulary -- in a release that ships no refusal
# detector by deliberate choice (D-54).
#
# `verify_or_check` is retained despite being inert on current data (0 hits
# on those 217 rows, 2 on all 859): it implements a qualifying form
# correctly and finding nothing is not the same defect as matching the
# wrong thing.
EXCLUDED_PATTERN_NAMES = ("safety_warning",)


def _select_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Resolve `RELEASE_1_1_PATTERN_NAMES` against the shared baseline
    module, at import time.

    Selection is by name so a rename or removal in `preprocess/flags.py`
    raises here instead of silently shipping a smaller pattern set -- a
    component quietly detecting less is exactly the "runs, returns results,
    and looks healthy" failure D-70 was found by looking for.
    """
    by_name = dict(DISCLAIMER_PATTERNS)
    missing = [name for name in RELEASE_1_1_PATTERN_NAMES if name not in by_name]
    if missing:
        raise RuntimeError(
            f"disclaimer patterns {missing!r} are no longer in "
            "preprocess.flags.DISCLAIMER_PATTERNS; ARCHITECTURE.md §7.2 names them "
            "as the Release 1.1 set, so this is a specification conflict, not a "
            "rename to absorb silently"
        )
    return tuple((name, by_name[name]) for name in RELEASE_1_1_PATTERN_NAMES)


RELEASE_1_1_PATTERNS = _select_patterns()


def _strip_disclaimers(text: str) -> tuple[str, list[str]]:
    """Find every `RELEASE_1_1_PATTERNS` match in `text` and return the text
    with those spans removed, plus the pattern names that matched.
    Overlapping matches (a later pattern's match starting inside an
    already-removed span) are skipped rather than double-counted or
    produce an out-of-order removal.

    Scans the **selected** subset, not all of `DISCLAIMER_PATTERNS` -- see
    the module docstring and D-70.
    """
    spans_and_reasons = sorted(
        (match.span(), name)
        for name, pattern in RELEASE_1_1_PATTERNS
        for match in pattern.finditer(text)
    )

    if not spans_and_reasons:
        return text, []

    pieces: list[str] = []
    reasons: list[str] = []
    cursor = 0
    for (start, end), name in spans_and_reasons:
        if start < cursor:
            continue  # overlaps a span already removed
        pieces.append(text[cursor:start])
        reasons.append(name)
        cursor = end
    pieces.append(text[cursor:])

    stripped = _WHITESPACE_RE.sub(" ", " ".join(pieces)).strip()
    return stripped, reasons


class DisclaimerDetector:
    stage: ClassVar[str] = "disclaimer_detection"
    implementation: ClassVar[str] = "baseline_disclaimer_patterns"
    # Bumped 1 -> 2 when D-70 narrowed the pattern set to three. This is an
    # identified scoring change, and `version` is what `RunContext.
    # component_selections` records so "a result names the exact
    # implementations that produced it" (§6) stays true across it --
    # otherwise records made before and after the narrowing are
    # indistinguishable in their own provenance. The **implementation id is
    # deliberately unchanged**: this is one implementation that changed, not
    # a second co-existing one, and other documents cite the id.
    version: ClassVar[str] = "2"
    maturity: ClassVar[Maturity] = "partial"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        working = record.texts.working
        stripped, reasons = _strip_disclaimers(working)
        detected = bool(reasons)

        new_named = dict(record.texts.named)
        new_named["disclaimer_stripped"] = stripped
        # `working` is deliberately left unchanged -- see the module docstring.
        new_texts = dataclasses.replace(record.texts, named=new_named)

        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={"matched_patterns": sorted(set(reasons))},
            text_out=None,
            errors=(),
        )

        return dataclasses.replace(
            record,
            texts=new_texts,
            flags=dataclasses.replace(record.flags, sa_disclaimer=("detected" if detected else "not_detected")),
            observations=record.observations + (observation,),
        )
