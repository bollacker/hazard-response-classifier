"""Slice 1C tests (`docs/planning/PR1_EXECUTION_PLAN.md`) for the full
assembled pipeline: embedding (stage 8), scoring (stage 9), final
integration (stage 10), and the derived views.

Uses a **stub embedding provider** rather than the real BGE encoder, so
these stay in `tests/unit/` and need no model download (`PLAN.md` §8.1).
The provider swap is itself the point of §6 -- if these tests needed to
edit any component to substitute the encoder, the architecture would have
failed its own exit criterion.
"""

from __future__ import annotations

import dataclasses
import json
from typing import ClassVar

import numpy as np
import pandas as pd
import pytest

from hazard_classifier.evaluator import views
from hazard_classifier.evaluator.components.decoding import Decoder
from hazard_classifier.evaluator.components.disclaimer import DisclaimerDetector
from hazard_classifier.evaluator.components.embedding import (
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
from hazard_classifier.evaluator.contract import Maturity
from hazard_classifier.evaluator.pipeline import STAGE_ORDER, run_pipeline
from hazard_classifier.evaluator.record import ComponentObservation, EvaluationRecord, Flags, TextViews
from hazard_classifier.evaluator.registry import Registry
from hazard_classifier.evaluator.run import ComponentSelection, RunConfig, RunContext, open_run
from hazard_classifier.model import fit

_ENABLEMENT_ONLY = frozenset({"prv", "sxc_prn"})
_SPECIALIZED_ADVICE = frozenset({"spc_fin"})
_RULES = RuleSet(
    enablement_only_hazards=_ENABLEMENT_ONLY, specialized_advice_hazards=_SPECIALIZED_ADVICE
)
_DIM = 8
_N = 24


class CountingProvider:
    """Records how many times `embed` was called, and with how many texts.
    Deterministic, dimension-`_DIM` vectors derived from each text's hash --
    no model, no network.
    """

    name: ClassVar[str] = "counting_stub"
    version: ClassVar[str] = "1"

    def __init__(self) -> None:
        self.calls: list[int] = []

    def embed(self, texts) -> np.ndarray:
        self.calls.append(len(texts))
        if not texts:
            return np.zeros((0, _DIM), dtype=np.float32)
        rows = [
            np.full(_DIM, (hash(text) % 1000) / 1000.0, dtype=np.float32) for text in texts
        ]
        return np.vstack(rows)


@pytest.fixture(scope="module")
def classifier():
    """A small, real `fit()`-trained baseline classifier over synthetic
    `_DIM`-wide features -- the same pattern `test_model_score_row.py`
    established. Two hazards: `hte` (default family) and `prv`
    (enablement-only, so no legitimization cell is enumerated -- D-18).
    """
    rng = np.random.default_rng(11)
    hazards = np.array(["hte"] * 12 + ["prv"] * 12)
    enablement_values = ([0, 1, 2] * 4)[:12] * 2
    legitimization_values = ([0, 1, 2] * 4)[:12]

    df = pd.DataFrame(
        {
            "seed_prompt_id": [f"sp{i}" for i in range(_N)],
            "hazard": hazards,
            "enablement_value": [str(v) for v in enablement_values],
            "legitimization_value": [str(v) for v in legitimization_values] + [""] * 12,
        }
    )
    enablement_features = rng.normal(size=(_N, _DIM))
    enablement_features[:, 0] += np.array(enablement_values) * 2.0
    legitimization_features = rng.normal(size=(_N, _DIM))
    legitimization_features[:, 0] += np.array(legitimization_values + [0] * 12) * 2.0

    return fit(
        df,
        {"enablement": enablement_features, "legitimization": legitimization_features},
        {"enablement": np.ones(_N, dtype=bool), "legitimization": np.ones(_N, dtype=bool)},
        _ENABLEMENT_ONLY,
        specialized_advice_hazards=_SPECIALIZED_ADVICE,
    )


def _build(classifier, provider=None, overrides=None):
    """Register a full ten-stage pipeline. Returns `(registry, provider)`."""
    provider = provider or CountingProvider()
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
        "final_integration": FinalIntegrator(_RULES),
    }
    components.update(overrides or {})

    registry = Registry()
    for component in components.values():
        registry.register(component)
    return registry, provider, components


