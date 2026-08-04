"""Slice 1A tests (`docs/planning/PR1_EXECUTION_PLAN.md`) for
`hazard_classifier/evaluator/registry.py`.
"""

from __future__ import annotations

import pytest

from hazard_classifier.evaluator.registry import Registry, UnregisteredComponentError


class _StubComponent:
    def __init__(self, stage: str, implementation: str, version: str = "1") -> None:
        self.stage = stage
        self.implementation = implementation
        self.version = version
        self.maturity = "working"

    def run(self, record):
        return record


def test_registered_component_is_returned_by_get() -> None:
    registry = Registry()
    component = _StubComponent("decoding", "baseline")
    registry.register(component)

    assert registry.get("decoding", "baseline") is component


def test_unknown_stage_implementation_pair_raises_naming_both() -> None:
    registry = Registry()

    with pytest.raises(UnregisteredComponentError) as excinfo:
        registry.get("decoding", "nonexistent")

    message = str(excinfo.value)
    assert "decoding" in message
    assert "nonexistent" in message
    assert excinfo.value.stage == "decoding"
    assert excinfo.value.implementation == "nonexistent"


def test_a_different_unknown_pair_names_that_pair_not_a_stale_one() -> None:
    # Guards against a copy-paste bug where the error message hard-codes
    # one example pair instead of the arguments actually passed.
    registry = Registry()

    with pytest.raises(UnregisteredComponentError) as excinfo:
        registry.get("refusal", "some-other-impl")

    message = str(excinfo.value)
    assert "refusal" in message
    assert "some-other-impl" in message
    assert "decoding" not in message


def test_registering_the_same_key_twice_replaces_the_first() -> None:
    registry = Registry()
    first = _StubComponent("decoding", "baseline", version="1")
    second = _StubComponent("decoding", "baseline", version="2")
    registry.register(first)
    registry.register(second)

    assert registry.get("decoding", "baseline") is second


def test_lookup_is_scoped_by_stage_not_implementation_alone() -> None:
    registry = Registry()
    registry.register(_StubComponent("decoding", "shared-name"))

    with pytest.raises(UnregisteredComponentError):
        registry.get("refusal", "shared-name")
