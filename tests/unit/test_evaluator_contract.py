"""Slice 1A tests (`docs/planning/PR1_EXECUTION_PLAN.md`) for
`hazard_classifier/evaluator/contract.py`.
"""

from __future__ import annotations

from hazard_classifier.evaluator import record as record_module
from hazard_classifier.evaluator.contract import Component, ComponentError, Maturity
from hazard_classifier.evaluator.record import EvaluationRecord


def test_component_error_reexport_is_the_same_class_defined_in_record() -> None:
    # contract.py's module-table position for ComponentError (ARCHITECTURE.md
    # §3.2) is a re-export, not a second definition -- see contract.py's
    # docstring for why. This is what makes that a re-export and not a
    # silently-diverging duplicate.
    assert ComponentError is record_module.ComponentError


def test_a_conforming_stub_satisfies_the_component_protocol() -> None:
    class StubComponent:
        stage = "decoding"
        implementation = "stub"
        version = "0"
        maturity: Maturity = "working"

        def run(self, record: EvaluationRecord) -> EvaluationRecord:
            return record

    assert isinstance(StubComponent(), Component)


def test_an_object_missing_run_does_not_satisfy_the_component_protocol() -> None:
    class NotAComponent:
        stage = "decoding"
        implementation = "stub"
        version = "0"
        maturity: Maturity = "working"

    assert not isinstance(NotAComponent(), Component)
