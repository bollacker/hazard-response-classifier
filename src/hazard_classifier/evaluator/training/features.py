"""The serve-time feature path, run offline for fitting
(`docs/planning/PR5_EXECUTION_PLAN.md` §5;
[D-72](../../../docs/planning/DECISIONS.md#d-72)).

`SCIENCE.md` §Legitimization Training and §Enablement Training both require
the models be trained "on human ground truth using **working text filtered
through the preceding components**". The structure selection behind D-68 was
not: `experiments/features.py` embeds the interim frame's raw `response_text`
with no decoding pass and no prompt-repetition removal. This module closes
that gap by producing training features the only way that can be shown to
match serve time -- **by running the real stages**.

Stages 1-7 are the pipeline's own components, in `pipeline.STAGE_ORDER`, with
`ARCHITECTURE.md` §3.1's exhaustion short-circuit applied; stage 8 is the
real `EmbeddingComponent`, one `provider.embed(...)` call per record over the
segments of the resolved text view, pooled by the real `PoolingStrategy`.
Nothing here re-implements segmentation, pooling, or text handling, so there
is no second implementation to drift from the one that scores.

**Exhausted rows are excluded from fitting, and the exclusion is recorded.**
A row whose working text empties in stages 1-7 is decided by `SCIENCE.md`
phase B1 and never reaches stage 9, so no L/E model ever scores it -- while
it still carries a human L/E label a naive fit would happily train on.
`scripts/probe_working_text_delta.py` measured **zero** such rows across all
859 interim rows, so this changes no number today; it is here because a fit
that silently trained on rows the evaluator cannot score would be invisible
in every output.

**Cost, stated so it is not rediscovered.** One `provider.embed` call per
row, matching stage 8 exactly rather than batching across rows for speed.
The full 859-row interim frame takes a few minutes on CPU. Fitting reads
these features once, outside any per-cell loop.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from ..components.decoding import Decoder
from ..components.disclaimer import DisclaimerDetector
from ..components.embedding import (
    POOLED_VECTOR_FACT,
    BgeEmbeddingProvider,
    EmbeddingComponent,
    EmbeddingProvider,
    MeanPooling,
    PoolingStrategy,
)
from ..components.empty import EmptyResponseDetector
from ..components.hazard import HazardDetectionPlaceholder
from ..components.narrative import NarrativeDetectionPlaceholder
from ..components.refusal import RefusalDetectionPlaceholder
from ..components.repetition import PromptRepetitionDetector
from ..pipeline import STAGE_ORDER
from ..record import EvaluationRecord, Flags, TextViews
from .provenance import ComponentRecord

__all__ = ["ExhaustedRow", "PipelineFeatures", "build_pipeline_features"]

# Stages 1-7: everything that can rewrite the working view. Keyed by stage
# name and ordered below by `STAGE_ORDER` itself, so a stage added to the
# pipeline is a loud `KeyError` here rather than a silently skipped step.
_TEXT_STAGE_COMPONENTS = {
    "empty_response": EmptyResponseDetector,
    "decoding": Decoder,
    "hazard_detection": HazardDetectionPlaceholder,
    "prompt_repetition": PromptRepetitionDetector,
    "narrative_detection": NarrativeDetectionPlaceholder,
    "refusal_detection": RefusalDetectionPlaceholder,
    "disclaimer_detection": DisclaimerDetector,
}

_TEXT_STAGES: tuple[str, ...] = STAGE_ORDER[:7]
_EMBEDDING_STAGE = STAGE_ORDER[7]

if set(_TEXT_STAGE_COMPONENTS) != set(_TEXT_STAGES) or _EMBEDDING_STAGE != "embedding":
    # Not a defensive `if` -- a real structural claim. `STAGE_ORDER` is the
    # single source of truth for the pipeline's shape, and this module's
    # fidelity to serve time depends on covering every text stage it names.
    raise AssertionError(
        "training/features.py no longer covers the pipeline's text stages: "
        f"STAGE_ORDER[:8] is {STAGE_ORDER[:8]}, this module knows "
        f"{sorted(_TEXT_STAGE_COMPONENTS)} plus {_EMBEDDING_STAGE!r}"
    )

_REQUIRED_COLUMNS = ("prompt_uid", "hazard", "prompt_text", "response_text")


@dataclasses.dataclass(frozen=True)
class ExhaustedRow:
    """A row whose working text emptied in stages 1-7, and the stage that
    emptied it. Excluded from fitting; recorded so the exclusion is countable
    rather than invisible.
    """

    prompt_uid: str
    hazard: str
    exhausted_at: str


@dataclasses.dataclass(frozen=True)
class PipelineFeatures:
    """Features for exactly the rows the evaluator would score.

    `pooled[i]` is the vector stage 8 publishes for `prompt_uids[i]` --
    the same array stage 9 reads at serve time, produced by the same
    components from the same text view.
    """

    prompt_uids: tuple[str, ...]
    hazards: np.ndarray
    working_texts: tuple[str, ...]
    pooled: np.ndarray  # (n_rows, n_features)
    exhausted_rows: tuple[ExhaustedRow, ...]
    text_view: str
    provider_name: str
    provider_version: str
    provider_model_name: str | None
    provider_model_revision: str | None
    pooling_name: str
    components: tuple[ComponentRecord, ...]

    @property
    def n_features(self) -> int:
        return int(self.pooled.shape[1])

    def row_index(self) -> dict[str, int]:
        """`prompt_uid -> row position`, for selecting a target's eligible
        subset without reordering or re-embedding anything.
        """
        return {uid: i for i, uid in enumerate(self.prompt_uids)}


def _blank_record(prompt_uid: str, prompt: str, response: str, hazard: str) -> EvaluationRecord:
    """The record stage 1 would receive for this row. `run` is `None`: no
    stage 1-8 component reads it, and fitting has no `RunContext` -- the
    artifact this fit produces is what a later run's context will name.
    """
    return EvaluationRecord(
        request_id=prompt_uid,
        prompt_uid=prompt_uid,
        response_id=prompt_uid,
        prompt_text=prompt,
        response_text=response,
        supplied_hazard=hazard,
        run=None,
        texts=TextViews(original=response, decoded=response, working=response),
        exhausted_at=None,
        observations=(),
        detected_hazards=(),
        evaluated_hazards=(hazard,),
        flags=Flags(),
        per_hazard={},
        overall_result="failure",
        overall_failure_reason="not scored: this record exists only to build training features",
    )


def _run_text_stages(
    record: EvaluationRecord, components: dict[str, object]
) -> tuple[EvaluationRecord, str | None]:
    """Stages 1-7 in `STAGE_ORDER` order, with §3.1's exhaustion
    short-circuit. Returns the record and the stage that exhausted it, or
    `None`.
    """
    for stage in _TEXT_STAGES:
        record = components[stage].run(record)
        if record.texts.working.strip() == "":
            return dataclasses.replace(record, exhausted_at=stage), stage
    return record, None


def _pooled_vector(record: EvaluationRecord) -> np.ndarray:
    for observation in reversed(record.observations):
        if observation.stage == _EMBEDDING_STAGE:
            return np.asarray(observation.facts[POOLED_VECTOR_FACT])
    raise AssertionError("stage 8 ran but published no pooled vector")


def build_pipeline_features(
    frame: pd.DataFrame,
    *,
    provider: EmbeddingProvider | None = None,
    pooling: PoolingStrategy | None = None,
    text_view: str = "working",
    allow_download: bool = False,
) -> PipelineFeatures:
    """Run stages 1-8 over every row of `frame` and return the features the
    L/E models are fitted on.

    `frame` needs `prompt_uid`, `hazard`, `prompt_text`, and `response_text`
    -- the columns `interim_data.load_interim` supplies.

    `provider`/`pooling` default to the real `BgeEmbeddingProvider` and
    `MeanPooling`, the same pair `profile.build_registry` gives stage 8, so
    the default path is serve time's. **Offline by default** (D-6): the first
    call on a machine without cached BGE weights needs `allow_download=True`,
    once, outside any loop. A test may substitute a stub, exactly as this
    project's other component tests do.

    `text_view` is stage 8's construction parameter (D-69, D-74) and defaults
    to `working` (D-55, D-72) -- the view the release scores.
    """
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"frame is missing required column(s) {missing}")
    if not frame["prompt_uid"].is_unique:
        raise ValueError("prompt_uid must be unique per row -- it is the feature row's identity")

    components: dict[str, object] = {
        stage: _TEXT_STAGE_COMPONENTS[stage]() for stage in _TEXT_STAGES
    }
    embedding_provider = provider or BgeEmbeddingProvider(allow_download=allow_download)
    pooling_strategy = pooling or MeanPooling()
    embedding = EmbeddingComponent(embedding_provider, pooling_strategy, text_view=text_view)

    prompt_uids: list[str] = []
    hazards: list[str] = []
    working_texts: list[str] = []
    vectors: list[np.ndarray] = []
    exhausted: list[ExhaustedRow] = []

    for row in frame.itertuples(index=False):
        prompt_uid = str(row.prompt_uid)
        hazard = str(row.hazard)
        record = _blank_record(prompt_uid, str(row.prompt_text), str(row.response_text), hazard)

        record, exhausted_at = _run_text_stages(record, components)
        if exhausted_at is not None:
            exhausted.append(
                ExhaustedRow(prompt_uid=prompt_uid, hazard=hazard, exhausted_at=exhausted_at)
            )
            continue

        record = embedding.run(record)
        prompt_uids.append(prompt_uid)
        hazards.append(hazard)
        working_texts.append(record.texts.working)
        vectors.append(_pooled_vector(record))

    if not vectors:
        raise ValueError(
            "every row exhausted in stages 1-7, so there are no rows the evaluator "
            "would score and nothing to fit on"
        )

    return PipelineFeatures(
        prompt_uids=tuple(prompt_uids),
        hazards=np.asarray(hazards),
        working_texts=tuple(working_texts),
        pooled=np.stack(vectors).astype(np.float64),
        exhausted_rows=tuple(exhausted),
        text_view=text_view,
        provider_name=embedding_provider.name,
        provider_version=embedding_provider.version,
        # `EmbeddingProvider` does not require these -- but D-23 makes the
        # encoder's identity the artifact's to carry, so they are read off
        # the concrete provider where it exposes them rather than left to a
        # serve-time default a caller could forget to override.
        provider_model_name=getattr(embedding_provider, "model_name", None),
        provider_model_revision=getattr(embedding_provider, "revision", None),
        pooling_name=pooling_strategy.name,
        components=_component_records(components, embedding),
    )


def _component_records(
    text_components: dict[str, object], embedding: EmbeddingComponent
) -> tuple[ComponentRecord, ...]:
    """The stages that produced this training text, as they stood, in
    `STAGE_ORDER`. See `ComponentRecord`: this is what makes PR 5's standing
    "a re-fit is owed when narrative, refusal, or hazard detection is built"
    checkable against an artifact rather than remembered.
    """
    ordered: list[object] = [text_components[stage] for stage in _TEXT_STAGES]
    ordered.append(embedding)
    return tuple(
        ComponentRecord(
            stage=component.stage,
            implementation=component.implementation,
            version=component.version,
            maturity=component.maturity,
        )
        for component in ordered
    )
