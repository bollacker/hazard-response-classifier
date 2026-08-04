"""The decoding-failure stub (`DECISIONS.md` D-51).

`SCIENCE.md` §Decoding requires the decoder to raise a decoding-failure flag
and an error when it cannot render all substantive content. That trigger is
deliberately **not** built for 1.1: the decoder always returns a result, and
its worst case is the un-decoded text. These tests pin the stub's contract so
that (a) the shortfall is visible in the test suite rather than only in a
docstring, and (b) whoever builds the real trigger has a failing-first target
and a clear list of what must change with it.
"""

from __future__ import annotations

import inspect

from hazard_classifier.evaluator.components import decoding
from hazard_classifier.evaluator.components.decoding import Decoder, _detect_decoding_failure
from hazard_classifier.evaluator.record import EvaluationRecord, Flags, TextViews


def _record(prompt: str, response: str) -> EvaluationRecord:
    return EvaluationRecord(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text=prompt,
        response_text=response,
        supplied_hazard="hte",
        run=None,
        texts=TextViews(original=response, decoded=response, working=response),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=("hte",),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )


def test_the_failure_trigger_is_a_stub_that_always_reports_success() -> None:
    assert _detect_decoding_failure("anything at all", {}) is False
    assert _detect_decoding_failure("", {"transform_confidence": 0.0}) is False
    # Even against input designed to look undecodable.
    assert _detect_decoding_failure("\x00\x01\x02 ??? ###", {"review_english_score": 0.0}) is False


def test_the_stub_is_a_named_seam_with_the_signature_a_real_trigger_needs() -> None:
    """Guards against the stub being inlined away. A real trigger replaces
    this function's body; if the function stops existing, the replacement
    point and this test's target both vanish silently.
    """
    signature = inspect.signature(_detect_decoding_failure)
    assert list(signature.parameters) == ["decoded_text", "view"]


def test_decoding_failed_is_not_evaluated_never_not_detected() -> None:
    """The forcing function for D-51's honesty requirement. Writing
    `not_detected` would claim the component looked for a decoding failure
    and found none; it never looked. This is the same rule slice 1B pins for
    the narrative and refusal placeholders (`ARCHITECTURE.md` §3.1, §6).
    """
    updated = Decoder().run(_record("A prompt.", "A perfectly ordinary response."))

    assert updated.flags.decoding_failed == "not_evaluated"
    assert updated.flags.decoding_failed != "not_detected"


def test_the_decoder_reports_partial_maturity_while_the_trigger_is_stubbed() -> None:
    """`SCIENCE.md` §Decoding's success criterion has two halves and only one
    is built, so the component may not claim `working` (D-51). If someone
    builds the real trigger, this assertion is the reminder to promote it.
    """
    assert Decoder.maturity == "partial"


def test_the_stub_is_visible_in_the_output_record() -> None:
    """The shortfall must be legible to a consumer reading a result, not
    only to someone reading this module's source.
    """
    updated = Decoder().run(_record("A prompt.", "A perfectly ordinary response."))
    observation = updated.observations[-1]

    assert observation.stage == "decoding"
    assert observation.maturity == "partial"
    assert observation.facts["failure_check"] == "stub_always_success"


def test_the_decoder_still_never_drops_content_or_empties_the_text() -> None:
    """The half of `SCIENCE.md` §Decoding that *is* met, and the reason the
    stub is tolerable: the worst case is the un-decoded text, so a decode
    that recovers nothing still passes the original forward intact.
    """
    response = "A perfectly ordinary response."
    updated = Decoder().run(_record("A prompt.", response))

    assert updated.texts.original == response
    assert updated.texts.working.strip() != ""
    assert updated.texts.decoded != ""


def test_module_docstring_records_the_stub() -> None:
    """Cheap guard against the explanation being deleted while the stub
    stays -- the gap must not become invisible.
    """
    assert "stub" in decoding.__doc__.lower()
