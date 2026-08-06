"""The record of a fit: what was fitted, and everything a later run needs to
reproduce or audit it (`docs/planning/PR5_EXECUTION_PLAN.md` §5, §6;
`ARCHITECTURE.md` §10).

**Pure data, and deliberately component-free.** `features.py` imports the
pipeline's concrete components to *produce* a fit; `artifact.py` must be able
to read one back without dragging any of them in, because slice C's scoring
component is downstream of the reader. Keeping these three types here rather
than in `release.py` is what makes that possible.

PR 5's exit criterion "runs reproduce results from locked model, rule, data,
split, and metric versions" is met by `FitProvenance`'s field set or it is
not met.
"""

from __future__ import annotations

import dataclasses
from typing import Mapping

from .multinomial import TargetModel

__all__ = ["ComponentRecord", "FitProvenance", "LEModels"]


@dataclasses.dataclass(frozen=True)
class ComponentRecord:
    """One pipeline stage as it stood when the training text was produced.

    **This is not bookkeeping.** `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5's work
    list records a standing obligation -- three of the components that filter
    the working view are placeholders in 1.1, so "the working text a 1.1
    model is fitted on is not the text a release with working narrative,
    refusal, and hazard detection will produce. **A re-fit is owed whenever
    any of them is built.**" Recording each stage's implementation, version,
    and maturity in the artifact is what turns that obligation from something
    a future session has to remember into something it can *check*: compare
    the artifact's training component set against the run's, and a re-fit is
    owed exactly where they differ.
    """

    stage: str
    implementation: str
    version: str
    maturity: str


@dataclasses.dataclass(frozen=True)
class FitProvenance:
    """What produced a fit, in the form `manifest.json` carries it.

    Every field here is either a locked decision's subject or the thing that
    makes the decision auditable after the fact:

    - `split_half`/`split_role` -- [D-73](../../../docs/planning/DECISIONS.md#d-73).
      Both vocabularies are recorded because `interim_data` says
      `train`/`eval` where `PREREGISTRATION_LE_STRUCTURE.md` says *fit*/*dev*,
      and silently confusing the two fits on the held-out rows.
    - `text_view` -- [D-72](../../../docs/planning/DECISIONS.md#d-72).
    - `embedding_*`/`pooling` -- [D-23](../../../docs/planning/DECISIONS.md#d-23):
      serve time reads the encoder identity from the artifact, never a
      hardcoded default.
    - `components` -- see `ComponentRecord`.
    - `exhausted_excluded` -- rows the evaluator could never score, kept out
      of the fit and counted rather than silently dropped.
    """

    source_path: str
    source_sha256: str
    split_path: str
    split_version: str
    split_half: str  # the loader's word: "train" | "eval"
    split_role: str  # the pre-registration's word: "fit" | "dev"
    text_view: str
    embedding_provider: str
    embedding_provider_version: str
    embedding_model_name: str | None
    embedding_model_revision: str | None
    pooling: str
    seed: int
    estimator: Mapping[str, object]
    components: tuple[ComponentRecord, ...]
    n_feature_rows: int
    exhausted_excluded: tuple[tuple[str, str, str], ...]  # (prompt_uid, hazard, stage)


@dataclasses.dataclass(frozen=True)
class LEModels:
    """Both fitted targets plus the provenance of the fit that produced them.

    Held together because they are fitted from one feature pass and shipped
    in one artifact -- but they are **separate models** (`S1`), and neither
    reads the other.
    """

    legitimization: TargetModel
    enablement: TargetModel
    provenance: FitProvenance

    @property
    def supported_hazards(self) -> frozenset[str]:
        """Every hazard with **at least one** fitted cell, across both
        targets. This is the artifact's frozen supported set and therefore
        what `hazard_scope` defaults to
        ([D-57](../../../docs/planning/DECISIONS.md#d-57)).

        The union rather than the intersection, deliberately: Legitimization
        does not apply to `prv`/`sxc_prn` at all (`SCIENCE.md` phase A), so
        an intersection would drop two hazards the evaluator can and must
        still score for Enablement.
        """
        return self.legitimization.supported_hazards | self.enablement.supported_hazards
