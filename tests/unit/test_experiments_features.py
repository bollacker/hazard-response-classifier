"""Tests for `hazard_classifier.experiments.features`
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` slice A §4.1).

No real BGE dependency -- `embed_fn` is stubbed throughout, per `PLAN.md`
§8.1's "unit tests need no model download" rule.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hazard_classifier.experiments.features import (
    SentenceEmbeddings,
    embed_responses,
    pool_sentences,
)


def _stub_embed_fn(dim: int = 6):
    calls: list[int] = []

    def embed_fn(sentences, *, model_name, revision, allow_download):
        calls.append(len(sentences))
        if not sentences:
            return np.zeros((0, dim), dtype=np.float32)
        rng = np.random.default_rng(abs(hash(tuple(sentences))) % (2**32))
        return rng.normal(size=(len(sentences), dim)).astype(np.float32)

    embed_fn.calls = calls  # type: ignore[attr-defined]
    return embed_fn


def _frame():
    return pd.DataFrame(
        {
            "prompt_uid": ["a", "b", "c"],
            "response_text": [
                "One sentence. Two sentences here!",
                "",  # empty response -- zero sentences
                "Only one sentence.",
            ],
        }
    )


def test_embed_responses_embeds_once_and_caches_across_calls(tmp_path):
    embed_fn = _stub_embed_fn()
    frame = _frame()

    first = embed_responses(frame, cache_dir=tmp_path, embed_fn=embed_fn)
    second = embed_responses(frame, cache_dir=tmp_path, embed_fn=embed_fn)

    assert len(embed_fn.calls) == 1, "second call should be served from cache, not re-embedded"
    assert first.row_ids == second.row_ids == ("a", "b", "c")
    np.testing.assert_array_equal(first.vectors, second.vectors)


def test_embed_responses_gives_every_row_exactly_one_range_including_empty(tmp_path):
    se = embed_responses(_frame(), cache_dir=tmp_path, embed_fn=_stub_embed_fn())

    assert len(se.row_ranges) == 3
    assert se.sentences_for_row(1).shape == (0, se.vectors.shape[1])  # the empty response
    assert se.sentences_for_row(0).shape[0] > 0
    assert se.sentences_for_row(2).shape[0] > 0


def test_embed_responses_cache_miss_on_changed_content(tmp_path):
    embed_fn = _stub_embed_fn()
    frame = _frame()
    embed_responses(frame, cache_dir=tmp_path, embed_fn=embed_fn)

    changed = frame.copy()
    changed.loc[0, "response_text"] = "A totally different response."
    embed_responses(changed, cache_dir=tmp_path, embed_fn=embed_fn)

    assert len(embed_fn.calls) == 2, "changed content must not be served from the first cache entry"


def test_embed_responses_requires_unique_id_column(tmp_path):
    frame = pd.DataFrame({"prompt_uid": ["a", "a"], "response_text": ["x", "y"]})
    with pytest.raises(ValueError):
        embed_responses(frame, cache_dir=tmp_path, embed_fn=_stub_embed_fn())


def test_pool_sentences_mean_max_and_concat():
    vectors = np.array([[1.0, 4.0], [3.0, 0.0]], dtype=np.float32)

    mean = pool_sentences(vectors, "P1")
    maxed = pool_sentences(vectors, "P2")
    concat = pool_sentences(vectors, "P3")

    np.testing.assert_allclose(mean, [2.0, 2.0])
    np.testing.assert_allclose(maxed, [3.0, 4.0])
    np.testing.assert_allclose(concat, [2.0, 2.0, 3.0, 4.0])


def test_pool_sentences_empty_input_is_zero_at_the_right_width():
    empty = np.zeros((0, 5), dtype=np.float32)
    assert pool_sentences(empty, "P1").shape == (5,)
    assert np.allclose(pool_sentences(empty, "P1"), 0)
    assert pool_sentences(empty, "P3").shape == (10,)


def test_pool_sentences_rejects_unknown_strategy():
    with pytest.raises(ValueError):
        pool_sentences(np.zeros((1, 3)), "P9")


def test_sentence_embeddings_pooled_uses_the_cache_own_width_not_the_bge_default():
    # A non-BGE-dimensioned embedding (8, not 768) with an all-empty row --
    # this is the forcing function for the width-inference bug found while
    # building this slice: pooling used to hardcode EMBEDDING_DIM (768) for
    # the empty-row zero vector regardless of the cache's actual dimension.
    se = SentenceEmbeddings(
        row_ids=("a", "b"),
        row_ranges=((0, 2), (2, 2)),
        vectors=np.ones((2, 8), dtype=np.float32),
    )

    pooled_p1 = se.pooled("P1")
    pooled_p3 = se.pooled("P3")

    assert pooled_p1.shape == (2, 8)
    assert pooled_p3.shape == (2, 16)
    assert np.allclose(pooled_p1[1], 0)