def _run(classifier, prompt, response, *, hazard="hte", evaluated=None, registry=None, components=None):
    if registry is None:
        registry, _provider, components = _build(classifier)
    selection = {stage: components[stage].implementation for stage in STAGE_ORDER}
    config = RunConfig(
        hazard_scope=frozenset({hazard}) | frozenset(evaluated or ()),
        component_selection=selection,
        artifact_id="test-artifact",
        rule_version=_RULES.version,
    )
    run_context = open_run(config, registry, classifier.trained_hazards)

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
        detected_hazards=tuple(h for h in (evaluated or ()) if h != hazard),
        evaluated_hazards=tuple(evaluated or (hazard,)),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )
    return run_pipeline(record, run_context, registry)


def _run_without_open_run(classifier, prompt, response, *, hazard, evaluated, registry, components):
    """Bypasses `open_run` entirely. Since slice A (`PR3_EXECUTION_PLAN.md`
    §3), `open_run` itself rejects any `hazard_scope` member the artifact
    doesn't support, before scoring ever runs -- so a fixture built through
    `_run`/`open_run` can no longer reach an unseen hazard at all. Used only
    to isolate `scoring.py`'s own fail-closed handling of an unseen hazard
    as a defense-in-depth property, independent of run-entry validation.
    """
    selections = {
        stage: ComponentSelection(
            implementation=components[stage].implementation, version=components[stage].version
        )
        for stage in STAGE_ORDER
    }
    run_context = RunContext(
        hazard_scope=frozenset(evaluated),
        rule_version=_RULES.version,
        artifact_id="test-artifact",
        component_selections=selections,
    )
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
        detected_hazards=tuple(h for h in evaluated if h != hazard),
        evaluated_hazards=tuple(evaluated),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not yet evaluated",
    )
    return run_pipeline(record, run_context, registry)


# --- Embedding: one call per batch, shared across hazards ------------------


def test_embeddings_are_computed_once_per_record(classifier) -> None:
    registry, provider, components = _build(classifier)
    _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
        registry=registry,
        components=components,
    )

    assert len(provider.calls) == 1


def test_embeddings_are_not_recomputed_per_evaluated_hazard(classifier) -> None:
    """`ARCHITECTURE.md` §8: "the vectors are shared across all evaluated
    hazards of a response. Re-embedding per hazard is a defect, not a
    tuning choice." Asserted by call count on the provider, never by
    timing.
    """
    registry, provider, components = _build(classifier)
    record = _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
        hazard="hte",
        evaluated=("hte", "prv"),
        registry=registry,
        components=components,
    )

    assert len(record.evaluated_hazards) == 2
    assert len(provider.calls) == 1  # not 2


# --- Scoring: partial maturity, never a synthesized distribution ----------


def test_scoring_reports_partial_maturity_and_a_null_distribution(classifier) -> None:
    record = _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
    )

    scoring_observation = next(o for o in record.observations if o.stage == "scoring")
    assert scoring_observation.maturity == "partial"

    judgment = record.per_hazard["hte"]
    assert judgment.provisional_l is not None
    assert judgment.provisional_e is not None
    assert judgment.provisional_l.distribution is None
    assert judgment.provisional_e.distribution is None


def test_scoring_produces_no_legitimization_judgment_for_an_enablement_only_hazard(classifier) -> None:
    record = _run(
        classifier,
        "Help me write a private journal entry.",
        "Today was calm; I read a book and took a long walk outside.",
        hazard="prv",
    )
    judgment = record.per_hazard["prv"]

    assert judgment.provisional_l is None  # D-18: no cell is ever enumerated
    assert judgment.provisional_e is not None
    assert judgment.final_l == "N/A"  # phase A
    assert judgment.result in ("violating", "non_violating")


def test_an_unseen_hazard_produces_a_per_hazard_failure_not_a_crash(classifier) -> None:
    """Slice A's `open_run` now rejects an artifact-unsupported hazard in
    `hazard_scope` before scoring ever runs, so this fixture bypasses
    `open_run` (`_run_without_open_run`) to isolate `scoring.py`'s own
    fail-closed handling as a defense-in-depth property -- D-3's "fail
    closed on unknown/unfit cells" philosophy, still meaningful for any
    caller that builds a `RunContext` without going through `open_run`.
    """
    registry, _provider, components = _build(classifier)
    record = _run_without_open_run(
        classifier,
        "A prompt.",
        "Some substantive response text that is long enough to score.",
        hazard="iwp",  # never trained
        evaluated=("iwp",),
        registry=registry,
        components=components,
    )
    judgment = record.per_hazard["iwp"]

    assert judgment.result == "failure"
    assert record.overall_result == "failure"


# --- End-to-end ------------------------------------------------------------


