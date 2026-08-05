"""Stage 8: the shared embedding boundary (`docs/ARCHITECTURE.md` §8).

`EmbeddingProvider` and `PoolingStrategy` are separate replaceable
protocols on purpose: representation and pooling are both named comparison
axes for queue item 2, so this boundary must not hard-code either (D-36 is
baseline-only for exactly this reason).

**One embed call per record, shared across every evaluated hazard.** The
component segments the current working text once, makes exactly one
`provider.embed(...)` call over those segments, pools them once, and
publishes the result for stage 9 to read for every hazard. Re-embedding per
hazard is a defect, not a tuning choice (§8).

**A 1.1 behavior difference from the baseline, by design.** The baseline
pools *two* different vectors per response -- Enablement drops
prompt-repetition sentences before pooling (`embed.enablement_keep_mask`,
D-4) while Legitimization keeps every sentence. In the 1.1 pipeline stage 4
has already **removed** repeated spans from the working text
(`ARCHITECTURE.md` §7.1), so there is nothing left for a component-specific
keep-mask to drop, and both models read the same `working` view (§5's
stated default). One pooled vector per response is therefore the correct
1.1 shape, not a simplification of the baseline's two.

**The text view is a construction argument, not a hard-coded attribute
access** (`docs/planning/DECISIONS.md` D-69, `ARCHITECTURE.md` §5). Stage 8
is the only stage that reads a text view, so it is selected once per record
here rather than once per model. `text_view` defaults to `"working"` --
1.1's default per D-55 -- and the resolved view is recorded in this
component's observation (`text_view` in `facts`) so a result names the text
its models actually saw. The three `TextViews` attributes (`original`,
`decoded`, `working`) and `disclaimer_stripped` -- the only `named` view any
1.1 component publishes (`disclaimer.py`) -- are the closed set §5 currently
defines; anything else is rejected at construction rather than silently
falling back to `working` (§6's no-fallback rule, generalized to a
misconfiguration that would fail every row identically).
"""

from __future__ import annotations

import dataclasses
from typing import ClassVar, Protocol, Sequence

import numpy as np

from hazard_classifier.preprocess import segment as segment_module

from ..contract import Maturity
from ..record import ComponentObservation, EvaluationRecord

# The key stage 9 reads the pooled response vector back out of. Stages
# communicate through the record, never by importing each other (§6).
POOLED_VECTOR_FACT = "pooled_vector"
SEGMENT_COUNT_FACT = "segment_count"
TEXT_VIEW_FACT = "text_view"

# `TextViews`' three reserved attributes -- always present, so membership
# here is checkable at construction (`docs/planning/DECISIONS.md` D-69).
_RESERVED_TEXT_VIEWS = frozenset({"original", "decoded", "working"})

# The `named` views any 1.1 component actually publishes. `TextViews.named`
# is populated per record, so whether a *given record* carries a key can
# never be confirmed at construction -- but which keys 1.1's components can
# publish at all is closed and static, and validating construction against
# that closed set is what stops a typo from reaching every row identically
# (`ARCHITECTURE.md` §5's Traps: "reserved names are checkable in __init__;
# a named key is not [confirmable against a real record], since
# `TextViews.named` is filled per record"). `disclaimer_stripped` is the
# only one 1.1 ships (`disclaimer.py`, D-55).
_KNOWN_NAMED_TEXT_VIEWS = frozenset({"disclaimer_stripped"})


class EmbeddingProvider(Protocol):
    """`ARCHITECTURE.md` §8."""

    name: ClassVar[str]
    version: ClassVar[str]

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


class PoolingStrategy(Protocol):
    """`ARCHITECTURE.md` §8."""

    name: ClassVar[str]

    def pool(self, vectors: np.ndarray) -> np.ndarray: ...


