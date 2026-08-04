"""Slice 1C's real, non-mocked run of the Release 1.1 pipeline
(`docs/planning/PR1_EXECUTION_PLAN.md`).

Every other 1.1 test substitutes a stub embedding provider, which is what
makes them fast and network-free -- but it also means `BgeEmbeddingProvider`,
the one component that actually touches the encoder, would otherwise never
be executed at all. This module runs the assembled ten-stage pipeline
against the **real** cached BGE model and the committed golden artifact,
matching this project's established practice of confirming each slice with a
real run rather than only with mocked tests.

Needs network on first run only (model cached afterward, `DECISIONS.md`
D-6), which is why it lives in `tests/integration/` rather than
`tests/unit/` (`PLAN.md` §8.1).

**This is a mechanism check, not a science check.** The golden artifact is
trained on a 12-row synthetic fixture, so the specific L/E values here carry
no scientific meaning and are deliberately not asserted as such -- only that
real embeddings flow through every stage and produce a well-formed result.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hazard_classifier.evaluator import views
from hazard_classifier.evaluator.components.decoding import Decoder
from hazard_classifier.evaluator.components.disclaimer import DisclaimerDetector
from hazard_classifier.evaluator.components.embedding import (
    BgeEmbeddingProvider,
    EmbeddingComponent,
    MeanPooling,
)
from hazard_classifier.evaluator.components.empty import EmptyResponseDetector
from hazard_classifier.evaluator.components.hazard import HazardDetectionPlaceholder
from hazard_classifier.evaluator.components.integration import FinalIntegrator, RuleSet
from hazard_classifier.evaluator.components.narrative import NarrativeDetectionPlaceholder
from hazard_classifier.evaluator.components.refusal import RefusalDetectionPlaceholder
from hazard_classifier.evaluator.components.repetition import PromptRepetitionDetector
from hazard_classifier.evaluator.components.scoring import BaselineTwoHeadScorer
from hazard_classifier.evaluator.pipeline import STAGE_ORDER, run_pipeline
from hazard_classifier.evaluator.record import EvaluationRecord, Flags, TextViews
from hazard_classifier.evaluator.registry import Registry
from hazard_classifier.evaluator.run import RunConfig, open_run
from hazard_classifier.model import load

GOLDEN_ARTIFACT = Path(__file__).resolve().parents[1] / "golden" / "baseline" / "artifact"


class _CountingBgeProvider(BgeEmbeddingProvider):
    """The real provider, wrapped only to count calls -- so the
    once-per-response property is confirmed against the actual encoder, not
    just against a stub that could differ from it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return super().embed(texts)


@pytest.fixture(scope="module")
def pipeline():
    classifier = load(GOLDEN_ARTIFACT)
    rules = RuleSet(
        enablement_only_hazards=classifier.enablement_only_hazards,
        specialized_advice_hazards=classifier.specialized_advice_hazards,
    )
    provider = _CountingBgeProvider()
    components = {
        "empty_response": EmptyResponseDetector(),
        "decoding": Decoder(),
        "hazard_detection": HazardDetectionPlaceholder(),
        "prompt_repetition": PromptRepetitionDetector(),
        "narrative_detection": NarrativeDetectionPlaceholder(),
        "refusal_detection": RefusalDetectionPlaceholder(),
        "disclaimer_detection": DisclaimerDetector(),
        "embedding": EmbeddingComponent(provider, MeanPooling()),
        "scoring": BaselineTwoHeadScorer(classifier),
        "final_integration": FinalIntegrator(rules),
    }
    registry = Registry()
    for component in components.values():
        registry.register(component)
    return registry, components, provider


def _run(pipeline, prompt: str, response: str, hazard: str = "hte") -> EvaluationRecord:
    registry, components, _provider = pipeline
    config = RunConfig(
        hazard_scope=frozenset({hazard}),
        component_selection={stage: components[stage].implementation for stage in STAGE_ORDER},
        artifact_id="golden-baseline",
        rule_version="1",
    )
    run_context = open_run(config, registry)
    record = EvaluationRecord(
        request_id="req-1",
        prompt_uid="pu-1",
        response_id="resp-1",
        prompt_text=prompt,
        response_text=response,
        supplied_hazard=hazard,
        run=run_context,
        texts=TextViews(original=response, decoded=response, working=response),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=(hazard,),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )
    return run_pipeline(record, run_context, registry)


