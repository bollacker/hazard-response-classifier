"""The carried record (`docs/ARCHITECTURE.md` §4, plus the text-view shape
from §5): `Result`, `FlagState`, `TextViews`, `Flags`, `Judgment`,
`HazardJudgment`, `ComponentObservation`, `EvaluationRecord`.

**Pure data. No logic, no imports from anywhere else in `evaluator/`**
(`ARCHITECTURE.md` §3.2's dependency rule) -- enforced structurally by
`tests/unit/test_evaluator_record.py`, not just by convention here.

Every record type is a frozen dataclass. There is no in-place mutation
anywhere in this module; a stage that wants to "update" a record calls
`dataclasses.replace(record, ...)`, which frozen dataclasses support natively
and which always returns a new instance, leaving the original untouched
(`ARCHITECTURE.md` §4: "updated immutably by each stage"). Dict-shaped
fields (`Flags.narrative_subtypes`, `TextViews.named`,
`ComponentObservation.facts`, `EvaluationRecord.per_hazard`) are coerced to
`types.MappingProxyType` in `__post_init__` so the same guarantee holds one
level down: a caller cannot mutate a record's dict-shaped field in place
even though `replace()` only does a shallow copy.
"""

from __future__ import annotations

import dataclasses
from types import MappingProxyType
from typing import Literal, Mapping

# `ARCHITECTURE.md` §3.2: the 1.1 result vocabulary, replacing the
# baseline's `safe`/`unsafe` (D-30, sub-review 1.1). The baseline keeps its
# own encoding in its own schema; see ARCHITECTURE.md §3.2 for the mapping
# where a view needs both.
Result = Literal["violating", "non_violating", "failure"]

# `ARCHITECTURE.md` §3.1: every flag is three-valued, not boolean, so a
# placeholder or a stage the exhaustion short-circuit skipped is visibly
# distinct from a stage that ran and found nothing.
FlagState = Literal["detected", "not_detected", "not_evaluated"]


def _frozen_mapping(value: Mapping) -> Mapping:
    """Coerce any mapping into a read-only `MappingProxyType` copy, so a
    dict-shaped dataclass field can't be mutated in place after construction
    even though the frozen dataclass itself only blocks attribute
    reassignment, not mutation of a mutable value it holds.
    """
    if isinstance(value, MappingProxyType):
        return value
    return MappingProxyType(dict(value))


@dataclasses.dataclass(frozen=True)
class TextStep:
    """One entry in `TextViews.history`: the stage that produced this text
    and the text that resulted. Not named explicitly in `ARCHITECTURE.md`
    §5's `history: tuple[TextStep, ...]` line beyond the type name -- this
    is the minimal (stage, text) pair that line requires.
    """

    stage: str
    text: str


@dataclasses.dataclass(frozen=True)
class TextViews:
    """`ARCHITECTURE.md` §5: named text views rather than one string the
    stages overwrite, so each consumer names the view it wants.
    """

    original: str
    decoded: str
    working: str
    history: tuple[TextStep, ...] = ()
    named: Mapping[str, str] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "named", _frozen_mapping(self.named))


@dataclasses.dataclass(frozen=True)
class Flags:
    """`ARCHITECTURE.md` §4. Every scalar flag defaults to `"not_evaluated"`
    -- the "nothing has looked yet" state -- never `"not_detected"`, which
    would falsely claim a stage ran and found nothing.
    """

    empty_payload: FlagState = "not_evaluated"
    decoding_failed: FlagState = "not_evaluated"
    prompt_repetition: FlagState = "not_evaluated"
    narrative: FlagState = "not_evaluated"
    narrative_subtypes: Mapping[str, FlagState] = dataclasses.field(default_factory=dict)
    refusal: FlagState = "not_evaluated"
    sa_disclaimer: FlagState = "not_evaluated"

    def __post_init__(self) -> None:
        object.__setattr__(self, "narrative_subtypes", _frozen_mapping(self.narrative_subtypes))


@dataclasses.dataclass(frozen=True)
class Judgment:
    """`ARCHITECTURE.md` §4. `distribution` is optional: two binary heads
    cannot produce a three-class multinomial, and deriving one from
    thresholded (not monotone-guaranteed-on-raw-probability) decisions is
    unsafe (D-9/D-10), so the wrapped baseline reports `distribution=None`
    rather than a synthesized value (D-45's principle applied to a model
    output). PR 5's real three-class model is the first implementation that
    fills it.
    """

    label: str
    distribution: tuple[float, float, float] | None
    model_version: str


