# PR 7 execution plan — evaluator runner, input schema, and batch entry point

> **PR 7 is complete (2026-08-05). This document is now a record of what was
> built**, not live work — the same status `PR1`–`PR5_EXECUTION_PLAN.md` and
> `QUEUE_ITEM_2_EXECUTION_PLAN.md` carry. All five slices landed; §8's
> completion block is the close, and §11's table is filled in with the tests
> that actually verify each exit criterion. **Item 4 stays open** — PR 5 and
> PR 6 remain, in that order. **Nothing is left open**: the one design
> concern the close raised — §2's all-or-nothing rejection — was decided by
> Kurt the same day as [D-75](DECISIONS.md#d-75), which keeps the strictness
> and fixes the ergonomics around it. See Open Questions at the foot of this
> file, which also records a claim this plan got wrong.

Written 2026-08-05, after PR 4 closed and PR 5 was planned and resequenced.
This is the working plan for `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7, a slice of
`STATUS.md` queue item 4. Written to be run from a clean session: everything a
session needs is either here or named here.

**Goal (from PR 7):** make the 1.1 evaluator runnable. No PR before this one
creates a way to invoke it — `pyproject.toml` exposes only the three baseline
CLIs, and `evaluator/views.py` records that `failures.csv` needs a batch runner
that does not exist.

**What that means concretely.** Everything the runner drives is built and
tested: ten stages, the registry, `open_run`, `validate_supplied_hazard`,
`run_pipeline`, and two of the four views. What is missing is the shell around
them — a way to get rows *in*, a profile that says how to run, a loop that
survives a bad row, and files *out*. **PR 7 is plumbing, and its risk is
correspondingly concentrated in edge cases rather than in science.**

**Three things a session should know before starting.**

1. **A run rejection and a per-row failure are different things, and the
   distinction is an exit criterion.** `ARCHITECTURE.md` §2 classifies a bad
   supplied hazard as a **run-level rejection** — "the supplied hazard of *any
   input row*" — so it must abort **before any row is scored**. A runner that
   validates each row as it reaches it aborts *mid-batch*, having already
   written results for earlier rows. §5's design is a deliberate two-pass loop
   because of this; it is the single easiest thing in PR 7 to get subtly wrong.
2. **`evaluated_hazards` is set at record construction and nothing ever
   updates it.** Stage 3 is a placeholder that returns no additional hazards,
   so supplied-only is correct in 1.1 — but the runner is the first code that
   builds records for real input, so PR 7 owns the construction contract and
   must say where the merge will live when stage 3 becomes real (§4).
3. **PR 7 runs before PR 5** ([D-71](DECISIONS.md#d-71)), so the only scoring
   implementation available is PR 1's wrapped baseline, and the only loadable
   artifact is the **baseline** one ([D-49](DECISIONS.md#d-49) defers the 1.1
   artifact to PR 5). That is expected, not a gap: the queue proposal says
   plainly "PR 5 is not required — the runner drives whichever scoring
   implementation the registry selects."

**Five slices** (`META_PLAN.md` §5): A the input schema and record
construction, B the run profile and artifact resolution, C the batch runner and
`failures.csv`, D the two entry points, E a real end-to-end run plus the sweep
and close. **§3's gate question is answered and absorbed**
([D-74](DECISIONS.md#d-74)) — the profile carries `text_view` as a construction
parameter, conditional on a test that flips it. **A session starts at slice A
and runs straight through; no gate is open.**

---

## 0. Read first

In this order. Do not skip — this project's failure mode is sessions
re-deriving settled ground.

| Doc | Why |
|---|---|
| `META_PLAN.md` | The process contract. §1.2 (**single-approver mode**), §3 (uncertainty protocol), §5 (queue rules), §6 (a sweep is a critique pass) govern this work |
| `STATUS.md` — header, Queue item 4, Awaiting User, Assumed concurrence | Live state. Nothing in Awaiting User blocks this scope |
| `../ARCHITECTURE.md` **§2**, §3, §3.1, §4, §5, §6, §7, §8, **§11** | The structure this builds inside. **§2 is slice C's specification** (the three rejection conditions and what a rejection is *not*); §11 is `failures.csv`'s; §4 is the record the runner constructs |
| `../SCIENCE.md` §Modular pipeline, §Hazard scope configuration, §Evidence and outputs | Behavior. Governs on any conflict. §Hazard scope is what D-57's default implements; §Evidence and outputs is why provenance must reach every output record |
| `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7 | The work items and exit criteria this plan implements |
| `DECISIONS.md` D-56, D-57, D-60, D-61, D-49, D-48, D-69, D-23 | D-56 created this PR; D-57 is the scope default; D-61 is the single-threaded contract; D-69 hands PR 7 the run-profile question (§3); D-48 is the standing baseline constraint |
| `PR4_EXECUTION_PLAN.md`, `PR5_EXECUTION_PLAN.md` | The template this plan follows. PR 5's §1 and §3 matter here because PR 7 must not build what PR 5 owns |
| `QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 | Nine lessons that each cost something. §10 below carries them forward |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions and standing constraints

- **PR 4 is complete** (`c93baae`); PRs 1–4 are landed. Item 4 stays open.
- **Sequencing: PR 7 → PR 5 → PR 6** ([D-56](DECISIONS.md#d-56) places PR 7 at
  the front; [D-71](DECISIONS.md#d-71) moved PR 5 ahead of PR 6). **PR 7 is
  next and blocks nothing** — PR 5's plan states it needs neither PR 7 nor
  PR 6, so the two can be run in either order if that turns out convenient.
- **Baseline is green: 433 tests**, `pytest` from the repo root, ~23 s.
- Environment: `~/.pyenv/versions/airr/bin/python`, or `pyenv activate airr`.
  Bare `python` fails on this machine.
- A loadable baseline artifact exists at `tests/golden/baseline/artifact`, and
  `tests/integration/test_evaluator_real_bge.py` already assembles the full
  ten-stage pipeline against it — **that assembly is the runner's core, written
  as a test**. Read it before writing slice C; much of PR 7 is promoting it
  into production code with the loop, the profile, and the failure path added.

**Standing constraint, carried from PR 1 through PR 4.** The baseline CLIs'
output must not change ([D-48](DECISIONS.md#d-48)). `cli/*`, `schema.py`,
`model.py`, `embed.py`, `heads.py`, `rules.py`, `metrics.py`, and
`preprocess/*` are **shared with the baseline**. PR 7 adds a **fourth** CLI; it
does not modify the three that exist, and it does not extend `schema.py`'s
`REQUIRED_COLUMNS`/`Mode` to carry 1.1's columns. The 1.1 input schema is a new
module (§4).

**Standing constraint: the runner never imports a concrete component.** It is
an exit criterion and it is also what `ARCHITECTURE.md` §6 means by
replaceability: selection is resolved through the registry by
`(stage, implementation_id)`. The runner imports `Registry`, `open_run`,
`run_pipeline`, and the views — never `DisclaimerDetector` or friends. **Whoever
registers the components is a separate, nameable place** (§5), and that is the
only file in PR 7 allowed to import them.

**Standing constraint: single-threaded per process** ([D-61](DECISIONS.md#d-61)).
Release 1.1 makes no thread-safety claim. If PR 7 wants parallelism it is at
the process level, and §9 says why it probably should not want any yet.

## 2. What already exists, and what PR 7 actually has to do

| PR 7 work item | Status |
|---|---|
| Define the 1.1 input schema (`request_id`, `prompt_uid`, `response_id`, prompt text, response text, supplied hazard) | **Not built.** `schema.py`'s `_CORE_COLUMNS` is the baseline's — `seed_prompt_id, prompt_uid, prompt_text, response_text, hazard` — and carries **neither `request_id` nor `response_id`**. New module, slice A |
| Define the run profile: component selections, artifact id, rule version, hazard scope | **Not built.** `RunConfig` holds exactly these four fields, but nothing constructs one from a file or from flags, and `hazard_scope` has no default anywhere — [D-57](DECISIONS.md#d-57) says so explicitly ("no 1.1 result can be produced until a caller invents one"). Slice B |
| Scope defaults to the artifact's frozen supported set (D-57); resolved set recorded | **Half built.** `open_run` *validates* scope against the artifact's set and records the resolved scope in `RunContext`, and `views.py` carries it into `results.jsonl`. The **default** is the missing half, and it belongs to the profile layer, not to `open_run` (§5) |
| Build the batch runner over `open_run`, `validate_supplied_hazard`, `run_pipeline`, never aborting the batch on a per-row failure | **Not built**, and the three pieces it composes are all built and tested. Slice C — read §5's two-pass note first |
| Build the `failures.csv` view (`ARCHITECTURE.md` §11) | **Not built.** `views.py` says so in its own docstring, and §11's row says "Built by PR 7". Slice C |
| Add the CLI entry point and the in-process Python entry point | **Not built.** `pyproject.toml` `[project.scripts]` has the three baseline CLIs. Slice D |
| Parallelize at process level or not at all (D-61) | **Nothing to build** — §9 |

**Found in passing, and worth fixing in slice A:** `evaluator/__init__.py`'s
docstring still says "only `record.py`, `contract.py`, `registry.py`, and
`run.py` exist so far (slice 1A — pure structure, no pipeline, no components
yet)". Four PRs stale, and it is the package's front door.

## 3. Entry gate — answered

> **G-1 was decided by Kurt on 2026-08-05, locked as
> [D-74](DECISIONS.md#d-74), and absorbed into `ARCHITECTURE.md` §5 before any
> code.** **Yes** — the profile carries an optional `text_view` defaulting to
> `working`, **conditional on an end-to-end test at a non-default value**;
> without that test the field does not ship. **There is no open gate: a session
> starts at slice A and runs straight through.** The rest of this section is
> the record of why, and §5 carries the one distinction that makes the answer
> compatible with D-69 rather than a partial reversal of it.

### G-1 — Does the run profile carry the model-input text view? — **answered: yes, conditionally**

[D-69](DECISIONS.md#d-69) built the text-view selection seam in PR 4 as a
construction argument on `EmbeddingComponent`, and deferred exactly one half of
the question to this PR: *"**PR 7 — the profile field.** PR 7's work list
already defines the run profile… If a model-input view belongs in a profile,
that is where it goes."* `ARCHITECTURE.md` §5 repeats it. So this is PR 7's
inherited call, not a new one.

- **Yes — an optional `text_view` field, defaulting to `working`.** Costs a few
  lines: the profile passes it to `EmbeddingComponent`'s constructor, which
  already validates it and records the resolved view in its observation. It
  makes [D-55](DECISIONS.md#d-55)'s deferred comparison a **configuration
  change end to end**, which is the entire rationale D-69 was decided on.
- **No — leave it a construction argument only.** The comparison is deferred
  and has no evaluation set to run against (D-55, D-66), so the field would be
  unexercised surface — the same argument D-69 used to *reject* registering a
  second embedding implementation in PR 4.

**Decided: yes, with the condition — a test that actually flips it.** The
asymmetry with D-69's rejected registry entry is that a profile field is read by
code PR 7 is building anyway and is exercised by a single end-to-end test at a
non-default value, whereas a registered implementation nothing selects is
exercised by nothing. **If the field ships without that test, it should not ship
at all** — D-74 makes that conditional part of the decision, not advice.

**The half of D-69's objection that did *not* expire, and how D-74 answers it.**
D-69 gave two reasons against a `RunConfig` field: no runner read one until
PR 7 (discharged here), *and* that it would be a second selection mechanism for
one stage, which §6 exists to prevent. The second is structural and still
stands. What resolves it is a distinction D-69 had no occasion to draw:

- **Which implementation serves a stage** is §6's configuration — keyed
  `(stage, implementation_id)`, resolved through the registry, recorded in
  `RunContext.component_selections`.
- **How the selected implementation is constructed** is not. `EmbeddingComponent`
  already takes its provider and its pooling strategy as construction
  arguments; neither is a registry key or a record field, and `text_view` is
  the same kind of thing.

So the profile carries a construction parameter, **not** a `RunConfig` or
`RunContext` field — adding one of those would be exactly the parallel
mechanism D-69 refused. Provenance needs no new field either: the resolved view
is already recorded in the stage-8 observation and reaches `results.jsonl`
through `views.py` (D-69, slice A).

`ARCHITECTURE.md` §5's profile bullet is rewritten accordingly — it no longer
says a profile field "is PR 7's", which was a statement about the future.

## 4. Slice A — The 1.1 input schema and record construction

**New module** (suggested `evaluator/input_schema.py`), never an extension of
`schema.py` (§1).

- **Columns**, per PR 7's work list: `request_id`, `prompt_uid`, `response_id`,
  `prompt_text`, `response_text`, and the supplied hazard. Name the hazard
  column deliberately — the baseline calls it `hazard`, the record calls it
  `supplied_hazard`, and the 1.1 schema should match the record, since that is
  what every downstream document calls it.
- **Validation is structural only**: missing columns, blank required values,
  duplicate `response_id`. **Hazard validity is not this module's job** — it is
  `validate_supplied_hazard`'s, against a scope that does not exist until
  `open_run` has run. Keep them apart; conflating them is how a run rejection
  ends up raised from a CSV reader with no scope to name.
- **Reject a blank `response_id` rather than synthesizing one.** Identity is
  the input's contract, and a synthesized id silently breaks a consumer's join
  back to their own data.
- **Record construction is a named function**, not inline in the loop, with the
  full contract in one place: `texts=TextViews(original=response,
  decoded=response, working=response)`, `exhausted_at=None`, empty
  observations/flags/`per_hazard`, `overall_result="failure"` and
  `overall_failure_reason="not yet evaluated"` as the pre-integration
  placeholders every existing test uses, and `run=` the `RunContext`.
- **`evaluated_hazards` — the contract nothing else owns.** Set it to
  `(supplied_hazard,)` and **pin that with a commented test**: in 1.1 stage 3
  is a placeholder that returns no additional hazards, so supplied-only is
  correct *because* `detected_hazards` is always empty, not because the merge
  is unnecessary. **Where the merge belongs when stage 3 becomes real is stage
  3 itself**, not the runner: `ARCHITECTURE.md` §2 says `hazard_scope`
  "constrains which *additional* hazards detection may return", and a component
  can read `record.run.hazard_scope` for that. Say so in the comment so the
  next session finds an answer instead of the question.
- Fix `evaluator/__init__.py`'s stale docstring (§2).

**Exit:** a CSV of 1.1 rows loads, validates, and produces well-formed records;
malformed input is rejected with a message naming the offending column or row;
433 + n tests green.

## 5. Slice B — The run profile and artifact resolution

- **The profile carries what `RunConfig` needs and resolves what it cannot**:
  component selections, artifact id, rule version, hazard scope — **plus
  `text_view`, optional and defaulting to `working`**
  ([D-74](DECISIONS.md#d-74), `ARCHITECTURE.md` §5). A JSON file is the natural
  form (it is provenance a consumer should be able to diff), with CLI flags
  able to override.
- **`text_view` is a construction parameter, and the code must keep it one.**
  It goes profile → component factory → `EmbeddingComponent(...)`. It does
  **not** become a `RunConfig` field, a `RunContext` field, or a second
  registry key — those are §6's implementation-selection surface and D-69
  refused a parallel mechanism there. `EmbeddingComponent` already validates
  the name at construction and records the resolved view in its observation,
  so PR 7 adds no validation and no provenance of its own; **if a session finds
  itself writing either, it has built the wrong thing.**
- **The conditional test is a deliverable, not a nicety** (D-74): one
  end-to-end run with `text_view: "disclaimer_stripped"`, asserting the
  stage-8 observation records that view in `results.jsonl` and that the
  embedded text is the stripped one. Without it the field does not ship —
  an unexercised profile field is the same unverified surface D-69 rejected
  when it declined to register a second embedding implementation.
- **`hazard_scope` defaults to the artifact's frozen supported set**
  ([D-57](DECISIONS.md#d-57)) **in the profile layer, not in `open_run`.**
  `open_run` should keep receiving a concrete scope, so `RunContext` always has
  a resolved one and §2's invariant holds. An explicit narrower scope is
  allowed; a wider one stays an `open_run` condition-(2) rejection, untouched.
- **Artifact resolution is baseline-only in PR 7, deliberately.**
  [D-49](DECISIONS.md#d-49) defers the 1.1 artifact format to PR 5, so the
  profile's `artifact_id` resolves to a **baseline** artifact directory loaded
  with `model.load`, which supplies both the classifier for
  `BaselineTwoHeadScorer` and `trained_hazards` for `open_run`. Build **one
  small named function** for this, not an abstraction layer with one
  implementation — PR 5 adds the 1.1 branch beside it. Note in that function
  that it is PR 5's extension point.
- **Component registration is one nameable place.** The runner must not import
  concrete components (§1), so a single `build_registry(...)`-style factory
  owns those imports and returns a populated `Registry` plus the default
  component selection. That factory is the only PR 7 file that imports
  `components/*`, and the exit criterion "the runner selects components only
  through the registry" is tested by asserting the runner module's own imports,
  the way `experiments/candidates.py::_assert_no_fixed_rule_import` does — a
  real check, not a comment.

**Traps:**

- Do not add a `RunConfig` field for the text view *and* a constructor argument
  and a CLI flag. One resolution path: profile → `EmbeddingComponent(...)`.
- `rule_version` must come from the `RuleSet` actually used, not a literal
  typed into a profile that can drift from it.

**Exit:** a profile file plus an artifact directory produce a valid
`RunContext` with a resolved, recorded hazard scope; a scope wider than the
artifact supports is rejected by `open_run` with a message naming the hazards.

## 6. Slice C — The batch runner and `failures.csv`

**The specification is `ARCHITECTURE.md` §2 and §11. Read §2's rejection list
before writing the loop.**

- **Two passes, and this is the crux of PR 7.** §2 makes a bad supplied hazard
  a **run-level rejection** — condition (1) is about "the supplied hazard of
  *any input row*" — and PR 7's exit criterion says a run rejection "aborts
  before any row is scored". So:
  1. load and structurally validate every row (slice A);
  2. `open_run` once;
  3. **`validate_supplied_hazard` over every row, before scoring any**;
  4. only then loop, scoring row by row.

  A runner that folds step 3 into step 4 aborts mid-batch with results already
  written for earlier rows, which is precisely what §2 says a rejection is not.
  **Write the test that would catch it**: a two-row input whose *second* row
  has an out-of-scope hazard must produce **no** output files and no scored
  record — not one row of results plus an error.
- **A per-row failure never aborts the batch.** Everything the pipeline itself
  produces — a `ComponentError`, a phase D per-hazard failure, an unexpected
  exception from a component — becomes a `failures.csv` row and the loop
  continues. The distinction to hold onto: **rejections are about the run's
  configuration and input contract; failures are about a row's content.**
- **`failures.csv` is a view derived from the record** (§11), not a second
  bookkeeping structure the runner maintains. Build it in `views.py` beside
  `result_view` and `prediction_rows`, with its own `FAILURES_VERSION` — §11
  requires every view be versioned separately. Carry the identity fields, the
  hazard, the failure reason from the `HazardJudgment`/`ComponentError`, and
  the stage that produced it. **Carry no text**, matching `prediction_rows`'
  sensitive-data bound.
- **A row whose every hazard failed still appears in `results.jsonl`.** The
  record is canonical and lossless; `failures.csv` is the narrow view. Do not
  make them exclusive.
- **Determinism:** same input, same profile, same artifact → byte-identical
  outputs. Sort nothing by dict iteration order, and write rows in input order.

**Exit:** an unlabeled input file produces `results.jsonl`, `predictions.csv`,
and `failures.csv`; a run rejection produces none of them; a per-row failure
produces all three with the failed row named in the third.

## 7. Slice D — The two entry points

- **In-process Python entry point first**, and the CLI as a thin wrapper over
  it. The exit criterion is that the two produce **identical records for
  identical input**, which is only cheap to guarantee if one calls the other.
- **A fourth CLI, not a modification of the three** (D-48). Suggested name
  `hrc-run` — `hrc-evaluate` is taken by the baseline and means something else
  (it scores *labelled* rows against ground truth). A session may pick a better
  name; what it may not do is reuse or repurpose an existing one.
- Flags: profile path, artifact directory, input CSV, output directory, plus
  `add_allow_download_flag` for the encoder, matching `cli/_common.py`'s
  existing conventions and its `fatal()` error style. Reuse `_common.py` rather
  than writing a fourth error path — it is shared code, but *reading* it is not
  a D-48 concern.
- **The identity test is a real test**, not an assertion that both call the
  same function: run both, compare the parsed `results.jsonl`.
- `pyproject.toml` gains one `[project.scripts]` entry.

**Exit:** `hrc-run --help` works from an installed environment; CLI and
in-process runs of the same input produce identical records.

## 8. Slice E — A real run, the sweep, and PR 7 close

> **Complete** (2026-08-05). **510 tests green** (502 + 8 new, all in one
> new integration module), `test_baseline_parity.py` unchanged. The
> sweep is a critique pass (`META_PLAN.md` §6), so it was expected to alter
> specifications rather than behavior, and it did: **this slice changed no
> source file except two docstrings** — `views.py`'s and
> `evaluator/__init__.py`'s.
>
> **The real run**, `tests/integration/test_evaluator_runner_real_bge.py`
> (8 tests): a 4-row CSV on disk, a profile with nothing injected — no
> `provider`, no `pooling`, so `build_registry`'s own default real
> `BgeEmbeddingProvider` is what runs — the golden baseline artifact, and
> all three views written to a temp directory and read back. Two hazard
> families (`hte`, and enablement-only `prv`), two exhaustion routes, the
> real CLI compared **byte-for-byte** against the in-process run, a
> second-row rejection writing no file at all, and D-74's non-default
> `text_view` asserted on the written `results.jsonl` rather than in
> memory. Separately, the installed `hrc-run` console script was driven by
> hand end to end — not only `--help` — and its three files inspected.
>
> **The measured cost** (`scripts/probe_runner_throughput.py`, the quotable
> source): 177 real rows from `data/`, mean response ~2.5k characters,
> CPU-only. **41.4 s total, 4.77 rows/s steady state**, with the first row
> costing 4.49 s while the encoder's weights load; median row 0.129 s,
> slowest 1.70 s. Startup, input validation, and writing all three views
> together are 0.044 s — the cost is the encoder, as §9 predicted, and §9's
> instruction not to redesign it was followed. Extrapolating: `data/`'s full
> 859 rows ≈ 3 minutes, 10,000 rows ≈ 35 minutes. **Not a finding** — no
> decision is requested.
>
> **Six findings, all closed in-session; five are documentation.**
>
> 0. **The real run corrected one of its own new assertions before it
>    landed.** It asserted that an exhausted row has *no* stage-8
>    observation. §3.1 in fact records a `skipped_short_circuit` observation
>    for every skipped stage, so the encoder's non-participation is stated in
>    the record rather than left to be inferred from a gap. The test now
>    asserts the stronger, true property. Recorded because it is the exact
>    thing a real run is for: a stub-backed test would have been written the
>    same wrong way and passed.
> 1. **`ARCHITECTURE.md` §3.2's module layout never gained PR 7's four
>    files** — `input_schema.py`, `profile.py`, `runner.py`, `entrypoint.py`.
>    It had described the package as of PR 1. Added, with `profile.py` marked
>    as the single dependency-rule exemption and the test that enforces it
>    named (§12 lesson 2, from the other direction).
> 2. **§2 attributed all three rejection conditions to `open_run`, with a
>    signature the code has never had.** `open_run(config, artifact) -> Run`
>    is really `open_run(config, registry, supported_hazards) ->
>    RunContext`, and it checks conditions (2) and (3) only — condition (1)
>    is a property of an *input row*, which no run-entry call can see. This
>    is not cosmetic: the split is *why* the two-pass runner is required
>    rather than preferred, and §2 is the section that was supposed to say
>    so. Corrected, with the requirement stated and the test that pins it
>    named.
> 3. **§6's parallelism bullet still said "where PR 7's runner needs it"** —
>    a sentence about the future that PR 7 answers: it needs none, builds
>    none, and now has a measured number instead. Rewritten (D-61's
>    absorption, re-checked).
> 4. **`README.md` said three components ship `partial`; §7's table says
>    four.** The dropped item is stage 9, L/E scoring — *the same undercount,
>    dropping the same item*, that PR 4's sweep corrected in §7's own prose
>    one PR earlier, surviving in the sibling document because the README
>    names the three D-entries (D-50, D-51, D-70) and stage 9 has none.
>    Corrected. **This is the fifth consecutive sweep to find D-47 inventory
>    staleness**, and the second to find this specific item missing.
> 5. **`README.md` described a three-CLI package** and a `scripts/`
>    directory holding one script, and carried a stale test count. All three
>    became false with PR 7. Corrected, plus a `docs/howto/hrc-run.md` and
>    its documentation-table row — every other CLI has one, and the queue
>    proposal's rules for every PR require documentation.
>
> **One finding recorded and deliberately not fixed**, because fixing it is a
> component change (§10): `components/scoring.py` accumulates
> `ComponentError`s across *every* evaluated hazard into one list and stores
> only `errors[0]` on its single observation, so in a multi-hazard record
> only the first failing hazard's error survives, and `failures.csv`
> attributes the rest to `final_integration`. It understates detail, never
> the fact of a failure — `HazardJudgment.failure_reason` is the
> authoritative text and the row is emitted from phase D's verdict, not from
> the observation. Slice C had recorded the narrower "both L and E for one
> hazard" version of this in `views.py`; the sweep found it was broader.
> Routed to `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5's work list, which replaces
> that component, so it lives in two places rather than one — PR 4's sweep
> finding 5, applied.
>
> **What was checked and was clean:** every PR 7 exit criterion maps to a
> named test (§11's table below, filled in); D-57's default is real for the
> first time and matches §2 exactly — `frozenset(classifier.trained_hazards)`,
> resolved in the profile layer and not in `open_run`, so `RunContext` always
> carries a concrete scope and condition (2) is unreachable by default;
> D-69's and D-74's absorption match what shipped, with `text_view` flowing
> profile → `build_registry` → `EmbeddingComponent(...)` and appearing in no
> `RunConfig`/`RunContext` field and no registry key; §11's `failures.csv`
> row and `views.py`'s docstring, both corrected in slice C, still describe
> the code; the D-47 inventory's other ten items are each still true of
> `ARCHITECTURE.md` §7 and `README.md`; no PR 7 exit criterion was met by
> scoping rather than by building, so no new ledger entry is owed
> (D-74 is the only decision this PR needed, and it was locked before slice
> B); and the three baseline CLIs are untouched (D-48).

- **A real, non-mocked end-to-end run**, extending
  `tests/integration/test_evaluator_real_bge.py` or beside it, as PR 2, PR 3,
  and PR 4 each did: a small CSV, the real BGE encoder, the golden baseline
  artifact, all three views written to a temp directory and read back. **PR 1's
  one verification gap was the un-exercised real provider**; PR 7's equivalent
  would be an un-exercised real file path.
- **Report the wall-clock cost of a real run** and note rows-per-second in
  `STATUS.md`. Not a performance-tuning exercise (§9) — a recorded number, so
  the first person to run a large batch is not surprised.
- **Full suite green, including `test_baseline_parity.py`** (D-48). PR 7 adds a
  CLI and must not perturb the three that exist.
- **Map each PR 7 exit criterion to what verifies it** (§11's table), and record
  anything met by scoping rather than by building with a ledger entry.
- **Re-check D-57's and D-69's absorption against what shipped** — D-57's
  default becomes real for the first time in this PR, and G-1 either fulfils
  `ARCHITECTURE.md` §5's profile-field sentence or requires rewriting it.
- **The D-47 inventory, item by item.** Four consecutive sweeps have found
  staleness there. PR 7 adds no component, but it is the first PR that makes
  the evaluator *runnable*, which is exactly when a limitations reader arrives.
- `STATUS.md`: each slice in Recently Completed, new assumed-concurrence rows
  with reversal scope, this plan marked as a record of what was built.
- **Do not close item 4** — PR 5 and PR 6 remain.

## 9. Performance: measure, do not redesign

`ARCHITECTURE.md` §8 fixes **one embed call per record**, shared across every
evaluated hazard. A batch of *N* rows therefore makes *N* encoder calls, which
is slower than one batched call over all rows — and **restructuring that is not
PR 7's to do.** It would change the embedding boundary §8 specifies, move a
component's work into the runner, and break the "one shared, replaceable
embedding pass per scoring batch" contract that D-35's principle carries into
1.1.

So: measure it (§8), record it, and if it is genuinely too slow for a real
benchmark run, that is a finding for `STATUS.md` and a decision for Kurt — not
a refactor a plumbing PR takes on its own initiative. The same applies to
process-level parallelism under [D-61](DECISIONS.md#d-61): permitted, but
nothing in 1.1 has demonstrated a need, and an unexercised parallel path is
untested surface.

## 10. Explicitly out of scope for PR 7

- **Any component change.** PR 7 drives the pipeline; it does not touch stages.
  If a stage looks wrong, that is a finding, not a fix (the exception PR 4's §10
  names: a specification that turns out false about the code).
- **The 1.1 evaluator artifact format and its reader** — PR 5's, under D-49.
  PR 7 loads the baseline artifact.
- **`metrics.json`** — `views.py` records that it needs approved criteria and
  the approved uncertainty method; PR 5 produces the numbers and PR 6 decides
  whether a view ships.
- **Batching the encoder across rows, or threading anything** — §9.
- **Modifying the three baseline CLIs or `schema.py`** (D-48).
- **The promotion decision (D-58) and the limitations document (D-47)** —
  PR 6's.

## 11. Exit criteria → how each is verified

Filled in at the close, 2026-08-05. Every row names the test that actually
runs, not the slice that was supposed to produce it.

| PR 7 exit criterion | Verified by |
|---|---|
| An unlabeled input file scores end-to-end with no retraining, producing `results.jsonl`, `predictions.csv`, and `failures.csv` | `test_evaluator_runner_real_bge.py::test_a_real_unlabeled_input_file_scores_end_to_end_into_all_three_views` — a CSV on disk, the real encoder (nothing injected), the golden artifact loaded read-only, all three files read back. Plus `test_evaluator_runner.py::test_a_clean_batch_writes_all_three_files_including_an_empty_failures_csv` at the unit level, and a by-hand run of the installed `hrc-run` console script |
| A run rejection aborts before any row is scored and names the offending value and reason; a per-row failure does not abort the batch | `test_evaluator_runner.py::test_a_bad_hazard_on_the_second_row_scores_nothing_and_writes_nothing` — the **second** row is the bad one, and the load-bearing assertion is `provider.calls == 0`, confirmed as a real forcing function by sabotage (folding validation into the scoring loop turns it red at `calls == 1`). Real-path twin: `test_evaluator_runner_real_bge.py::test_a_run_rejection_on_the_real_path_writes_no_output_file_at_all`, which asserts the output directory does not exist rather than listing three absent names. The other half: `test_a_failing_row_does_not_abort_the_batch_and_lands_in_failures`, `test_a_mixed_batch_scores_the_good_rows_and_fails_only_the_bad_one`, `test_a_component_that_raises_fails_only_its_own_row`, and `test_a_run_rejection_is_never_swallowed_into_a_failures_row` — which pins that the two classes cannot collapse into each other |
| The resolved hazard scope is recorded in the run context and in every output record | `test_evaluator_runner_real_bge.py::test_the_resolved_hazard_scope_reaches_every_written_record` — asserted on the written `results.jsonl`, not on the in-memory context, and with no `hazard_scope` in the profile, so it is D-57's default that is being read back. Plus `test_evaluator_profile.py::test_resolve_defaults_hazard_scope_to_the_artifacts_trained_hazards` and `test_evaluator_entrypoint.py::test_run_records_the_resolved_hazard_scope_in_every_output_record` |
| The CLI and the in-process interface produce identical records for identical input | `test_cli_run.py::test_cli_and_in_process_produce_identical_records_for_identical_input` (parsed **and** byte-for-byte; confirmed a real check by sabotage — making the CLI override `text_view` after loading the profile turns it red), and `test_evaluator_runner_real_bge.py::test_the_cli_and_the_in_process_run_agree_byte_for_byte_on_the_real_path`, which repeats it with a profile file read from disk and the real encoder |
| The runner selects components only through the registry and never imports a concrete component | `test_evaluator_profile.py::test_only_profile_py_imports_components` — a parsed-source assertion over every `.py` directly under `evaluator/`, in the shape of `experiments/candidates.py::_assert_no_fixed_rule_import`. It globs at collection time, so it picked up `runner.py` and `entrypoint.py` with no edit. `test_profile_py_does_import_components` is the other half: it fails if the check ever becomes vacuous |
| *(D-74's own condition on shipping `text_view` at all)* | `test_evaluator_profile.py::test_profile_text_view_flows_to_the_embedded_text_and_into_results_jsonl` — an end-to-end run at `disclaimer_stripped`, asserting the encoder received the stripped text. Extended at the close by `test_evaluator_runner_real_bge.py::test_a_non_default_text_view_in_a_profile_file_reaches_the_written_result`, which reads the resolved view back out of a `results.jsonl` on disk |

## 12. Lessons carried forward

1. **Read the code, not just the docs about the code**
   (`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 lesson 6). Three of this plan's
   specifics — `evaluated_hazards` never being updated, `hazard_scope` having
   no default, `schema.py` lacking the 1.1 identity columns — came from reading
   modules, not from the queue proposal.
2. **A specification sentence about the future is a debt.**
   `ARCHITECTURE.md` §5 says a profile field "is PR 7's"; §11 says
   `failures.csv` is "built by PR 7"; `views.py`'s docstring says the runner
   "does not exist yet". All three become false the moment PR 7 lands, and all
   three must be updated in the same session — this is the absorption-gap
   failure mode, seen from the other direction.
3. **Beware the component that runs and looks healthy** (§10 lesson 5). A
   runner that scores 999 of 1000 rows and quietly drops one is the exact shape
   of this failure. Count rows in and rows out, and assert the total.
4. **Distinguish the two failure classes.** Rejections are about configuration
   and the input contract; failures are about a row's content. Most of PR 7's
   subtlety is in keeping them apart.
5. **End with Open Questions, even if empty** (§10 lesson 9, `META_PLAN.md` §3).

## 13. When a slice raises something this plan did not anticipate

`SCIENCE.md` governs on any behavioral conflict; `ARCHITECTURE.md` on any
structural one. Per `META_PLAN.md` §3: below ~90% confidence, or in conflict
with a specification, or a tradeoff only Kurt can make — stop and add it to
**Awaiting User** rather than choosing.

The specific risk here: **PR 7 touches every part of the system without owning
any of it**, so a session will meet several things that look broken from the
runner's seat. The default response is a finding, not a fix. The one exception
is the same one PR 4 acted on — a specification sentence that is false about
the code — where the specification is what to correct, in the same session.

## Open Questions

**None open.** Both rows below are answered; they are kept as the record of
what was asked and how it was settled.

| Question | Status | Where it lands |
|---|---|---|
| **G-1** — does the run profile carry the model-input text view? | **Answered 2026-08-05: yes, conditional on an end-to-end test at a non-default value.** The structural half of D-69's objection is answered by distinguishing *which implementation serves a stage* (§6's registry) from *how it is constructed* (the profile) — so no `RunConfig`/`RunContext` field and no second registry key | [D-74](DECISIONS.md#d-74); `ARCHITECTURE.md` §5's profile bullet, rewritten; slice B |
| **An all-or-nothing abort on one bad hazard** is what `ARCHITECTURE.md` §2 specifies, and §6 implements it as written. It is also harsh for a large benchmark input, where most harnesses would route the bad row to `failures.csv` and continue | **Closed 2026-08-05 as [D-75](DECISIONS.md#d-75)** — Kurt took the mitigation, not the amendment. §2 is unchanged: condition (1) is still run-level, still aborts before any row is scored, still writes nothing. What changed is that a rejection now names **every** offending row rather than the first, and `hrc-run --check-input` reports them without scoring anything | **A correction is part of this closure.** The row previously said one bad hazard code "discards the entire run's work" on a 35-minute input. That was wrong, and it is the kind of claim §12 lesson 1 exists to catch: pass 1 runs *before* any scoring, so a 10,000-row file is rejected in about **two seconds** with nothing embedded and nothing thrown away. The real cost was narrower — the message named only the first offender, making a file with *k* bad codes a *k*-round fix-and-rerun loop, and there was no way to ask the question without starting a run. D-75 fixes exactly that and rejects the §2 amendment on the record, with the reasoning for keeping the strictness |

Nothing else in PR 7 is open. The pipeline, the record, the registry, the
rejection conditions, the view contracts, and the single-threaded contract are
all settled by `ARCHITECTURE.md` §2–§11 and D-56/D-57/D-60/D-61 — and none of
them should be re-derived.
