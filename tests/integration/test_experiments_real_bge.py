"""Slice A's real, non-mocked embedding pass for the comparison harness
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md` §4.1).

Every unit test of `experiments.features` substitutes a stub `embed_fn` --
which is what keeps them fast and network-free, but also means the real
`embed.embed_sentences` call `embed_responses` makes would otherwise never be
executed at all. The stub's signature was written to match the real one *by
inspection*, and this project has been caught before by a claim that was true
in the docs and untested in the code (`PR3_EXECUTION_PLAN.md` lesson 6). This
module runs the real thing on a handful of real interim rows.

Needs network on first run only (model cached afterward, `DECISIONS.md` D-6),
which is why it lives in `tests/integration/` rather than `tests/unit/`
(`PLAN.md` §8.1).

**Mechanism check, not a science check.** Nothing here asserts anything about
what the vectors mean -- only that real embeddings flow through segmentation,
caching, and every pooling axis with the right shapes.
"""

from __future__ import annotations

import numpy as np

from hazard_classifier.embed import EMBEDDING_DIM
from hazard_classifier.experiments.features import embed_responses
from hazard_classifier.interim_data import load_interim

# Small: this proves the wiring, and the full 859-row pass belongs to slice B's
# cache-building step, not to the test suite.
N_ROWS = 6


def test_embed_responses_runs_against_the_real_bge_model(tmp_path):
    frame = load_interim().head(N_ROWS)

    embeddings = embed_responses(frame, cache_dir=tmp_path)

    assert len(embeddings.row_ids) == N_ROWS
    assert embeddings.vectors.shape[1] == EMBEDDING_DIM
    assert embeddings.vectors.shape[0] > 0
    assert np.isfinite(embeddings.vectors).all()

    # Every row got a range, and the ranges tile the vector block in order.
    assert embeddings.row_ranges[0][0] == 0
    assert embeddings.row_ranges[-1][1] == embeddings.vectors.shape[0]
    for (_, end), (start, _) in zip(embeddings.row_ranges, embeddings.row_ranges[1:]):
        assert end == start


def test_the_real_embedding_pass_is_cached_not_recomputed(tmp_path):
    """§4.1's whole point: one pass, reused. If this regresses, the 32-config
    ladder silently pays for 32 embedding passes.
    """
    frame = load_interim().head(N_ROWS)

    first = embed_responses(frame, cache_dir=tmp_path)
    cached_files = sorted(p.name for p in tmp_path.iterdir())
    second = embed_responses(frame, cache_dir=tmp_path)

    np.testing.assert_array_equal(first.vectors, second.vectors)
    assert first.row_ranges == second.row_ranges
    assert len(cached_files) == 2, f"expected one .npz and one .meta.json, got {cached_files}"


def test_every_pooling_axis_produces_usable_features_from_real_embeddings(tmp_path):
    """`P2`/`P3` exist as comparison axes only because the cache stores
    per-sentence vectors (§4.1). This confirms all three pool from one pass.
    """
    frame = load_interim().head(N_ROWS)
    embeddings = embed_responses(frame, cache_dir=tmp_path)

    p1 = embeddings.pooled("P1")
    p2 = embeddings.pooled("P2")
    p3 = embeddings.pooled("P3")

    assert p1.shape == (N_ROWS, EMBEDDING_DIM)
    assert p2.shape == (N_ROWS, EMBEDDING_DIM)
    assert p3.shape == (N_ROWS, 2 * EMBEDDING_DIM)
    for pooled in (p1, p2, p3):
        assert np.isfinite(pooled).all()

    # P3 is literally mean concatenated with max -- not a third computation.
    np.testing.assert_allclose(p3[:, :EMBEDDING_DIM], p1, rtol=1e-6)
    np.testing.assert_allclose(p3[:, EMBEDDING_DIM:], p2, rtol=1e-6)
    # Mean and max genuinely differ on real multi-sentence responses.
    assert not np.allclose(p1, p2)