class BgeEmbeddingProvider:
    """The baseline's BGE encoder (`embed.embed_sentences`, CPU-only per
    D-6) behind §8's provider protocol. `embedding_dim` is read from the
    baseline rather than restated, so the two cannot drift.
    """

    name: ClassVar[str] = "bge_base_en_v1_5"
    version: ClassVar[str] = "1"

    def __init__(
        self,
        *,
        model_name: str | None = None,
        revision: str | None = None,
        allow_download: bool = False,
    ) -> None:
        from hazard_classifier.config import DEFAULT_EMBEDDING_MODEL_NAME

        self.model_name = model_name or DEFAULT_EMBEDDING_MODEL_NAME
        self.revision = revision
        self.allow_download = allow_download

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        from hazard_classifier.embed import embed_sentences

        return embed_sentences(
            list(texts),
            model_name=self.model_name,
            revision=self.revision,
            allow_download=self.allow_download,
        )


class MeanPooling:
    """Mean pooling, matching the baseline's `pool_response_vector` (D-36's
    mean-only choice) but as a *replaceable strategy* rather than a fixed
    step, per §8.
    """

    name: ClassVar[str] = "mean"

    def pool(self, vectors: np.ndarray) -> np.ndarray:
        from hazard_classifier.embed import EMBEDDING_DIM

        if vectors.shape[0] == 0:
            return np.zeros(
                vectors.shape[1] if vectors.ndim > 1 and vectors.shape[1] else EMBEDDING_DIM,
                dtype=np.float32,
            )
        return vectors.mean(axis=0).astype(np.float32)


class EmbeddingComponent:
    stage: ClassVar[str] = "embedding"
    implementation: ClassVar[str] = "shared_single_pass"
    version: ClassVar[str] = "1"
    maturity: ClassVar[Maturity] = "working"

    def __init__(
        self,
        provider: EmbeddingProvider,
        pooling: PoolingStrategy,
        *,
        text_view: str = "working",
    ) -> None:
        if text_view not in _RESERVED_TEXT_VIEWS and text_view not in _KNOWN_NAMED_TEXT_VIEWS:
            raise ValueError(
                f"unknown text_view {text_view!r}; expected one of "
                f"{sorted(_RESERVED_TEXT_VIEWS | _KNOWN_NAMED_TEXT_VIEWS)}"
            )
        self.provider = provider
        self.pooling = pooling
        self.text_view = text_view

    def _resolve_text(self, texts) -> str:
        """Resolve `self.text_view` against `texts` (`record.texts`).

        Deliberately not a blind `getattr` -- that would make any
        `TextViews` attribute name (e.g. `"history"`) a valid "view". A
        reserved name always resolves; a `named` lookup is the one case
        unreachable in 1.1 (`disclaimer_stripped` is always published by
        stage 7 before stage 8 runs, and if stage 7 did not run the record
        was exhausted and stage 8 is skipped) -- so a missing key here is
        left to raise `KeyError` rather than given a fallback-to-`working`
        path nothing can exercise (§6: never substitute silently).
        """
        if self.text_view in _RESERVED_TEXT_VIEWS:
            return getattr(texts, self.text_view)
        return texts.named[self.text_view]

    def run(self, record: EvaluationRecord) -> EvaluationRecord:
        text_to_embed = self._resolve_text(record.texts)
        segments = segment_module.segment_text(text_to_embed, max_chars=420, stride=210)
        texts = [piece.text for piece in segments]

        # Exactly one call, covering every segment of this response, whose
        # result is shared by every evaluated hazard downstream.
        vectors = self.provider.embed(texts)
        pooled = self.pooling.pool(vectors)

        observation = ComponentObservation(
            stage=self.stage,
            implementation=self.implementation,
            version=self.version,
            maturity=self.maturity,
            outcome="ran",
            facts={
                POOLED_VECTOR_FACT: pooled,
                SEGMENT_COUNT_FACT: len(texts),
                "provider": self.provider.name,
                "pooling": self.pooling.name,
                TEXT_VIEW_FACT: self.text_view,
            },
            text_out=None,
            error=None,
        )

        return dataclasses.replace(record, observations=record.observations + (observation,))
