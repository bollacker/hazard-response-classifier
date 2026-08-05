"""Slice A §4.1 -- the shared, cached embedding pass for the L/E
structure-selection comparison
(`docs/planning/QUEUE_ITEM_2_EXECUTION_PLAN.md`).

Re-embedding inside a 32-configuration ladder is the defect `ARCHITECTURE.md`
§8 names explicitly (a component may re-embed per config, "about a hundred
times slower" per the plan) -- this module embeds every response's sentences
exactly once and caches the result to disk, keyed by model name, revision,
and the exact (row id, response text) content embedded, so a data change
invalidates the cache automatically rather than silently serving stale
vectors.

**Pooling is a comparison axis (`P1` mean, `P2` max, `P3` mean+max), so the
cache stores per-sentence vectors, not a pre-pooled response vector.** Pooling
is applied downstream, per candidate, by `pool_sentences` below -- storing a
pooled vector would make `P2`/`P3` require re-embedding, defeating the cache.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from hazard_classifier.embed import DEFAULT_MODEL_NAME, EMBEDDING_DIM, embed_sentences
from hazard_classifier.preprocess.segment import segment_text

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_CACHE_DIR = _REPO_ROOT / "docs" / "planning" / "item2_results" / "embedding_cache"

# Matches `embed.build_component_features`'s own segmentation parameters, so
# a response is cut into the same sentence-sized pieces the baseline already
# embeds -- there is no locked reason for the ladder to segment differently.
_SEGMENT_MAX_CHARS = 420
_SEGMENT_STRIDE = 210

POOLING_STRATEGIES: tuple[str, ...] = ("P1", "P2", "P3")

EmbedFn = Callable[..., np.ndarray]


@dataclass(frozen=True)
class SentenceEmbeddings:
    """Per-response sentence embeddings, ragged across rows.

    `vectors` is one `(total_sentences, EMBEDDING_DIM)` array holding every
    sentence of every response, concatenated in row order. `row_ranges` gives
    each row's `[start, end)` slice into `vectors`, so a response with zero
    sentences (an empty response) is representable as an empty slice rather
    than a dropped row -- every row of the input frame gets exactly one
    entry here, regardless of how many sentences it produced.
    """

    row_ids: tuple[str, ...]
    row_ranges: tuple[tuple[int, int], ...]
    vectors: np.ndarray

    def __post_init__(self) -> None:
        if len(self.row_ids) != len(self.row_ranges):
            raise ValueError(
                f"row_ids ({len(self.row_ids)}) and row_ranges "
                f"({len(self.row_ranges)}) must be the same length"
            )

    def sentences_for_row(self, i: int) -> np.ndarray:
        start, end = self.row_ranges[i]
        return self.vectors[start:end]

    def pooled(self, strategy: str) -> np.ndarray:
        """`(n_rows, width)` -- every row's sentences pooled by `strategy`
        (§2.3's Pooling axis). `width` is this cache's own embedding
        dimension for `P1`/`P2`, twice that for `P3` -- taken from
        `self.vectors`, not assumed, so a non-BGE-dimensioned `embed_fn`
        (e.g. a unit-test stub) still pools an all-empty row to the right
        width instead of silently mismatching real rows.
        """
        width = self.vectors.shape[1] if self.vectors.shape[0] else EMBEDDING_DIM
        return np.stack(
            [
                pool_sentences(self.sentences_for_row(i), strategy, width=width)
                for i in range(len(self.row_ids))
            ]
        )


def pool_sentences(sentence_vectors: np.ndarray, strategy: str, *, width: int | None = None) -> np.ndarray:
    """Pool one response's per-sentence vectors into one feature vector, per
    the pre-registration §2.3 Pooling axis (`P1` mean, `P2` max, `P3` mean
    and max concatenated).

    A response with zero sentences pools to an all-zero vector -- an
    arbitrary placeholder that must never be read as a meaningful
    representation, mirroring `embed.pool_response_vector`'s own convention
    for the same case. This harness has no `effective`/D-4 short-circuit
    (that is a production concern), so a caller that cares whether a row had
    zero sentences must check `sentence_vectors.shape[0]` itself.

    `width` fixes the zero vector's dimension when `sentence_vectors` itself
    carries no columns to infer it from (a genuinely empty `(0, 0)` input).
    Callers that already know the embedding dimension (`SentenceEmbeddings.pooled`)
    should always pass it explicitly rather than relying on the
    `EMBEDDING_DIM` (BGE, 768) default, which is wrong for any other encoder.
    """
    if strategy not in POOLING_STRATEGIES:
        raise ValueError(f"unknown pooling strategy {strategy!r}, expected one of {POOLING_STRATEGIES}")

    vectors = np.asarray(sentence_vectors, dtype=np.float32)
    if vectors.ndim == 2 and vectors.shape[1]:
        # A 2D array always carries its true width in shape[1], even with
        # zero rows -- trust that over any caller-supplied `width` before
        # falling back to it.
        width = vectors.shape[1]
    elif width is None:
        width = EMBEDDING_DIM

    if vectors.shape[0] == 0:
        zero = np.zeros(width, dtype=np.float32)
        return np.concatenate([zero, zero]) if strategy == "P3" else zero

    if strategy == "P1":
        return vectors.mean(axis=0)
    if strategy == "P2":
        return vectors.max(axis=0)
    return np.concatenate([vectors.mean(axis=0), vectors.max(axis=0)])


def _content_sha256(row_ids: Sequence[str], texts: Sequence[str]) -> str:
    """Hashes the exact `(row_id, text)` pairs being embedded, in order --
    not just the model name/revision -- so a source-data change (a
    re-frozen split, a corrected row) invalidates the cache automatically
    instead of silently serving vectors for text that no longer matches.
    """
    payload = json.dumps(list(zip(row_ids, texts)), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_key(model_name: str, revision: str | None, content_sha256: str) -> str:
    basis = f"{model_name}|{revision or ''}|{content_sha256}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _cache_paths(cache_dir: pathlib.Path, key: str) -> tuple[pathlib.Path, pathlib.Path]:
    return cache_dir / f"{key}.npz", cache_dir / f"{key}.meta.json"


def _segment_responses(
    row_ids: Sequence[str], texts: Sequence[str]
) -> tuple[list[str], list[tuple[int, int]]]:
    all_segment_texts: list[str] = []
    row_ranges: list[tuple[int, int]] = []
    for text in texts:
        pieces = segment_text(str(text), max_chars=_SEGMENT_MAX_CHARS, stride=_SEGMENT_STRIDE)
        start = len(all_segment_texts)
        all_segment_texts.extend(piece.text for piece in pieces)
        row_ranges.append((start, len(all_segment_texts)))
    return all_segment_texts, row_ranges


def _load_cache(npz_path: pathlib.Path, meta_path: pathlib.Path) -> SentenceEmbeddings:
    meta = json.loads(meta_path.read_text())
    with np.load(npz_path) as data:
        vectors = data["vectors"]
        starts = data["row_starts"]
        ends = data["row_ends"]
    row_ids = tuple(meta["row_ids"])
    if len(row_ids) != len(starts):
        raise ValueError(
            f"cache corruption: {meta_path.name} names {len(row_ids)} rows but "
            f"{npz_path.name} has {len(starts)} row ranges"
        )
    row_ranges = tuple(zip((int(s) for s in starts), (int(e) for e in ends)))
    return SentenceEmbeddings(row_ids=row_ids, row_ranges=row_ranges, vectors=vectors)


def _write_cache(
    npz_path: pathlib.Path,
    meta_path: pathlib.Path,
    *,
    row_ids: Sequence[str],
    row_ranges: Sequence[tuple[int, int]],
    vectors: np.ndarray,
    model_name: str,
    revision: str | None,
    content_sha256: str,
) -> None:
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    starts = np.asarray([r[0] for r in row_ranges], dtype=np.int64)
    ends = np.asarray([r[1] for r in row_ranges], dtype=np.int64)
    np.savez(npz_path, vectors=vectors, row_starts=starts, row_ends=ends)
    meta_path.write_text(
        json.dumps(
            {
                "row_ids": list(row_ids),
                "model_name": model_name,
                "revision": revision,
                "content_sha256": content_sha256,
                "n_rows": len(row_ids),
                "n_sentences": int(vectors.shape[0]),
            },
            indent=2,
        )
        + "\n"
    )


def embed_responses(
    frame: pd.DataFrame,
    *,
    id_column: str = "prompt_uid",
    text_column: str = "response_text",
    model_name: str = DEFAULT_MODEL_NAME,
    revision: str | None = None,
    cache_dir: pathlib.Path = DEFAULT_CACHE_DIR,
    allow_download: bool = False,
    embed_fn: EmbedFn = embed_sentences,
) -> SentenceEmbeddings:
    """One embedding pass over every row of `frame`, cached to disk.

    Segments each row's `text_column` the same way `embed.build_component_features`
    does, embeds every sentence of every row in one batched call, and caches
    the ragged per-sentence result keyed by model name, revision, and the
    exact content embedded (`_content_sha256`) -- so a second call with the
    same rows and model is a cache hit, and a changed source (or a different
    `frame`) is a cache miss rather than stale data.

    **Offline by default** (`allow_download=False`, matching `embed_sentences`):
    the first call on a machine without the cached BGE weights needs
    `allow_download=True`. Do that once, while building the cache -- never
    pass it inside the comparison loop itself, since every candidate reuses
    this same cached pass.

    `embed_fn` defaults to the real `embed_sentences` and exists so unit tests
    can substitute a stub instead of requiring the real BGE model
    (`PLAN.md` §8.1's "unit tests need no model download" rule).
    """
    if id_column not in frame.columns:
        raise ValueError(f"frame has no {id_column!r} column")
    if text_column not in frame.columns:
        raise ValueError(f"frame has no {text_column!r} column")
    if not frame[id_column].is_unique:
        raise ValueError(f"{id_column!r} must be unique per row -- it is the cache's row identity")

    row_ids = tuple(str(v) for v in frame[id_column])
    texts = tuple(str(v) for v in frame[text_column])
    content_sha256 = _content_sha256(row_ids, texts)
    key = _cache_key(model_name, revision, content_sha256)
    npz_path, meta_path = _cache_paths(pathlib.Path(cache_dir), key)

    if npz_path.exists() and meta_path.exists():
        return _load_cache(npz_path, meta_path)

    all_segment_texts, row_ranges = _segment_responses(row_ids, texts)
    vectors = embed_fn(
        all_segment_texts,
        model_name=model_name,
        revision=revision,
        allow_download=allow_download,
    )

    _write_cache(
        npz_path,
        meta_path,
        row_ids=row_ids,
        row_ranges=row_ranges,
        vectors=vectors,
        model_name=model_name,
        revision=revision,
        content_sha256=content_sha256,
    )
    return SentenceEmbeddings(row_ids=row_ids, row_ranges=tuple(row_ranges), vectors=vectors)
