"""The component contract (`docs/ARCHITECTURE.md` §6): `Component`, the
protocol every stage implements; `ComponentError`; `Maturity`.

**Packaging note, not an architecture deviation:** `ARCHITECTURE.md` §3.2's
module table assigns `ComponentError` to this file, but `Component.run`'s
own signature needs `EvaluationRecord` from `record.py`, and §3.2 also
requires `record.py` to import nothing from `evaluator/` at all --
including `ComponentError`, which `ComponentObservation.error` needs. Both
constraints can't hold if `ComponentError` is defined here. Resolved by
defining it once in `record.py` (where the field that needs it actually
lives) and re-exporting it here, so `from
hazard_classifier.evaluator.contract import ComponentError` still works as
the module table implies -- same public surface, one canonical definition,
no cycle.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Protocol, runtime_checkable

from .record import ComponentError, EvaluationRecord

__all__ = ["Component", "ComponentError", "Maturity"]

Maturity = Literal["working", "partial", "placeholder"]


@runtime_checkable
class Component(Protocol):
    """`ARCHITECTURE.md` §6. Every stage implements this. A component reads
    the record and returns an updated record; it never calls or imports
    another component (enforced by the module layout, not by this
    protocol), assigns no final result, and applies no exception or
    applicability decision -- all of that is the final integrator's (§9).

    `@runtime_checkable` so a registered object can be `isinstance`-checked
    for the required shape (presence of the four `ClassVar`s and `run`) --
    a lightweight duck-typing gate, not a signature or type check, which
    `Protocol`'s runtime support never provides.
    """

    stage: ClassVar[str]
    implementation: ClassVar[str]
    version: ClassVar[str]
    maturity: ClassVar[Maturity]

    def run(self, record: EvaluationRecord) -> EvaluationRecord: ...
