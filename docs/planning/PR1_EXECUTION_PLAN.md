# PR 1 execution plan — replaceable evaluator architecture

Written 2026-08-04. This is the working plan for `RELEASE_1_1_QUEUE_PROPOSAL.md`
PR 1, the first slice of `STATUS.md` queue item 4. It is written to be run from
a clean session: everything a session needs is either here or named here.

**Goal (from PR 1):** convert the current evaluator into independently
replaceable components **without changing current scores.**

---

## 0. Read first

In this order. Do not skip §Read first — this project's failure mode is
sessions re-deriving settled ground.

| Doc | Why |
|---|---|
| `META_PLAN.md` | The process contract. §5 governs how the queue is read and updated |
| `STATUS.md` — header, Queue, Awaiting User | Live state; Awaiting User is non-blocking but names what is assumed |
| `../ARCHITECTURE.md` §§1–13 | **The specification for this work.** §3.2 is the module layout, §4 the record, §6 the component contract |
| `../SCIENCE.md` §Modular pipeline, §Final integration | Behavior. Governs on any conflict with architecture |
| `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 1 | The work items and exit criteria this plan implements |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions — all met as of 2026-08-04

- Entry gate cleared; `RELEASE_1_1_QUEUE_PROPOSAL.md` is approved and
  authorizes these phases.
- `ARCHITECTURE.md` specifies the design, including §3.2's module layout and
  §4's optional `distribution`.
- Baseline is green: **151 tests**, `pytest` from the repo root.
- Environment: `pyenv activate airr` (or `~/.pyenv/versions/airr/bin/python`).

**Standing constraint for all of PR 1:** the three baseline CLIs keep working
and their outputs do not change. The baseline in `ARCHITECTURE.md` §14 is not
being rewritten — it becomes the set of implementations the new wrappers call.

## 2. Slices

One slice per session, per `META_PLAN.md` §5. Each ends green with its own
tests and a `STATUS.md` update.

### Slice 0 — Golden baseline capture

**This must land before any refactor, on untouched code.** PR 1's central exit
criterion is "the same inputs produce unchanged current text, features, scores,
probabilities, labels, and failures," and nothing in the repo captures today's
outputs. Without this the criterion is unverifiable and the refactor is
unfalsifiable.

Deliverables:

- `tests/golden/capture_baseline.py` — a script, not a test, that runs
  `hrc-train` → `hrc-evaluate` → `hrc-predict` against
  `examples/sample_input.csv` and writes every output file plus the fitted
  artifact's `thresholds.json`/`rules.json`/`manifest.json` under
  `tests/golden/baseline/`.
- Committed golden outputs from a real, non-mocked run against the real cached
  BGE model.
- `tests/integration/test_baseline_parity.py` — reruns the same pipeline and
  asserts byte-equality against the committed goldens.

Notes and traps:

- `heads.npz` is binary and float-valued. Compare the **arrays** with
  `np.testing.assert_array_equal` after loading, not the file bytes — `.npz` is
  a zip and embeds timestamps.
- `manifest.json` carries `training_timestamp`. Exclude it from comparison, or
  capture with it unset. Do not make the test tolerant of *other* drift to work
  around this one field.
- Use a fixed seed (`config.DEFAULT_SEED`) and CPU-only (D-6) so the run is
  deterministic. Confirm determinism by capturing twice and diffing before
  committing.
- `artifacts/riki_eval_v1` is **stale** — D-45 removed `constant_probability`
  and it no longer loads. Do not use it. Train fresh.

Exit: parity test passes on unmodified code, and fails if you perturb any
fitted parameter by hand. Prove the second by doing it once.

### Slice 1A — Record, contract, registry

Pure structure. No behavior, no wiring, no pipeline yet.

Deliverables (`ARCHITECTURE.md` §3.2, §4, §6):

- `evaluator/record.py` — `Result`, `FlagState`, `TextViews`, `Flags`,
  `Judgment`, `HazardJudgment`, `ComponentObservation`, `EvaluationRecord`.
  Frozen dataclasses; updates return new instances.
- `evaluator/contract.py` — the `Component` protocol, `ComponentError`,
  `Maturity`.
- `evaluator/registry.py` — `(stage, implementation_id) -> Component`,
  with registration and lookup.
- `evaluator/run.py` — `RunConfig`, `RunContext`, `RunRejectedError`, and
  `open_run` **limited to registry validation only**. Supplied-hazard and
  hazard-scope validation are PR 3's; do not build them here.

Tests:

- A record round-trips through an immutable update without mutating the
  original.
- `Flags` defaults to `not_evaluated` everywhere — the "nothing has looked yet"
  state, not `not_detected`.
- `Judgment.distribution` accepts `None` (`ARCHITECTURE.md` §4).
- Registry rejects an unknown `(stage, implementation)` with a message naming
  both.
- `record.py` imports nothing else from `evaluator/` — assert structurally, by
  inspecting the module's imports, not by reading it.

### Slice 1B — Pipeline, placeholders, detection wrappers

Deliverables:

- `evaluator/pipeline.py` — the ten-stage order from `ARCHITECTURE.md` §3 and
  the §3.1 exhaustion short-circuit. **No scientific decision logic**: the
  pipeline decides order and data passing, nothing else.
- `evaluator/components/` stages 1–7:
  - `empty.py` (working) — whitespace-trim test, changes no text.
  - `decoding.py` (working) — wraps `preprocess/decode.py`.
  - `hazard.py`, `narrative.py`, `refusal.py` (placeholders) — pass content
    through unchanged, `outcome="not_evaluated"`, flags left `not_evaluated`,
    no judgment.
  - `repetition.py` (partial) — `ARCHITECTURE.md` §7.1: the two **exact**
    normalized-substring paths from `preprocess/flags.py`, and **not**
    `partial_contiguous`. Removes matched spans from working text; sets
    `exhausted_at` when removal empties it.
  - `disclaimer.py` (partial) — wraps the existing disclaimer detection;
    publishes `named["disclaimer_stripped"]` while leaving `working` intact.

Tests:

- Stage order is exactly `SCIENCE.md` §Modular pipeline's.
- Exhaustion at each of stages 1, 4, 5, 6, 7 skips all later stages and reaches
  the integrator with `exhausted_at` set correctly.
- **A placeholder is distinguishable from a negative result** — after a run,
  `flags.refusal == "not_evaluated"`, never `"not_detected"`. This is the
  forcing function for §6's placeholder rule; a placeholder that writes
  `not_detected` passes a naive test and silently claims it looked.
- A prompt-only response ends with empty working text, `prompt_repetition`
  detected, and `exhausted_at == "prompt_repetition"` — the input
  `SCIENCE.md` phase B1 now handles.
- Repetition-plus-authored-content leaves the authored text in `working`.

### Slice 1C — Embedding, scoring, integration, views, parity

Deliverables:

- `evaluator/components/embedding.py` — `EmbeddingProvider` and
  `PoolingStrategy` per §8, wrapping `embed.py`. **One embed call per batch**,
  shared across every evaluated hazard.
- `evaluator/components/scoring.py` — wraps the baseline two-head model.
  Maturity **`partial`**; reports `label` and `distribution=None`. Nothing
  synthesizes a distribution (`ARCHITECTURE.md` §4 — the derivation is unsafe
  because `p_high > p_nonzero` is reachable).
- `evaluator/components/integration.py` — the final integrator per §9 and
  `SCIENCE.md` §Per-hazard finalization: phase A → B (B1's bullets **in
  order**) → C → D, then the family table, then the rollup. Reads `label`,
  never `distribution`; never reads a text view.
- `evaluator/views.py` — the derived views of §11, at minimum the one the
  parity test needs.

Tests:

- **The parity test from slice 0 still passes**, now with the pipeline in the
  repo. This is PR 1's headline exit criterion.
- Embeddings are computed once per batch — assert via call count on the
  provider, not by timing.
- B1's bullet order: refusal-plus-repetition gives L0/E0 and
  disclaimer-plus-narrative L0/E0. An unordered implementation yields L1 here,
  which is why `SCIENCE.md` §Evidence and outputs names this as required
  verification.
- Phase D returns a failure on a missing `label`, and **not** on a missing
  `distribution`.
- Every component can be swapped for a stub via the registry without editing
  another component — the real test of §6, and the reason PR 1 exists.

## 3. Exit criteria → how each is verified

| PR 1 exit criterion | Verified by |
|---|---|
| Every component replaceable without editing another | Slice 1C registry-swap test |
| Placeholders pass through without creating judgments | Slice 1B `not_evaluated` forcing function |
| Wrapped L/E report `partial` and `distribution=None`; nothing synthesizes one | Slice 1C scoring tests |
| IDs and the complete carried record survive the pipeline | Slice 1B end-to-end record assertions |
| Same inputs → unchanged **baseline** text, features, scores, probabilities, labels, failures | Slice 0 goldens + slice 1C parity. Scoped to the baseline path 2026-08-04 (`DECISIONS.md` D-48) — the 1.1 pipeline deliberately differs and is judged against `SCIENCE.md` |
| Embeddings created once per scoring batch | Slice 1C call-count test |
| ~~Artifact save/load preserve component and rule versions~~ | **Deferred to PR 5 / PR 6, 2026-08-04 (`DECISIONS.md` D-49)** — this row asked slice 1C to test an artifact no slice was scheduled to build. PR 1 carries instead: component selections, versions, and rule version survive into the `results.jsonl` view (slice 1C view test) |

## 4. Explicitly out of scope for PR 1

Named so a session does not drift into them:

- Supplied-hazard and hazard-scope validation, and multi-hazard routing — PR 3.
- Summarized or closely-paraphrased prompt repetition — **not in Release 1.1
  at all** (`DECISIONS.md` D-50). `SCIENCE.md` wants all three eventually;
  1.1 ships exact-only as **partial** and discloses the gap. *(Corrected
  2026-08-04: this line previously assigned the work to PR 2 while also
  saying 1.1 ships exact-only — contradictory, since PR 2 is a 1.1 PR. That
  contradiction is what D-50 resolved.)*
- Real narrative, refusal, or hazard detection — placeholders until the
  Standards examples and approved implementations exist.
- Any three-class model work — PR 5, blocked on the Standards dataset.
- Deleting or rewriting the baseline. It stays green through PR 1.
- Changing `safe`/`unsafe` in baseline outputs (D-30). The 1.1 vocabulary is
  `Result` (§3.2); the baseline schema keeps its own.

## 5. When a slice raises something this plan did not anticipate

Per `META_PLAN.md` §3: if confidence is below ~90%, or it conflicts with a
specification, or it is a tradeoff only the user can make — stop and add it to
**Awaiting User** rather than choosing. Two live examples of the kind of thing
that qualifies: the `distribution` question that produced §4's optional field,
and the B1/B2 defect that produced the phase B fold. Both were found by writing
the spec, not by reasoning about it in advance, and more will surface here.

Record every slice in `STATUS.md`'s Recently Completed with what landed, what
it verified, and anything found in passing.
