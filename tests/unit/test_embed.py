"""Tests for `hazard_classifier.embed`'s pure pooling logic (no network/model
download -- `PLAN.md` §8.1: unit tests need no model download). The BGE
wrapper itself (`embed_sentences`) is exercised separately in
`tests/integration/test_pipeline_mechanism.py`, which does need the model.
"""

from __future__ import annotations

import numpy as np
import pytest

from hazard_classifier import embed as embed_module
from hazard_classifier.embed import (
    EMBEDDING_DIM,
    build_component_features,
    build_legacy_component_features,
    embed_sentences,
    enablement_keep_mask,
    pool_response_vector,
)
from hazard_classifier.pipeline import EvaluationIdentity


def test_embed_sentences_empty_list_returns_zero_rows_without_loading_a_model() -> None:
    result = embed_sentences([])
    assert result.shape == (0, EMBEDDING_DIM)


def test_enablement_keep_mask_drops_only_prompt_repetition_without_continuation() -> None:
    # toy's effective_indices: drop iff (prompt_repetition AND NOT later_authored).
    prompt_repetition = np.array([True, True, False, False])
    later_authored = np.array([False, True, False, True])
    mask = enablement_keep_mask(prompt_repetition, later_authored)
    assert list(mask) == [False, True, True, True]


def test_pool_response_vector_mean_pools_only_kept_rows() -> None:
    embeddings = np.array([[1.0, 1.0], [3.0, 3.0], [100.0, 100.0]], dtype=np.float32)
    keep_mask = np.array([True, True, False])
    vector, effective = pool_response_vector(embeddings, keep_mask)
    assert effective is True
    assert np.allclose(vector, [2.0, 2.0])


def test_pool_response_vector_zero_kept_sentences_is_not_effective() -> None:
    embeddings = np.array([[5.0, 5.0]], dtype=np.float32)
    keep_mask = np.array([False])
    vector, effective = pool_response_vector(embeddings, keep_mask)
    assert effective is False
    assert vector.shape == (2,)


def test_pool_response_vector_genuinely_empty_response_is_not_effective() -> None:
    embeddings = np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
    keep_mask = np.zeros((0,), dtype=bool)
    vector, effective = pool_response_vector(embeddings, keep_mask)
    assert effective is False
    assert vector.shape == (EMBEDDING_DIM,)


def test_build_component_features_uses_one_preparation_and_embedding_path(
    monkeypatch,
) -> None:
    prepared_rows = []
    embedded_batches = []

    from hazard_classifier import pipeline as pipeline_module

    original_prepare = pipeline_module.prepare_response

    def recording_prepare(
        prompt_text: str,
        response_text: str,
        intended_hazard: str = "",
        *,
        identity=None,
    ):
        prepared = original_prepare(
            prompt_text,
            response_text,
            intended_hazard=intended_hazard,
            identity=identity,
        )
        prepared_rows.append(prepared)
        return prepared

    def fake_embed(sentences, **_kwargs):
        embedded_batches.append(list(sentences))
        return np.arange(len(sentences) * 2, dtype=np.float32).reshape(-1, 2)

    monkeypatch.setattr(pipeline_module, "prepare_response", recording_prepare)
    monkeypatch.setattr(embed_module, "embed_sentences", fake_embed)
    monkeypatch.setattr(embed_module, "EMBEDDING_DIM", 2)

    identities = [
        EvaluationIdentity("prompt-1", "response-1", "request-1"),
        EvaluationIdentity("prompt-2", "response-2", "request-2"),
    ]
    features, effective, disclaimer_counts = build_component_features(
        ["First prompt.", "Second prompt."],
        ["A separate answer.", "Consult a qualified professional."],
        ["hte", "spc_hlt"],
        identities=identities,
    )

    assert len(prepared_rows) == 2
    assert [prepared.intended_hazard for prepared in prepared_rows] == [
        "hte",
        "spc_hlt",
    ]
    assert [prepared.identity for prepared in prepared_rows] == identities
    assert len(embedded_batches) == 1
    assert embedded_batches[0] == [
        segment.text
        for prepared in prepared_rows
        for segment in prepared.segments
    ]
    assert features["enablement"].shape == (2, 2)
    assert features["legitimization"].shape == (2, 2)
    assert effective["enablement"].all()
    assert effective["legitimization"].all()
    assert list(disclaimer_counts) == [0, 1]


def test_build_component_features_rejects_misaligned_input_sequences() -> None:
    identity = EvaluationIdentity("prompt-1", "response-1", "request-1")

    with pytest.raises(ValueError, match="response_texts"):
        build_component_features(["prompt"], [], identities=[identity])

    with pytest.raises(ValueError, match="hazards"):
        build_component_features(
            ["prompt"],
            ["response"],
            [],
            identities=[identity],
        )

    with pytest.raises(ValueError, match="identities"):
        build_component_features(["prompt"], ["response"], [""], identities=[])

    with pytest.raises(TypeError, match="EvaluationIdentity"):
        build_component_features(
            ["prompt"],
            ["response"],
            [""],
            identities=["not-an-identity"],
        )


def test_legacy_feature_builder_is_explicitly_unidentified(monkeypatch) -> None:
    prepared_rows = []

    from hazard_classifier import pipeline as pipeline_module

    original_prepare = pipeline_module.prepare_legacy_response

    def recording_prepare(prompt_text, response_text, intended_hazard=""):
        prepared = original_prepare(
            prompt_text,
            response_text,
            intended_hazard=intended_hazard,
        )
        prepared_rows.append(prepared)
        return prepared

    def fake_embed(sentences, **_kwargs):
        return np.ones((len(sentences), 2), dtype=np.float32)

    monkeypatch.setattr(pipeline_module, "prepare_legacy_response", recording_prepare)
    monkeypatch.setattr(embed_module, "embed_sentences", fake_embed)
    monkeypatch.setattr(embed_module, "EMBEDDING_DIM", 2)

    build_legacy_component_features(["prompt"], ["response"], ["hte"])

    assert prepared_rows[0].identity is None
