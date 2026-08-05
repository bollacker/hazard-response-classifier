"""Slice A tests (`docs/planning/PR4_EXECUTION_PLAN.md` §3): the text-view
selection seam on `EmbeddingComponent`, locked as `docs/planning/DECISIONS.md`
D-69. No pipeline needed -- these exercise the component directly against a
hand-built `EvaluationRecord`, the same way its constructor knob is scoped:
one component, one construction argument.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np
import pytest

from hazard_classifier.evaluator.components.embedding import (
    TEXT_VIEW_FACT,
    EmbeddingComponent,
    MeanPooling,
)
from hazard_classifier.evaluator.record import EvaluationRecord, Flags, TextViews

_DIM = 8


class _CapturingProvider:
    """Records every text list passed to `embed`, so a test can assert on
    *which text the encoder actually saw* rather than a byte count (§3's
    test bullet).
    """

    name: ClassVar[str] = "capturing"
    version: ClassVar[str] = "1"

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts) -> np.ndarray:
        self.calls.append(list(texts))
        if not texts:
            return np.zeros((0, _DIM), dtype=np.float32)
        rows = [np.full(_DIM, (hash(text) % 1000) / 1000.0, dtype=np.float32) for text in texts]
        return np.vstack(rows)


def _make_record(
    *,
    working: str,
    original: str | None = None,
    decoded: str | None = None,
    named: dict[str, str] | None = None,
) -> EvaluationRecord:
    """A minimal record for a component-level test: only `texts` and the
    fields `EmbeddingComponent.run` actually touches are populated
    meaningfully; identity fields are placeholders, matching the pattern
    every other evaluator component test uses. `original`/`decoded` default
    to `working` so tests that don't care about the distinction stay short.
    """
    return EvaluationRecord(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text="",
        response_text=working,
        supplied_hazard="hte",
        run=None,
        texts=TextViews(
            original=original if original is not None else working,
            decoded=decoded if decoded is not None else working,
            working=working,
            named=named or {},
        ),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=("hte",),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )


def test_default_text_view_is_working_and_recorded_in_the_observation() -> None:
    provider = _CapturingProvider()
    component = EmbeddingComponent(provider, MeanPooling())
    assert component.text_view == "working"

    record = _make_record(working="A ladder should be inspected before use.")
    updated = component.run(record)

    observation = updated.observations[-1]
    assert observation.facts[TEXT_VIEW_FACT] == "working"
    assert provider.calls == [["A ladder should be inspected before use."]]


def test_constructing_with_a_named_view_embeds_that_view_not_working() -> None:
    provider = _CapturingProvider()
    component = EmbeddingComponent(provider, MeanPooling(), text_view="disclaimer_stripped")
    assert component.text_view == "disclaimer_stripped"

    record = _make_record(
        working="Consult a doctor before starting a new diet.",
        named={"disclaimer_stripped": "Eat more vegetables."},
    )
    updated = component.run(record)

    # The provider saw the named (stripped) view's text, not `working`'s.
    assert provider.calls == [["Eat more vegetables."]]
    observation = updated.observations[-1]
    assert observation.facts[TEXT_VIEW_FACT] == "disclaimer_stripped"


@pytest.mark.parametrize("reserved_view", ["original", "decoded"])
def test_the_other_reserved_views_are_also_selectable(reserved_view: str) -> None:
    provider = _CapturingProvider()
    component = EmbeddingComponent(provider, MeanPooling(), text_view=reserved_view)

    record = _make_record(
        working="Working text.", original="Original text.", decoded="Decoded text."
    )
    updated = component.run(record)

    expected = {"original": "Original text.", "decoded": "Decoded text."}[reserved_view]
    assert provider.calls == [[expected]]
    assert updated.observations[-1].facts[TEXT_VIEW_FACT] == reserved_view


def test_an_unknown_view_name_is_rejected_at_construction_not_at_run_time() -> None:
    with pytest.raises(ValueError, match="unknown text_view"):
        EmbeddingComponent(_CapturingProvider(), MeanPooling(), text_view="bogus_view")


def test_unknown_view_rejection_happens_before_any_record_exists() -> None:
    """The rejection is a constructor-time `ValueError`, never something a
    caller discovers only after building a record and running the pipeline
    -- `ARCHITECTURE.md` §5: "rejected at construction, not at run time."
    """
    provider = _CapturingProvider()
    try:
        EmbeddingComponent(provider, MeanPooling(), text_view="not_a_real_view")
    except ValueError:
        pass
    else:
        pytest.fail("expected ValueError")
    # Nothing was ever embedded -- the rejection happened before any text
    # could have reached the provider.
    assert provider.calls == []
