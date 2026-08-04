"""Stage 4: prompt-repetition detection (`docs/ARCHITECTURE.md` §7.1,
`docs/SCIENCE.md` §Prompt-repetition detection). Partial: only the two
EXACT normalized-substring cases from `preprocess/flags.py`'s
`prompt_repetition_features` (`verbatim_or_decoded`,
`prompt_plus_continuation`) -- not `partial_contiguous`, a similarity
heuristic that is neither exact matching nor the summarized/paraphrased
detection the standard eventually wants (§7.1's recorded gap).

Unlike the baseline (which only flags a segment for pooling and never
removes anything), this component actually removes the matched span from
`TextViews.working`, preserving whatever authored content surrounds it --
"what stage 4 must do that no existing code does" (§7.1).
"""

from __future__ import annotations

import dataclasses
import re
from typing import ClassVar

from hazard_classifier.preprocess.decode import normalize_unicode
from hazard_classifier.preprocess.flags import normalize_for_repetition

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord, TextStep

_ALNUM_RE = re.compile(r"[a-z0-9]")
_WHITESPACE_RE = re.compile(r"\s+")

# Mirrors prompt_repetition_features's own `len(segment_norm) < 12` guard
# against matching on trivially short, coincidental overlaps.
_MIN_MATCH_LENGTH = 12


def _normalize_with_offsets(text: str) -> tuple[str, list[int]]:
    """Like `preprocess.flags.normalize_for_repetition` (lowercase, collapse
    non-alphanumeric runs to a single space, strip), but also returns a
    list mapping each character of the normalized string back to the raw
    index in `text` it came from. `normalize_for_repetition` alone is
    enough to *detect* a match; translating a normalized match span back
    into raw offsets -- needed to remove only the matched span and keep the
    rest -- needs this. Not part of the baseline, which never had to remove
    anything (`DECISIONS.md` D-4 only ever drops a segment wholesale from
    pooling).

    A matched span's start and end always land on an actual alphanumeric
    character (`prompt_norm` never starts or ends with the normalized
    space that represents a collapsed run, since `normalize_for_repetition`
    strips it), so the span's raw boundaries from this offset list alone
    are exact at both ends -- with one exception the caller handles: any
    non-alphanumeric raw characters trailing immediately *after* the match
    (e.g. the period ending a copied prompt sentence) aren't covered by
    this offset list at all, since they normalize away to nothing or get
    absorbed into the *next* token's boundary space. The caller extends
    past them explicitly.
    """
    lowered = normalize_unicode(text).lower()
    normalized_chars: list[str] = []
    offsets: list[int] = []
    previous_was_space = True  # collapses a leading non-alnum run, matching normalize_for_repetition's .strip()

    for index, ch in enumerate(lowered):
        if _ALNUM_RE.fullmatch(ch):
            normalized_chars.append(ch)
            offsets.append(index)
            previous_was_space = False
        elif not previous_was_space:
            normalized_chars.append(" ")
            offsets.append(index)
            previous_was_space = True

    while normalized_chars and normalized_chars[-1] == " ":
        normalized_chars.pop()
        offsets.pop()

    return "".join(normalized_chars), offsets


def _detect_and_remove(working: str, prompt: str) -> tuple[str, bool]:
    """Apply the two exact cases to the whole `working` text as a single
    unit (unlike the baseline, which applies them per sentence-level
    segment -- stage 4 operates on `TextViews.working` directly, not the
    baseline's internal sentence list). Returns `(new_working, detected)`.
    """
    working_norm, working_offsets = _normalize_with_offsets(working)
    prompt_norm = normalize_for_repetition(prompt)

    if not prompt_norm or not working_norm or len(working_norm) < _MIN_MATCH_LENGTH:
        return working, False

    if working_norm in prompt_norm:
        # The whole response is contained in the prompt: verbatim_or_decoded.
        return "", True

    if len(prompt_norm) >= _MIN_MATCH_LENGTH and prompt_norm in working_norm:
        # prompt_plus_continuation: remove only the matched span, keeping
        # whatever authored content surrounds it.
        match_start = working_norm.index(prompt_norm)
        match_end = match_start + len(prompt_norm) - 1
        raw_start = working_offsets[match_start]
        raw_end = working_offsets[match_end] + 1
        # Consume any trailing punctuation/whitespace run immediately after
        # the match too (e.g. the period ending a copied prompt sentence) --
        # it belongs to the matched clause, not the authored continuation,
        # and the offset list itself has no entry for it (see
        # _normalize_with_offsets's docstring).
        while raw_end < len(working) and not _ALNUM_RE.fullmatch(working[raw_end].lower()):
            raw_end += 1
        remainder = working[:raw_start] + " " + working[raw_end:]
        remainder = _WHITESPACE_RE.sub(" ", remainder).strip()
        return remainder, True

    return working, False


class PromptRepetitionDetector:
    stage: ClassVar[str] = "prompt_repetition"
    implementation: ClassVar[str] = "exact_normalized_substring"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "partial"

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        working = record.texts.working
        new_working, detected = _detect_and_remove(working, record.prompt_text)
        changed = new_working != working

        new_history = record.texts.history
        if changed:
            new_history = new_history + (TextStep(stage=self.stage, text=new_working),)
        new_texts = dataclasses.replace(record.texts, working=new_working, history=new_history)

        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={"removed_span": detected},
            text_out=new_working if changed else None,
            error=None,
        )

        return dataclasses.replace(
            record,
            texts=new_texts,
            flags=dataclasses.replace(
                record.flags, prompt_repetition=("detected" if detected else "not_detected")
            ),
            observations=record.observations + (observation,),
        )
