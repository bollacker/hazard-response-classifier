"""The training feature path, run against the **real** BGE encoder
(`docs/planning/PR5_EXECUTION_PLAN.md` §5, slice A).

Every unit test of `evaluator.training.features` substitutes a stub
embedding provider, which is what keeps them fast and network-free -- and
also means `BgeEmbeddingProvider`, the one piece that actually touches the
encoder, would never run in the fitting path at all. This project has been
caught before by a claim that was true in the docs and untested in the code
(`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 lesson 6), and the claim this slice
rests on is precisely that **the features the models are fitted on are the
features stage 9 reads at serve time**
([D-72](../../docs/planning/DECISIONS.md#d-72)).

So the test here is an identity, not a shape check: for a real interim row,
the vector `build_pipeline_features` produces must be **the same array** the
real `EmbeddingComponent` publishes for that row's working text.

Needs network on first run only (model cached afterward,
`DECISIONS.md` D-6), which is why this lives in `tests/integration/`
(`PLAN.md` §8.1).

**A mechanism check, not a science check.** Nothing here asserts anything
about what the vectors mean, and no fit is performed: a handful of rows
cannot fill a per-hazard cell, and every number the real fit produces is a
dev-class number under D-66 in any case.
"""

from __future__ import annotations

import numpy as np

from hazard_classifier.embed import EMBEDDING_DIM
from hazard_classifier.evaluator.components.embedding import (
    POOLED_VECTOR_FACT,
    BgeEmbeddingProvider,
    EmbeddingComponent,
    MeanPooling,
)
from hazard_classifier.evaluator.record import EvaluationRecord, Flags, TextViews
from hazard_classifier.evaluator.training.features import build_pipeline_features
from hazard_classifier.interim_data import load_interim

# Small: this proves the wiring. The full 635-row fit belongs to slice B's
# artifact build, not to the test suite.
N_ROWS = 6


def _serve_time_pooled(working_text: str) -> np.ndarray:
    """What stage 8 publishes at serve time for a record whose working view
    is `working_text`, produced by the real component and the real encoder.
    """
    record = EvaluationRecord(
        request_id="x",
        prompt_uid="x",
        response_id="x",
        prompt_text="",
        response_text=working_text,
        supplied_hazard="cse",
        run=None,
        texts=TextViews(original=working_text, decoded=working_text, working=working_text),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=("cse",),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason=None,
    )
    component = EmbeddingComponent(BgeEmbeddingProvider(), MeanPooling())
    return np.asarray(component.run(record).observations[-1].facts[POOLED_VECTOR_FACT])


def test_training_features_are_real_bge_vectors_of_the_working_view():
    frame = load_interim().head(N_ROWS)

    features = build_pipeline_features(frame)

    assert len(features.prompt_uids) == N_ROWS
    assert features.pooled.shape == (N_ROWS, EMBEDDING_DIM)
    assert np.isfinite(features.pooled).all()
    assert features.provider_name == "bge_base_en_v1_5"
    assert features.pooling_name == "mean"
    assert features.text_view == "working"


def test_a_training_feature_row_equals_what_stage_8_would_publish():
    """The identity D-72 turns on. If this ever drifts, the models are fitted
    on text the evaluator does not produce -- which is exactly the defect
    gate G-1 was raised to close, reappearing on the other side.
    """
    frame = load_interim().head(N_ROWS)

    features = build_pipeline_features(frame)

    for position in (0, N_ROWS - 1):
        np.testing.assert_array_equal(
            features.pooled[position],
            _serve_time_pooled(features.working_texts[position]),
        )


def test_working_text_differs_from_the_raw_response_on_real_decoded_rows():
    """Not a property of this module, but the reason it exists: on the real
    data 291 of 859 rows differ between the two views
    (`scripts/probe_working_text_delta.py`), overwhelmingly through decoding.
    A pass where they never differ would mean stages 1-7 are not running.
    """
    frame = load_interim().head(120)

    features = build_pipeline_features(frame, provider=_NullProvider(), pooling=MeanPooling())

    raw = dict(zip(frame["prompt_uid"].astype(str), frame["response_text"].astype(str)))
    changed = sum(
        1
        for uid, working in zip(features.prompt_uids, features.working_texts)
        if working != raw[uid]
    )
    assert changed > 0


class _NullProvider:
    """Zero vectors: this one test is about *text*, and paying for 120 real
    embedding passes to assert nothing about them would be waste.
    """

    name = "null"
    version = "1"

    def embed(self, texts) -> np.ndarray:
        return np.zeros((len(texts), 4), dtype=np.float32)
