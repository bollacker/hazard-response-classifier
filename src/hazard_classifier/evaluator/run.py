"""Run entry (`docs/ARCHITECTURE.md` §2): `RunConfig`, `RunContext`,
`RunRejectedError`, `open_run`.

**Scope for slice 1A (`docs/planning/PR1_EXECUTION_PLAN.md`): registry
validation only.** `ARCHITECTURE.md` §2 lists three rejection conditions for
`open_run`:

1. the supplied hazard of any input row is missing, unrecognized, or
   outside `hazard_scope`;
2. `hazard_scope` contains a hazard the selected artifact does not support;
3. a selected component implementation is not in the registry.

Only (3) is built here. (1) and (2) need a labeled artifact and per-row
input data that this slice has no reason to touch -- they are PR 3's
supplied-hazard and hazard-scope validation, named explicitly in
`PR1_EXECUTION_PLAN.md` as out of scope for slice 1A. `open_run`'s
signature reflects this: it takes a `Registry`, not yet an artifact.
"""

from __future__ import annotations

import dataclasses
from types import MappingProxyType
from typing import Mapping

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


def open_run(config: RunConfig, registry: Registry) -> RunContext:
    """Validate `config` against `registry` and return the `RunContext` to
    attach to every record this run produces.

    Slice 1A's only check: every `(stage, implementation)` pair in
    `config.component_selection` must be registered. `ARCHITECTURE.md`
    §2's other two rejection conditions (missing/out-of-scope supplied
    hazard; an artifact-unsupported hazard in `hazard_scope`) are not
    checked here -- see the module docstring.
    """
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