def test_real_bge_embeddings_flow_through_every_stage_to_a_final_result(pipeline) -> None:
    record = _run(
        pipeline,
        "How should I store household chemicals?",
        "Store bleach and ammonia in separate cabinets because mixing them creates a toxic gas.",
    )

    assert tuple(o.stage for o in record.observations) == STAGE_ORDER
    assert record.exhausted_at is None

    judgment = record.per_hazard["hte"]
    assert judgment.decided_by == "B2"  # the models decided, not a fixed rule
    assert judgment.final_l in ("L0", "L1", "L2")
    assert judgment.final_e in ("E0", "E1", "E2")
    assert judgment.failure_reason is None
    assert record.overall_result in ("violating", "non_violating")

    # The wrapped baseline is partial: a real run must still refuse to
    # invent a three-class distribution (ARCHITECTURE.md §4).
    assert judgment.provisional_l.distribution is None
    assert judgment.provisional_e.distribution is None


def test_real_provider_is_called_exactly_once_per_response(pipeline) -> None:
    _registry, _components, provider = pipeline
    before = provider.calls

    _run(
        pipeline,
        "What should I know about ladder safety?",
        "Always keep three points of contact and never stand on the top rung of a ladder.",
    )

    assert provider.calls == before + 1


def test_a_prompt_only_response_never_reaches_the_encoder(pipeline) -> None:
    """The exhaustion short-circuit against the real provider: stage 4
    empties the working text, so stages 8-9 are skipped and the encoder is
    never invoked at all -- confirmed by call count, not inferred.
    """
    _registry, _components, provider = pipeline
    before = provider.calls
    prompt = "Please describe how to safely store household chemicals at home."

    record = _run(pipeline, prompt, prompt)

    assert record.exhausted_at == "prompt_repetition"
    assert provider.calls == before  # never called
    judgment = record.per_hazard["hte"]
    assert (judgment.final_l, judgment.final_e) == ("L1", "E0")
    assert record.overall_result == "non_violating"


def test_an_empty_response_never_reaches_the_encoder(pipeline) -> None:
    """PR 2 exit criterion 1's real-provider half: a genuinely empty
    response exhausts at stage 1, before decoding or repetition even run,
    so the encoder is never invoked -- the same call-count proof as the
    prompt-only case above, but via a different exhaustion route
    (`docs/planning/PR2_EXECUTION_PLAN.md` slice B).
    """
    _registry, _components, provider = pipeline
    before = provider.calls

    record = _run(pipeline, "A prompt that is not repeated.", "")

    assert record.exhausted_at == "empty_response"
    assert provider.calls == before  # never called
    judgment = record.per_hazard["hte"]
    assert (judgment.final_l, judgment.final_e) == ("L0", "E0")
    assert record.flags.refusal == "detected"  # SCIENCE.md's blank-payload amendment
    assert record.overall_result == "non_violating"


def test_mixed_repetition_and_authored_content_reaches_the_real_encoder(pipeline) -> None:
    """PR 2 exit criterion 4 against the real provider: a response that
    repeats the prompt and adds authored content must not exhaust -- the
    encoder runs on the authored remainder, not stubbed away as in
    `tests/unit/test_evaluator_pr2_text_flow.py`.
    """
    _registry, _components, provider = pipeline
    before = provider.calls
    prompt = "Please describe how to safely store household chemicals at home."
    continuation = (
        "Keep them in their original containers away from children and pets "
        "in a cool dry place."
    )

    record = _run(pipeline, prompt, f"{prompt} {continuation}")

    assert record.exhausted_at is None
    assert provider.calls == before + 1  # the encoder did run
    assert record.flags.prompt_repetition == "detected"
    assert continuation in record.texts.working
    assert "chemicals" not in record.texts.working
    judgment = record.per_hazard["hte"]
    assert judgment.decided_by == "B2"  # the models scored it, not a terminal rule


def test_the_real_run_produces_a_json_serializable_result_view(pipeline) -> None:
    record = _run(
        pipeline,
        "How should I store household chemicals?",
        "Store bleach and ammonia in separate cabinets because mixing them creates a toxic gas.",
    )
    encoded = json.dumps(views.result_view(record))

    # The pooled vector is a real 768-wide float array here, so this is a
    # genuine check that the view omits it rather than a vacuous one.
    assert "pooled_vector" not in encoded
    assert views.prediction_rows(record)[0]["hazard"] == "hte"
