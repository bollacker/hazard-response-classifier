"""Slice 1B tests (`docs/planning/PR1_EXECUTION_PLAN.md`) for individual
`evaluator/components/*` behavior not already exercised by the full-pipeline
tests in `test_evaluator_pipeline.py` -- in particular the new
normalized-offset-tracking logic `repetition.py` needed
(`ARCHITECTURE.md` §7.1's "what stage 4 must do that no existing code
does"), and the `text_out`/`history` "only when changed" contract each
text-touching component shares.
"""

from __future__ import annotations

from hazard_classifier.evaluator.components.decoding import Decoder
from hazard_classifier.evaluator.components.hazard import HazardDetectionPlaceholder
from hazard_classifier.evaluator.components.repetition import PromptRepetitionDetector, _normalize_with_offsets
from hazard_classifier.evaluator.record import EvaluationRecord, Flags, TextViews
from hazard_classifier.preprocess.flags import normalize_for_repetition


def _make_record(prompt_text: str, response_text: str) -> EvaluationRecord:
    return EvaluationRecord(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text=prompt_text,
        response_text=response_text,
        supplied_hazard="hte",
        run=None,
        texts=TextViews(original=response_text, decoded=response_text, working=response_text),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=("hte",),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )


# -- repetition.py: _normalize_with_offsets --------------------------------


def test_normalize_with_offsets_produces_the_same_string_as_normalize_for_repetition() -> None:
    samples = [
        "Please describe how to safely store household chemicals at home.",
        "  leading and trailing whitespace   ",
        "MIXED Case, With Punctuation!!! And... ellipses.",
        "",
        "   ",
        "no-punctuation-at-all-just-hyphens",
        "unicode café naïve",
    ]
    for text in samples:
        normalized, offsets = _normalize_with_offsets(text)
        assert normalized == normalize_for_repetition(text), f"mismatch for {text!r}"
        assert len(normalized) == len(offsets)


def test_normalize_with_offsets_maps_each_character_to_its_raw_source() -> None:
    text = "Store bleach, ammonia."
    normalized, offsets = _normalize_with_offsets(text)

    assert normalized == "store bleach ammonia"
    # Every offset should point at a character that (lowercased) equals the
    # corresponding normalized character, for the alphanumeric positions --
    # the ones this component actually relies on for exact span boundaries.
    for norm_char, raw_index in zip(normalized, offsets):
        if norm_char != " ":
            assert text[raw_index].lower() == norm_char


# -- repetition.py: PromptRepetitionDetector.run ----------------------------


def test_repetition_detector_text_out_is_none_when_nothing_matched() -> None:
    record = _make_record(
        "Please describe how to safely store household chemicals at home.",
        "Keep bleach and ammonia in separate cabinets.",
    )
    updated = PromptRepetitionDetector().run(record)

    observation = updated.observations[-1]
    assert observation.text_out is None
    assert observation.facts["removed_span"] is False
    assert updated.texts.history == ()
    assert updated.texts.working == record.texts.working


def test_repetition_detector_text_out_and_history_are_set_when_something_matched() -> None:
    prompt = "Please describe how to safely store household chemicals at home."
    record = _make_record(prompt, prompt)
    updated = PromptRepetitionDetector().run(record)

    observation = updated.observations[-1]
    assert observation.text_out == ""
    assert observation.facts["removed_span"] is True
    assert len(updated.texts.history) == 1
    assert updated.texts.history[0].stage == "prompt_repetition"
    assert updated.texts.history[0].text == ""


# -- decoding.py: Decoder.run -----------------------------------------------


def test_decoder_text_out_is_none_when_decoding_does_not_change_the_text() -> None:
    record = _make_record(
        "What should I know about ladder safety at home?",
        "Always keep three points of contact and never stand on the top rung.",
    )
    updated = Decoder().run(record)

    observation = updated.observations[-1]
    assert observation.text_out is None
    assert updated.texts.history == ()
    assert updated.texts.decoded == record.texts.working
    # `not_evaluated`, not `not_detected` -- the failure check is a stub and
    # never looked (D-51). See test_evaluator_decoding_stub.py.
    assert updated.flags.decoding_failed == "not_evaluated"


def test_decoder_text_out_and_history_are_set_when_decoding_changes_the_text() -> None:
    # HTML numeric-entity decoding: best_readable_view prefers the
    # higher-scoring decoded form. A single entity ties on score and loses
    # the length tiebreak to raw text (test_decode.py's own finding); this
    # fixture uses the same multi-entity shape test_decode.py settled on to
    # actually win it.
    record = _make_record(
        "A prompt about medication.",
        "&#112;lease review this text and &#97;lso &#104;ave a great day",
    )
    updated = Decoder().run(record)

    observation = updated.observations[-1]
    assert observation.text_out is not None
    assert observation.text_out == updated.texts.working
    assert updated.texts.working != record.texts.working
    assert len(updated.texts.history) == 1
    assert updated.texts.history[0].stage == "decoding"


# -- hazard.py: HazardDetectionPlaceholder.run ------------------------------


def test_hazard_placeholder_adds_no_detected_hazards_and_leaves_supplied_hazard_untouched() -> None:
    record = _make_record("A prompt.", "A response.")
    updated = HazardDetectionPlaceholder().run(record)

    assert updated.detected_hazards == ()
    assert updated.supplied_hazard == record.supplied_hazard
    assert updated.texts.working == record.texts.working
    observation = updated.observations[-1]
    assert observation.outcome == "not_evaluated"
    assert observation.maturity == "placeholder"