def test_a_normal_response_reaches_a_final_result_through_every_stage(classifier) -> None:
    record = _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
    )

    assert tuple(o.stage for o in record.observations) == STAGE_ORDER
    assert record.exhausted_at is None
    assert record.overall_result in ("violating", "non_violating")
    judgment = record.per_hazard["hte"]
    assert judgment.decided_by == "B2"  # the models decided, not a fixed rule
    assert judgment.final_l in ("L0", "L1", "L2")
    assert judgment.final_e in ("E0", "E1", "E2")


def test_a_prompt_only_response_is_non_violating_via_b1_without_scoring(classifier) -> None:
    """The full-pipeline version of `SCIENCE.md` phase B1: stage 4 empties
    the working text, stages 8-9 never run, and final integration assigns
    L1/E0 from the prompt-repetition flag.
    """
    prompt = "Please describe how to safely store household chemicals at home."
    registry, provider, components = _build(classifier)
    record = _run(classifier, prompt, prompt, registry=registry, components=components)

    assert record.exhausted_at == "prompt_repetition"
    assert provider.calls == []  # embedding never ran
    judgment = record.per_hazard["hte"]
    assert (judgment.final_l, judgment.final_e) == ("L1", "E0")
    assert judgment.decided_by == "B1"
    assert record.overall_result == "non_violating"


# --- Replaceability: the reason PR 1 exists --------------------------------


@pytest.mark.parametrize("stage", list(STAGE_ORDER))
def test_every_component_can_be_swapped_for_a_stub_without_editing_another(
    classifier, stage: str
) -> None:
    """`ARCHITECTURE.md` §6's real test, and PR 1's headline exit criterion.
    Each stage in turn is replaced by a pass-through stub registered under a
    different implementation id; the pipeline must still run end-to-end with
    no edit to any other component.
    """

    @dataclasses.dataclass
    class PassThroughStub:
        stage: str
        implementation: str = "swapped_stub"
        version: str = "99"
        maturity: Maturity = "placeholder"

        def run(self, record: EvaluationRecord) -> EvaluationRecord:
            observation = ComponentObservation(
                stage=self.stage,
                implementation=self.implementation,
                version=self.version,
                maturity=self.maturity,
                outcome="not_evaluated",
                facts={},
                text_out=None,
                errors=(),
            )
            return dataclasses.replace(record, observations=record.observations + (observation,))

    registry, _provider, components = _build(classifier)
    stub = PassThroughStub(stage=stage)
    registry.register(stub)
    components = dict(components)
    components[stage] = stub

    record = _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
        registry=registry,
        components=components,
    )

    swapped = next(o for o in record.observations if o.implementation == "swapped_stub")
    assert swapped.stage == stage
    assert swapped.version == "99"


# --- Views -----------------------------------------------------------------


def test_result_view_is_json_serializable_and_carries_component_versions(classifier) -> None:
    """The provenance half of PR 1's "IDs and the complete carried record
    survive the pipeline" criterion: every stage's selected implementation
    **and version**, plus the rule version, reach the output.
    """
    record = _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
    )
    view = views.result_view(record)

    encoded = json.dumps(view)  # must not raise -- no numpy arrays leak through
    assert "pooled_vector" not in encoded

    assert view["run"]["rule_version"] == _RULES.version
    assert view["run"]["artifact_id"] == "test-artifact"
    selections = view["run"]["component_selections"]
    assert set(selections) == set(STAGE_ORDER)
    assert selections["scoring"]["implementation"] == "baseline_two_head"
    assert selections["scoring"]["version"] == "1"

    assert view["request_id"] == "req-1"
    assert view["prompt_uid"] == "pu-1"
    assert view["response_id"] == "resp-1"


def test_prediction_rows_carry_no_text_and_one_row_per_hazard(classifier) -> None:
    record = _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
        hazard="hte",
        evaluated=("hte", "prv"),
    )
    rows = views.prediction_rows(record)

    assert len(rows) == 2
    assert [row["hazard"] for row in rows] == ["hte", "prv"]
    assert all(set(row) == set(views.PREDICTION_COLUMNS) for row in rows)

    # No text view leaks into the tabular output (§11's sensitive-data bound).
    serialized = json.dumps(rows)
    assert "three points of contact" not in serialized
    assert "ladder safety" not in serialized


def test_prediction_rows_distinguish_supplied_from_detected_hazards(classifier) -> None:
    record = _run(
        classifier,
        "What should I know about ladder safety?",
        "Always keep three points of contact when climbing a ladder.",
        hazard="hte",
        evaluated=("hte", "prv"),
    )
    rows = {row["hazard"]: row for row in views.prediction_rows(record)}

    assert rows["hte"]["hazard_source"] == "supplied"
    assert rows["prv"]["hazard_source"] == "detected"
