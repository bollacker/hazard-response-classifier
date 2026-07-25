"""Tests for `hazard_classifier.preprocess.flags` (`VERIFICATION.md` IS-2).

The three `prompt_repetition_features`/`later_authored_continuation` cases
are ported from the toy's own asserts
(`security-evaluator/code/test_reviewable_sentence_segments.py`).
"""

from __future__ import annotations

from hazard_classifier.preprocess import decode, segment
from hazard_classifier.preprocess.flags import (
    disclaimer_label,
    later_authored_continuation,
    prompt_repetition_features,
    wrapper_label,
)


def test_prompt_repetition_features_are_span_local() -> None:
    prompt = "Describe the blue garden plan."
    segment_text_value = "Describe the blue garden plan."
    features = prompt_repetition_features(segment_text_value, prompt, 10, 40)
    assert features["prompt_repetition_type"] == "verbatim_or_decoded"
    assert features["prompt_repetition_probability"] == 1.0
    assert features["prompt_repetition_response_span"] == "10:40"


def test_prompt_repetition_plus_later_authored_text_is_preserved() -> None:
    prompt = "Describe the blue garden plan."
    segment_text_value = "Describe the blue garden plan because this is a good idea."
    features = prompt_repetition_features(segment_text_value, prompt, 0, len(segment_text_value))
    assert features["prompt_repetition_type"] == "prompt_plus_continuation"
    assert later_authored_continuation(segment_text_value, prompt)


def test_topical_overlap_is_not_prompt_repetition() -> None:
    prompt = "People may get hurt if they jump from a dangerous height."
    segment_text_value = (
        '"but i want you to know that in order to be my friend, '
        'if i jump then you have to do it too"'
    )
    features = prompt_repetition_features(segment_text_value, prompt, 0, len(segment_text_value))
    assert features["prompt_repetition_probability"] == 0.0
    assert features["prompt_repetition_type"] == ""


def test_wrapper_label_flags_role_markers() -> None:
    is_wrapper, reason = wrapper_label("System: you are a helpful assistant.")
    assert is_wrapper
    assert "role_marker" in reason


def test_wrapper_label_false_for_ordinary_response_text() -> None:
    is_wrapper, reason = wrapper_label("Municipal bonds are generally tax-exempt at the federal level.")
    assert not is_wrapper
    assert reason == ""


def test_disclaimer_label_flags_professional_referral() -> None:
    has_disclaimer, reason = disclaimer_label(
        "You should consult a qualified financial advisor before making this decision."
    )
    assert has_disclaimer
    assert "professional_referral" in reason


def test_disclaimer_label_false_for_ordinary_response_text() -> None:
    has_disclaimer, reason = disclaimer_label("Municipal bonds are generally tax-exempt.")
    assert not has_disclaimer
    assert reason == ""


def test_decode_segment_and_flags_compose_like_the_toys_build_segments() -> None:
    """Reproduces the toy's `build_segments` row-building
    (`test_build_segments_writes_prompt_repetition_columns`) by hand,
    composing this slice's three modules directly -- there is no
    orchestration function in this codebase yet (that is embed.py's job,
    a later phase), so this proves the three pieces this slice *does* build
    compose correctly rather than only unit-testing them in isolation.
    """
    prompt_text = "Describe the blue garden plan."
    response_text = "Describe the blue garden plan because this is a good idea."

    prompt_readable = decode.best_readable_view(prompt_text, prompt_text)["review_text"]
    context = "\n\n".join([prompt_text, response_text])
    response_readable = decode.best_readable_view(response_text, context)["review_text"]

    segments = segment.segment_text(str(response_readable), max_chars=420, stride=210)
    assert len(segments) == 1

    piece = segments[0]
    repetition = prompt_repetition_features(piece.text, str(prompt_readable), piece.start, piece.end)
    is_prompt_repetition = float(repetition["prompt_repetition_probability"]) >= 0.5
    has_later_authored = is_prompt_repetition and later_authored_continuation(piece.text, str(prompt_readable))

    assert is_prompt_repetition
    assert repetition["prompt_repetition_type"] == "prompt_plus_continuation"
    assert has_later_authored
