"""The run profile and artifact resolution
(`docs/planning/PR7_EXECUTION_PLAN.md` §5, `docs/ARCHITECTURE.md` §2, §5,
§10; [D-57](../../docs/planning/DECISIONS.md#d-57),
[D-69](../../docs/planning/DECISIONS.md#d-69),
[D-74](../../docs/planning/DECISIONS.md#d-74)).

**This is the only PR 7 module that imports `components/*`.** The runner
(slice C) must select components only through the registry and never import
a concrete one (§1's standing constraint) -- `build_registry` below is the
one nameable place that owns those imports, exactly as
`experiments/candidates.py::_assert_no_fixed_rule_import` makes its own
constraint a real, checkable assertion rather than a comment
(`tests/unit/test_evaluator_profile.py` parses every other module in this
package and asserts none of them import `.components`).

**`text_view` is a construction parameter, not a second selection
mechanism** (D-69, D-74). It flows exactly one way: `RunProfile.text_view` ->
`build_registry` -> `EmbeddingComponent(provider, pooling, text_view=...)`.
It is never a `RunConfig`/`RunContext` field and never a registry key --
`run.py` is untouched by this module.

**`hazard_scope` defaults to the artifact's frozen supported set, resolved
here, not in `run.open_run`** (D-57). `open_run` keeps receiving a concrete
scope either way, so `RunContext` always carries a resolved one and
`ARCHITECTURE.md` §2's invariant holds regardless of whether a profile
supplied an explicit scope.

**Artifact resolution handles both formats** (PR 5 slice C; the 1.1 format is
[D-49](../../docs/planning/DECISIONS.md#d-49)'s deliverable, built in slice
B). `resolve_artifact` dispatches on `artifact.is_evaluator_artifact` -- the
1.1 `manifest.json` declares a `format`, the baseline's has no such key -- and
`build_registry` selects the stage-9 implementation to match: a 1.1 artifact
gets `MultinomialPerHazardScorer` (**working**, real three-class
distributions), a baseline artifact gets `BaselineTwoHeadScorer`
(**partial**, `distribution=None`).

**Both scorers stay registered either way.** §6 keys the registry on
`(stage, implementation_id)`, so a profile's `component_selection` can name
either -- but only the one matching the loaded artifact can actually score,
because the other has no model to score with. `build_registry` therefore
registers exactly the one its artifact supports, and a profile naming the
other is rejected by `open_run`'s registry validation with a message naming
it, rather than failing every row at stage 9.

**`rule_version` comes from the `RuleSet` actually used, never a literal
typed into a profile that could drift from it** (§5's stated trap).
`build_registry` constructs the `RuleSet` from the resolved artifact's own
frozen hazard-family sets and reports its `version` back; nothing here
accepts a `rule_version` string from the profile file.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Mapping, NamedTuple

from ..model import HazardResponseClassifier
from ..model import load as _load_baseline_artifact
from .artifact import EvaluatorArtifact, is_evaluator_artifact, load_artifact
from .components.decoding import Decoder
from .components.disclaimer import DisclaimerDetector
from .components.embedding import (
    BgeEmbeddingProvider,
    EmbeddingComponent,
    EmbeddingProvider,
    MeanPooling,
    PoolingStrategy,
)
from .components.empty import EmptyResponseDetector
from .components.hazard import HazardDetectionPlaceholder
from .components.integration import FinalIntegrator, RuleSet
from .components.narrative import NarrativeDetectionPlaceholder
from .components.refusal import RefusalDetectionPlaceholder
from .components.repetition import PromptRepetitionDetector
from .components.scoring import BaselineTwoHeadScorer, MultinomialPerHazardScorer
from .pipeline import STAGE_ORDER
from .registry import Registry
from .run import RunConfig, RunContext, open_run

__all__ = [
    "RunProfile",
    "ProfileError",
    "load_profile",
    "resolve_artifact",
    "BuiltRegistry",
    "build_registry",
    "ResolvedRun",
    "resolve",
]


class ProfileError(ValueError):
    """A structural problem with a run profile: a missing required field."""


@dataclasses.dataclass(frozen=True)
class RunProfile:
    """What a run needs, and what it can resolve rather than state
    (`PR7_EXECUTION_PLAN.md` §5). Provenance a consumer should be able to
    diff -- `load_profile` reads this shape from JSON, and a CLI (slice D)
    may override individual fields from flags before calling `resolve`.

    - `artifact_id`: the baseline artifact directory `resolve_artifact`
      loads (D-49).
    - `hazard_scope`: `None` means "default to the artifact's frozen
      supported set" (D-57); an explicit, narrower set may be supplied. A
      *wider* scope is not rejected here -- that stays `open_run`'s
      condition-(2) rejection, unchanged.
    - `component_selection`: `None` means "use `build_registry`'s defaults
      for every stage"; a partial mapping overrides only the named stages.
    - `text_view`: the construction parameter `build_registry` passes to
      `EmbeddingComponent` (D-69, D-74). Defaults to `working` (D-55).
    """

    artifact_id: str
    hazard_scope: frozenset[str] | None = None
    component_selection: Mapping[str, str] | None = None
    text_view: str = "working"

    def __post_init__(self) -> None:
        if self.hazard_scope is not None:
            object.__setattr__(self, "hazard_scope", frozenset(self.hazard_scope))
        if self.component_selection is not None:
            object.__setattr__(self, "component_selection", dict(self.component_selection))


def load_profile(path: str | Path) -> RunProfile:
    """Read a JSON run profile from `path` into a `RunProfile`. Every field
    but `artifact_id` is optional in the file; a missing `artifact_id`
    raises `ProfileError` naming it.
    """
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    if "artifact_id" not in data or not str(data["artifact_id"]).strip():
        raise ProfileError(f"run profile {path!s} is missing required field 'artifact_id'")

    return RunProfile(
        artifact_id=str(data["artifact_id"]),
        hazard_scope=(
            frozenset(data["hazard_scope"]) if data.get("hazard_scope") is not None else None
        ),
        component_selection=data.get("component_selection"),
        text_view=str(data.get("text_view", "working")),
    )


ResolvedArtifact = EvaluatorArtifact | HazardResponseClassifier


def resolve_artifact(artifact_id: str | Path) -> ResolvedArtifact:
    """Resolve `artifact_id` to a loaded artifact, of either format.

    Dispatch is on the 1.1 `manifest.json`'s `format` field, which the
    baseline manifest does not have -- a declared marker rather than a guess
    at directory contents, so a corrupt 1.1 artifact reports *its own*
    problem (`ArtifactError`) instead of being silently retried as a
    baseline one.

    This is the one place either format is loaded. A second, parallel
    resolution path elsewhere is what would let the two drift.
    """
    if is_evaluator_artifact(artifact_id):
        return load_artifact(artifact_id)
    return _load_baseline_artifact(artifact_id)


def _supported_hazards(artifact: ResolvedArtifact) -> frozenset[str]:
    """The artifact's frozen supported hazard set -- what `hazard_scope`
    defaults to (D-57) and what `run.validate_supplied_hazard` checks
    against. For a 1.1 artifact that is `rules.json`'s set, derived at write
    time from the fitted cells; for the baseline, `trained_hazards`.
    """
    if isinstance(artifact, EvaluatorArtifact):
        return artifact.rules.supported_hazards
    return frozenset(artifact.trained_hazards)


class BuiltRegistry(NamedTuple):
    """`build_registry`'s result: a populated `Registry`, the default
    `(stage -> implementation_id)` selection every one of its components
    reports, and the `rule_version` the constructed `RuleSet` actually
    carries -- never a literal a caller could type out of sync with it.
    """

    registry: Registry
    component_selection: dict[str, str]
    rule_version: str


def build_registry(
    artifact: ResolvedArtifact,
    *,
    text_view: str = "working",
    provider: EmbeddingProvider | None = None,
    pooling: PoolingStrategy | None = None,
    allow_download: bool = False,
) -> BuiltRegistry:
    """Build and register the ten stage-1.1 components against `artifact`,
    and return the populated `Registry` plus their default selection.

    **The only place in PR 7 that imports `components/*`** (§1's standing
    constraint on the runner) -- `resolve` below, and slice C's runner after
    it, only ever go through the `Registry` this returns.

    **Stage 9's implementation follows the artifact, not a flag.** A 1.1
    evaluator artifact carries fitted multinomial cells and gets
    `MultinomialPerHazardScorer`; a baseline artifact carries binary heads and
    gets `BaselineTwoHeadScorer`. Selecting the other one is not a
    configuration a caller should be able to express, because the model it
    would need is not in the artifact -- so the mismatch is unrepresentable
    here rather than a per-row failure later.

    `provider`/`pooling` default to the real `BgeEmbeddingProvider`/
    `MeanPooling` (offline by default, D-6 -- pass `allow_download=True` to
    fetch weights); a caller may substitute a stub for a fast, network-free
    test, exactly as `tests/integration/test_evaluator_real_bge.py`'s
    fixture and this project's other component tests already do.

    `text_view` is passed straight to `EmbeddingComponent`'s constructor
    (D-69, D-74) -- the only place it is used in this function.
    """
    embedding_provider = provider or BgeEmbeddingProvider(allow_download=allow_download)
    pooling_strategy = pooling or MeanPooling()

    if isinstance(artifact, EvaluatorArtifact):
        # D-23: the frozen `rules.json` is the serve-time source of truth for
        # both hazard-family sets, never installed config.
        rules = RuleSet(
            enablement_only_hazards=artifact.rules.enablement_only_hazards,
            specialized_advice_hazards=artifact.rules.specialized_advice_hazards,
        )
        scorer = MultinomialPerHazardScorer(artifact)
    else:
        rules = RuleSet(
            enablement_only_hazards=artifact.enablement_only_hazards,
            specialized_advice_hazards=artifact.specialized_advice_hazards,
        )
        scorer = BaselineTwoHeadScorer(artifact)

    components = {
        "empty_response": EmptyResponseDetector(),
        "decoding": Decoder(),
        "hazard_detection": HazardDetectionPlaceholder(),
        "prompt_repetition": PromptRepetitionDetector(),
        "narrative_detection": NarrativeDetectionPlaceholder(),
        "refusal_detection": RefusalDetectionPlaceholder(),
        "disclaimer_detection": DisclaimerDetector(),
        "embedding": EmbeddingComponent(embedding_provider, pooling_strategy, text_view=text_view),
        "scoring": scorer,
        "final_integration": FinalIntegrator(rules),
    }

    registry = Registry()
    for component in components.values():
        registry.register(component)

    default_selection = {stage: components[stage].implementation for stage in STAGE_ORDER}
    return BuiltRegistry(registry=registry, component_selection=default_selection, rule_version=rules.version)


class ResolvedRun(NamedTuple):
    """Everything `run.open_run` needed plus what produced it: the
    `RunContext` a batch runner attaches to every record, the `Registry`
    that resolved it, and the loaded `artifact` -- whose supported hazard set
    is what `run.validate_supplied_hazard` and the runner's per-row loop
    check the supplied hazard against, without re-loading it.

    *(Renamed from `classifier` 2026-08-05 by PR 5 slice C: with the 1.1
    format loadable, this is a `HazardResponseClassifier` only half the
    time. Use `profile._supported_hazards` rather than reaching for a
    format-specific attribute.)*
    """

    run_context: RunContext
    registry: Registry
    artifact: ResolvedArtifact


def resolve(
    profile: RunProfile,
    *,
    provider: EmbeddingProvider | None = None,
    pooling: PoolingStrategy | None = None,
    allow_download: bool = False,
) -> ResolvedRun:
    """Resolve a `RunProfile` into a valid `RunContext` (`PR7_EXECUTION_PLAN.md`
    §5's exit criterion): load the artifact, build and register its
    components, default `hazard_scope` to the artifact's supported set when
    the profile did not supply one (D-57), and call `run.open_run` -- which
    still performs its own condition-(2)/(3) rejections, so a hazard scope
    wider than the artifact supports is rejected here with a message naming
    it, unchanged.
    """
    artifact = resolve_artifact(profile.artifact_id)
    built = build_registry(
        artifact,
        text_view=profile.text_view,
        provider=provider,
        pooling=pooling,
        allow_download=allow_download,
    )

    supported = _supported_hazards(artifact)
    hazard_scope = profile.hazard_scope if profile.hazard_scope is not None else supported

    component_selection = dict(built.component_selection)
    if profile.component_selection is not None:
        component_selection.update(profile.component_selection)

    config = RunConfig(
        hazard_scope=hazard_scope,
        component_selection=component_selection,
        artifact_id=profile.artifact_id,
        rule_version=built.rule_version,
    )
    run_context = open_run(config, built.registry, supported)

    return ResolvedRun(run_context=run_context, registry=built.registry, artifact=artifact)
