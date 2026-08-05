"""Tests for `hazard_classifier/evaluator/run.py`: registry validation
(slice 1A, `docs/planning/PR1_EXECUTION_PLAN.md`) and hazard/scope
validation (slice A, `docs/planning/PR3_EXECUTION_PLAN.md` §3) -- together,
`ARCHITECTURE.md` §2's three rejection conditions.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from hazard_classifier.evaluator.registry import Registry
from hazard_classifier.evaluator.run import (
    ComponentSelection,
    RunConfig,
    RunContext,
    RunRejectedError,
    open_run,
    validate_supplied_hazard,
)


class _StubComponent:
    def __init__(self, stage: str, implementation: str, version: str = "1") -> None:
        self.stage = stage
        self.implementation = implementation
        self.version = version
        self.maturity = "working"

    def run(self, record):
        return record


def _config(**overrides) -> RunConfig:
    defaults = dict(
        hazard_scope=frozenset({"hte"}),
        component_selection={"decoding": "baseline"},
        artifact_id="artifact-1",
        rule_version="v1",
    )
    defaults.update(overrides)
    return RunConfig(**defaults)


def test_open_run_resolves_registered_components_into_a_run_context() -> None:
    registry = Registry()
    registry.register(_StubComponent("decoding", "baseline", version="3"))

    context = open_run(_config(), registry, {"hte"})

    assert isinstance(context, RunContext)
    assert context.hazard_scope == frozenset({"hte"})
    assert context.artifact_id == "artifact-1"
    assert context.rule_version == "v1"
    assert context.component_selections["decoding"] == ComponentSelection(
        implementation="baseline", version="3"
    )


def test_open_run_rejects_an_unregistered_component_naming_stage_and_implementation() -> None:
    registry = Registry()  # nothing registered

    with pytest.raises(RunRejectedError) as excinfo:
        open_run(_config(), registry, {"hte"})

    message = str(excinfo.value)
    assert "decoding" in message
    assert "baseline" in message


def test_open_run_resolves_every_selected_stage_not_just_the_first() -> None:
    registry = Registry()
    registry.register(_StubComponent("decoding", "baseline", version="1"))
    registry.register(_StubComponent("refusal", "baseline", version="2"))

    context = open_run(
        _config(component_selection={"decoding": "baseline", "refusal": "baseline"}),
        registry,
        {"hte"},
    )

    assert context.component_selections["decoding"].version == "1"
    assert context.component_selections["refusal"].version == "2"


def test_run_config_component_selection_is_read_only() -> None:
    config = _config()

    assert isinstance(config.component_selection, MappingProxyType)
    with pytest.raises(TypeError):
        config.component_selection["decoding"] = "other"  # type: ignore[index]


def test_run_context_component_selections_is_read_only() -> None:
    registry = Registry()
    registry.register(_StubComponent("decoding", "baseline"))
    context = open_run(_config(), registry, {"hte"})

    assert isinstance(context.component_selections, MappingProxyType)
    with pytest.raises(TypeError):
        context.component_selections["decoding"] = None  # type: ignore[index]


def test_run_config_hazard_scope_is_coerced_to_a_frozenset() -> None:
    config = _config(hazard_scope={"hte", "prv"})

    assert config.hazard_scope == frozenset({"hte", "prv"})
    assert isinstance(config.hazard_scope, frozenset)


# --- Slice A: hazard/scope validation (`PR3_EXECUTION_PLAN.md` §3) ---------


def test_open_run_rejects_a_hazard_scope_hazard_the_artifact_does_not_support() -> None:
    registry = Registry()
    registry.register(_StubComponent("decoding", "baseline"))

    with pytest.raises(RunRejectedError) as excinfo:
        open_run(_config(hazard_scope={"hte", "cse"}), registry, {"hte"})

    assert "cse" in str(excinfo.value)


def test_open_run_accepts_when_every_hazard_scope_member_is_supported() -> None:
    registry = Registry()
    registry.register(_StubComponent("decoding", "baseline"))

    context = open_run(_config(hazard_scope={"hte", "prv"}), registry, {"hte", "prv", "cse"})

    assert context.hazard_scope == frozenset({"hte", "prv"})


def _run_context(hazard_scope: frozenset[str]) -> RunContext:
    return RunContext(
        hazard_scope=hazard_scope,
        rule_version="v1",
        artifact_id="artifact-1",
        component_selections={},
    )


def test_validate_supplied_hazard_rejects_a_blank_value() -> None:
    with pytest.raises(RunRejectedError) as excinfo:
        validate_supplied_hazard("   ", _run_context(frozenset({"hte"})))

    assert "missing" in str(excinfo.value)


def test_validate_supplied_hazard_rejects_a_hazard_outside_scope() -> None:
    with pytest.raises(RunRejectedError) as excinfo:
        validate_supplied_hazard("prv", _run_context(frozenset({"hte"})))

    assert "prv" in str(excinfo.value)


def test_validate_supplied_hazard_does_not_case_fold() -> None:
    """D-27: `normalize_hazard` strips and replaces hyphens, but never
    lowercases. `"HTE"` therefore normalizes to `"HTE"`, which is not a
    member of a scope spelled `{"hte"}` -- this must reject, not accept.
    """
    with pytest.raises(RunRejectedError) as excinfo:
        validate_supplied_hazard("HTE", _run_context(frozenset({"hte"})))

    assert "HTE" in str(excinfo.value)


def test_validate_supplied_hazard_accepts_a_normalized_match() -> None:
    validate_supplied_hazard("spc-fin", _run_context(frozenset({"spc_fin"})))
