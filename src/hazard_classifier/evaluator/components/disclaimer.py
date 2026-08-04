"""Stage 7: disclaimer detection (`docs/ARCHITECTURE.md` §7, §5;
`docs/SCIENCE.md` §Disclaimer detection). Partial: wraps the baseline's
`preprocess/flags.py` disclaimer patterns, but -- per `ARCHITECTURE.md` §5's
resolution of C-4 -- publishes the stripped variant as
`named["disclaimer_stripped"]` rather than removing it from `working`.
`working` is left intact deliberately: which view the E model actually
consumes is an open empirical question (C-4, `ARCHITECTURE.md` §12), to be
settled by evaluation on fixed human-labeled data, not decided here. This
is why the component is `"partial"`, not `"working"`: `SCIENCE.md`'s
disclaimer-detection success criterion describes a component that removes
disclaimer text from the text going forward, which this one does not do to
the default `working` view.
"""

from __future__ import annotations

import dataclasses
import re
from typing import ClassVar

from hazard_classifier.preprocess.flags import DISCLAIMER_PATTERNS

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord

_WHITESPACE_RE = re.compile(r"\s+")


def _strip_disclaimers(text: str) -> tuple[str, list[str]]:
    """Find every `DISCLAIMER_PATTERNS` match in `text` and return the text
    with those spans removed, plus the pattern names that matched.
    Overlapping matches (a later pattern's match starting inside an
    already-removed span) are skipped rather than double-counted or
    produce an out-of-order removal.
    """
    spans_and_reasons = sorted(
        (match.span(), name)
        for name, pattern in DISCLAIMER_PATTERNS
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
    version: ClassVar[str] = "1"
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
            error=None,
        )

        return dataclasses.replace(
            record,
            texts=new_texts,
            flags=dataclasses.replace(record.flags, sa_disclaimer=("detected" if detected else "not_detected")),
            observations=record.observations + (observation,),
        )
