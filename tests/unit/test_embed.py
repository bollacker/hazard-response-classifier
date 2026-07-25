"""Tests for `hazard_classifier.embed`'s pure pooling logic (no network/model
download -- `PLAN.md` §8.1: unit tests need no model download). The BGE
wrapper itself (`embed_sentences`) is exercised separately in
`tests/integration/test_pipeline_mechanism.py`, which does need the model.
"""

from __future__ import annotations

import numpy as np

from hazard_classifier.embed import (
    EMBEDDING_DIM,
    embed_sentences,
    enablement_keep_mask,
    pool_response_vector,
)


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