@dataclasses.dataclass(frozen=True)
class HazardJudgment:
    """`ARCHITECTURE.md` §4, built in two passes.

    **Pass 1, stage 9 (scoring):** the L/E models write `provisional_l` and
    `provisional_e` (either may be `None` -- L is absent for an
    enablement-only hazard, and either is absent when the model could not
    produce it). Nothing else is known yet.

    **Pass 2, stage 10 (final integration):** the fixed phases write
    `final_l`/`final_e`, `decided_by`, and `result`.

    So `decided_by` and `result` default to `None`, meaning "final
    integration has not run for this hazard yet" -- resolved here rather
    than in slice 1A, whose scope explicitly excluded the pipeline data
    flow that made the question answerable. A `None` `result` is never a
    finished output: `views.py` and the rollup both treat reaching one as a
    programming error, not as a third outcome alongside
    violating/non-violating.
    """

    hazard: str
    source: Literal["supplied", "detected"]
    legitimization_applies: bool
    provisional_l: Judgment | None = None
    provisional_e: Judgment | None = None
    final_l: Literal["L0", "L1", "L2", "N/A"] | None = None
    final_e: Literal["E0", "E1", "E2"] | None = None
    decided_by: Literal["A", "B1", "B2", "C"] | None = None
    result: Result | None = None
    failure_reason: str | None = None


@dataclasses.dataclass(frozen=True)
class ComponentError:
    """Not spelled out field-by-field in `ARCHITECTURE.md` beyond its name
    and its use (`ComponentObservation.error`, and §6's no-fallback rule:
    "it records a per-hazard `ComponentError`"). This is the minimal shape
    that use requires: which stage raised it, a human-readable message, and
    the hazard it's scoped to when the error is hazard-specific rather than
    record-wide (e.g. a whole-response decoding failure has no single
    hazard to name).
    """

    stage: str
    message: str
    hazard: str | None = None


@dataclasses.dataclass(frozen=True)
class ComponentObservation:
    """`ARCHITECTURE.md` §4: one entry per stage that ran, in execution
    order, recording what it did -- never what it decided (§6: "assigns no
    final result, applies no exception, makes no applicability decision").
    """

    stage: str
    implementation: str
    version: str
    maturity: Literal["working", "partial", "placeholder"]
    outcome: Literal["ran", "skipped_short_circuit", "not_evaluated", "error"]
    facts: Mapping[str, object]
    text_out: str | None
    error: ComponentError | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts", _frozen_mapping(self.facts))


@dataclasses.dataclass(frozen=True)
class EvaluationRecord:
    """`ARCHITECTURE.md` §4: one record per (response, run), built once at
    run entry and updated immutably by every stage. The record is
    canonical; every output (`ARCHITECTURE.md` §11) is a view derived from
    it, never the record itself.

    `run` is typed as `object` here rather than `run.RunContext` to hold
    §3.2's dependency rule exactly as stated -- "`record.py` imports nothing
    from this package" -- rather than the narrower "imports nothing except
    what it structurally needs." `run.py` imports `EvaluationRecord`'s
    sibling types from here freely; the reverse import is what the rule
    forbids, so `RunContext`'s actual shape is enforced only where a real
    `RunContext` is constructed and attached, not by this field's
    annotation.
    """

    # identity
    request_id: str
    prompt_uid: str
    response_id: str

    # inputs, never mutated
    prompt_text: str
    response_text: str
    supplied_hazard: str

    # run context (a `run.RunContext`; see the class docstring for why this
    # is typed loosely)
    run: object

    # text
    texts: TextViews
    exhausted_at: str | None

    # component observations, in execution order
    observations: tuple[ComponentObservation, ...]

    # hazards
    detected_hazards: tuple[str, ...]
    evaluated_hazards: tuple[str, ...]

    # flags, accumulated
    flags: Flags

    # judgments
    per_hazard: Mapping[str, HazardJudgment]
    overall_result: Result
    overall_failure_reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "per_hazard", _frozen_mapping(self.per_hazard))
