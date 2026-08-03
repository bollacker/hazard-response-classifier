# Decision Ledger

This file records only current decisions jointly approved by Riki and Kurt.
Proposals and unanswered questions belong in `STATUS.md`.

`../SCIENCE.md` documents the currently selected Assessment Standard and
scientific target. Assessment requirements come from that selected, versioned
standard and may change; this ledger does not restate or freeze them.

`../ARCHITECTURE.md` owns module order, interfaces, records, and implementation
structure. This ledger records the choices that constrain that architecture
without duplicating its specification.

The full pre-staging baseline ledger remains available in Git history through
commit `3b4634e`. Except for the current versions below, its D-1 through D-37
entries are historical implementation provenance, not Release 1.1 constraints.
Reusing an old baseline choice requires a new joint decision.

## D-3: No fallback for unavailable hazard-specific operations

Date: 2026-07-23
Modified: 2026-08-03 by Kurt and Riki
Status: locked

Decision: If a module branches its operation by hazard and has no operation
available for a qualifying hazard, scoring fails. Do not fall back to another
operation or invent a module result.

Boundary: D-3 concerns the capability of a hazard-aware module. D-11 separately
governs an unknown supplied hazard.

## D-4: Blank or exhausted working text goes to final integration

Date: 2026-07-23
Modified: 2026-08-03 by Kurt and Riki
Status: locked

Decision:

1. A blank supplied response is flagged as a refusal through the Refusal
   detector. The complete carried record goes to the final integrator and
   every other module is skipped.
2. If any module returns an empty string as working text, the pipeline skips
   every remaining module and sends the complete carried record to the final
   integrator.
3. The final integrator uses the accumulated flags and the governing
   Assessment Standard to determine the result. Model-assigned Legitimization
   and Enablement judgments are not required in these cases.

Boundary: D-4 is a routing decision. `../SCIENCE.md` defines the applicable
Assessment behavior; `../ARCHITECTURE.md` defines the concrete handoff.

## D-5: Unfittable operations are explicitly unavailable

Date: 2026-07-23
Modified: 2026-08-03 by Kurt and Riki
Status: locked

Decision: If training cannot produce a valid operation, mark that operation
unavailable. Do not create a constant-probability substitute or otherwise
invent an operation result. An artifact may still serve its other available
operations. A request that requires the unavailable operation fails under
D-3.

Boundary: The training and artifact implementation belongs in
`../ARCHITECTURE.md`.

## D-11: Unknown supplied hazards fail before scoring

Date: 2026-07-23
Modified: 2026-08-03 by Kurt and Riki
Status: locked

Decision: An unknown supplied hazard fails before scoring. The evaluator
produces no score and returns a clear, human-readable error.

Boundary: D-11 is input validation. It does not govern module availability or
blank-response routing.

## D-38: Assessment behavior comes from the selected Assessment Standard

Date: 2026-08-03
Status: locked

Decision: Assessment behavior is governed by the Assessment Standard selected
for the release, not by this ledger. `../SCIENCE.md` documents the current
standard and scientific target and is mutable when the selected standard, its
version, or its authoritative interpretation changes.

Repository decisions may constrain how the evaluator implements, exposes,
tests, versions, or records the standard. They may not replace or permanently
freeze an Assessment requirement.
