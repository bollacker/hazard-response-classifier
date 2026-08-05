"""Run entry (`docs/ARCHITECTURE.md` §2): `RunConfig`, `RunContext`,
`RunRejectedError`, `open_run`, `validate_supplied_hazard`.

`ARCHITECTURE.md` §2 lists three rejection conditions:

1. the supplied hazard of any input row is missing, unrecognized, or
   outside `hazard_scope`;
2. `hazard_scope` contains a hazard the selected artifact does not support
   (D-23 -- the artifact's frozen sets are authoritative);
3. a selected component implementation is not in the registry.

All three are now built. `open_run` checks (2) and (3) once, at run entry,
against `supported_hazards` (the artifact's frozen hazard set -- callers
pass `classifier.trained_hazards`, not a new artifact loader; D-49 defers
the 1.1 evaluator artifact past this PR) and `registry`. (1) collapses to a
single membership test against `hazard_scope` once (2) has already ruled
out any unsupported hazard being in scope -- see `validate_supplied_hazard`,
called once per response, before `pipeline.run_pipeline` is invoked for it
(`docs/planning/PR3_EXECUTION_PLAN.md` §3.1).
"""

from __future__ import annotations

import dataclasses
from types import MappingProxyType
from typing import AbstractSet, Mapping

from ..schema import normalize_hazard
from .registry import Registry, UnregisteredComponentError


@dataclasses.dataclass(frozen=True)
class RunConfig:
    """`ARCHITECTURE.md` §2. `component_selection` maps stage name to the
    chosen implementation id -- the raw configuration input `open_run`
    resolves against a `Registry`.
    """

    hazard_scope: frozenset[str]
    component_selection: Mapping[str, str]
    artifact_id: str
    rule_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "hazard_scope", frozenset(self.hazard_scope))
        object.__setattr__(self, "component_selection", MappingProxyType(dict(self.component_selection)))


@dataclasses.dataclass(frozen=True)
class ComponentSelection:
    """One resolved entry in `RunContext.component_selections`: the
    implementation id `RunConfig` named, plus the version the registered
    `Component` actually reports -- resolved once at `open_run` time so a
    result can name the exact code that produced it
    (`ARCHITECTURE.md` §6: "recorded... so a result names the exact
    implementations that produced it").
    """

    implementation: str
    version: str


@dataclasses.dataclass(frozen=True)
class RunContext:
    """`ARCHITECTURE.md` §4: what `EvaluationRecord.run` carries --
    `hazard_scope`, `rule_version`, `artifact_id`, and each stage's
    resolved component selection (implementation id + version). Built once
    by `open_run` and attached to every record produced by the run.
    """

    hazard_scope: frozenset[str]
    rule_version: str
    artifact_id: str
    component_selections: Mapping[str, ComponentSelection]

    def __post_init__(self) -> None:
        object.__setattr__(self, "hazard_scope", frozenset(self.hazard_scope))
        object.__setattr__(self, "component_selections", MappingProxyType(dict(self.component_selections)))


class RunRejectedError(Exception):
    """`ARCHITECTURE.md` §2: raised by `open_run` for a run-level rejection.
    Never reaches the integrator -- nothing has been scored yet. Carries a
    human-readable message naming the offending value and the reason,
    rather than a bare stage/implementation pair a caller would have to
    re-render into words.
    """


def open_run(config: RunConfig, registry: Registry, supported_hazards: AbstractSet[str]) -> RunContext:
    """Validate `config` against `registry` and `supported_hazards`, and
    return the `RunContext` to attach to every record this run produces.

    Two checks, run once for the whole run (`ARCHITECTURE.md` §2's
    conditions (2) and (3)):

    - every hazard in `config.hazard_scope` must be in `supported_hazards`
      (the artifact's frozen hazard set -- D-23); and
    - every `(stage, implementation)` pair in `config.component_selection`
      must be registered.

    Condition (1) (a response's own supplied hazard) is per-response, not
    checked here -- see `validate_supplied_hazard`.
    """
    unsupported = config.hazard_scope - frozenset(supported_hazards)
    if unsupported:
        raise RunRejectedError(
            f"run rejected: hazard_scope contains {sorted(unsupported)!r}, "
            "which the selected artifact does not support"
        )

    selections: dict[str, ComponentSelection] = {}
    for stage, implementation in config.component_selection.items():
        try:
            component = registry.get(stage, implementation)
        except UnregisteredComponentError as exc:
            raise RunRejectedError(
                f"run rejected: stage={stage!r} selects implementation={implementation!r}, "
                "which is not registered"
            ) from exc
        selections[stage] = ComponentSelection(implementation=implementation, version=component.version)

    return RunContext(
        hazard_scope=config.hazard_scope,
        rule_version=config.rule_version,
        artifact_id=config.artifact_id,
        component_selections=selections,
    )


def validate_supplied_hazard(supplied_hazard: str, run_context: RunContext) -> None:
    """`ARCHITECTURE.md` §2 condition (1), checked once per response,
    before `pipeline.run_pipeline` is invoked for it.

    Normalizes `supplied_hazard` first (`schema.normalize_hazard` --
    `.strip().replace("-", "_")`, no lowercasing -- D-27, carried for 1.1).
    Rejects a blank value, or one outside `run_context.hazard_scope`.
    Because `open_run` already validated `hazard_scope` against the
    artifact's supported hazards, "unrecognized" and "outside scope" are one
    membership test here, not two.
    """
    normalized = normalize_hazard(supplied_hazard)
    if normalized == "":
        raise RunRejectedError(f"run rejected: supplied_hazard={supplied_hazard!r} is missing")
    if normalized not in run_context.hazard_scope:
        raise RunRejectedError(
            f"run rejected: supplied_hazard={normalized!r} is not in hazard_scope={sorted(run_context.hazard_scope)!r}"
        )
