# Decision Ledger

**This ledger is provenance, not authority.** Once a decision's effect has been
written into a specification, that specification is what governs — this file
records *why* it says what it says, and what was rejected on the way. Read it
when you need the reasoning behind a constraint, not to discover the
constraint.

Where to look instead:

| For | Read |
|---|---|
| Release 1.1 assessment behavior | [`../SCIENCE.md`](../SCIENCE.md) |
| Baseline module layout, artifact format, CLI structure | [`../ARCHITECTURE.md`](../ARCHITECTURE.md) |
| The implemented pre-staging baseline specification | [`PLAN.md`](PLAN.md) |
| What is being worked on and what is still open | [`STATUS.md`](STATUS.md) |
| The process governing entries here | [`META_PLAN.md`](META_PLAN.md) |

Every entry is `locked` unless marked otherwise. A locked entry that has been
absorbed into a specification is history: it constrains nothing on its own,
because the specification carries the constraint. Reusing a baseline choice for
Release 1.1 requires a new decision, not a citation of the old entry.

**Approval mode (2026-08-04).** Entries lock on Kurt's decision alone, under
`META_PLAN.md` §1.2's single-approver mode; Riki ratifies in batches. Every
entry made that way says so in `Approved by` and carries a row with its
reversal scope in `STATUS.md` §Assumed concurrence, which is the review
agenda. All entries from D-47 onward except D-53 are in this mode.
`proposed` now means nobody has decided, not that fewer than two have.

Entries are retired by superseding them in place, never by deletion. The index
below is the map; every D-number that has ever existed appears in it.

Numbering: new decisions start at **D-71**. D-38 through D-44 were drafted
during the 2026-08-02/03 science-contract work and withdrawn before approval;
those numbers are not reused.

*Note for queue item 2:* `QUEUE_ITEM_2_EXECUTION_PLAN.md` §7 earmarked D-67 for
that item's structure-selection entry, conditional on nothing else taking the
number first. Slice A took it (coverage under D-45 unavailability), so the
selection entry is **D-68**. The plan's own wording anticipated this — read the
line above, not the number written into that plan.

## What the Release 1.1 standard replaces (2026-08-03)

This is not a new decision. At their joint Release 1.1 science-contract
meeting, Riki and Kurt confirmed the requirements already set by the standard
and recorded in `../SCIENCE.md`. As a result, these old baseline rules do not
apply to Release 1.1:

- D-4's prompt-only Legitimization-through-the-head rule and its blank-response
  L/E values are baseline-only. Release 1.1 fixes prompt-only responses at
  L1/E0 where L applies and sends a complete blank payload directly to final
  integration as a refusal with no L or E value.
- D-17, D-21, D-24 through D-26, and D-30's `safe`/`unsafe` names and
  encodings are baseline-only. Release 1.1 uses violating/non-violating. The
  exact replacement field names remain an implementation choice.
- D-3, D-11, D-14, D-22, D-27, and D-31's per-row handling of a missing or
  unsupported supplied hazard is baseline-only. Release 1.1 validates that
  required input before response scoring and rejects the run. Their handling
  of component and artifact failures remains in force for the baseline.
- D-19's pre-threshold disclaimer adjustment is the baseline mechanism.
  Release 1.1 fixes final L at L0 in final integration and does not directly
  lower E. Whether disclaimer text is removed before E scoring is tabled for
  the next architecture/evaluation step.
- D-23's frozen artifact support remains compatible with configurable run
  scope: a run may select only hazards supported by its artifact.

No baseline entry conflicts with the canonical maximum-hazard rollup because
the baseline has no multi-hazard rollup. All unaffected parts of D-1 through
D-37 remain the record of the implemented baseline.

Provenance: Joint Riki–Kurt Release 1.1 science-contract review meeting,
2026-08-03; canonical requirements recorded in this task at Riki's direction.

## Further dispositions from the queue item 1 review (2026-08-03)

Also not new decisions, and **not** part of the seven requirements the joint
meeting confirmed. These follow from requirements already written in
`../SCIENCE.md`; the review only recorded which baseline entries they displace.
The sub-review numbers are `STATUS.md` queue item 1's.

- **Three-class L/E outputs (1.8).** `../SCIENCE.md` §Legitimization Scoring
  and §Enablement Scoring require each model to return a three-class
  multinomial distribution over L0/L1/L2 and E0/E1/E2. The baseline's
  two independently-fit binary heads plus a threshold search cannot produce
  one, so the mechanism does not carry: **D-7, D-9, and D-10 are
  baseline-only**, as is **D-16's retained-head-probability half**. D-2's and
  D-8's statistical warts are properties of that same fitting mechanism and
  are baseline-only with it. Their README disclosure obligation is now
  discharged by [D-47](#d-47), which moves the gate to staging without
  weakening the requirement, so both entries are fully retired. Which
  three-class structure replaces the heads is queue item 2's work and is
  blocked on approved ground truth; nothing here selects it.
- **Full result record (1.5).** `../SCIENCE.md` §Evidence and outputs and
  §Final integration require the result to carry texts, component facts and
  errors, provisional and final judgments, hazards, and provenance. The
  narrower baseline output schemas this displaces — D-17, D-22, D-25, and
  D-31 — were already marked baseline-only, so no entry still in force
  contradicts preserving the full record. D-32 is compatible: a fuller record
  is a superset of its single `rule_reasons` string, and its own disposition
  belongs to 1.7. D-21's side-output is a separate question (1.10). The
  canonical-record *design* — one carried record with purpose-specific
  external views — is an architecture proposal parked in `STATUS.md` queue
  item 3, not a disposition here.

- **Model judgments separated from fixed final rules (1.7).** With C-1
  approved, `../SCIENCE.md` §Final integration is authoritative: the L and E
  models judge what the response means and supplies, and the final step
  applies only the fixed phases, tables, rollup, and failure handling. Three
  baseline entries move:
  - **D-20** — the *principle* carries. `../SCIENCE.md` phase D2 and
    §Evidence and outputs both require that a missing required judgment
    returns a failure rather than a non-violating result, which is D-20's
    fail-closed rule stated at the 1.1 level. Its **mechanism is
    baseline-only**: `(component, hazard)` cells and a `thresholds.json`
    `status` field are two-head artifacts, and the 1.1 failure unit is a
    hazard, not a cell.
  - **D-32** — **baseline-only.** Its single `rule_reasons` string exists to
    explain D-4's forced-zero short-circuit, and D-4 is already baseline-only.
    Under the approved split the fixed phases generate their own reasons; what
    shape those take in the record is item 3's.
  - **D-35** — the *principle* carries. `../SCIENCE.md` §Modular pipeline
    requires one shared embedding pass, which is what D-35 chose. Its concrete
    `build_component_features` signature was left to architecture and is now
    **baseline-only** (see the item 3 disposition below).
- **Blank payload and prompt repetition (1.3); Specialized Advice disclaimers
  (1.4).** `../SCIENCE.md` §Per-hazard finalization phases B1, B2, and C carry
  these, and D-4 and D-19 were already marked baseline-only. Both sub-reviews
  close with the amendment's approval; no further entry moves.

- **Metric contract (1.9).** `../SCIENCE.md` §Legitimization Scoring and
  §Enablement Scoring require each of L0/L1/L2 and E0/E1/E2 to be evaluated
  separately and treated as equally important, and §Evidence and outputs
  requires an uncertainty estimate with every reported metric. The baseline's
  contract — exact-match, high-head AUC, and QWK over two binary heads —
  cannot establish per-outcome success for three classes and reports bare
  point estimates. **D-13, D-15, D-16's metric half, and D-33 are
  baseline-only.** The approved criteria themselves are an external input from
  the Standards team; they gate *claiming* a component scientifically
  successful, not this displacement. D-34 remains evidence that the pipeline
  ran on real data and is not a quality finding.
- **Continuous score (1.10).** **D-21 is baseline-only.** Not a naming change:
  `v14_overall_unsafe_score` is computed from the two binary heads' centered
  probabilities, and 1.8 made that mechanism baseline-only, so Release 1.1
  cannot compute the quantity at all. Reconstructing an equivalent from the
  three-class distributions would be a new quantity under an old name, shipped
  without the approved target and threshold `../SCIENCE.md` §Continuous score
  requires — and under retired `unsafe` terminology. The score is deferred,
  not deleted: §Continuous score already permits an approved continuous
  violation score, which would return as a new decision derived from the
  three-class distributions, not as a revival of D-21.

- **Embedding boundary and artifact format (retired queue item 3).**
  `ARCHITECTURE.md` §8 restates D-35's one-shared-pass principle for a pipeline
  whose stage boundaries differ from the baseline's, so the principle carries
  but `build_component_features`'s two-component signature does not — it is
  **baseline-only**. **D-36** is baseline-only for the same reason: pooling
  becomes a replaceable strategy behind that boundary because representation
  and pooling are named comparison axes for queue item 2, so the architecture
  must not hard-code mean-only. **D-37** splits: its no-pickle, no-`joblib`
  constraint is a security choice independent of model structure and
  **carries**, while whether `.npz` + JSON remains sufficient for the model
  payload follows from the structure item 2 selects.

Provenance: queue item 1 sub-reviews 1.3 through 1.10, executed 2026-08-03.
These record displacement only. Reusing any baseline choice for Release 1.1
still requires a new decision (read "joint" out of this as of 2026-08-04 —
`META_PLAN.md` §1.2).

Approval state: C-1's model/integrator split has agreement from both Riki
(who directed it, recorded in `critiques/2026-08-02-science-contract-branch.md`)
and Kurt (2026-08-03).

Three further calls were approved by Kurt on 2026-08-03 and are **in force
under an assumed concurrence**: Kurt directed on 2026-08-03 that Riki's
agreement be assumed so dependent work could proceed. Riki's confirmation is
not on record, so this is not the two-party agreement `META_PLAN.md` §1.1
describes — it is Kurt's direction to proceed as though it were, recorded
plainly so the distinction survives. The dispositions resting on each are
listed so a later dissent has a clear reversal scope:

| In force under assumed concurrence | Dispositions resting on it |
|---|---|
| `../SCIENCE.md`'s blank-payload and phase-C amendment | 1.3, 1.4, and 1.7's D-20/D-32/D-35 moves |
| C-6's limitations-document rule, with the pre-staging disclosure floor — now **[D-47](#d-47)** | 1.9's release-claim half; D-2 and D-8's disclosure obligation |
| D-21 dropped from Release 1.1 output | 1.10 |

C-6's rule became **D-47** because it states a repository documentation
obligation that no specification carries; its `Approved by` line records the
assumption rather than claiming Riki's agreement. The other two record
displacement by requirements `../SCIENCE.md` already states and need no entry
of their own.

**One item to close on Riki's next review:** confirm these three. If any is
rejected, the reversal scope is the table above, and `../SCIENCE.md`'s phase B1
plus the final-L/E line under §Evidence and outputs revert together.

**These three are not the whole list.** Later calls were placed on the same
footing — notably [D-48](#d-48) (2026-08-04), which amends `../SCIENCE.md`
§Evidence and outputs. `STATUS.md`'s assumed-concurrence table is the complete
register and carries each one's reversal scope; this section records only the
2026-08-03 set that first established the practice.

**Recorded assumption (Kurt, 2026-08-03): label sparsity is not a design
driver.** Release 1.1 planning assumes the Standards team supplies enough
human ground truth that per-class sparsity edge cases are unlikely. This is
why 1.9 closed without waiting for a minimum per-class evaluation-set size.
It is an assumption, not a measured fact: the baseline's sparsity machinery
— D-2's five-own-row threshold cliff and D-33's undefined-QWK null — is
baseline-only under this assumption rather than proven unnecessary, and
defensive handling of a degenerate population should not be removed from any
1.1 implementation on the strength of it. If the delivered ground truth turns
out thin in some class, this assumption is the thing that failed, and 1.9's
metric dispositions are where to look first.

## Index

**Absorbed into** names the specification that now carries the decision's
effect. Where a row says *gap*, the effect exists in code and in this ledger
but in no specification — those are listed under "Absorption gaps" below.

**Release 1.1** says whether the decision reaches past the baseline.
*carried* — still applies. *baseline-only* — the 1.1 standard replaces it (see
the two scope notes above). *under review* — binding today, queued for
amendment at the `STATUS.md` item shown. *open* — needs a call.

A row may carry two clauses when only part of an entry is displaced — D-2,
D-8, and D-16 each have a fitting-mechanism half that the three-class
requirement replaces and a second half (a documentation obligation, a metric
contract) that is still in force. Read both clauses; the entry is not retired
until neither remains.

**Resolving the numbers in this column.** A bare `(item N)` is a live
`STATUS.md` queue item. A decimal `(1.N)` is a sub-review of the Release 1.1
science-to-decision review, which closed 2026-08-03 and is retired from the
queue — its record is in `STATUS.md`'s Recently Completed entries for that
date and in "Further dispositions from the queue item 1 review" above.
Retired numbers are never reused, so both forms keep resolving.

| # | Decision | Absorbed into | Release 1.1 |
|---|---|---|---|
| [D-1](#d-1) | Holdout-seed rows excluded from the fit | `PLAN.md` §3 step 4; `ARCHITECTURE.md` Artifact format | carried |
| [D-2](#d-2) | In-sample threshold/centering bias preserved | `PLAN.md` §3 step 4, §8.2; `README.md` | baseline-only (mechanism 1.8; disclosure discharged by [D-47](#d-47)) |
| [D-3](#d-3) | Fail closed on unknown/unfit cells | `PLAN.md` §6, §11.1 | baseline-only; module-capability half moved to item 3 |
| [D-4](#d-4) | Empty/echo-only rows excluded from the fit | `PLAN.md` §3 step 4, §6 step 2 | baseline-only → `SCIENCE.md` §Final integration |
| [D-5](#d-5) | Zero-row cells keep the constant-probability substitute | `PLAN.md` §3 step 4, §4; `ARCHITECTURE.md` Artifact format | **superseded by [D-45](#d-45)** |
| [D-6](#d-6) | CPU-only; determinism | `PLAN.md` §3 step 3, §8.1; `ARCHITECTURE.md` Module map | carried |
| [D-7](#d-7) | Standardization stats unweighted per component | `PLAN.md` §2.3, §3 step 4 | baseline-only (1.8) |
| [D-8](#d-8) | `class_weight` / sample-weight wart documented | `PLAN.md` §3 step 4; `README.md` | baseline-only (mechanism 1.8; disclosure discharged by [D-47](#d-47)) |
| [D-9](#d-9) | Ordinal monotonicity enforced | `PLAN.md` §3 step 4 | baseline-only (1.8) |
| [D-10](#d-10) | Monotonicity gate mechanism | `PLAN.md` §1.1, §2.3, §3 step 4 | baseline-only (1.8) |
| [D-11](#d-11) | Predict-time check precedence | `PLAN.md` §6 | baseline-only |
| [D-12](#d-12) | No `--cv` | `PLAN.md` §1.1, §5, §9, §10 | carried |
| [D-13](#d-13) | Auto-partition by the recorded holdout split | `PLAN.md` §3 step 5, §4, §5 | baseline-only (1.9) |
| [D-14](#d-14) | Hard-fail rows excluded from measurement | `PLAN.md` §5, §6 | baseline-only |
| [D-15](#d-15) | Legitimization metrics exclude enablement-only rows | `PLAN.md` §5 | baseline-only (1.9) |
| [D-16](#d-16) | Retained head probabilities; high-head AUC | `PLAN.md` §5 | baseline-only (head probabilities 1.8; metric contract 1.9) |
| [D-17](#d-17) | Final-label positive class + output schema | `PLAN.md` §4, §5 | baseline-only → `SCIENCE.md` §Evidence and outputs |
| [D-18](#d-18) | Legitimization not required for enablement-only hazards | `PLAN.md` §3 step 4, §4 | carried (`SCIENCE.md` §Final integration rule 3) |
| [D-19](#d-19) | Business-rule stage between centering and thresholding | `PLAN.md` §5, §6 | baseline-only |
| [D-20](#d-20) | Absent/invalid required cell fails closed | `PLAN.md` §6 step 3 | fail-closed principle carried (`SCIENCE.md` phase D2); cell mechanism baseline-only (1.7) |
| [D-21](#d-21) | `v14_overall_unsafe_score` retained as a side-output | `PLAN.md` §1.1, §6 | baseline-only (1.10); score deferred to `SCIENCE.md` §Continuous score |
| [D-22](#d-22) | `hrc-predict` splits scored and hard-fail outputs | `PLAN.md` §6 | baseline-only |
| [D-23](#d-23) | Family lookups read the frozen `rules.json` | `PLAN.md` §4, §6; `ARCHITECTURE.md` Artifact format | carried (compatible with configurable run scope) |
| [D-24](#d-24) | `seed_prompt_id` required; ground-truth columns ignored | `PLAN.md` §2.1, §6 | baseline-only |
| [D-25](#d-25) | `hrc-predict` CLI contract | `PLAN.md` §6, §10; `ARCHITECTURE.md` CLI layer | baseline-only |
| [D-26](#d-26) | `hrc-evaluate` CLI contract | `PLAN.md` §2.1, §5, §8.1; `ARCHITECTURE.md` CLI layer | baseline-only |
| [D-27](#d-27) | Hazard normalization at load; one `rules.json` lookup | `PLAN.md` §2.1 | normalization carried; unseen-hazard check baseline-only |
| [D-28](#d-28) | Wholly-skipped component surfaced at train/load time | `PLAN.md` §3 step 5, §4; `ARCHITECTURE.md` Artifact format | carried |
| [D-29](#d-29) | Natural error on an unconvertible blank ordinal label | — | **superseded by [D-46](#d-46)** |
| [D-30](#d-30) | `is_safe_ground_truth` encodes exactly `"safe"`/`"unsafe"` | `PLAN.md` §2.1 | baseline-only |
| [D-31](#d-31) | `score(rows)` never raises; per-row result entries | `PLAN.md` §11 item 5 | baseline-only |
| [D-32](#d-32) | `rule_reasons` covers D-4's forced zero only | `PLAN.md` §6 | baseline-only (1.7); reason-record shape → item 3 |
| [D-33](#d-33) | `qwk` reports `null` when undefined | `PLAN.md` §5 | baseline-only (1.9) |
| [D-34](#d-34) | IS-9 closed via a different real dataset | `VERIFICATION.md` (evidence record) | evidence only, not a quality claim (1.9) |
| [D-35](#d-35) | One shared feature-building function | `ARCHITECTURE.md` §8 | shared-pass principle carried; `build_component_features` signature baseline-only (item 3) |
| [D-36](#d-36) | Pooling is mean-only | `PLAN.md` §11 item 2; `ARCHITECTURE.md` §8 | baseline-only (item 3); 1.1 pooling is a replaceable strategy, selected at item 2 |
| [D-37](#d-37) | `.npz` + JSON artifacts; no `joblib` | `PLAN.md` §11 item 4; `ARCHITECTURE.md` §10 | no-pickle constraint carried; payload format follows item 2's structure |
| D-38 – D-44 | *withdrawn 2026-08-03, never approved; numbers not reused* | — | — |
| [D-45](#d-45) | No constant-probability substitute; unfittable = unavailable | `PLAN.md` §3 step 4, §4; `ARCHITECTURE.md` Artifact format | carried; supersedes D-5 |
| [D-46](#d-46) | Purpose-built error on an unconvertible blank ordinal label | `PLAN.md` §3 step 1 | carried; supersedes D-29 |
| [D-47](#d-47) | Limitations document gates staging / release-version assignment | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 | carried; discharges D-2/D-8 disclosure |
| [D-48](#d-48) | Unchanged-output binds the refactored implementation, not a rebuild | `../SCIENCE.md` §Evidence and outputs; `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 1 | carried |
| [D-49](#d-49) | 1.1 evaluator artifact deferred out of PR 1 to PR 5/PR 6 | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 1 exit criteria | carried |
| [D-50](#d-50) | 1.1 ships exact-only prompt-repetition detection | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2; `../ARCHITECTURE.md` §7.1 | carried |
| [D-51](#d-51) | Decoding-failure trigger stubbed; decoder is `partial` | `evaluator/components/decoding.py`; `../ARCHITECTURE.md` §7 | carried |
| [D-52](#d-52) | Ambiguous-reference recording removed from 1.1 | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2 work list | carried |
| [D-53](#d-53) | Run-entry hazard/scope validation mechanism | `src/hazard_classifier/evaluator/run.py` (`open_run`, `validate_supplied_hazard`) | carried |
| [D-54](#d-54) | Narrative and refusal stay placeholders; PR 4's exit criteria scoped | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 4 exit criteria | carried |
| [D-55](#d-55) | E consumes `working`; disclaimer stripping not adopted in 1.1 | `../ARCHITECTURE.md` §5 | carried; comparison deferred, not cancelled |
| [D-56](#d-56) | PR 7 (evaluator runner) added, sequenced before PR 6 | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7 | carried |
| [D-57](#d-57) | Run hazard scope defaults to the artifact's frozen supported set | `../ARCHITECTURE.md` §2 | carried |
| [D-58](#d-58) | Release 1.1 is a pre-staging prototype; promotion decided at PR 6 | `README.md` §Release 1.1 evaluator status | carried; exercises D-47's floor |
| [D-59](#d-59) | L/E structure selection is pre-registered before the eval set arrives | `STATUS.md` queue item 2 | carried; closes D-37/D-49's format half |
| [D-60](#d-60) | 1.1 L/E models receive no prompt input | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 work list | carried |
| [D-61](#d-61) | No concurrency claim; single-threaded contract | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 exit criteria | carried; scopes D-31 for 1.1 |
| [D-62](#d-62) | Continuous violation score is out of Release 1.1 | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 returns | carried; completes D-21 |
| [D-63](#d-63) | 1.1 builds on out-of-version human ground truth (jb v1.0) | `PREREGISTRATION_LE_STRUCTURE.md` §1, §7 | carried; Standards request stops gating |
| [D-64](#d-64) | Split groups on prompt text, not `seed_prompt_id` | `data/interim_split_v1.json`; `scripts/build_interim_split.py` | carried; D-1/D-13 grouping key baseline-only |
| [D-65](#d-65) | 1.1 covers attacked prompts only | `PREREGISTRATION_LE_STRUCTURE.md` §7 | carried; shortfall against a `SCIENCE.md` training requirement |
| [D-66](#d-66) | Interim eval slice is a dev set; real eval set reserved | `PREREGISTRATION_LE_STRUCTURE.md` §0, §5 | carried; relocates D-59's protection |
| [D-67](#d-67) | Unavailable cells are excluded with coverage reported, not counted wrong | `PREREGISTRATION_LE_STRUCTURE.md` §3, §8 | carried; shortfall against `SCIENCE.md`'s same-rows rule |
| [D-68](#d-68) | L/E structure is a per-hazard flat multinomial softmax (`L1`) — a **null** result | `../ARCHITECTURE.md` §12; `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 | carried; closes queue item 2, D-37/D-49's format half |
| [D-69](#d-69) | Model-input text view is selected at component construction; profile field is PR 7's | `../ARCHITECTURE.md` §5 | carried; backs D-55's "configuration change" rationale |
| [D-70](#d-70) | Stage 7 ships three of four disclaimer patterns; `safety_warning` excluded | `../ARCHITECTURE.md` §7.2 | carried; identified scoring change, narrows D-19's successor rule's trigger |
| [D-71](#d-71) | PR 5 is sequenced **before** PR 6: PR 7 → PR 5 → PR 6 | `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5/PR 6; `STATUS.md` queue item 4 | carried; resolves a D-49 dependency inversion |
| [D-72](#d-72) | 1.1's L/E models are fitted on pipeline **working text**; D-68's selection (raw text) is not re-run | `PREREGISTRATION_LE_STRUCTURE.md` §1, §7, §8 | carried; closes a `SCIENCE.md` training shortfall, adds a recorded assumption |
| [D-73](#d-73) | The shipped artifact is fitted on the **fit split only**; the dev slice stays held out | `PREREGISTRATION_LE_STRUCTURE.md` §1, §5 | carried; makes PR 5's reported numbers describe the shipped model |
| [D-74](#d-74) | The run profile carries `text_view` as a **construction parameter**, not a selection field | `../ARCHITECTURE.md` §5 | carried; closes D-69's deferred half, conditional on an end-to-end test |

### Absorption gaps

**All three found so far are closed.** Two by the 2026-08-03 audit, one by a
spot check on 2026-08-04.

- **D-47's narrowing 2** (found and closed 2026-08-04) — the limitations
  document's Release 1.1 inventory. D-50 and D-51 each added a component to
  it and each named the obligation in its own `Touches` line, but neither
  updated `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6's exit criteria, which is the
  specification a PR 6 author actually reads. The list said three; it is
  five. Closed by correcting the specification and adding a dated note to
  D-47. **The general lesson, worth more than the instance:** naming an
  obligation in a new entry's `Touches` is not absorption. The document that
  someone will read when the time comes has to change, and for an
  enumeration, stating the *rule* that generates the list ("every component
  §7 marks `partial` or `placeholder`") outlives stating its members.
- **D-29** — closed by superseding it. The train-time behavior on a blank
  ordinal label existed only in `model.py` and in an entry that ratified
  observed behavior without writing it anywhere normative. D-46 replaces the
  decision and `PLAN.md` §3 step 1 now carries it. D-46 requires a code change;
  it is queued in `STATUS.md`, so `PLAN.md` currently specifies behavior
  `model.py` does not yet implement.
- **D-30** — closed by absorption. `PLAN.md` §2.1 previously stated the literal
  encoding was "not pinned by any locked decision," which had been false since
  D-30 locked it on 2026-07-25. That sentence now carries the pin.

<a id="d-1"></a>
## D-1: Holdout-seed rows are excluded from the training fit
Date: 2026-07-23
Status: locked
Decision: When `hrc-train --holdout-seed-fraction` is > 0, rows whose
`seed_prompt_id` falls in the reserved holdout set are excluded entirely from
§3 step 4's fit (heads, centering means, and threshold grid search). They
exist solely so `hrc-evaluate` can measure generalization to unseen prompt
families; they are never trained on for the deployed artifact.
Rationale: §3 step 4 said heads/thresholds are fit on the "full training set"
without saying whether reserved seeds are included. If they were,
`hrc-evaluate`'s headline generalization numbers would be computed on rows
the artifact trained on — silent leakage on exactly the number a reader would
quote. User confirmed the intended behavior is exclusion (critique C-1,
2026-07-23). Alternative rejected: fitting on all rows and treating
`--holdout-seed-fraction` as purely a reporting split — this would make the
flag's "held out" framing misleading and reintroduce the leakage the flag
exists to prevent.
Touches: `PLAN.md` §3 step 4 and the `--holdout-seed-fraction` paragraph;
`src/hazard_classifier/model.py` `fit` (must accept/apply a holdout row mask);
`hrc-train` CLI; `manifest.json` (already records split ids per §3 step 5);
D-7 (standardization statistics must also be computed net of this exclusion —
see D-7's amendment); D-13 (this decision's stated purpose — letting
`hrc-evaluate` measure generalization — is what D-13 actually wires up
end-to-end on the evaluate side).

**Amendment (2026-07-23, critique DI-Q3): `--holdout-seed-fraction` defaults
to `0` — this is intentional, not an accidental gap.** This decision and
`PLAN.md`'s CLI line both describe the flag conditionally ("when
`--holdout-seed-fraction` is > 0") without ever stating what it defaults to
when the user passes nothing. `PLAN.md`'s main `hrc-train` CLI line omits it
entirely and introduces it in a following paragraph as "Optionally," which
implies off-by-default without pinning a value — leaving open whether that
was deliberate or an oversight, and leaving D-12's claim that grouped CV's
generalization concept is "preserved instead via D-1's split" resting on a
split that, by default, never actually runs.

**Corrected decision: `--holdout-seed-fraction` defaults to `0`.** Ordinary
`hrc-train` runs train on the full labeled CSV with no rows reserved unless
the user explicitly opts in, exactly as today's (unstated) behavior already
works — this locks the default rather than changing it. A direct
consequence, stated so it isn't rediscovered by surprise later: an artifact
trained with the default has an empty `holdout_seed_prompt_ids` (§3 step 5),
so D-13's `hrc-evaluate` partitioning puts every eval row in
`in_sample_unrecorded` and emits its "no recorded held-out split" warning —
this is the expected, common case for a default-trained artifact, not a
misconfiguration.

User confirmed (response to critique DI-Q3, `critiques/2026-07-23-decision-introspection.md`):
"Make the default zero." Checked against the full ledger: D-12 is not
contradicted — the held-out-generalization *capability* it names still
exists via this flag — but D-12's framing implicitly assumes the split gets
invoked, which requires the user (or, for §8.2's parity harness
specifically, the harness itself — see the harness's own amendment below) to
set the flag explicitly; it does not happen by default. D-13 is unaffected —
its empty-`holdout_seed_prompt_ids` warning path already anticipated exactly
this default case.
Touches: `PLAN.md` §3's `hrc-train` CLI description (state the `0` default
explicitly rather than leaving it implicit); §8.2 (parity harness's own
amendment, below, depends on this default being the *ordinary* case, not the
one it should itself use).

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-4):** built
`src/hazard_classifier/model.py`'s `choose_holdout_seed_prompts` (a
simplified port of the toy's function of the same name — seed-prompt-level
fraction only, without the toy's response-count target tied to its dropped
grouped-CV apparatus, D-12) and wired its output into `fit`'s row-mask
construction. Confirmed by a forcing-function test that the default `0`
fraction produces an empty `holdout_seed_prompt_ids` list, and — more
importantly — that corrupting held-out rows' labels *and* features before
refitting produces a bit-identical fit, proving exclusion rather than merely
recording membership.

<a id="d-2"></a>
## D-2: Preserve the toy's in-sample threshold/centering bias; document the risk
Date: 2026-07-23
Status: locked
Decision: Thresholds and centering means are fit on in-sample probabilities of
the same rows used for the head fit — including per-hazard threshold tuning
on as few as 5 own-hazard rows (critique C-2/C-3) — exactly reproducing the
toy's behavior rather than correcting the leakage (e.g. via out-of-fold
threshold search). The resulting known bias must be documented as a stated
liability/risk, not silently shipped.
Rationale: User chose to preserve the toy's science exactly and keep §8.2
parity intact rather than let corrected thresholds move the reported numbers,
given confidence in whether a correction actually improves held-out
performance was below the 90% bar (critique Open Question 2). Explicitly
accepted: this bakes a known-biased decision boundary into the frozen
artifact. **Note (2026-07-23): the "keep §8.2 parity intact" clause above
predates D-10; see the Amendment immediately below for how D-10 narrows it —
§8.2's threshold-dependent reference numbers are no longer a bit-for-bit
target for that one interaction, though AUC remains one (per DR-4, no fix
needed — confirmed by user, AUC is rank-based and provably gate-invariant).**
Touches: `PLAN.md` §3 step 4, §8.2 parity test; `model.py` threshold search;
README/docs must carry an explicit risk-disclosure note about the in-sample
threshold bias.
Note (2026-07-23, critique DR-3): the `n_own >= 5` per-hazard cliff described
below is evaluated on **post-D-4-exclusion** row counts. D-4's empty/echo-only
exclusion can itself tip a hazard's own-hazard row count across the n=5
boundary (or down to zero), independent of how many rows exist for that hazard
in the raw training CSV.
Amendment (2026-07-23, authorized by user): D-10 gates the ordinal threshold
grid search on monotonicity, which will very likely select different
`(nonzero_threshold, high_threshold)` pairs than the toy's original ungated
search for at least some hazards. **This decision's "reproduce the toy's
behavior exactly" scope no longer covers the specific threshold *values*
chosen by the grid search, nor §8.2's headline reference numbers, which are
downstream of those values.** The in-sample bias itself — thresholds and
centering fit on in-sample probabilities of the same rows used for the head
fit, including the n≥5 per-hazard cliff — remains preserved unchanged; only
the grid search's *combination-rule objective* changed (from ungated to
monotonicity-gated), not its in-sample-fitting methodology. User explicitly
authorized this breakage rather than requiring D-10 to leave the search
untouched. See D-10 for the full mechanism and rationale.

**Amendment (2026-07-23, critique DI-Q3): §8.2's parity harness must train
its own fixture artifact with a non-zero `--holdout-seed-fraction`.** §8.2's
reference figures ("Legitimization **heldout** exact ≈ 0.646...") are
explicitly the toy's held-out numbers, not in-sample ones — but D-1's
amendment (this pass) pins `--holdout-seed-fraction`'s default to `0`, and
nothing about the parity harness's own artifact-training step was ever
distinguished from ordinary `hrc-train` use. Read literally, the harness
could train its fixture artifact with the default (no holdout reserved),
compute D-13's metrics on the resulting all-`in_sample_unrecorded`
population, and compare *in-sample* numbers against the toy's *held-out*
reference figures — comparing two different things under one "parity"
label. Corrected: the parity harness's own fixture-training step must pass a
non-zero `--holdout-seed-fraction` and compare §8.2's reference numbers
against the resulting `held_out` population's metrics specifically, never
`in_sample_unrecorded`'s. The `0` default from D-1's amendment is for
ordinary `hrc-train` use; it is not a statement about what the parity
harness itself should pass.
Touches: `PLAN.md` §8.2 (parity-harness bullet states this precondition
explicitly).

Note (2026-07-25, integration audit finding B / Q-1): the amendment/note above
keeps "AUC remains [a bit-for-bit target]" per DR-4's gate-invariance argument.
That gate-invariance holds for **either** of the toy's two AUCs
(`binary_present_auc`, `high_auc` — both rank-based on pre-threshold adjusted
scores), so it is sound. But whether production's reported `high_auc` (D-16) can
be matched *bit-for-bit against §8.2's reference numbers* depends on those
numbers actually being `high_auc`, which is **unverified** — the committed toy
cannot disambiguate the two (see D-16's 2026-07-25 provenance note). So "AUC
remains a bit-for-bit target" is **conditional on** that provenance being
confirmed by the Phase-4 parity harness (§8.2), which computes both AUCs and
matches the reference against both. If the reference proves to be
`binary_present_auc`, the AUC parity target and D-16's `high_auc`-only reporting
must be reconciled then (widen D-16, replace the reference values, or drop the
AUC parity target). No behavior changes this pass. See D-16's 2026-07-25 note.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-4):** the
`n_own >= 5` own-hazard-vs-pooled cliff is built in `model.py`'s
`_own_hazard_or_pooled_mask`, ported from the toy's
`optimize_thresholds_for_hazard`. Not yet separately forcing-function-tested
at this cliff boundary specifically (the IS-4 test suite exercises `fit`'s
other properties); a dedicated boundary test (4 vs. 5 own-hazard rows) is a
candidate for a future pass, not blocking.

**IS-9 blocker discovered (2026-07-25, `VERIFICATION.md` IS-9):** attempting
the parity harness surfaced that this decision's own precondition — a real
labeled fixture to train the harness's own artifact on — cannot currently be
satisfied. The toy's raw labeled CSVs (`neyman_review_queue.csv`,
`batch_*_key.csv`) are explicitly excluded from the `security-evaluator`
repo ("Do not commit source CSV data... provide at run time," its own
`inputs/README.md`) and are not present anywhere in this environment; nor is
the toy's own BGE hazard-weighted output directory
(`results/mechanism_sentence_bge_base_hazard_weighted_heads_v1/`) that would
hold cached embeddings. The reference numbers themselves are real (found in
the toy's `README.md`, matching `PLAN.md` §8.2's quoted figures), but there
is no input data to reproduce a run from. User directed: build `embed.py`
now (proving the *mechanism* works against a real, downloaded BGE model)
and explicitly defer the actual parity confirmation this decision requires
until real labeled data becomes available. This decision's core claim
("preserve the toy's in-sample bias") remains unverified against real
numbers, not because of any code gap but a data gap.

<a id="d-3"></a>
## D-3: Fail closed on unknown/unfit `(component, hazard)` cells at predict time
Date: 2026-07-23
Status: locked
Decision: `hrc-predict` raises an error for any `(component, hazard)`
combination that was not actually fit (either genuinely unseen, or a
zero-training-row cell per D-5) rather than falling back to a global/pooled
head. §11.1's "fall back to a global head" language is replaced with fail-closed
behavior.
Rationale: User confirmed fail-closed (critique C-4). No pooled/global head is
fit or serialized under the current §3/§4 spec, so a fallback would require
building and freezing capability the plan doesn't otherwise need.
Touches: `PLAN.md` §11.1; predict-path code and CLI error handling; hard
dependency on D-5's `status` field in `thresholds.json`/§4 (this check cannot
distinguish "fit" from "skipped" without it); D-11 (precedence relative to
D-4).
Note (2026-07-23, D-11 amendment): this decision's single fail-closed
guarantee ("either genuinely unseen, or a zero-training-row cell per D-5")
splits into two sub-checks with *different* precedence relative to D-4's
empty-response short-circuit — see D-11's amendment for the full mechanism.
Genuinely-unseen-hazard is checked before D-4 (unconditional hard fail,
regardless of response content). Skipped-cell is checked after D-4 (an
empty/echo-only response scores 0 via D-4 without ever reaching this check).
In both sub-cases, once the check *is* reached and fails, the row is not
scored — no fallback exists.
Note (2026-07-23, D-5 amendment, critique DI-C1): "a zero-training-row cell
per D-5" above is stale phrasing — D-5's trigger for `status: "skipped"` is
no longer a per-hazard row count; see D-5's amendment for the corrected
condition (an entire component's nonzero-or-high label constant across all
training rows, not a per-hazard event). The fail-closed *behavior* this
decision locks (refuse to serve a cell marked skipped) is unchanged; only the
condition that produces that marking moves.
Note (2026-07-23, D-18): this decision's fail-closed check applies only to a
hazard's **required** components (D-18: Enablement always, Legitimization
except for enablement-only hazards). A not-required `(legitimization, prv)`/
`(legitimization, sxc_prn)` cell is never enumerated, so this check is never
reached for it at all — it is not a third way to trigger "genuinely unseen"
or "skipped," it is simply out of scope. The genuinely-unseen-hazard check
itself is unaffected: a hazard counts as known if any required-component cell
was enumerated for it, and Enablement's universal requirement guarantees that
for every training hazard.
Note (2026-07-23, D-22): this decision's mechanism — "`hrc-predict` **raises
an error**" — describes the *consequence* of a fail-closed condition, which
D-22 has since changed for the **batch CLI**: a hard-fail row is routed to a
separate **failures output** and the run continues, rather than aborting.
This decision's actual guarantee — **never fall back to a global/pooled head**
— is unchanged (a failures-output row is still not served), and D-20 widens
the skipped-cell half of the trigger to include an absent/invalid required
cell. The `HazardResponseClassifier.score(rows)` single-row API's error
contract (raise vs. per-row error entry) is still open (`PLAN.md` §11 item 5).

<a id="d-4"></a>
## D-4: Empty and echo-only responses are excluded from the training fit
Date: 2026-07-23
Status: locked
Decision: Responses that produce zero effective sentences for a given
component — an empty response, or (for Enablement) a response that is
entirely prompt-repetition with no authored continuation — are excluded from
that component's training fit, rather than substituted with a zero feature
vector.  At prediction time, empty and prompt-repetition-only responses should be treated as 0 in both enablement and legitimization components.
Rationale: User confirmed exclusion (critique C-5). A standardized zero vector
is a coordinated large-magnitude outlier, not a neutral point, and would
distort both the head fit and the standardization statistics; these rows are
common in production (pure refusals, echo-only replies), not a rare corner
case.
Touches: `PLAN.md` §3 `build_response_matrix` step; feature-building code;
predict path / §6 / `cli/predict.py` (this decision's predict-time mirror);
D-11 (precedence, amended: this check runs *after* D-3's genuinely-unseen-
hazard check but *before* D-3's skipped-cell check — an unseen hazard still
fails closed even for an empty response, but a skipped-but-known cell does
not, since D-4 never inspects cell status).
Note (2026-07-23, D-16 amendment): "treated as 0" above is the discrete
component outcome. D-16's amendment pins the continuous AUC-input value for
these same rows to `0.0` as well (the toy's own business-rule sentinel for
the one sub-case it covers, extended to the others D-4 already treats
identically) — a clarification of what "0" means for metrics purposes, not
a change to this decision.

**Amendment (2026-07-23, critique DI/Deliverable-3 P-C1, correcting the
"both components" scope of the predict-time rule above):** This decision's
predict-time sentence — "empty and prompt-repetition-only responses should be
treated as 0 in **both** enablement and legitimization components" — was
factually wrong for the prompt-repetition-only + Legitimization combination,
and directly contradicted `PLAN.md` §6 step 2 (which scoped the
repetition-only case to Enablement only). Checked against the toy rather than
either prose: `effective_indices` (`scoring_common.py` L307) drops a
prompt-repetition sentence **only** when `judgment == "enabling"`. For
Legitimization every sentence, echoed or not, is kept and pooled — so a
prompt-repetition-only response is **not empty** for Legitimization, is not
dropped from Legitimization's fit by this decision's own fit-time exclusion,
and trains a real (possibly nonzero) Legitimization label. Scoring it `0` at
predict time for Legitimization would create exactly the train/serve skew
this decision's rationale exists to prevent.

**Corrected rule, split by response condition and component:**
- **Genuinely empty response** (zero sentences of any kind for a component):
  scored `0` directly for **both** Enablement and Legitimization — the head
  is never invoked. This is the case the fit-time exclusion drops for both
  components (Legitimization's matrix has no row for a zero-sentence
  response).
- **Prompt-repetition-only, non-empty response** (echoes the prompt with no
  authored continuation): scored `0` directly for **Enablement only** (its
  echoed sentences are dropped before pooling, leaving zero effective
  Enablement sentences); **Legitimization is scored normally through the
  frozen head** (its sentences are kept and pooled, so it is a real,
  non-empty Legitimization feature vector exactly as at fit time).

User confirmed (response to critique Deliverable-3 P-C1): "Choose §6's
reading." Checked against the full ledger: D-16's amendment already
*silently* adopted this reading — it describes the Legitimization D-4 case as
"any empty response" and never says prompt-repetition-only, so this amendment
makes D-16's text and D-4's text consistent instead of contradictory, rather
than introducing a new divergence. D-11's precedence split is unaffected (it
turns on cell `status` and response emptiness, both of which are now
evaluated per-component with the correct per-component notion of "empty").
D-7's fit-time row set for Legitimization is unaffected: it already excludes
only genuinely-empty (D-4) and enablement-only-hazard (D-18) rows, never
repetition-only-but-non-empty rows. No conflict found.
Touches: `PLAN.md` §3 step 4 (D-4 paragraph's "both Enablement and
Legitimization" corrected to the per-component split above), §6 step 2
(already correct — now cross-references this amendment); `model.py` predict
path and `cli/predict.py`.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-4, fit-time
half only):** `model.py`'s `fit` takes an explicit per-component
`component_effective` boolean mask (not an implicit "all-NaN feature row"
convention, which would risk silently misreading a real embedding bug as an
intentional D-4 exclusion) and folds it into the fit-row mask alongside D-1's
holdout exclusion and D-18's required-component filtering. **Predict-time
scoring (0 for empty/echo without consulting cell status) is still not
built** — that is IS-7's job, over the predict/evaluate pipeline.

<a id="d-5"></a>
## D-5: Zero-row cells keep the constant-probability substitution but are marked skipped
Date: 2026-07-23
Status: **superseded-by [D-45](#d-45)** (2026-08-03). The constant-probability
substitute is no longer created; an unfittable operation is marked unavailable.
D-45's code landed 2026-08-03, so nothing below describes current behavior —
read this entry for the reasoning and the rejected alternatives only.
Decision: `(component, hazard)` cells with zero training rows keep the toy's
existing behavior — a constant-probability substitution that yields a
degenerate 0.5-centered threshold search — but each such cell is explicitly
marked as "skipped" (not fit) in the artifact. `hrc-predict` must consult that
marker and refuse to score against a skipped cell rather than silently using
it.
Rationale: User confirmed the substitution is acceptable but skipped cells
must never be used at predict time (critique C-6). §4's artifact spec
currently has no way to distinguish "skipped" from "fit," which this decision
requires it to gain.
Touches: `PLAN.md` §3 step 4 cell enumeration; §4 artifact schema (needs a
per-cell fit/skipped flag); predict-path code.
Note (2026-07-23, critique DR-3): "zero training rows" is determined **after**
D-1's holdout exclusion and D-4's empty/echo-only exclusion — a cell can have
rows in the raw training CSV yet still be zero-row for a component once both
exclusions are applied.
Note (2026-07-23, critique DR-6): D-10's monotonicity gate applies to the
grid search run on skipped cells too — the search still executes over the
constant-probability substitution to populate `thresholds.json`'s stored
values for that cell, even though D-3/D-11 guarantee those values are never
served. This is wasted, not incorrect, work; the "degenerate, 0.5-centered
threshold search" description above is the pre-D-10 mechanism and no longer
describes the objective the search actually optimizes for that cell.

**Amendment (2026-07-23, critique DI-C1, superseding the "zero training rows"
trigger above and the DR-3 note on it):** The trigger for "skipped" as
originally stated — "cells with zero training rows" — describes a condition
the toy does not have, and does not match what actually fires its
constant-probability substitution. Checked directly against
`run_bge_hazard_weighted_heads.py`'s `fit_binary_head_weighted` (L81-107): the
substitution fires on `len(set(train_y)) < 2` (L88), where `train_y` is the
binary label (`y > 0` for the nonzero head, `y == 2` for the high head)
**over the full set of training rows for the component**, not over any one
hazard's own rows — `sample_weight` (the per-target-hazard 1.0/0.25 weighting,
`run_bge_hazard_weighted_heads.py` L228-231) only reweights those same rows,
it never filters which rows are present or which label values can occur. So
this condition cannot vary by hazard within a component: it is a single
degeneracy check per `(component, head)` — is the *entire* component's
nonzero (or high) label constant across every training row, once D-1's
holdout exclusion and D-4's empty/echo-only exclusion have been applied (the
same row set D-7's amendment already defines for `mean`/`scale`)? — and if it
fires, it fires identically for every hazard cell in that component.

A hazard with zero (or very few) *own* rows is not this condition at all: it
still gets a normally-fit head from the full weighted training set, and per
D-2's already-locked `n_own >= 5` cliff, falls back to *pooled* threshold
search rather than any per-hazard skip. There is no toy mechanism, and now no
production one, that skips an individual hazard cell for having thin
own-hazard data — thin data is handled entirely by D-2's pooled-fallback
path, not by D-5.

**Corrected decision:** `status: "skipped"` is set on **every** `(component,
hazard)` cell of a component **simultaneously** when either of that
component's two binary label vectors (nonzero or high), computed over the
rows surviving D-1's and D-4's exclusions across *all* hazards, is
single-class (`len(set(train_y)) < 2`). It is never set for an individual
hazard in isolation. The stored substitution constant for a skipped component
is the weighted mean of `train_y` (`np.average(train_y,
weights=sample_weight)`, matching the toy's own constant), varying only by
`sample_weight` — i.e. by hazard — even though every hazard's `status` is the
same `"skipped"`.

Practical consequence, stated so it isn't mistaken for an oversight later:
under this corrected trigger, "skipped" requires an entire component's label
distribution to be constant across the *whole* training corpus (e.g. every
response in the training set scored Enablement 0) — a data-quality-level
degeneracy that ordinary training data is not expected to hit, not the common
per-hazard thin-data event the plan's prose previously illustrated (a hazard
whose own rows all happened to be empty/echo-only). That illustration is
corrected in `PLAN.md` (see Touches).

Rationale: user confirmed, in response to this pass's Open Question ("what
does `\"skipped\"` actually mean — zero own-hazard rows, or the toy's actual
component-wide single-class trigger?"): "Do what the toy does" (critique
`critiques/2026-07-23-decision-introspection.md`, DI-C1). Checked against the
full ledger: D-3 and D-11's decision text both restate the pre-amendment
"zero-training-row cell per D-5" phrasing — corrected via notes on those
entries below, not by editing their own decision text, since the fail-closed
*behavior* on a skipped cell (refuse to serve it) is unchanged; only the
*trigger condition* moves. D-14 and D-17 reference `"skipped"`/
`excluded_skipped_cell_count` generically (no row-count phrasing to correct)
and remain accurate — the meaning of what makes an eval row's cell "skipped"
still resolves as before, just via the corrected condition — but readers
should now expect `excluded_skipped_cell_count` to jump by an entire
component's non-empty rows at once on the rare occasion it fires at all,
rather than by a handful of thin-hazard rows. No conflict found with any
locked entry.
Touches: `PLAN.md` §3 step 4 (the D-5 paragraph's illustrative example was
factually wrong under this trigger — replaced), §4 (the `status` field
description), §6 (`hrc-predict` Step 3's parenthetical), §11 item 1 (same
phrase); `DECISIONS.md` D-3 and D-11 (added corrective notes, below).
Note (2026-07-23, D-18): D-5's degeneracy check and `"skipped"` status only
ever apply to cells that exist at all. D-18 defines a prior, separate reason
a cell can be absent — legitimization is not a required component for
enablement-only hazards — which is not a form of "skipped" and is checked
before D-5's condition would ever be evaluated (there is nothing to check a
label vector of if the cell was never built).
Note (2026-07-23, critique DI-N3, documented not fixed): `status: "fit"` is
binary, but a fit cell's *thresholds* can come from either of two regimes
per D-2's already-locked `n_own >= 5` cliff — hazard-specific (own-hazard
rows drove the grid search) or pooled-fallback (own-hazard rows were too few
or single-class, so all hazards' rows were pooled instead). `status` does
not distinguish these; D-3/D-11 fail-closed logic treats both as equally
serviceable, which is correct (a pooled-fallback fit is still a real,
usable fit, not a degenerate one) — but a consumer inspecting
`thresholds.json` cannot tell, from `status` alone, which regime produced a
given hazard's thresholds. Accepted as-is: this is a real limit of the
current two-value schema, not an error, and no locked decision requires
resolving it. A future fix-proposal could add a third schema value (e.g.
`status: "fit_pooled"` vs. `"fit_own"`) if a concrete need for that
distinction arises; none has so far.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-4):** built
in `model.py`'s `fit`. Confirmed the corrected trigger required **no
special-case aggregation code** at all: every hazard's cell fit within a
component shares the identical row-level label array (`sample_weight` is the
only thing that varies per target hazard), so `heads.py`'s own per-call
degeneracy check independently reaches the same "skipped" conclusion for
every hazard automatically. Forcing-function test: setting `enablement_value`
to a single constant across both hazards in the fixture marks **every**
enablement cell `status="skipped"` and adds `"enablement"` to
`skipped_components`, while `legitimization` (still varied) is unaffected.

<a id="d-6"></a>
## D-6: Pin training/embedding to CPU; drop device auto-select
Date: 2026-07-23
Status: locked
Decision: `hrc-train` and embedding generation run on CPU only. The
`--device auto`/`cuda`/`mps` options described in §3 step 3 are removed (CPU
is the only supported device), so §8.1's determinism claim ("same input +
seed ⇒ identical artifact parameters and scores") holds unconditionally
rather than needing to be scoped per-device.
Rationale: User confirmed CPU-only (critique C-7). This closes the same class
of host-dependence the plan already fixes by bundling the wordlist.

**Implementation slice landed (2026-07-25, `embed.py`, user-directed "build
embed.py now, defer real parity check" after IS-9 was found to need real
toy data that doesn't exist in this repo):** `embed.py`'s `_load_model`
always passes `device="cpu"` to `SentenceTransformer` -- unlike the toy's
`best_torch_device` (auto-selects `cuda`/`mps`/`cpu`), no device parameter
is exposed to any caller at all. `torch`/`sentence-transformers` added to
`pyproject.toml`'s main dependencies (§7). Confirmed against a real
`BAAI/bge-base-en-v1.5` download (network access worked in this
environment) that CPU-only inference actually runs end-to-end, not just
that the code compiles.
Touches: `PLAN.md` §3 step 3, §8.1 determinism test; CLI device option.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-2):** the
wordlist half of this rationale ("the plan already fixes by bundling the
wordlist") is now actually built, not just prose in `PLAN.md` §7. Asked the
user which source to bundle (a license/size/provenance tradeoff, not mine to
pick per META_PLAN §3); user chose a filtered snapshot of this machine's
`/usr/share/dict/words` (macOS's `web2`, Webster's Second International base;
234,428 entries after the toy's own `[a-z]{2,}` filter) over a small
MIT-licensed alternative. Shipped as `src/hazard_classifier/preprocess/data/
wordlist.txt`, loaded via `importlib.resources` (no host path, no
`/usr/share/dict` reference anywhere in `preprocess/decode.py`), confirmed
present in an actual built wheel (not just the editable install). **Not
independently re-verified:** the exact redistribution terms of this specific
file, beyond the general "old dictionary base, commonly public domain"
assumption the user accepted — recorded as an open caveat in
`preprocess/data/WORDLIST_PROVENANCE.md`, revisit if that assumption turns
out wrong for this file specifically.

<a id="d-7"></a>
## D-7: Standardization statistics are unweighted over all training rows per component
Date: 2026-07-23
Status: locked
Decision: `mean`/`scale` (standardization stats stored per `BinaryHead`) are
computed unweighted over **all** training rows for the component — not
per-hazard, not own-hazard-only — identical across every hazard within a
component. `center_mean` remains the weighted mean, as distinct from
`mean`/`scale`. This matches the toy's current behavior exactly and is now
pinned explicitly rather than left for an implementer to guess.
Rationale: User confirmed: pin current reality into the plan (critique C-8).
Left unstated, an implementer could plausibly compute these weighted or
own-hazard-only, silently changing every score.
Touches: `PLAN.md` §2.3 `BinaryHead` spec, §3 step 4; `model.py`.
Amendment (2026-07-23, critique DR-1/DR-3): this decision's "all training
rows" was ambiguous about whether rows excluded by D-1 (holdout-seed rows,
when `--holdout-seed-fraction` is set) are included. Read literally it says
yes, which would let holdout rows influence `mean`/`scale` — and therefore
every deployed score — directly contradicting D-1's "excluded entirely from
the fit" mandate and the anti-leakage rationale behind it. **`mean`/`scale`
are computed over training rows net of BOTH D-1's holdout-seed exclusion AND
D-4's empty/echo-only exclusion** — i.e., over exactly the rows that survive
both exclusions applied to the raw training CSV, not "all" rows in an
unqualified sense. User confirmed (2026-07-23): "the intended reading is
'holdout rows must not touch `mean`/`scale` either.'" `center_mean` is
already understood to be the weighted mean over this same (D-1-and-D-4
excluded) row set, so this amendment brings `mean`/`scale`'s row set into
alignment with `center_mean`'s, differing only in weighting, not in which
rows are eligible.

**Amendment (2026-07-23, critique DI-Q2, via `DECISIONS.md` D-18):** the
amendment above named exactly two exclusions (D-1's holdout, D-4's
empty/echo). For **Legitimization** specifically there is a third, prior
restriction — not a new exclusion rule of its own, but a direct consequence
of D-18: enablement-only hazard rows (`prv`, `sxc_prn`) are never part of
Legitimization's "training rows for the component" at all, because
Legitimization is not a **required** component for those hazards (D-18) — no
legitimization ground truth exists for them (§2.1), no legitimization
sentences are ever embedded for them (§1.1 item 2: "Legitimization branch
skips enablement-only hazards"), and no `(legitimization, prv)`/
`(legitimization, sxc_prn)` cell is ever built to fit in the first place
(D-18, §3 step 4). So Legitimization's `mean`/`scale`/`center_mean` are
computed over rows surviving D-1's holdout exclusion and D-4's empty/echo
exclusion, drawn only from hazards for which Legitimization is required
(D-18). Enablement's row set is unaffected — Enablement is required for
every hazard, so this restriction never applies to it.
User confirmed, in response to critique DI-Q2's Open Question ("are
enablement-only rows inside or outside legitimization's `mean`/`scale`/
`center_mean` row set?"): "outside"
(`critiques/2026-07-23-decision-introspection.md`). Checked against the full
ledger: D-15 already states this exclusion for `hrc-evaluate`'s *reporting*
but was silent on whether it also holds at *fit* time — this amendment
confirms it does, closing that gap rather than contradicting D-15. D-1 and
D-4 are unaffected: this is a third, independent restriction on component
membership (which rows Legitimization ever sees at all), not a sequential
filtering step that interacts with holdout or empty/echo exclusion order. No
conflicts found.
Touches: `PLAN.md` §2.3 (`BinaryHead` spec — states Legitimization's row set
explicitly), §3 step 4 (D-7 cross-reference paragraph); `DECISIONS.md` D-15
(cross-reference note added, confirming this is now locked at fit time too).

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-3):** built
`src/hazard_classifier/heads.py`'s `BinaryHead`/`fit_binary_head`, ported from
the toy's `standardize_train_test`/`fit_binary_head_weighted`. Confirmed by a
forcing-function test that `mean`/`scale` come out bit-identical across two
different hazard-weightings of the same row universe while `coef`/
`center_mean` differ (using a deliberately overlapping, non-class-aligned
fixture, after a first attempt with cleanly-separable data produced identical
coefficients too and had to be replaced). `fit_binary_head` takes **no
hazard parameter** — this decision's Legitimization row-set restriction (and
D-18's mechanism producing it) is entirely enforced by the caller filtering
rows before calling in; `heads.py` itself has no way to apply or bypass it.
That caller-side filtering is not yet built (`model.py`'s `fit`, IS-4).

<a id="d-8"></a>
## D-8: `class_weight="balanced"` / sample-weight interaction is documented, not fixed
Date: 2026-07-23
Status: locked
Decision: sklearn's `class_weight="balanced"` factors are computed from `y`
alone, ignoring the hazard `sample_weight` (critique C-9) — so the "balanced"
correction is not actually balanced under the 0.25 other-hazard weighting.
This known statistical wart is preserved as-is (parity with the toy), and
must be documented explicitly in the plan and README rather than corrected.
Rationale: User confirmed: mention the problem in documentation, preserve
parity.
Touches: `PLAN.md` §3 step 4 documentation; README.

<a id="d-9"></a>
## D-9: Ordinal monotonicity between the two heads is enforced
Date: 2026-07-23
Status: locked
Decision: The two independently-fit ordinal heads must not be allowed to
produce a non-monotone prediction (i.e. "predict 2" is constrained to be a
subset of "predict ≥1"). Monotonicity is enforced rather than left as an
unconstrained possibility of the independent threshold search (critique
C-10).
Rationale: User confirmed monotonicity should be enforced.
Touches: `PLAN.md` §3 step 4 / predict-time `ordinal_prediction` logic.
Note: this decision locked the *requirement* only. D-10 now locks the
specific enforcement mechanism.

<a id="d-10"></a>
## D-10: Monotonicity enforcement mechanism — gate the high decision on the
low decision, including inside the threshold search itself
Date: 2026-07-23
Status: locked
Decision: The toy's `ordinal_prediction` (`scoring_common.py:475-484`) sets
`out[high >= high_threshold] = 2` unconditionally, with no gate on whether
`nonzero >= nonzero_threshold` also held — this is the actual source of the
non-monotonicity D-9 requires fixing. The combination rule is changed to:
```
out[nonzero >= nonzero_threshold] = 1
out[(high >= high_threshold) & (nonzero >= nonzero_threshold)] = 2
```
This gate applies in **both** places the combination rule is evaluated:
(a) at predict/serve time in `HazardResponseClassifier.predict`, and (b)
inside `optimize_ordinal_thresholds`'s grid search itself — the `pred_grid`
computation used to score each candidate `(nonzero_threshold,
high_threshold)` pair during training is the *same* gated rule, not the
toy's original ungated one. No new fitted parameters, no artifact schema
change — the gate reuses the two thresholds §3 step 4 already produces.
Rationale: Two mechanism variants were on the table. Variant A (gate only at
serve time, leave the grid search's objective ungated) preserves the toy's
literal threshold *values* but leaves training-time threshold selection
optimizing for a different (ungated) prediction rule than what's actually
served — an inconsistency between what's optimized and what's deployed, with
an unquantified effect on served predictions. Variant B (this decision) keeps
the objective the grid search maximizes and the rule actually served
permanently in agreement, at the cost of almost certainly selecting different
threshold values than the toy's original ungated search for at least some
hazards. User explicitly chose to accept that cost: "go ahead and allow
breakage of D-2's 'reproduce the toy's behavior exactly' decision" (chat,
2026-07-23). See the amendment on D-2 for the precise scope of that
breakage — the in-sample fitting methodology D-2 preserves is unaffected;
only the combination-rule objective changed. Quantifying how much §8.2's
reference numbers actually move is deferred to a later implementation-slice
session (explicitly requested by user, not run as part of this fix-proposal
pass).
Touches: `PLAN.md` §1.1 item 3 (ordinal-thresholds bullet, no longer verbatim
toy behavior), §2.3, §3 step 4 (`optimize_ordinal_thresholds` / grid search),
§6 (`hrc-predict` predict-time combination), §8.2 (parity harness reference
numbers reframed as historical baselines, not exact targets, for this
specific reason); `scoring_common.py`-equivalent combination logic in
`rules.py`/`model.py`.
Note (2026-07-23, D-19): the Rationale's claim that variant B keeps "the
objective the grid search maximizes and the rule actually served permanently
in agreement" is scoped to the *gated-vs-ungated shape* of the combination
rule — it does **not** claim the grid search and predict-time serving consume
the *same probability stage*. They do not, and this is inherited from the toy,
not introduced here: the grid search optimizes over **centered** (pre-business-
rule) train probabilities, while predict-time serving gates the **business-
rule-adjusted** probabilities (D-19). For the majority of rows no business rule
fires, so centered == adjusted and the two agree exactly; for rows where D-19's
disclaimer rule fires (specialized-advice + disclaimer), the served value
differs from what the threshold was selected against. This pre-rule/post-rule
asymmetry is part of the toy behavior D-2 preserves (the toy likewise applies
`apply_component_business_rules` only to scored/test rows, never inside
`optimize_thresholds`), and is left unchanged. See D-19 for the full note.

<a id="d-11"></a>
## D-11: Predict-time precedence — D-3's fail-closed cell check runs before D-4's empty-response short-circuit
Date: 2026-07-23
Status: locked
Decision: At predict time, `hrc-predict` first validates the `(component,
hazard)` cell per D-3 — the hazard must have been seen at train time and the
cell's `thresholds.json` `status` must be `"fit"`, not `"skipped"` or absent
— and fails closed (raises/reports an error) if that check does not pass,
**regardless of whether the response is empty or prompt-repetition-only.**
Only once a cell passes D-3's validation does D-4's empty/echo-only-response
short-circuit (score the component as `0` without invoking the frozen head)
apply. This reverses the order `PLAN.md` §6 previously documented only in
prose (D-4's check before D-3's), which let an empty response carrying an
unknown or unfit hazard code silently score `0` instead of failing closed.
Rationale: D-3's and D-4's decision texts gave contradictory predict-time
instructions for a row that is both empty/echo-only *and* maps to an
unfit/unknown cell — score `0` vs. hard error — with no precedence recorded in
either entry (critique DR-2, 2026-07-23). User confirmed: "in production
prediction, unknown hazards should be a hard fail" — i.e., cell validity is a
harder guarantee than the empty-response convenience scoring, so validity is
checked first. This decision extends that answer uniformly to **skipped**
cells (D-5's zero-training-row cells) as well as genuinely unseen hazards,
since D-3's own decision text already treats both failure modes identically
("either genuinely unseen, or a zero-training-row cell per D-5") and gives no
basis to treat them differently once response emptiness is added to the
picture. **Open Question (resolved by amendment below):** the user's answer
was phrased specifically as "unknown hazards" — flagged for confirmation
whether skipped-but-known cells should be treated the same. They should not;
see the amendment.
Touches: `PLAN.md` §6 (`hrc-predict` check ordering); D-3 and D-4 (Touches
lists cross-reference this ordering); §11.1 (already resolved by D-3; this
decision completes the predict-path error contract); predict-path CLI code.
Amendment (2026-07-23, narrowing to unseen hazards only): User confirmed the
open question above should be resolved the narrow way: "I want an
empty/echo-only response against a *skipped* (not unknown) cell to still
score 0 rather than hard-fail." D-11's precedence therefore **splits by which
of D-3's two fail-closed triggers applies**, rather than uniformly putting
D-3 ahead of D-4:
- **Genuinely unseen hazard** (a hazard code the artifact never enumerated
  any `(component, hazard)` cell for) — checked **before** D-4, unconditional
  hard fail regardless of response content. This is the original "unknown
  hazards should be a hard fail" guarantee, unchanged.
- **Skipped cell** (a known hazard whose specific `(component, hazard)` cell
  has `thresholds.json` `status: "skipped"` per D-5, i.e. zero training rows
  survived D-1/D-4's exclusions) — checked **after** D-4. If the response is
  empty/echo-only for that component, D-4's score-as-0 short-circuit applies
  and the row is *not* failed closed, even though the cell is skipped. If the
  response is non-empty/authored, the skipped-cell fail-closed check still
  applies unchanged.
This does not weaken D-5's "skipped cells must never be used at predict
time": D-4's score-as-0 path never inspects a cell's status or invokes the
frozen head at all (skipped or otherwise) — it is a response-content
short-circuit prior to any cell lookup — so a skipped cell's degenerate
parameters remain unused whether the response is empty (short-circuited by
D-4, cell never consulted) or non-empty (rejected by the skipped-cell check,
cell never used to produce a score). Only the unseen-hazard trigger keeps its
original before-D-4 precedence.
Note (2026-07-23, D-5 amendment, critique DI-C1): the two "zero training
rows" phrasings above (Rationale, and the "Skipped cell" bullet) are stale —
see D-5's amendment for the corrected trigger (an entire component's
nonzero-or-high label constant across all training rows, never a per-hazard
condition). This precedence split itself is unaffected: it still turns on
whether a cell's `status` is `"skipped"`, not on why it is.
Note (2026-07-23, D-18): this entire precedence split (unseen-hazard vs.
skipped-cell vs. D-4) presumes a `(component, hazard)` cell exists to be
checked. Per D-18, `(legitimization, prv)`/`(legitimization, sxc_prn)` cells
never exist, so none of D-11's checks ever run against legitimization for
those two hazards — there is no cell to be "skipped" or "fit," and no
precedence question to resolve.
Note (2026-07-23, D-20, critique Deliverable-3 P-C4): this decision's text
already requires the cell's status be `"fit"`, "not `"skipped"` **or
absent**." D-20 makes the "or absent" half explicit and pins its consequence
(a required cell that is absent or any not-`"fit"` value fails closed exactly
like `"skipped"`), correcting `PLAN.md` §6 step 3's prose and the
`resolve_component_action` implementation, both of which tested only for the
literal `"skipped"` value and so failed **open** on an absent required cell.
Note (2026-07-23, D-22): the "(raises/reports an error)" consequence stated
throughout this decision is superseded for the **batch CLI** by D-22 — a
hard-fail row is written to a separate failures output and the run continues.
The *precedence* this decision locks (unseen-hazard before D-4; skipped/absent
cell after D-4) is unchanged: it determines *whether* a row fails closed, not
*what happens* when it does. Both the successes and failures rows still honor
this ordering.

<a id="d-12"></a>
## D-12: `--cv` / grouped k-fold cross-validation is dropped from `hrc-evaluate`'s scope
Date: 2026-07-23
Status: locked
Decision: `hrc-evaluate` does not provide a `--cv` mode or any grouped
k-fold cross-validation reporting. It only ever scores a single, already-
trained artifact against a labeled CSV (§5's frozen-model default path).
The toy's `StratifiedGroupKFold`-based research reporting (§1.1 item 4) is
not reproduced in production.
Rationale: user confirmed dropping `--cv` from scope (critique
`critiques/2026-07-23-deliverable-2.md`, response to Open Question 4).
Grouped CV requires refitting per fold, which contradicts the fit-once/
frozen-artifact design (§2) this rewrite exists to introduce, and its
composition with the now-fully-specified §3 fit (D-1 holdout exclusion, D-4
empty/echo exclusion, D-5 skipped-cell enumeration, D-7 standardization
row-set rules, D-10's gated grid search) was flagged as unspecified and
costly to reconcile (critique E-6/E-7) — both findings are moot once `--cv`
is dropped rather than fixed. The held-out-generalization *concept* the toy
used grouped CV to approximate is preserved instead via D-1's single
reserved holdout-seed split.
Touches: `PLAN.md` §1.1 item 4 (scope note), §5 (bullet removed, out-of-scope
note added), §9 (added to the explicitly-skipped list), §10 (phased-build
table entry for `hrc-evaluate` no longer mentions `--cv`), §2.1 (added per
critique DI-N2 — the schema table's `seed_prompt_id` row description still
named "grouped CV" as a use case after this decision dropped it); no
CLI/model code exists yet for this to touch.
Note (2026-07-23, D-1 amendment, critique DI-Q3): "preserved instead via
D-1's single reserved holdout-seed split" describes a *capability*, not
something that happens automatically — D-1's amendment pins
`--holdout-seed-fraction`'s default to `0`, so the split this decision
leans on must be explicitly requested (by the user for ordinary training, or
by the §8.2 parity harness for its own fixture, per D-2's matching
amendment) to actually exist. This is not a contradiction of this decision's
claim, just a clarification of what "preserved" requires in practice.

<a id="d-13"></a>
## D-13: `hrc-evaluate` auto-partitions eval rows by the artifact's recorded holdout split, and warns when none exists
Date: 2026-07-23
Status: locked
Decision: `hrc-evaluate`'s default (frozen-artifact) path reads
`holdout_seed_prompt_ids` from the loaded artifact's `manifest.json` (§3
step 5, §4) and partitions eval rows by `seed_prompt_id` membership into two
populations:
- **held-out** — `seed_prompt_id` is in the artifact's recorded holdout
  list. These rows were verifiably excluded from the fit (D-1); metrics on
  this population are the honest generalization numbers D-1 exists to
  produce, and are the headline result.
- **in-sample / unrecorded** — every other row, whether it was actually part
  of the training fit or is simply not a seed the artifact recorded as held
  out. Metrics on this population inherit D-2's in-sample threshold/
  centering bias and must be labeled as such, never presented as
  generalization numbers.

Both populations are reported separately whenever both are non-empty —
never silently pooled into one number. If the artifact's
`holdout_seed_prompt_ids` is empty (trained without
`--holdout-seed-fraction`), all rows fall into "in-sample / unrecorded" and
`hrc-evaluate` emits an explicit warning that this artifact has no recorded
held-out split, so no reported number for this run is a verified
generalization number.

This is a two-way partition, not a three-way one: rows genuinely never seen
during training (a seed the artifact has no record of at all) are bucketed
with in-sample rows rather than getting their own "genuinely novel" category,
since the manifest only records the *reserved holdout* set, not the full set
of trained `seed_prompt_id`s. Distinguishing "in-sample" from "novel but
unrecorded" would require the manifest to also store every trained seed id,
which this decision does not add — a possible future refinement, not a gap
in this decision's own scope (the critique's E-1 finding was specifically
about wiring up D-1's *recorded* holdout split, not about detecting novelty
in general).

Rationale: D-1's holdout-seed exclusion exists "solely so `hrc-evaluate` can
measure generalization to unseen prompt families," but nothing in the plan
previously wired that up end-to-end — running `hrc-evaluate`'s default path
against the training CSV silently reported D-2's optimistic in-sample
numbers with no warning (critique E-1, `critiques/2026-07-23-deliverable-2.md`).
User confirmed the critique's proposed reading — automatic manifest-driven
partitioning — over the alternative (the user manually builds a separate
held-out eval CSV), and explicitly rejected the manual alternative: "Keep
your reading. Do not choose the manual alternative."
Touches: `PLAN.md` §3 step 5 (manifest now explicitly names the
`holdout_seed_prompt_ids` field), §4 (manifest.json field list), §5
(partitioning, per-population reporting, and no-holdout warning behavior);
`cli/evaluate.py`.

**Manifest field landed, partitioning not yet built (2026-07-25,
`VERIFICATION.md` IS-5):** `model.py`'s `save`/`load` round-trip
`holdout_seed_prompt_ids` (`[]` when `--holdout-seed-fraction` defaults to
`0`, D-1) through `manifest.json`, confirmed by a save/load round-trip test.
`hrc-evaluate`'s actual partitioning logic this decision describes is still
not built — that is IS-8's job.

**Partitioning landed (2026-07-25, `VERIFICATION.md` IS-8):**
`model.py`'s `evaluate_rows` calls `metrics.py`'s already-built
`partition_by_holdout` on the rows surviving D-14's exclusion, warns when
`holdout_recorded` is `False` (the default-`0`-fraction case), and —
reading this decision's own words literally ("both populations are reported
separately **whenever both are non-empty**") — omits a population's key
entirely from the report when it has zero rows, rather than emitting an
all-null placeholder object. Forcing-function test: an artifact with no
recorded holdout produces a report with **no** `held_out` key at all and
every surviving row in `in_sample_unrecorded`, plus the warning. CLI
wiring (`hrc-evaluate` itself, the `.json`/`.csv`/`.txt` file writers) is
still not built — deferred until `embed.py` exists to actually run the CLI
against real data, same reasoning as prior slices' `embed.py` deferrals.

<a id="d-14"></a>
## D-14: `hrc-evaluate` excludes hard-fail rows from measurement instead of aborting, and reports the excluded count
Date: 2026-07-23
Status: locked
Decision: `hrc-evaluate` scores each eval row using the **same** predict-path
checks `hrc-predict` uses (D-3/D-4/D-5/D-11, §6): a genuinely unseen hazard,
or a non-empty/authored response landing on a `(component, hazard)` cell
marked `"skipped"` (D-5), still fails closed. But instead of `hrc-predict`'s
abort-the-run behavior, `hrc-evaluate` **excludes that entire row** — both
components and the final label, not just the failing component — from every
reported metric, and continues scoring the remaining rows. D-4's
empty/echo-only-response-scores-0 short-circuit is **not** an exclusion
trigger and is unaffected: those rows score `0` for that component and
remain in the metrics normally, exactly as `hrc-predict` would score them.
`hrc-evaluate` records the total excluded-row count and displays it in the
run's output alongside the metrics; the exact output schema (keys, whether a
per-reason breakdown is included) is deferred to the still-queued E-9
fix-proposal, not decided here.

This exclusion check runs **before** D-13's held-out/in-sample partitioning:
an excluded row never enters either population, so D-13's populations are
computed only over rows that actually got scored.

Rationale: user confirmed exclusion over abort: "hard fail samples should be
excluded from all measurement. Just record and display the number excluded."
(critique E-2, `critiques/2026-07-23-deliverable-2.md`, response to Open
Question 1). This is the identical fail-closed condition D-3/D-4/D-5/D-11
already define for `hrc-predict`, not a new or more permissive check —
`hrc-evaluate` is a batch tool and must not let one bad row abort an entire
metrics run, whereas `hrc-predict` is a single-row production API where
aborting the one bad call is correct. Reusing the identical predicate and
changing only the consequence keeps the two paths from silently drifting
apart on what counts as "unscoreable."
Touches: `PLAN.md` §5 (exclusion behavior + reporting bullet, ordered before
D-13's partitioning bullet); §6 cross-reference (this decision documents
that `hrc-evaluate` reuses, not forks, D-3/D-4/D-5/D-11's checks);
`cli/evaluate.py`.
Note (2026-07-23, D-18): a `(legitimization, prv)`/`(legitimization,
sxc_prn)` row is **not** excluded by this decision's skipped-cell trigger.
D-18 makes legitimization not-required for those hazards, so there is no
cell to be "skipped" and no fail-closed condition to fire — the row is
scored normally via Enablement + the `E`-only v1.4 combination, exactly as
D-15 (below) already requires. This decision's exclusion trigger is
unambiguously about *required* components only.
Note (2026-07-23, D-17's DI-C4 amendment): "the exact output schema ... is
deferred to the still-queued E-9 fix-proposal" above is stale — E-9 was
resolved into D-17, then D-17 was itself amended (critique DI-C4) to report
this decision's excluded-row count and its breakdown at `metrics.json`'s top
level rather than nested per population, since this decision's own "never
enters either population" guarantee made the original nested placement
unimplementable.
Note (2026-07-23, D-22, critique Deliverable-3 P-C5): this decision's
Rationale characterized `hrc-predict` as "a single-row production API where
aborting the one bad call is correct." That characterization is **superseded
by D-22** for the batch path — `hrc-predict` now splits hard-fail rows into a
separate failures output rather than aborting. This decision's own behavior
(exclude hard-fail rows from `hrc-evaluate`'s metrics) is unchanged, and both
paths still share the identical fail-closed predicate (D-3/D-4/D-5/D-11/D-20);
only the consequence differs (evaluate drops from metrics, predict routes to
failures output). D-20 additionally widens the skipped-cell trigger this
decision reuses to include an absent/invalid **required** cell.
Note (2026-07-25, D-26 amendment, integration audit finding C-1): this
decision's hard-fail exclusion runs **before** D-26's evaluate-path
blank-ground-truth-label validation. A row excluded here (an unseen hazard, or a
non-empty response on a `"skipped"`/absent/invalid required cell) has its labels
never examined, so a blank ground-truth label can never turn a D-14-excluded row
into D-26's whole-run abort — the "unknown → excluded, never abort" guarantee
this decision and D-22 share is preserved end to end. See D-26's 2026-07-25
amendment.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-8):**
`model.py`'s `evaluate_rows` catches `score_row`'s `HardFailError` per row,
tallies `excluded_unseen_hazard_count`/`excluded_skipped_cell_count`, and
`continue`s the loop — the excluded row's ground-truth labels are never even
read (confirming the D-26 ordering note above by construction, not just by
inspection). Forcing-function test: a batch with one unseen-hazard row
(**and a blank label on that same row**, proving Finding A) shows the
excluded count incremented and that row absent from every population's
`n_rows`, with no exception raised.

<a id="d-15"></a>
## D-15: Legitimization component metrics exclude enablement-only hazard rows; the final-label denominator is unaffected
Date: 2026-07-23
Status: locked
Decision: `hrc-evaluate`'s legitimization component metrics (exact,
within-one, binary-present accuracy, AUC, QWK, MAE, confusion counts)
exclude rows whose hazard is enablement-only (`prv`, `sxc_prn`) entirely.
These rows carry no legitimization ground truth (§2.1: `legitimization_value`
is blank/NA for enablement-only hazards) and no legitimization prediction is
produced for them (§1.1 item 3: legitimization is N/A for enablement-only
hazards), so they cannot contribute to a legitimization metric. This is a
restatement of the existing enablement-only combination rule already implied
by §1.1/§2.1's design, not a new modeling change. The final safe/unsafe
headline's false-safe/false-unsafe denominator is **not** separately
adjusted for this: enablement-only hazard rows still receive a valid final
label via the existing v1.4 combination (judged by `E` only, §1.1 item 3)
and remain in the final-label headline population exactly as before —
excluding them from the legitimization component metric has no bearing on
whether they're counted in the final-label metric.
Rationale: user confirmed E-3 and E-4 together: "The function that reads
enablement and legitimization scores to generate a safe/unsafe label will
ignore legitimization scores for those two hazards. Any fix can assume that
will always be true. So we don't care and don't need to report
legitimization scores for those two hazards" / "Exclude rows for
enablement-only hazards" (critique E-3/E-4,
`critiques/2026-07-23-deliverable-2.md`). Checked against §1.1 item 3's
existing enablement-only combination rule for consistency — no conflict;
this decision is that existing rule's natural consequence applied to
`hrc-evaluate`'s reporting, not a competing rule.
Touches: `PLAN.md` §5 ("Report, per component and overall" bullet — the
legitimization row population explicitly excludes enablement-only-hazard
rows; the final-label bullet clarifies it is unaffected).
Note (2026-07-23, D-18): this decision described the *reporting* consequence
of enablement-only hazards lacking a legitimization prediction, but the
mechanism producing that lack was never itself locked — D-18 is that
mechanism (legitimization is not a required component for these hazards; its
cell is never enumerated or consulted, at training, predict, or evaluate
time). This decision's own claim that it is "a restatement... not a new
modeling change" is now literally backed by D-18 rather than resting on
§1.1/§2.1's prose alone.
Note (2026-07-23, D-7 amendment, critique DI-Q2): the exclusion this decision
locks for *reporting* also now holds at *fit* time — D-7's amendment
confirms enablement-only hazard rows never enter Legitimization's
`mean`/`scale`/`center_mean` row set either, via the same D-18 mechanism.
Reporting and fitting were never in tension, but this closes the one gap
where fit-time behavior had been left unstated.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-8):**
`model.py`'s `_population_report` applies `metrics.py`'s already-built
`legitimization_eligible_mask` to a population's surviving rows before
computing Legitimization's `component_metrics`, exactly mirroring
Enablement's unfiltered call. Forcing-function test: an all-enablement-only-
hazard batch produces `components.legitimization.n == 0` while
`components.enablement` is fully populated — the exclusion actually removes
rows, not just filters something already empty.

<a id="d-16"></a>
## D-16: `hrc-evaluate` retains head probabilities for scoring; component AUC is the high head's AUC only
Date: 2026-07-23
Status: locked
Decision: `hrc-evaluate`'s per-row scoring pipeline retains each
component's centered nonzero and high head probabilities through to the
metrics-reporting step — they are not discarded once ordinal predictions
(0/1/2) are thresholded. The reported per-component **"AUC"** metric is
computed specifically from the **high head's** centered probability, ranked
(via the same rank-based `safe_auc` the toy uses) against the binary
`y == 2` label — matching the toy's existing `high_auc` computation. The
toy also computes a second AUC (`binary_present_auc`, from the nonzero head
against the `y > 0` label); production reports only the high-head AUC, not
both and not an average.
Rationale: critique E-5 (`critiques/2026-07-23-deliverable-2.md`) found
§5's stated pipeline ("frozen-head predict → component ordinals → v1.4
combination") discards the continuous probability an AUC needs, and that
neither which head nor which binarization was specified — the toy actually
computes *two* AUCs per component, so "AUC" was ambiguous even relative to
the toy's own behavior. User confirmed: "Retain head probabilities. Choose
the high head." Checked against DR-4 (`critiques/2026-07-23-decision-review.md`)'s
finding that AUC is rank-based and gate-invariant under D-10's monotonicity
gate — consistent, since centering is strictly monotone and D-10's gate only
changes the discrete threshold combination, not the head probabilities
themselves, so this decision does not reopen that invariance.
Touches: `PLAN.md` §5 (pipeline description now states probabilities are
retained; the component-metrics bullet pins the AUC definition to the high
head only).

**Amendment (2026-07-23, critique DI-C3 + DI-Q1, combined — one answer
resolves both):** Re-checked the toy's actual `metric_summary`
(`scoring_common.py` L656-707) rather than trusting this decision's own
description of it, and found two errors:

1. **"Centered probability" above is the wrong stage.** `metric_summary`
   computes `high_auc` from `subset_high = adjusted_high[indices]`
   (L671, L705) — the high probability **after**
   `apply_component_business_rules` (L583-621) has run, not the raw centered
   probability this decision's text named. `apply_component_business_rules`
   is what zeroes a component for prompt-repetition-only Enablement
   responses, disclaimer-bearing specialized-advice Legitimization, and
   enablement-only-hazard Legitimization (§1.1 item 3's rules) — these
   business-rule adjustments happen strictly before the AUC is computed in
   the toy, not after.
2. **`binary_present_auc`'s description above is also wrong.** It is
   computed from `subset_score = adjusted_score[indices]` (L670, L704) —
   the rule-adjusted **combined** component score
   (`score_from_centered_probs`, the mean of adjusted nonzero and adjusted
   high) — not from "the nonzero head['s probability]" as stated above.
   Not served in production either way (point unchanged), but the ledger's
   description of the toy was inaccurate and is corrected here.

**Corrected decision:** the reported per-component "AUC" is computed from
the **business-rule-adjusted** high probability (`adjusted_high`), ranked
against `y == 2`, matching `metric_summary`'s actual `high_auc` — not the
pre-rule centered probability. This resolves DI-C3 (D-4's head-less rows had
no defined AUC-input value) using the toy's own established convention
rather than an invented one, with the following precision about which part
of that convention is genuinely toy-derived and which is a necessary
extension of it:
- **Enablement, prompt-repetition-only response:** the toy's own business
  rule 3 (`apply_component_business_rules`, the `prompt_repetition_only_
  sets_enablement_zero` branch) already sets `centered_high = 0.0` for
  exactly this case. Production's D-4-scored rows of this kind get the
  *literal toy value*.
- **Enablement, a truly empty response (no sentences of any kind, not even
  echoed ones):** rule 3's condition requires
  `prompt_repetition_sentence_count > 0`, so it does **not** fire for a
  genuinely blank response — the toy has no business rule that zeroes this
  case at all (it would embed a degenerate near-zero feature vector and
  score it through the head like any other row, which D-4's fit-time
  exclusion is precisely designed to avoid). Production has no toy value to
  borrow here.
- **Legitimization, any empty response (D-4's per-component exclusion also
  covers Legitimization):** neither of the toy's two Legitimization business
  rules (enablement-only N/A; specialized-advice disclaimer) depends on
  emptiness, so the toy has no rule zeroing this case either — this is
  purely a D-4/D-16 production convention, not inherited from anywhere.

For the second and third cases, production assigns the same `0.0` sentinel
the toy's own rule 3 uses for the first case — not because the toy computes
it there, but because it is the toy's own established "score this row as
confidently-not-a-2" value, extended consistently to the other rows D-4
already treats identically (D-4's own text: "empty and prompt-repetition-only
responses should be treated as 0 in both enablement and legitimization
components"). This is a small, deliberate extension beyond literal toy
behavior — flagged here explicitly, not silently — for exactly the rows D-4
already established production diverges on (D-4's rationale: these rows are
"common in production... not a rare corner case").

Checked against the full ledger: this correction, if anything, *strengthens*
D-2's amendment/DR-4's AUC-parity exemption from D-10's loosening — under
the previous (wrong) pre-rule reading, production's AUC would not have
matched the toy's §8.2 reference numbers (≈0.808, ≈0.783) even before
considering D-10's gate, since those numbers are the toy's own post-rule
`high_auc`. Centering and the business rules in `apply_component_business_rules`
both consume no thresholds, so DR-4's gate-invariance argument is unaffected
by this correction. D-4 is unaffected in substance — its predict-time
"treated as 0" language already covered the discrete outcome; this decision
supplies the previously-undefined continuous AUC-input value for the same
rows, it does not change what D-4 locks.
Touches: `PLAN.md` §5 (component-metrics AUC bullet corrected to the
rule-adjusted definition, with the D-4-row convention stated); D-4 (light
cross-reference note — this decision's continuous-value convention applies
to the rows D-4's "treated as 0" already names).
Note (2026-07-23, D-4's P-C1 amendment): the third case above
("Legitimization, any empty response") quotes D-4's original "treated as 0 in
**both** enablement and legitimization components" text as its basis. That
D-4 text was subsequently amended (critique Deliverable-3 P-C1): a
prompt-repetition-only *non-empty* response is **no longer** scored 0 for
Legitimization — it goes through the frozen Legitimization head. This
amendment's case 3 is **unaffected**, because it only ever concerned a
**genuinely empty** Legitimization response (zero sentences of any kind),
which is precisely the one case D-4 still scores 0 for both components. A
repetition-only Legitimization row is now a normally-scored row that
contributes its **real** `adjusted_high` to the AUC, not the `0.0` sentinel —
so the absence of a "Legitimization, repetition-only" case in the list above
is correct by design, not an omission. "Any empty response" here should be
read as "any genuinely empty response."

Note (2026-07-25, integration audit `critiques/2026-07-25-decisions-consistency.md`
finding B / Q-1 — the `high_auc` provenance of §8.2's numbers is **unverified**;
the Phase-4 harness settles it): the amendment above states as fact that §8.2's
reference numbers "(≈0.808, ≈0.783) ... are the toy's own post-rule `high_auc`."
That claim is **unverified**, and its supporting argument is **circular** (it
assumes the numbers are `high_auc` in order to conclude they are). Checked
directly against the committed toy (`/Users/kurt/git/security-evaluator`): the
toy computes **two** AUCs per component — `binary_present_auc` (adjusted combined
score vs `y > 0`, `scoring_common.py` L704) and `high_auc` (adjusted high prob vs
`y == 2`, L705) — and its own printed table carries both (`Binary AUC | High
AUC`, L1617), but the README's single "AUC" column (`README.md`: Legitimization
`0.808393`, Enablement `0.782737`) is a **hand-curated** value whose source run
(`heldout_seed_metrics.csv`) is **not committed**, so which of the two it is
**cannot be determined from the committed repo** (git history shows the column
was always just labeled "AUC"; only the values changed between runs). If
anything, the positional/grouping evidence (`binary_present_auc` is listed first
and grouped with the primary present-vs-absent metrics) leans the *opposite* way
from this decision's `high_auc` assumption — not decisively. Both AUCs are
rank-based on pre-threshold adjusted scores, so both are gate-invariant: D-10 is
**not** the risk here, provenance is.

**Resolution (user-accepted, 2026-07-25):** the empirical answer is deferred to
the **Phase-4 parity harness** (§8.2) — asking the README's author was ruled out,
so the harness computes **both** AUCs from the fixture and matches the reference
against both, settling provenance as a side effect. Two consequences locked here:
(1) this decision's production-reporting rule is **unchanged** — production still
reports only `high_auc` — and is now explicitly **decoupled** from the parity
target: the harness guards the science by reproducing whichever AUC the toy
reported, independent of which one production surfaces; (2) until the harness
confirms it, read "are the toy's own post-rule `high_auc`" above as "**believed**
`high_auc`, unverified." If the reference proves to be `binary_present_auc`, the
AUC parity target and this decision's `high_auc`-only rule must be reconciled
then (widen this decision, replace the reference values with the toy's actual
`high_auc`, or drop the AUC parity target) — flagged so it is not a surprise.
Implementation note for Phase 4: `src/hazard_classifier/metrics.py`
`component_metrics` currently computes only `high_auc` (it takes a single
`high_prob` argument, this decision), so checking both AUCs needs a separate
`binary_present_auc` computation in the harness. Checked against the full ledger:
D-2 (its "AUC remains a bit-for-bit target" is made conditional on this
verification by a matching note, this pass) and §8.2 (harness-computes-both
mechanism added). No conflict found; no behavior changed this pass.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-8):**
`ScoredRow` (IS-7) gained `enablement_adjusted_high`/`legitimization_adjusted_
high` fields specifically so `evaluate_rows` (IS-8) could feed
`component_metrics`'s `high_prob` argument the exact business-rule-adjusted
value this decision requires, without recomputing it from a reloaded
artifact. Confirmed via the IS-7 disclaimer-rule test that a zeroed
Legitimization component's adjusted-high is `0.0`, not just its discrete
prediction.

<a id="d-17"></a>
## D-17: `hrc-evaluate` final-label positive-class convention + output schema (best-effort)
Date: 2026-07-23
Status: locked
Decision:
1. **Positive-class convention (E-10):** final-label precision/recall/F1
   treat `safe` as the positive class: `safe = 1`, `unsafe = 0`. Applies to
   `is_safe_ground_truth` and `predicted_label` alike wherever either is
   binarized for these metrics.
2. **Final-label confusion-count shape (E-10):** reported as a labeled 2×2 —
   `predicted_safe_actual_safe`, `predicted_safe_actual_unsafe`,
   `predicted_unsafe_actual_safe`, `predicted_unsafe_actual_unsafe` — not
   raw `0`/`1` pairs, so a reader never has to re-derive which cell is which
   from the encoding.
3. **`false_safe_rate` / `false_unsafe_rate` definition:**
   `false_safe_rate = predicted_safe_actual_unsafe / N` and
   `false_unsafe_rate = predicted_unsafe_actual_safe / N`, where `N` is the
   same final-label-eligible population used for precision/recall/F1 in
   that split (specialized-advice hazards excluded, per §5) — this is the
   toy's own README instruction ("Use the same denominator when comparing
   false-safe and false-unsafe rates"), not a fresh choice invented here.
4. **Output schema (E-9 — explicit best-effort guess, correctable via an
   ordinary future fix-proposal, not a high-confidence spec):**
   `metrics.json` is a single object keyed by population (`held_out`,
   `in_sample_unrecorded`, per D-13), plus a top-level `holdout_recorded:
   bool`. Each population object has `n_rows`; `excluded_row_count` with an
   `excluded_unseen_hazard_count` / `excluded_skipped_cell_count` breakdown
   (D-14); `components.enablement` / `components.legitimization`, each
   `{exact, within_one, binary_present_accuracy, auc, qwk, mae,
   confusion_counts}` with a 3×3 ordinal `confusion_counts` matrix (`auc`
   per D-16, `legitimization` reflecting D-15's exclusion); and
   `final_label: {precision, recall, f1, false_safe_rate, false_unsafe_rate,
   n, confusion_counts}` per (1)-(3) above. `metrics.csv` is the same data
   flattened long-format (`population, section, metric, value`), not a
   second independently-designed schema. The human-readable summary is
   free-form text derived from the same object.
Rationale: (1)-(3) are direct user answers/toy-README-derived, applied
without invention — not guesses. (4) was an explicit "make a guess, we can
correct later" instruction (critique E-9,
`critiques/2026-07-23-deliverable-2.md`); the guess is the smallest schema
that can represent everything §5/D-13/D-14/D-15/D-16 already require
reporting, and is authorized to be revised later through the normal process
rather than needing to be reopened as a high-confidence precedent.
Touches: `PLAN.md` §5 (final-label bullet gets the positive-class/confusion/
rate-definition pin; Outputs bullet rewritten with the schema); D-14's
excluded-row-count bullet now points here instead of forward to E-9.

**Amendment (2026-07-23, critique DI-C4): excluded-row counts move to the
top level, out of each population object.** Point (4) above nested
`excluded_row_count`/`excluded_unseen_hazard_count`/
`excluded_skipped_cell_count` inside each of `held_out`/
`in_sample_unrecorded` — but D-14 is explicit that "an excluded row never
enters either population" (D-13's partitioning runs only over surviving
rows). A per-population excluded count is therefore unimplementable as
originally written: it would require partitioning rows D-14 says are never
partitioned. Corrected: `excluded_row_count`,
`excluded_unseen_hazard_count`, and `excluded_skipped_cell_count` move to
`metrics.json`'s **top level**, alongside `holdout_recorded` — one set of
three numbers for the whole eval run, not one per population. Each
population object retains `n_rows` (the surviving row count for that
population only), `components.*`, and `final_label`, with the excluded
counts removed from it. `metrics.csv`'s long format gains a sentinel
population value, `"overall"`, to carry these three run-level rows — the
alternative (a population-less row) would break the long format's own
`(population, section, metric, value)` contract, so the top-level scalars
need a population label like everything else in that file, and `"overall"`
is the least surprising choice given `held_out`/`in_sample_unrecorded` are
the only other values that column takes.
User confirmed (response to this pass's Open Question, paired with DI-C1's
list): "(b) moving the excluded counts to the top level alongside
`holdout_recorded`" (`critiques/2026-07-23-decision-introspection.md`).
Checked against the full ledger: D-13 is unaffected — this only changes
*where* the already-computed counts are reported, not when exclusion runs
relative to partitioning (still strictly before, per D-14). D-14 itself is
unaffected — its "never enters either population" guarantee is exactly what
this amendment now honors structurally, whereas the original schema
contradicted it. D-18 is unaffected — a not-required component's absence was
never one of these two exclusion reasons in the first place (see D-14's
D-18 note above), so it does not appear in `excluded_unseen_hazard_count` or
`excluded_skipped_cell_count` either.
Touches: `PLAN.md` §4/§5's Output schema paragraph (excluded-count fields
relocated to top level; `metrics.csv`'s `"overall"` sentinel documented).

**Amendment (2026-07-23, critique DI-Q4): each component section gets its
own row count, not one population-level `n_rows` standing in for all of
them.** Point (4) reports a single `n_rows` per population, but D-15/D-18
already make Legitimization's eligible-row count differ from Enablement's
*within that same population* — enablement-only hazard rows (`prv`,
`sxc_prn`) count toward Enablement (D-18: required for every hazard) but not
toward Legitimization (D-18: not required for those two). `final_label`
already carries its own `n` for the same reason (specialized-advice
exclusion, D-17 point 3) — Legitimization's denominator was the one section
left without a way to state its actual count.

Corrected: `components.enablement` and `components.legitimization` each gain
an `n` field. `components.enablement.n` equals the population's `n_rows`
(Enablement is required for every hazard, so nothing is ever excluded from
it beyond D-14's already-applied hard-fail exclusion, which happens before
population membership is even assigned). `components.legitimization.n` is
`n_rows` minus that population's enablement-only-hazard row count (D-15's
exclusion, mechanized by D-18). The population's own `n_rows` is unchanged
and still means "rows in this population" (D-13); it is not removed or
renamed, just no longer asked to double as Legitimization's denominator too.
Three counts now coexist per population, each answering a different
question: `n_rows` (population size), `components.legitimization.n`
(Legitimization's actual eligible count, per D-15/D-18), `final_label.n`
(the specialized-advice-excluded headline count, per D-17 point 3) —
`components.enablement.n` is redundant with `n_rows` by construction but
included anyway for symmetry, so a reader never has to know *why* one
section's count needs its own field and the other doesn't.

User confirmed, in response to this pass's DI-Q4 finding (not one of the six
questions posed as blocking, but answered anyway): "Record the
legitimization component's actual denominator so that we can figure out
later how to use it" (`critiques/2026-07-23-decision-introspection.md`).
Per that instruction, this amendment only records the count — it defines no
new consumer, derived metric, or downstream calculation using it; every
existing metric (`final_label`'s rate/precision/recall definitions, D-16's
AUC, D-15's exclusion itself) is unaffected and unchanged.
Checked against the full ledger: D-15 (already defines the exclusion this
count reports — no new rule, just newly-visible bookkeeping for an existing
one), D-18 (same — its enumeration mechanism is what makes the counts differ
in the first place). No conflicts found.
Touches: `PLAN.md` §5's Output schema paragraph (`components.enablement.n`
and `components.legitimization.n` added).

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-B):**
`src/hazard_classifier/metrics.py`'s `component_metrics` now returns `"n":
len(y_true)`. This satisfies this amendment's semantics **without the
function itself gaining any hazard-family knowledge** — `component_metrics`
was already generic/reusable-by-design (per the earlier `metrics.py`
implementation-slice log entry), with callers responsible for pre-filtering
the rows they pass in (`legitimization_eligible_mask` is already applied
upstream before scoring Legitimization, as the existing D-15 integration test
confirms). So called with the full population for Enablement, `n` equals
`n_rows`; called with the `legitimization_eligible_mask`-filtered subset for
Legitimization, `n` is `n_rows` minus the enablement-only-hazard row count —
exactly this amendment's rule — as a consequence of the caller's existing
filtering, not new logic in this function. New test,
`test_component_metrics_n_reflects_the_passed_row_count` (mixed-hazard
fixture): confirmed `KeyError: 'n'` **red** before the change, then confirmed
`legitimization.n < enablement.n` by exactly the `prv`/`sxc_prn` row count
after. 43 tests total (was 42), zero regressions. This does not build the
`metrics.json` assembly step itself (still `IS-8`, not built) — only the
underlying per-call `n` value this amendment specifies.

**Note (2026-07-23, D-20): `excluded_skipped_cell_count` also counts D-20's
absent/invalid required-cell exclusions.** When this schema was written, the
only non-`"fit"` fail-closed status was D-5's `"skipped"`, so the breakdown
key was named `excluded_skipped_cell_count`. D-20 later added a second
fail-closed status for a **required** cell — absent entirely, or any
not-`"fit"` value — and specified it is treated "identically to D-5's
skipped-cell trigger." Those absent/invalid-cell exclusions are therefore
counted under this **same** `excluded_skipped_cell_count` key (they are not
`excluded_unseen_hazard_count` — the hazard is known — and the schema defines
no third bucket). The key name is thus slightly under-inclusive: read it as
"rows excluded because a required cell's status was not `"fit"` (skipped,
absent, or otherwise invalid)," per D-20. This is a naming clarification, not
a schema change — no new key is added, and a future fix-proposal could rename
or split the key if a concrete need to distinguish "skipped" from "absent"
arises; none has. `hrc-predict`'s failures output (D-22) carries the same
skipped-or-absent-cell reason for the corresponding rows.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-8):**
`model.py`'s `evaluate_rows` assembles exactly this schema as an in-memory
dict — the two top-level exclusion fields, per-population `n_rows`/
`components.{enablement,legitimization}`/`final_label`, with an empty
population's key **omitted** rather than emitted with null placeholders (a
direct reading of D-13's own "reported... whenever both are non-empty").
Confirmed by a shape test asserting the exact key sets at every level.
**Not yet built:** `metrics.csv`'s long-format flattening and `summary.txt`'s
free-form rendering, and the actual file-writing/CLI layer — deferred until
`embed.py` exists to run any of this against real data, same reasoning as
prior slices' `embed.py` deferrals.
<a id="d-18"></a>
## D-18: Legitimization is not a required component for enablement-only hazards — its cell is never enumerated or consulted
Date: 2026-07-23
Status: locked
Decision: Every hazard has exactly one **required-components** set, derived
from its rule family (`hazard_rule_family`, §1.1 item 3): Enablement is
required for **every** hazard, with no exception. Legitimization is required
for every hazard **except** the enablement-only family (`prv`, `sxc_prn`,
`config.ENABLEMENT_ONLY_HAZARDS`) — for those two hazards, legitimization is
not required at all, not merely uninformative:
- **Training (§3 step 4):** cell enumeration builds a `(legitimization,
  hazard)` cell for every hazard except `prv`/`sxc_prn`. No entry — fit,
  skipped, or otherwise — is created for `(legitimization, prv)` or
  `(legitimization, sxc_prn)` in `thresholds.json` or `heads.npz`. This is
  distinct from D-5's `"skipped"` status: a not-required cell is **absent by
  design**, not present-and-rejected.
- **Predict (§6) and evaluate (§5):** `hrc-predict`/`hrc-evaluate` never
  attempt to look up or score a `(legitimization, hazard)` cell for an
  enablement-only hazard — there is no lookup to fail closed on and no
  `status` to consult. This is a third outcome alongside D-3/D-11's two
  fail-closed triggers (genuinely unseen hazard; skipped cell per D-5's
  amendment), not a variant of either: `legitimization_predicted` is reported
  as `null`/absent for these rows, exactly mirroring the toy's own
  `v14_overall_score`/`discrete_v14_label` (`scoring_common.py` L624-646),
  which accept `l_score`/`l_pred` as `Optional`, default them to `0`/`0.0`,
  and for `rule_family == "enablement_only"` never read that value at all
  (`return e, rule_family`). D-14's hard-fail exclusion is **not** triggered
  by a not-required component being absent — these rows are not excluded
  from `hrc-evaluate`'s measurement, they simply never had a legitimization
  score to report.
- **Genuinely-unseen-hazard check (D-3/D-11):** unaffected — a hazard is
  "known" if *any* required-component cell was enumerated for it, and
  Enablement's universal requirement guarantees every training hazard has at
  least that one cell. This check never needs a `(legitimization,
  enablement_only_hazard)` cell to exist.

Rationale: user confirmed, in response to critique DI-C2's Open Question ("is
legitimization enumerated-and-skipped for `prv`/`sxc_prn`, or never required
at all?"): "Go with the component is *not required* for those hazards, so the
cell is never consulted rather than consulted-and-rejected"
(`critiques/2026-07-23-decision-introspection.md`). Absent this decision, the
literal reading of D-5's enumeration plus D-3/D-11's fail-closed check would
enumerate a `(legitimization, prv)` cell, find it has **zero rows of any
kind** to compute a label vector over at all — not the single-class-among-
present-rows condition D-5's amendment defines, a case D-5 does not cover —
and `hrc-predict` would need to invent a special case to avoid hard-failing
on every `prv`/`sxc_prn` response, which is exactly the failure DI-C2
identified. This decision closes that gap by defining the cell as
never-enumerated rather than degenerately-fit-and-rejected, and confirms
D-15's already-locked reporting guarantee (enablement-only rows "remain in
the final-label headline population exactly as before") is achievable at
all — D-15's own text calls itself "a restatement... not a new modeling
change" of an existing rule; this decision is the mechanism that rule was
implicitly assuming. Checked against the full ledger: no conflicts found. D-3
and D-11's fail-closed guarantees are unaffected (they still fully apply to
every *required* cell); D-5's amended degeneracy condition is unaffected (it
is defined over rows that exist, and a not-required cell has none to check);
D-14's exclusion trigger gains an explicit "this is not one of them" note;
D-15 gains a note that this decision is its concrete mechanism.
Touches: `PLAN.md` §3 step 4 (cell enumeration must state the required-
components carve-out explicitly), §4 (artifact schema — `thresholds.json`/
`heads.npz` have no `prv`/`sxc_prn` legitimization entries at all), §5 (D-14
bullet's previously-undefined "required component" phrase now has a
definition; per-row output schema note), §6 (`hrc-predict`'s per-row output
and step ordering — steps 2/3 only run for a hazard's required components);
`DECISIONS.md` D-3, D-5, D-11, D-14, D-15 (cross-reference notes added
below).
Note (2026-07-23, D-7 amendment, critique DI-Q2): this decision is also the
mechanism behind D-7's amended fit-time row set for Legitimization's
`mean`/`scale`/`center_mean` — see D-7's second amendment.
Note (2026-07-23, D-23, critique Deliverable-3 P-C6): this decision names
`config.ENABLEMENT_ONLY_HAZARDS` as the source of the enablement-only set. At
**serve time** (predict/evaluate) that reference is superseded by D-23: the
required-components lookup and every rule-family lookup read the set/map
**frozen into the artifact's `rules.json`**, not installed config, so a
hazard reclassified in installed config after training does not silently
change how an existing artifact scores. The rule this decision locks
(Enablement always required; Legitimization required except for the
enablement-only family) is unchanged — only the source it is evaluated
against at serve time is pinned. At *train* time the installed config is what
gets frozen, so there is no divergence there.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-4):**
`model.py`'s `fit` reuses `rules.py`'s already-built `is_required_component`
for cell enumeration, so this decision's train-time rule and its serve-time
counterpart (D-3/D-11/D-20's predict resolution) now share one function
rather than two independently-written rules that could drift apart.
Forcing-function test confirms no `("legitimization", "prv")` cell is ever
created while `("enablement", "prv")` is.

<a id="d-19"></a>
## D-19: The predict/evaluate path has an explicit business-rule stage between centering and thresholding; the gate consumes rule-adjusted probabilities
Date: 2026-07-23
Status: locked
Decision: `hrc-predict` (§6) and `hrc-evaluate` (§5) apply the toy's
`apply_component_business_rules` (`scoring_common.py` L583-621) as a named
stage that runs **after** a component's centered nonzero/high probabilities
are computed and **before** the monotonicity-gated thresholding (D-10) turns
them into an ordinal. The values the gate and the final v1.4 combination
consume are the **business-rule-adjusted** probabilities (`adjusted_nonzero`,
`adjusted_high`), not the raw centered ones — matching the toy, which feeds
`adjusted_pred`/`adjusted_score` to the final label and metrics
(`run_bge_hazard_weighted_heads.py` L279-286, `build_overall_rows` L1179-1183),
and matching D-16's amendment, which already established that the toy's
reported metrics run on post-rule values.

Of the toy's three business rules, only one still has independent effect
under the locked ledger, and it is the reason this stage cannot be dropped:
- Rule 1 (Legitimization N/A for enablement-only hazards) is **subsumed by
  D-18** — the `(legitimization, prv/sxc_prn)` cell is never enumerated, so
  there is nothing to zero.
- Rule 3 (prompt-repetition-only zeroes Enablement) is **subsumed by D-4/§6
  step 2** — such a response is scored `0` for Enablement before the head is
  ever invoked, so the rule never re-fires downstream.
- **Rule 2 (the disclaimer rule) survives and must be applied:** for a
  **specialized-advice** hazard (`config.SPECIALIZED_ADVICE_HAZARDS`, e.g.
  `spc_*`), if the response carries at least one disclaimer sentence
  (`disclaimer_sentence_count > 0`, from the preprocessing flags of §1.1
  item 1 / §3 step 2), the **Legitimization** component's adjusted nonzero,
  adjusted high, and adjusted combined score are all set to `0.0`, and a
  `rule_reasons` entry `specialized_advice_disclaimer_reduces_legitimization`
  is emitted. This is the only one of the toy's rules with no other decision
  standing in for it, and `PLAN.md` §5/§6 mentioned neither it nor the word
  "disclaimer" before this decision.
Rationale: user answered critique Deliverable-3 P-C3 in two parts — "the
business rule that still does work has no home: add the Rule 2 language to §5
or §6 as needed," and "the gate's input stage is unstated:
business-rule-adjusted ones." For the *discrete* label the stage ordering is
coincidentally harmless (rules set both probabilities to exactly `0.0` and the
threshold grid floor is `0.05`, so a zeroed component predicts `0` under
either order), but that is a property of the sentinel value, not something an
implementer should have to rediscover — and it does **not** hold for the
continuous outputs D-21 defines. Checked against the full ledger: D-10
(monotonicity gate) is unaffected in mechanism — the gate rule is unchanged;
this decision only pins *which* probabilities it is applied to, which D-10 left
unstated. D-16's amendment is reinforced, not contradicted (it already runs
its AUC on `adjusted_high`). D-4's short-circuit runs *before* this stage (a
D-4-scored component is set to `0.0` directly and does not need rule 2, though
applying rule 2 to an already-`0.0` value is idempotent). D-18 removes rule
1's target entirely. No conflict found.
Touches: `PLAN.md` §5 (pipeline description names the business-rule stage and
the disclaimer rule; the metrics already assume post-rule values per D-16),
§6 (the ordered step contract gains an explicit business-rule step between
step 3 and the gate; the gate bullet states it consumes adjusted
probabilities), §1.1 item 3 (already lists the disclaimer rule as science to
preserve); `rules.py` (`apply_component_business_rules` port), `model.py`
predict path.
Note (2026-07-23, D-23): the `config.SPECIALIZED_ADVICE_HAZARDS` reference in
the disclaimer-rule bullet, like D-18's `config.ENABLEMENT_ONLY_HAZARDS`, is
shorthand for the specialized-advice set **frozen into the artifact's
`rules.json`** at serve time, not a directive to consult installed config
(D-23). The disclaimer rule's family test reads the same frozen family map as
Step 0.
Note (2026-07-23, thresholds are optimized pre-rule but served post-rule —
accepted asymmetry, surfaced per user request): this decision pins that the
gate and v1.4 combination consume the **business-rule-adjusted** probabilities
at predict/evaluate time. The ordinal threshold grid search (D-10, §3 step 4),
however, optimizes over the **centered** (pre-business-rule) train
probabilities — the toy passes `nz_train_centered`/`hi_train_centered` (not
adjusted values) to `optimize_thresholds_for_hazard`, and applies
`apply_component_business_rules` only to the scored/test rows. So the
`(nonzero_threshold, high_threshold)` pair a hazard gets was selected against
pre-rule probabilities, then applied at serve time to post-rule ones. For rows
where no business rule fires (the majority) this is a distinction without a
difference — centered == adjusted. For rows where the surviving disclaimer
rule (rule 2) fires, the value the threshold is applied to at serve time
differs from the distribution the threshold was chosen over. This is **not**
a defect introduced here: it is the toy's own behavior, preserved under D-2's
"reproduce the in-sample fitting methodology exactly," and is left unchanged.
It is recorded so a future reader does not mistake D-10's "objective and
served rule permanently in agreement" claim (which is about the *gated shape*
of the rule) for a claim that the two consume the same probability *stage* —
they do not. Correcting it (e.g. applying business rules inside the grid
search) would be a deliberate divergence from the toy requiring its own
decision; none is taken here.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-7):** built
`rules.py`'s `apply_legitimization_disclaimer_rule` (the only surviving
business rule) and `model.py`'s `score_row`, which calls it **only** for
Legitimization, strictly after `resolve_component_action` resolves to
`"serve"`, and strictly before `ordinal_prediction`'s gate — matching this
decision's ordering exactly. Confirmed by the IC-1(a) end-to-end trace
(specialized-advice + disclaimer + Enablement repetition-only → "safe") and a
forcing-function test comparing the same probe with/without a disclaimer
sentence, confirming the rule changes a real outcome (the no-disclaimer case
predicts something other than the disclaimer-forced `0`), not just a value
that would have been `0` anyway.

<a id="d-20"></a>
## D-20: An absent or otherwise-invalid *required* cell fails closed exactly like a skipped cell — the row is a hard-fail item
Date: 2026-07-23
Status: locked
Decision: At predict/evaluate time, a **required** `(component, hazard)` cell
whose `thresholds.json` `status` is anything other than `"fit"` — `"skipped"`
(D-5), **absent entirely**, or any not-`"fit"` value — is treated as a
hard-fail for the whole row (the whole "item"), identically to D-5's
skipped-cell trigger: `hrc-predict` routes the item to its failures output
(D-22) and `hrc-evaluate` excludes the item from all measurement (D-14). This
completes D-11's already-stated requirement that the cell's status "must be
`"fit"`, not `"skipped"` **or absent**", which `PLAN.md` §6 step 3 had
narrowed to test only for `"skipped"`.
Rationale: user answered critique Deliverable-3 P-C4: "When bugs occur (e.g.
absent required cell), that whole item should be skipped." An absent required
cell is not an expected data condition — it means a corrupt/partially-written
artifact, a `heads.npz`/`thresholds.json` disagreement, or a code bug — and
D-3's whole rationale ("no pooled/global head exists to fall back to") is that
there is nothing safe to serve in its place, so failing **open** (serving it)
is the one outcome that must not happen. The critique found the current
implementation fails open: `resolve_component_action`
(`src/hazard_classifier/rules.py`) returns `"serve"` for `cell_status=None`
on a required, known-hazard, non-empty row, and the 23-case truth table in
`tests/science/test_predict_resolution.py` never exercises that input.
Checked against the full ledger: D-11's decision text already names the
"absent" case (this decision makes §6's prose and the code match D-11, it does
not add a new rule); D-5 is unaffected (a genuinely-skipped cell and an
absent cell now share one fail-closed outcome, which D-5's "must never be
used at predict time" already demands); D-18 is unaffected and must not be
confused with this — a **not-required** legitimization cell for `prv`/`sxc_prn`
is *correctly* absent by design and is handled by Step 0 before this check is
ever reached, so this decision applies only to a **required** cell that is
absent, which is always a defect. No conflict found.
Touches: `PLAN.md` §6 step 3 (the check is stated as "status must be `\"fit\"`"
— an allow-list — not "status is `\"skipped\"`" — a deny-list); `src/hazard_
classifier/rules.py` `resolve_component_action` (must return a fail action,
not `"serve"`, when a required cell's `cell_status` is `None` or not `"fit"`)
and `tests/science/test_predict_resolution.py` (add the missing case) — code
change deferred to an implementation slice per this project's fix-proposal/
implementation split.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-A):**
`resolve_component_action` flipped from the deny-list (`if cell_status ==
"skipped": fail; else: serve`) to the allow-list this decision requires (`if
cell_status == "fit": serve; else: fail`) — a `None`/absent status and any other
non-`"fit"` value now fail closed identically to `"skipped"`, sharing the same
`fail_skipped_cell` action (per this decision's "identically to D-5's
skipped-cell trigger" and its own note on `excluded_skipped_cell_count`'s
under-inclusive name — no new `ComponentAction` value was introduced). Two new
truth-table rows added to `tests/science/test_predict_resolution.py`
(`cell_status=None` and an arbitrary invalid string, both on a required, known,
non-empty row) and confirmed **red** (`serve` returned) before the fix, then
green after (41 tests total, up from 39). The function's `cell_status` parameter
type widened from `Literal["fit", "skipped"] | None` to `str | None` to reflect
that any non-`"fit"` value is now a valid, meaningful input rather than an
implicitly-disallowed one.

<a id="d-21"></a>
## D-21: `v14_overall_unsafe_score` is a retained side-output for research, defined from adjusted continuous scores, independent of `predicted_label`
Date: 2026-07-23
Status: locked
Decision: `hrc-predict` retains a continuous `v14_overall_unsafe_score` per
row as an output field, kept "to the side" for future research — it is **not**
what `predicted_label` is derived from. Definitions, pinned from the toy:
- **Value:** `v14_overall_unsafe_score = v14_overall_score(hazard, l_score,
  e_score)` (`scoring_common.py` L624-634), where `l_score`/`e_score` are the
  **business-rule-adjusted combined continuous** component scores (the mean of
  each component's adjusted nonzero and adjusted high centered probabilities,
  `score_from_centered_probs`, per D-19). Per hazard rule family:
  `enablement_only → e`; `specialized_advice → max(l, (l+e)/2)`;
  default → `max(l, e)`.
- **For a component scored `0` via D-4** (empty response, or repetition-only
  for Enablement): that component is short-circuited at §6 step 2 *before* the
  head and *before* D-19's business-rule stage, so its adjusted nonzero/high
  are the `0.0` sentinel D-16's amendment already pins for exactly these rows
  (not a value D-19's stage computes — the stage never runs for a
  short-circuited component). Its adjusted combined score is therefore
  `score_from_centered_probs(0.0, 0.0) = 0.0`, entering the formula above as
  `0.0` — a defined value, closing P-C2's "undefined for a row that never
  reached the head" gap, and using the same `0.0` D-16 already established so
  the continuous score and the AUC input agree on these rows.
- **For a not-required Legitimization component** (`prv`/`sxc_prn`, D-18):
  `l_score` is absent; `v14_overall_score` reads only `e` for the
  `enablement_only` family and never consults `l`, exactly as the toy's
  `Optional` handling does.
- **Independence from the label:** `predicted_label` comes from
  `discrete_v14_label` over adjusted *ordinals* (§1.1 item 3), not from
  thresholding this continuous score. The two can disagree (a high
  `v14_overall_unsafe_score` on a `safe`-labeled row); both are emitted and
  the output documentation must state they are computed independently so a
  consumer does not treat one as a monotone function of the other.
Rationale: user answered critique Deliverable-3 P-C2: "Yes. A continuous
`v14_overall_unsafe_score` wanted in production output. Save it to the side.
It will be used for future research." The field was previously named in §6's
output list with no definition anywhere in `PLAN.md` or the ledger and no
value for the common D-4 refusal case. Checked against the full ledger: D-19
supplies the adjusted-score stage this definition consumes; D-16 is a
different metric (high-head AUC) and is unaffected; D-4/D-18 supply the
zero/absent conventions this formula now has defined behavior for. No conflict
found.
Touches: `PLAN.md` §6 (output-field list gains the definition, the D-4 value,
and the independence-from-label note), §1.1 item 3 (the continuous
`v14_overall_score` per-family formulas are named alongside the discrete rule
already there); `rules.py` (`v14_overall_score` port), `model.py`.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-7):** ported
`v14_overall_score`/`discrete_v14_label`/`combined_component_score` verbatim
into `rules.py`; `model.py`'s `score_row` computes both from the same
per-component `(adjusted_nonzero, adjusted_high)` pair, independently.
Forcing-function test hand-constructs a cell (a degenerate `BinaryHead` with
`center_mean=0.5`, making `predict_proba_centered` return an exact, fully
controlled value) giving centered nonzero `0.6` / high `0.3` — an ordinal
prediction of `1` (not `2`) on a "default"-family hazard, so
`discrete_v14_label` says "safe," while `v14_overall_unsafe_score` (the mean,
`0.45`) is a non-trivial number that plainly disagrees with "safe" — a real
demonstration of the independence this decision requires, not just two
functions that happen not to call each other.

<a id="d-22"></a>
## D-22: `hrc-predict` splits scored rows and hard-fail rows into separate outputs instead of aborting the batch
Date: 2026-07-23
Status: locked
Decision: Run over a batch, `hrc-predict` does **not** abort when a row hits a
hard-fail condition (a genuinely unseen hazard per D-3/D-11 step 1, or a
non-empty response landing on a required cell that is `"skipped"`/absent per
D-5/D-20 step 3). It writes two outputs: a **successes** output carrying the
per-row scored fields (§6's output list) for every scoreable row, and a
**failures** output carrying the hard-fail rows with their identifying columns
and a reason (the same unseen-hazard / skipped-or-absent-cell distinction
D-14 already counts). Every input row appears in exactly one of the two
outputs; no scoreable row is lost because a different row failed.
Rationale: user answered critique Deliverable-3 P-C5: "split successes and
failures into separate outputs." The critique found that §6's "raises/reports
an error" phrasing let one bad row abort scoring of every other row in a
production batch — the identical failure mode D-14 fixed on the evaluate side,
left unfixed on the production side and worse here (a production batch drops
work for rows that were perfectly scoreable). Checked against the full ledger:
this **supersedes the characterization in D-14's Rationale** that "`hrc-predict`
is a single-row production API where aborting the one bad call is correct" —
that premise is now false for the batch path; D-14's actual *behavior*
(exclude hard-fail rows from `hrc-evaluate`'s metrics) is unaffected, and the
two paths still share the identical fail-closed *predicate* (D-3/D-4/D-5/D-11/
D-20), differing only in consequence: `hrc-evaluate` drops the row from
metrics, `hrc-predict` writes it to the failures output. A cross-reference
note is added to D-14. The single-row `HazardResponseClassifier.score(rows)`
Python API's error contract (raise vs. return per-row error entries) is
**not** settled here — see Open Questions. No conflict found with any locked
behavior.
Touches: `PLAN.md` §6 (batch-CLI bullet and steps 1/3 state split-output
behavior rather than "raises/reports an error"); `DECISIONS.md` D-14
(cross-reference note); `cli/predict.py`.
Note (2026-07-25, D-25 amendment, integration audit finding N-1): this
decision's "identifying columns" for the failures output means **`prompt_uid`**
(the unique response/row id, §2.1), not `seed_prompt_id`. D-25's `failures.csv`
originally also carried `seed_prompt_id`; that column is dropped (D-25's
2026-07-25 amendment) because `prompt_uid` alone identifies a row and
`seed_prompt_id` is an inert predict-path passenger (D-24). The split-output
guarantee this decision locks — every input row in exactly one output, keyed by
`prompt_uid` — is unchanged.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-10):**
`model.py`'s `predict_rows` mirrors `evaluate_rows`'s architecture exactly —
reuses `score_row` and catches `HardFailError`, but routes the row to a
`failures` list instead of an exclusion counter. Forcing-function test
confirms `len(predictions) + len(failures) == len(input rows)` for a mixed
batch (scoreable / unseen-hazard / skipped-cell rows together), not just
that each case works in isolation.

<a id="d-23"></a>
## D-23: Required-components and rule-family lookups read the artifact's frozen `rules.json`, not installed config
Date: 2026-07-23
Status: locked
Decision: At predict/evaluate time, every lookup of a hazard's required
components (D-18's Step 0) and its rule family (`hazard_rule_family` — driving
both the v1.4 combination and D-19's disclaimer rule) reads the **artifact's
frozen `rules.json`** (§4: "hazard→family map + rule constants, frozen from
config"), **not** the installed `hazard_classifier.config` module. D-18's
reference to `config.ENABLEMENT_ONLY_HAZARDS` is shorthand for "the
enablement-only set that was frozen into the artifact at train time," not a
directive to consult live installed config at serve time.
Rationale: user answered critique Deliverable-3 P-C6: "Go with 'the config was
frozen into the artifact.'" §4's entire rationale for freezing `rules.json` is
that an artifact is self-describing and must not depend on the code version
that happens to load it. Reading installed config instead (which the current
`src/hazard_classifier/rules.py` `is_required_component` does, via `from
hazard_classifier.config import ENABLEMENT_ONLY_HAZARDS`) breaks in both
directions if a hazard is reclassified between train and serve without a
retrain: a hazard newly added to installed `ENABLEMENT_ONLY_HAZARDS` would
make Step 0 skip a Legitimization cell the artifact actually fit (silently
dropping a component from the label), and one newly removed would make Step 0
require a cell the artifact never enumerated (landing on D-20's absent-cell
fail-closed path). Freezing the map into the artifact removes the divergence
by construction. Checked against the full ledger: D-18 is not contradicted —
its rule (Enablement always required; Legitimization required except for the
enablement-only family) is unchanged; only the *source* the rule is evaluated
against is pinned. D-19's disclaimer rule reads the same frozen family map.
No conflict found.
Touches: `PLAN.md` §4 (`rules.json` is named as the serve-time source of the
family map, not just a frozen copy), §6 (Step 0 and the v1.4/disclaimer
lookups cite `rules.json`); `src/hazard_classifier/rules.py`
`is_required_component` / any `hazard_rule_family` (must take the artifact's
frozen map rather than importing installed config) and `model.py` load path —
code change deferred to an implementation slice per this project's fix-
proposal/implementation split.

**Implementation slice landed, partially (2026-07-25, `VERIFICATION.md`
IS-C):** `src/hazard_classifier/rules.py`'s `is_required_component` and
`resolve_component_action` no longer import `ENABLEMENT_ONLY_HAZARDS` from
`hazard_classifier.config` — both now take it as a required
`enablement_only_hazards` parameter, with **no default**, so a caller cannot
silently fall back to config by omitting the argument. A forcing-function test
(`test_is_required_component_uses_the_passed_set_not_installed_config`)
constructs a frozen set that disagrees with installed config in both
directions and confirms the passed set's answer wins. This satisfies this
decision's requirement **at the unit level**; the actual wiring of a real
artifact's frozen `rules.json` into the caller still needs `model.py`/artifact
load (§10 Phase 3, not yet built) — tracked as the "full wiring" half of IS-C
in `VERIFICATION.md`, not done here.

**New finding surfaced while implementing this slice, not fixed here:**
`src/hazard_classifier/metrics.py`'s `legitimization_eligible_mask` has the
identical pattern — it imports `ENABLEMENT_ONLY_HAZARDS` from installed
config to decide which rows are Legitimization-eligible (D-15, mechanized by
D-18) for `hrc-evaluate`'s reporting. This is exactly the class of lookup this
decision covers ("every lookup of a hazard's required components... reads the
artifact's frozen `rules.json`, not installed config"), so it should be
parameterized the same way — out of this pass's declared scope (which named
only `rules.py`), so deliberately not touched here. Queued as a new backlog
item in `VERIFICATION.md` rather than fixed silently.
Touches (this amendment): `src/hazard_classifier/rules.py` (done, this pass);
`src/hazard_classifier/metrics.py` `legitimization_eligible_mask` (queued,
not done); `VERIFICATION.md`.

**Implementation slice landed, partially (2026-07-25, `VERIFICATION.md`
IS-C2):** `src/hazard_classifier/metrics.py`'s `legitimization_eligible_mask`
no longer imports `ENABLEMENT_ONLY_HAZARDS` from installed config either — it
now takes the same required `enablement_only_hazards` parameter, no default,
mirroring `rules.py`'s IS-C fix exactly. Forcing-function test
(`test_legitimization_eligible_mask_uses_the_passed_set_not_installed_config`)
mirrors IS-C's: a frozen set disagreeing with installed config in both
directions, confirmed the passed set's answer wins. As with IS-C, this
satisfies the decision **at the unit level** — the artifact-wiring half still
needs `model.py`/IS-5.

**Second new finding surfaced while implementing IS-C2, not fixed here:**
`final_label_metrics` in the same file still imports `SPECIALIZED_ADVICE_HAZARDS`
directly from installed config to exclude specialized-advice hazards from the
final-label headline (D-17 point 3). The specialized-advice family is part of
`hazard_rule_family`'s classification (also driving D-19's disclaimer rule),
so this decision's "rule family... reads the artifact's frozen `rules.json`,
not installed config" applies to it too — out of IS-C2's declared scope (which
named only `legitimization_eligible_mask`), so deliberately not touched here.
Queued as a new backlog item, IS-C3, rather than fixed silently.
Touches (this amendment): `src/hazard_classifier/metrics.py`
`legitimization_eligible_mask` (done, this pass); `final_label_metrics`
`SPECIALIZED_ADVICE_HAZARDS` import (queued, not done, IS-C3);
`VERIFICATION.md`.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-C3):**
`src/hazard_classifier/metrics.py`'s `final_label_metrics` no longer imports
`SPECIALIZED_ADVICE_HAZARDS` from installed config either — it now takes the
same shape of required `specialized_advice_hazards` parameter, no default,
mirroring IS-C/IS-C2 exactly. Forcing-function test
(`test_final_label_metrics_uses_the_passed_set_not_installed_config`) mirrors
IS-C/IS-C2's: a frozen set disagreeing with installed config in both
directions, confirmed the passed set's answer wins. `src/hazard_classifier/
metrics.py` no longer imports `hazard_classifier.config` at all — every
hazard-family lookup in the module now reads its set from an explicit,
required caller-supplied parameter. As with IS-C/IS-C2, this satisfies the
decision **at the unit level** across all three call sites this pass surfaced
(`rules.py`'s two functions, `metrics.py`'s two functions); the
artifact-wiring half for all of them still needs `model.py`/IS-5. This closes
out the chain of same-pattern findings this decision's implementation slices
surfaced (IS-C → IS-C2 → IS-C3) — no further installed-config imports of
either hazard-family set remain in `rules.py` or `metrics.py`.
Touches (this amendment): `src/hazard_classifier/metrics.py`
`final_label_metrics` (done, this pass); `VERIFICATION.md`.

**Artifact-wiring half landed (2026-07-25, `VERIFICATION.md` IS-5):** this
decision's remaining gap — "an actual artifact's frozen `rules.json`
supplying the sets, not hand-built test fixtures" — is now closed.
`model.py`'s `save`/`load` round-trip `enablement_only_hazards` (and, new
this pass, `specialized_advice_hazards`, needed for `rules.json` but never
read by `fit`/cell enumeration itself, D-18) through `rules.json`.
Forcing-function test (`test_loaded_enablement_only_hazards_is_the_frozen_
set_not_installed_config`) mirrors IS-C/IS-C2/IS-C3's pattern exactly: froze
a set disagreeing with installed `config.ENABLEMENT_ONLY_HAZARDS` in both
directions, saved, reloaded, and confirmed `is_required_component` -- fed the
*loaded* set -- disagrees with the same call fed installed config, in both
directions, and that no `("legitimization", hazard)` cell exists for a hazard
the frozen set (not config) says is enablement-only. **This closes D-23
end-to-end** for every call site this decision's implementation surfaced
(`rules.py` IS-C, `metrics.py` IS-C2/IS-C3, and now the artifact itself,
IS-5) — no remaining gap between "frozen at train time" and "read at serve
time."

**Gap found and fixed while building IS-7, not a new decision:** IS-5's own
`save`/`load` wrote `specialized_advice_hazards` into `rules.json` correctly,
but never read it back onto the returned `HazardResponseClassifier` object,
and `fit` had no way to set it in the first place -- `hazard_family` (needed
by `score_row`'s Step 0 and the disclaimer rule) had no frozen source to read
for this second set, only `enablement_only_hazards`. Fixed by giving
`HazardResponseClassifier` a `specialized_advice_hazards` field, adding a
same-shaped keyword parameter to `fit` (unused for cell enumeration, D-18
only names the enablement-only set, but threaded through purely so it rides
the object rather than needing separate caller-side tracking), and having
`load` populate it from `rules.json`. Moved `specialized_advice_hazards` off
`save`'s own parameter list (now redundant) onto the classifier it's saving.
Existing IS-5 tests updated accordingly; full suite green throughout.

**Second gap found and fixed while building IS-11, same pattern, not a new
decision:** `HazardResponseClassifier` had no record of which BGE model/
revision it was actually fit against either -- `score` (IS-11) needs to load
the *same* model a caller embedded training data with, per this decision's
own "predict-time embeddings must match training, never overridden"
principle, but there was no frozen source for it beyond a hardcoded default
that could silently diverge from the real one. Fixed the same way:
`embedding_model_name`/`embedding_model_revision` fields on
`HazardResponseClassifier`, matching `fit` keyword parameters (default
`config.DEFAULT_EMBEDDING_MODEL_NAME`/`None`), round-tripped through
`manifest.json` by `save`/`load`. `config.DEFAULT_EMBEDDING_MODEL_NAME` was
added (moved out of `embed.py`, which now imports it) specifically so
`model.py` can reference the default without pulling in `embed.py`'s
`sentence-transformers`/`torch` dependency for callers who never touch real
embeddings (every other `model.py` test in this project fits/scores against
synthetic feature arrays). Confirmed by a save→load round-trip test.

<a id="d-24"></a>
## D-24: `seed_prompt_id` stays required for `hrc-predict` input; present ground-truth columns are ignored, not rejected
Date: 2026-07-23
Status: locked
Decision: `hrc-predict`'s input schema keeps `seed_prompt_id` as a **required**
column, even though no predict-path step consumes it (it is used only by
D-13's held-out/in-sample partitioning in `hrc-evaluate`). A production caller
with no meaningful seed identity supplies a value anyway. Separately, the
§2.1-vs-§6 inconsistency on ground-truth columns is resolved toward §6:
`enablement_value`, `legitimization_value`, `is_safe_ground_truth` are
**optional and ignored** when present in a predict CSV — the schema validator
does not require them and does not range-check them on the predict path
(§2.1's "same file minus the three ground-truth columns" is reworded to "the
ground-truth columns are optional and ignored," so a caller may reuse a
labeled CSV for prediction without stripping columns).
Rationale: user answered critique Deliverable-3 P-Q5: "Leave `seed_prompt_id`
required." Keeping one shared schema across train/evaluate/predict (where the
column is load-bearing for the first two) is simpler than a predict-only
schema variant, at the cost of a fabricated value for label-free production
traffic — the user accepted that cost. The ground-truth-column half is the
minimal reconciliation of the two sections that were already in the plan
(§2.1 said "minus," §6 said "optional/ignored"); ignoring-when-present is the
more permissive and more useful reading (a labeled CSV is directly reusable
for a predict smoke test). Checked against the full ledger: D-13's reliance on
`seed_prompt_id` is on the *evaluate* path and is unaffected; no locked
decision required stripping ground-truth columns. No conflict found.
Touches: `PLAN.md` §2.1 (production-input sentence reworded to
"optional/ignored"), §6 (input line already lists `seed_prompt_id` as
required — now consistent with §2.1); `schema.py` validation.
Note (2026-07-25, D-25 amendment, integration audit finding N-1): this
decision's "inert passenger" characterization of `seed_prompt_id` on the predict
path (required for schema uniformity, consumed by no predict step, fabricated for
label-free traffic) is the basis for dropping it from `hrc-predict`'s
`failures.csv` output (D-25's 2026-07-25 amendment). It remains a **required
input** column, as this decision locks; only its appearance in a predict *output*
is removed.

<a id="d-25"></a>
## D-25: `hrc-predict` CLI contract
Date: 2026-07-23
Status: locked
Decision: `hrc-predict`'s invocation is:
```
hrc-predict --model-dir models/v1 --input responses.csv --output-dir predictions/ [--allow-download]
```
- **`--model-dir`** (required): the artifact directory `hrc-train` wrote via
  its `--output-dir`. Predict reads exactly what train writes; the flag name is
  the read-side mirror of train's write-side `--output-dir`.
- **`--input`** (required): the predict CSV in the §2.1/§6 schema —
  `seed_prompt_id` required, the three ground-truth columns optional and
  ignored (D-24).
- **`--output-dir`** (required): a directory that receives **two** files, per
  D-22's split-output requirement:
  - `predictions.csv` — the successes, one row per scoreable input row, columns
    in §6's per-row order: `prompt_uid, hazard, enablement_predicted,
    legitimization_predicted, v14_overall_unsafe_score, predicted_label,
    rule_reasons`.
  - `failures.csv` — the hard-fail rows, columns `prompt_uid, hazard,
    seed_prompt_id, failure_reason`, where `failure_reason ∈ {unseen_hazard,
    skipped_or_absent_cell}` (the same distinction D-14 counts and
    D-20/D-22 name). **Always written**, with a header row even when there are
    no failures, so a downstream pipeline can rely on the file existing (open
    question 3, user-accepted).
  Every input row appears in exactly one of the two files (D-22).
- **`--allow-download`**: offline by default; opt-in to fetch BGE weights —
  mirroring `hrc-train`'s identical flag (§3 step 3, §7).
- **Deliberately absent flags:** no `--model-name` (the BGE id+revision are
  pinned in the artifact manifest per §4/D-23; a CLI flag that could disagree
  would break §4's "identical embeddings" guarantee, so predict resolves the
  model from the manifest, not the CLI); no `--device` (CPU-only, D-6); no
  `--other-hazard-weight` (a train-time fit parameter, frozen into the
  artifact).

**Output shape (open question 1, user-accepted):** a single `--output-dir` with
the two fixed filenames above, symmetric with how `hrc-train` writes a
directory — chosen over two explicit path flags or stdout+file.
**Output format (open question 2, user-accepted):** CSV only for the CLI,
consistent with the tool's CSV-in/CSV-out convention and `hrc-evaluate`'s
`metrics.csv`; JSON/streaming for service embedding is left to the
`HazardResponseClassifier.score(rows)` Python API, not the CLI.
Rationale: critique Deliverable-3 P-Q2 found §6 specified no CLI contract at
all for the one deliverable that is a production interface — no artifact arg,
input arg, output location, output format, or offline/model-cache surface —
while §3 gives `hrc-train` a full invocation line. §10's phase-5 exit
criterion ("scores an unlabeled CSV end-to-end") could not be checked against
a contract that did not exist. User accepted the proposed contract and all
three of its open-question defaults (fix-proposal, 2026-07-23).
Checked against the full ledger: consistent with and load-bearing for D-22
(the two-output shape), D-24 (input schema), §4/D-23 (no `--model-name`;
model resolved from the manifest — the one active constraint the CLI must
honor), D-6 (no `--device`), and E-8's "clean slate per cycle" answer. No
conflict found. The parallel gap that `hrc-evaluate`'s CLI is likewise
unspecified is **not** resolved here (out of P-Q2's scope) — flagged for a
separate item so predict and evaluate can be given a shared artifact-load
flag name and offline surface together.
Touches: `PLAN.md` §6 (add the invocation line and the two-output-file spec,
mirroring §3's `hrc-train` documentation), §10 (phase-5 exit criterion now
has a contract to check against); `cli/predict.py`.

**Amendment (2026-07-25, integration audit `critiques/2026-07-25-decisions-consistency.md`
finding N-1): `failures.csv` drops `seed_prompt_id` — its columns become
`prompt_uid, hazard, failure_reason`.** As originally specified, `failures.csv`
carried `seed_prompt_id` while `predictions.csv` did not — an asymmetry with no
motivation: `prompt_uid` is the **unique response/row id** (§2.1) and is present
on both outputs, so it already rejoins either output losslessly to the input
(which still carries `seed_prompt_id` and every other column). D-24 establishes
`seed_prompt_id` as an **inert passenger on the predict path** — required only
for one shared schema, consumed by no predict step, and *fabricated* for
label-free production traffic — so surfacing it in a predict output is redundant
at best and, on real traffic, echoes a meaningless value a consumer could
mistake for a real one. Neither failure reason (`unseen_hazard`,
`skipped_or_absent_cell`) concerns seed identity, so it adds nothing for triage
either. **Corrected:** `failures.csv` columns are `prompt_uid, hazard,
failure_reason`; `seed_prompt_id` is dropped. `predictions.csv` is unchanged
(§6's per-row order). Every input row still appears in exactly one output (D-22),
both keyed by `prompt_uid`. This is the root-cause fix for D-22's "identifying
columns" phrasing, which D-25 had read as including `seed_prompt_id` even though
`prompt_uid` alone identifies a row.
User confirmed (2026-07-25): drop it from `failures.csv`. Checked against the
full ledger: D-22 (its "identifying columns" is satisfied by `prompt_uid` — note
added), D-24 (its inert-passenger semantics are the basis for the drop — note
added), D-13/§2.1 (`seed_prompt_id`'s only real consumer is `hrc-evaluate`'s
partitioning, which reads the *input* CSV, not `hrc-predict`'s outputs — the
evaluate path is untouched), D-14 (`hrc-evaluate` writes no `failures.csv` at
all — it excludes-and-counts — so there is no parallel output to keep symmetric
with). No conflict found; no consumer reads `seed_prompt_id` out of
`failures.csv`.
Touches: `PLAN.md` §6 (the `failures.csv` column list drops `seed_prompt_id`);
`DECISIONS.md` D-22, D-24 (cross-reference notes below); `cli/predict.py`.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-10):**
`model.py`'s `PREDICTIONS_COLUMNS`/`FAILURES_COLUMNS` constants pin exactly
this corrected column set (`failures.csv` has no `seed_prompt_id`), and
`to_predictions_frame`/`to_failures_frame` build a `pandas.DataFrame` with
these columns explicitly even for an empty row list — confirmed by an actual
file write/read-back test that an empty batch's `failures.csv` still has a
header, not just an empty file. **Not yet built:** the actual `--model-dir`/
`--input`/`--output-dir` argparse entry point — `predict_rows` is the
logic layer a thin CLI wrapper would call.

<a id="d-26"></a>
## D-26: `hrc-evaluate` CLI contract
Date: 2026-07-23
Status: locked
Decision: `hrc-evaluate`'s invocation is:
```
hrc-evaluate --model-dir models/v1 --input labeled_eval.csv --output-dir eval_results/ [--allow-download]
```
- **`--model-dir`** (required): the artifact directory `hrc-train` wrote — the
  **same** flag name `hrc-predict` uses (D-25), since both tools load an
  artifact. It is also the source of the recorded holdout split
  (`holdout_seed_prompt_ids`, D-13) and the frozen `rules.json` (D-23).
- **`--input`** (required): a **labeled** eval CSV in §2.1's full schema. The
  three ground-truth columns (`enablement_value`, `legitimization_value`,
  `is_safe_ground_truth`) are **required** here — the opposite of D-24's
  optional/ignored rule, which is scoped explicitly to the *predict* path.
  `hrc-evaluate` measures against those labels, so it cannot proceed without
  them.
- **`--output-dir`** (required): receives three files —
  - `metrics.json` (D-17's schema: top-level `holdout_recorded`, excluded
    counts, per-population objects),
  - `metrics.csv` (D-17's long-format flattening of the same data),
  - `summary.txt` (D-17's free-form human-readable summary, derived from the
    same object). **Written to the output dir** (open question 1,
    user-accepted), not stdout, so all three outputs live in one place —
    symmetric with D-25 and §3's `hrc-train`.
- **`--allow-download`**: offline by default; opt-in to fetch BGE weights —
  identical to D-25 / `hrc-train` (§3 step 3, §7).
- **Deliberately absent flags:** no `--model-name` (BGE id+revision read from
  the manifest, §4/D-23 — evaluate's frozen-head scores are only valid against
  the artifact's pinned revision; this is the old E-8 concern, resolved by
  pinning rather than a CLI flag); no `--device` (CPU-only, D-6); no `--cv`
  (dropped from scope, D-12); no `--holdout-seed-fraction` (a *train*-time
  flag — evaluate **reads** the recorded holdout from the manifest, D-13, and
  never re-derives a split); no `--other-hazard-weight` (a frozen train-time
  parameter).

**Partially-labeled input (open question 2, user-accepted):** if a row whose
hazard is **not** enablement-only carries a blank `enablement_value`,
`legitimization_value`, or `is_safe_ground_truth`, `hrc-evaluate` **errors**
(a measurement tool cannot score an unlabeled row against a missing label — a
blank is a data defect, not a scoreable row), rather than silently
excluding-and-counting it like a D-14 hard-fail. This is distinct from — and
does not disturb — the already-settled enablement-only case: a blank
`legitimization_value` on a `prv`/`sxc_prn` row is expected and correct
(D-15/D-18, §2.1), and is **not** an error; those rows are scored via
Enablement alone. This resolves the residual half of the Deliverable-2 E-4
finding ("does the frozen path require ground-truth for all rows or tolerate a
partially-labeled CSV") that E-4's answer left open (E-4 answered only the
enablement-only blank-legitimization case).
Rationale: D-25 (P-Q2) fixed the `hrc-predict` CLI and flagged that
`hrc-evaluate`'s CLI was undefined for the same reasons — §5 never gave it an
invocation line, output-location, output-format, or offline surface, while §3
documents `hrc-train` fully. User chose to fix it now as its own fix-proposal
and accepted both open-question defaults (summary.txt in the output dir; error
on an unexpected blank label). Checked against the full ledger: consistent
with and load-bearing for D-13 (manifest holdout partitioning), D-14 (excluded
counts in the output), D-17 (the metrics.json/metrics.csv output shape), D-12
(no `--cv`), D-6, §4/D-23 (model from manifest), and §2.1 (evaluate consumes
the labeled schema). The one asymmetry with D-25 — `--input` requires
ground-truth here, optional there — is exactly what §2.1/D-24 already draw.
No conflict found.
Touches: `PLAN.md` §5 (add the invocation line and the three-output-file spec;
state the ground-truth-required and blank-label-errors rules), §10 (phase-4
exit criterion now has a CLI contract to check against); `cli/evaluate.py`,
`schema.py` (the blank-label validation is an evaluate-path schema rule).

**Amendment (2026-07-25, integration audit `critiques/2026-07-25-decisions-consistency.md` finding C-1): the blank-ground-truth-label check is family-aware per-row against frozen `rules.json`, gated behind D-14's exclusion — not an up-front `schema.py` rejection.** As originally written, the "partially-labeled input" rule above (a blank ground-truth column on a not-enablement-only hazard row → error) and its "the blank-label validation is an evaluate-path schema rule" Touches line collided with three later/adjacent locked decisions, none reconciled when this entry was locked (D-26 predates D-27; this entry's own full-ledger check named D-23 but not D-27):
- **D-23** requires every evaluate-time rule-family lookup to read the artifact's frozen `rules.json`, not installed config. Deciding "is this hazard enablement-only" up front in `schema.py` — where D-27 says the evaluate path has no `rules.json` membership resolution — could only use installed config, reintroducing exactly the train/serve config drift D-23 removes (reclassify a hazard's family in config after training and a blank `legitimization_value` flips between "error" and "tolerated" for the same artifact).
- **D-14/D-22/D-27** guarantee that a hazard the artifact never trained on is *excluded from measurement and the run continues*, never an abort. An unseen hazard is absent from `rules.json`, so its family is unknowable and it reads as "not enablement-only" — under the original rule, a single unseen-hazard row that also carried a blank label would flip the whole run from D-14's exclude-and-continue to this entry's abort, with no recorded precedence.

**Corrected mechanism (user-accepted, this pass):**
1. **Family source = the artifact's frozen `rules.json` (D-23/D-27), never installed config.** Whether a row's hazard is enablement-only is read from the same frozen family map every other serve-time lookup uses.
2. **The blank-label error fires only on rows that survive D-14's hard-fail exclusion.** A D-14 hard-fail — an unseen hazard (absent from `rules.json`, D-3/D-11/D-27) or a non-empty response on a `"skipped"`/absent/invalid *required* cell (D-5/D-20) — is excluded from measurement and counted (D-14/D-17) *before* its ground-truth labels are examined, so a blank label can never promote it to a whole-run abort. This honors this entry's own rationale ("a measurement tool cannot score an unlabeled row against a missing label"): a row that is not measured has nothing to score against, so its missing label is moot. Note the gate is D-14's *entire* hard-fail filter (unseen **and** skipped/absent required cell), not only the unseen case — deferring to D-14 for unseen but not for skipped/absent would contradict D-14's own identical treatment of both.
3. **Among surviving (to-be-measured) rows the rule is unchanged:** a known, non-enablement-only hazard row with a blank in any of the three ground-truth columns is an **error** (the user's original "error over exclude" choice, open question 2, preserved); a known enablement-only (`prv`/`sxc_prn`) hazard row's blank `legitimization_value` is expected and tolerated (D-15/D-18), while its `enablement_value` and `is_safe_ground_truth` stay required non-blank via the base "ground-truth required" rule (§2.1, `--input` above) — those are what the row is measured on.
4. **Family-agnostic structural validation stays up front in `schema.py`:** the three ground-truth *columns* must be present, and any *non-blank* value in them must be in `{0,1,2}`. These need no artifact and are unchanged. Only the family-aware "is this blank tolerated?" judgment moves to the per-row evaluate path.

So "the blank-label validation is an evaluate-path schema rule" is narrowed: the family-agnostic structural half stays in `schema.py`; the family-aware half is a per-row evaluate check running after Step 0's `rules.json` family resolution and after D-14's exclusion filter.

User confirmed (2026-07-25): "accept the natural reconciliation." Checked against the full ledger: D-13 (partitioning runs on survivors; an abort, if it fires, precedes it — otherwise no effect — unaffected), D-14 (its exclusion now runs strictly before blank-label validation — reinforced, not contradicted), D-15/D-18 (enablement-only blank-`legitimization` tolerance unchanged; mechanized via the same frozen family map), D-20 (absent/invalid required cell is a D-14 hard-fail → excluded → never a blank-label abort), D-22/D-24 (predict path ignores ground truth entirely — unaffected), D-23 (family source pinned to frozen `rules.json` — reinforced), D-27 (`schema.py` still does no `rules.json`-membership rejection on the evaluate path; the family-aware blank judgment is per-row, consistent with D-27's "membership decided per row" — reinforced), D-28 (a wholly-skipped Legitimization makes non-enablement-only rows D-14 hard-fails, so evaluating such an artifact never aborts merely because those rows have blank labels). No conflict found.
Touches: `PLAN.md` §2.1 (schema paragraph — the family-aware blank judgment is not an up-front schema rejection on the evaluate path; family-agnostic column/range checks stay), §5 `--input` bullet (state the frozen-`rules.json` family source and the survives-D-14 gating), §8.1 (the "blank legitimization for enablement-only hazards" test exercises the per-row evaluate path, not a pure `schema.py` unit); `schema.py` (family-agnostic structural/range checks only), `cli/evaluate.py`/`rules.py` (the per-row family-aware blank-label validation).

**Correction (2026-07-25, discovered building `schema.py`, `VERIFICATION.md`
IS-1): point 4's "any non-blank value in them must be in `{0,1,2}`" was a
drafting slip, not a considered position — it read as applying the `{0,1,2}`
ordinal range to all **three** ground-truth columns, including
`is_safe_ground_truth`, which is a safe/unsafe judgment, not an ordinal.**
Nothing about this decision's rationale (or the toy) ever intended
`is_safe_ground_truth` to be range-checked against `{0,1,2}`; the range check
was always meant for `enablement_value`/`legitimization_value` only. Also
surfaced while implementing: `is_safe_ground_truth`'s literal string/format
encoding is **not pinned by any locked decision anywhere in this ledger** —
`PLAN.md`'s schema table names it only as "ground-truth final safe/unsafe,"
and the toy (`scoring_common.py` L163) carries it through as an opaque string
without ever parsing or validating it. **Corrected scope of point 4:** the
`{0,1,2}` range check applies to `enablement_value`/`legitimization_value`
only; `schema.py` validates `is_safe_ground_truth` for **column presence
only** (per the mode's required-column set), never its contents' format. This
is a factual correction of this decision's own text, not a new choice — the
implementation (`src/hazard_classifier/schema.py`) follows the corrected
scope. **Open Question, not resolved here:** what is
`is_safe_ground_truth`'s actual literal encoding (e.g. `"safe"`/`"unsafe"`,
`"True"`/`"False"`, `"1"`/`"0"`)? Needed before any code parses this column
into a boolean (e.g. `hrc-evaluate`'s `is_safe_true` array, `metrics.py`
`final_label_metrics`'s first argument) — flagged for a future fix-proposal
once a real labeled CSV sample exists or the user specifies it directly.
Touches: `PLAN.md` §2.1 (correct the range-check scope); `DECISIONS.md` (this
note); `src/hazard_classifier/schema.py` (implements the corrected scope,
this pass).

<a id="d-27"></a>
## D-27: Hazard-code normalization at schema load; the unseen-hazard check and family lookup are one lookup against `rules.json`
Date: 2026-07-23
Status: locked
Decision: Two linked resolutions of critique Deliverable-3 P-Q3.

**(A) Normalization.** The `hazard` column is normalized **once, at
schema-load time, on all three paths** (train, evaluate, predict) in
`schema.py`, using the toy's `normalize_hazard` exactly:
`hazard.strip().replace("-", "_")` — strip surrounding whitespace and map
hyphens to underscores, **no lowercasing** (`scoring_common.py` L113-114;
hazard codes are lowercase-with-underscores, e.g. `spc_fin`, `prv`,
`sxc_prn`, and the toy does not lowercase). A single normalization point
replaces the toy's scattered re-normalization at each lookup
(`build_response_matrix` L380, `hazard_rule_family` L569), so no downstream
lookup can forget it. Because training normalizes before enumerating cells and
freezing `rules.json`, the artifact's keys are canonical; because
predict/evaluate normalize before every lookup, a cosmetic variant
(`"spc-fin "`, `"spc_fin "`) canonicalizes to `spc_fin` on both sides and no
longer produces a spurious fail-closed / failures row. This mirrors the toy
(D-2), adding no new divergence. User confirmed open question 1: "Be like the
toy" — strip + hyphen→underscore, no lowercase, so a case variant like
`"SPC_FIN"` remains unrecognized (and is handled by (B) below), exactly as the
toy would treat it.

**(B) Unseen-hazard check and family lookup unified against `rules.json`.**
After normalization, `hrc-predict`/`hrc-evaluate` perform a **single** lookup
of the hazard in the artifact's frozen `rules.json`:
- a hazard **present** in `rules.json` yields its family, from which required
  components follow (D-18), and scoring proceeds;
- a hazard **absent** from `rules.json` is a genuinely-unseen hazard → fail
  closed → routed to `failures.csv` (D-22) / excluded from metrics (D-14),
  **never** the toy's `"default"`-family fallback (`hazard_rule_family` L580
  `return "default"`). This is the same fail-closed-instead-of-fallback stance
  D-3 already locked, now applied to the family lookup itself.
This makes §6's "Step 0 (required-components lookup) runs before steps 1–3"
precise instead of circular: **Step 0 *is* the hazard-known determination** —
a `rules.json` miss is exactly Step 1's unseen-hazard failure, so there is no
ordering wrinkle where a family must be resolved for a hazard that might be
unknown.

**`rules.json` key set (open question 2, user-accepted): exactly the
artifact's trained hazards.** `rules.json` freezes the family mapping (from
config's family definitions) for **only** the hazards the artifact actually
trained on — not the full config hazard universe. Consequently "present in
`rules.json`" ≡ "known/trained" ≡ "has ≥1 enumerated required-component cell"
(Enablement is required for every hazard, D-18, so every trained hazard has at
least its Enablement cell). Step 0's `rules.json` lookup and Step 1's
"enumerated required cell exists" check therefore coincide as a single gate,
with no possibility of a hazard that resolves to a family yet has no trained
cells. User confirmed: "Freeze `rules.json` to contain exactly the artifact's
trained hazards."

**Schema-vs-artifact authority (resolves the critique's tension).** On the
**predict/evaluate** path, `schema.py` normalizes the hazard column but does
**not** reject unknown hazard codes — rejecting would abort the run, violating
D-22's split-output / D-14's exclude-and-continue behavior. Hazard membership
on these paths is decided solely by the (B) `rules.json` lookup, per row. On
the **train** path, `schema.py` may validate hazard codes against config's
known set up front (§2.1), since there is no artifact to defer to and a
malformed code there is a genuine input error.
Rationale: critique Deliverable-3 P-Q3 found hazard normalization specified
nowhere in `PLAN.md` (the toy normalizes before every lookup) and an
ordering wrinkle where §6's Step 0 family lookup precedes the unseen-hazard
check yet is undefined for an unknown code. User accepted the proposed fix and
both open-question defaults. Checked against the full ledger: reinforces D-23
(`rules.json` as sole serve-time hazard authority), D-3/D-11/D-18 (fail closed;
"known" ≡ enumerated required cell — now literally equal to "in `rules.json`"),
D-22/D-14 (unknown → failures/excluded, not abort), D-2 (normalization mirrors
the toy). No conflict found.
Touches: `PLAN.md` §2.1 (schema module normalizes the `hazard` column via the
toy's `normalize_hazard`, and does not reject unknown hazards on the predict/
evaluate path), §3 step 2/4 (train-time normalization before cell
enumeration), §4 (`rules.json` contains exactly the artifact's trained
hazards, not the full config universe), §6 (Step 0 restated as the unified
`rules.json` hazard-known + family lookup; normalization named); `schema.py`,
`rules.py`/`model.py` (single normalization point; `rules.json` build/read).
Note (2026-07-25, D-26 amendment, integration audit finding C-1): D-26's
blank-ground-truth-label check (a data-defect error on a to-be-measured
evaluate row) is now governed by this decision's authority split too — the
family-aware "is this hazard enablement-only?" half of that check is a **per-row**
determination against the frozen `rules.json` family map (not an up-front
`schema.py` rejection, and not installed config), and it runs only on rows that
survive D-14's exclusion, so an unknown hazard is excluded per (B) above rather
than promoted to a whole-run abort by a blank label. This decision's "`schema.py`
does not reject unknown hazards on the predict/evaluate path" is preserved
unchanged; D-26's amendment simply moves its own family-aware validation onto the
per-row `rules.json` path this decision already defines. See D-26's 2026-07-25
amendment.

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-5):**
`model.py`'s `save` writes `rules.json`'s `trained_hazards` and
`hazard_family` map from `classifier.trained_hazards` (every hazard `fit`
enumerated at least one required-component cell for) — never the full
config hazard universe. Forcing-function test confirms
`set(rules_json["hazard_family"].keys()) == set(trained_hazards)` exactly
after a save/load round-trip. The unified Step-0 lookup this decision
describes (`hrc-predict`'s single `rules.json` lookup for hazard-known +
family) is still not built — that is IS-7's job, over the predict pipeline.

<a id="d-28"></a>
## D-28: A wholly-skipped component is surfaced at train and load time, not one serve-row at a time
Date: 2026-07-23
Status: locked
Decision: Resolves critique Deliverable-3 P-Q4. Per D-5's amendment "skipped"
is always a **whole-component** condition (if a component's nonzero or high
label is single-class across the training corpus, every cell of that component
is skipped together), so the only degenerate states are a wholly-skipped
**Enablement** or a wholly-skipped **Legitimization**. D-18 makes their blast
radius very different: Enablement is required for *every* hazard, so a
wholly-skipped Enablement makes the artifact able to score **nothing**;
Legitimization is required for every hazard *except* the enablement-only
family, so a wholly-skipped Legitimization leaves the artifact fully usable for
an enablement-only (`prv`/`sxc_prn`) workload and inoperable for the rest.
D-5's own note establishes either state is a data-quality-level degeneracy
ordinary training is not expected to hit — essentially always a defect, never
a normal config.

Three surfacing mechanisms, so the condition is visible before serve time
rather than discovered one failing row at a time:
1. **Manifest rollup `skipped_components`** (new field, §3 step 5 / §4):
   `hrc-train` records the list of wholly-skipped components (`[]` in the
   normal case, e.g. `["legitimization"]`). This is a denormalized rollup of
   `thresholds.json`'s per-cell `status` (which remains authoritative, D-5);
   it exists so the load-time check is O(1) and human-visible.
2. **Train-time behavior:**
   - A wholly-skipped **Enablement** → `hrc-train` **hard-fails** (non-zero
     exit, no deployable artifact), because Enablement is required for every
     hazard (D-18) and there is no workload the artifact could serve (open
     question 1, user-accepted).
   - A wholly-skipped **Legitimization** → `hrc-train` **warns prominently and
     still writes** the artifact, recording it in `skipped_components`; the
     artifact stays valid for an enablement-only-hazard workload (open
     question 2, user-accepted).
3. **Load-time behavior (`hrc-predict` / `hrc-evaluate`):** on load, read
   `skipped_components` and emit an up-front warning naming the skipped
   component(s) and the hazard families they make unscoreable, **before**
   processing any rows. This is **always warn-and-continue** (open question 3,
   user-accepted): it introduces **no new batch-abort**. Per-row handling is
   unchanged — a row needing a skipped required cell still routes to
   `failures.csv` (predict, D-22) / is excluded from metrics (evaluate, D-14),
   exactly as D-20/D-5 already specify. In a mixed batch the scoreable rows
   (e.g. enablement-only hazards when Legitimization is skipped) are still
   served.
Rationale: critique Deliverable-3 P-Q4 found that nothing in §3 step 5, §4, or
§6 gated a wholly-skipped-component artifact — `hrc-train` wrote it and exited
0, `hrc-predict` loaded it fine, and the defect surfaced only as a per-row
failure at serve time, even though §4's per-cell `status` field exists for
exactly this class of concern. User accepted the proposed fix and all three
open-question defaults. Checked against the full ledger: reinforces D-5 (the
whole-component skip is surfaced earlier, its meaning unchanged and skipped
cells still never served), is justified by D-18 (why a skipped Enablement is
fatal but a skipped Legitimization only narrowing), and does **not** conflict
with D-22/D-14 — the load-time check is a warning, not an abort, and per-row
failures still route exactly as before; the one hard-fail is at train time,
which D-22/D-14 do not govern. D-3/D-11/D-20's per-row fail-closed serve
behavior is untouched. No conflict found.
Touches: `PLAN.md` §3 step 5 (manifest gains `skipped_components`; train-time
hard-fail on skipped Enablement, warn+write on skipped Legitimization), §4
(manifest field list), §5 (`hrc-evaluate` load-time warning), §6
(`hrc-predict` load-time warning; note that per-row handling is unchanged);
`hrc-train`/`model.py` (compute the rollup, apply the train-time gate),
`cli/predict.py`/`cli/evaluate.py` (load-time warning).

**Implementation slice landed (2026-07-25, `VERIFICATION.md` IS-6, train-time
half only):** built directly into `model.py`'s `fit`, right after each
component's cell-fitting loop. A wholly-skipped **Enablement** raises a new
`WhollySkippedEnablementError` immediately (before Legitimization's loop even
runs, since there is no deployable classifier to keep building toward); a
wholly-skipped **Legitimization** emits a `warnings.warn(..., UserWarning)`
and `fit` returns normally. **Load-time behavior (`hrc-predict`/
`hrc-evaluate` warning on a loaded artifact's `skipped_components`) is still
not built** — there is no predict/evaluate pipeline yet (IS-7). **Cross-check
finding, fixed in passing, not a new decision:** two IS-4/IS-5 tests
(`test_model_fit.py`, `test_model_artifact.py`) had used a single-class-
**Enablement** fixture to exercise D-5's per-cell skip-marking mechanism in
isolation, predating this decision's implementation — once this gate landed,
that exact fixture started raising instead of just marking cells skipped.
Fixed by switching those two tests to a single-class-**Legitimization**
fixture instead (D-5's marking mechanism is component-symmetric, so the
substitution preserves each test's original intent); a new, dedicated test
file (`test_model_train_gate.py`) now covers the Enablement-hard-fails /
Legitimization-warns-and-writes distinction directly. Full suite green: 99
tests (was 96), zero regressions.

<a id="d-29"></a>
## D-29: `hrc-train` raises the natural, unpolished error on a blank ground-truth label it cannot convert to an ordinal int
Date: 2026-07-25
Status: **superseded-by [D-46](#d-46)** (2026-08-03). D-46 selects this entry's
own option 2. The deliberate `hrc-train`/`hrc-evaluate` asymmetry recorded
below is no longer accepted; the two now match.
Decision: When `model.py`'s `fit` encounters a blank `legitimization_value`
(or, symmetrically, a blank `enablement_value`) on a row that survives
D-1/D-4/D-18's filtering and therefore should have real ground truth to
convert to an ordinal int, no bespoke error handling is added. The row's
blank value is left to surface as Python's natural
`ValueError: invalid literal for int() with base 10: ''` from the `int()`
conversion inside `fit`, aborting the training run with that message.
Rationale: this gap was surfaced by `VERIFICATION.md` IS-4 (`model.py`'s
`fit`, 2026-07-25): a non-enablement-only hazard row with a blank
`legitimization_value` is a data defect `schema.py` deliberately does not
reject at load time (D-26's family-aware blank-label judgment is scoped to
`hrc-evaluate` only, since `schema.py` cannot resolve hazard family without
an artifact); no locked decision previously said what `hrc-train` itself
should do about it. Three options were posed: (1) leave the natural
`ValueError` as-is; (2) raise a clearer, purpose-built error naming the
offending row(s), mirroring D-26's `hrc-evaluate` precedent of erroring on
this exact condition; (3) silently exclude such rows from Legitimization's
fit, treating it as a fourth D-4-style exclusion. **User chose option 1**
("Choose option 1, leave the natural ValueError as-is"). This means
`hrc-train` and `hrc-evaluate` are **deliberately asymmetric** on this point
— `hrc-evaluate` raises a purpose-built, clearly-worded error (D-26) while
`hrc-train` raises Python's unpolished built-in one for the same underlying
defect — an accepted asymmetry, not an oversight, since the user picked the
simplest option knowing the alternative existed.
Touches: no code change — `src/hazard_classifier/model.py`'s `fit` (built in
IS-4) already produces exactly this behavior; this decision ratifies it as
intentional rather than leaving it an unresolved gap. Closes the IS-4
Awaiting User finding in `STATUS.md`. No conflict with D-26 (a different code
path, `hrc-evaluate`, whose own error contract is unchanged) or any other
locked entry.

<a id="d-30"></a>
## D-30: `is_safe_ground_truth`'s literal encoding is the exact strings `"safe"`/`"unsafe"`
Date: 2026-07-25
Status: locked
Decision: The `is_safe_ground_truth` CSV column's non-blank value is exactly
the string `"safe"` (parses to `True`, i.e. is-safe) or `"unsafe"` (parses to
`False`) — a case-sensitive exact match, not a fuzzy/case-insensitive parse
and not a numeric (`"1"`/`"0"`) or Python-boolean-string (`"True"`/`"False"`)
convention. Any other non-blank value is a data-defect parse error.
Rationale: this was an Open Question since D-26's 2026-07-25 correction note
(surfaced while building `schema.py`, IS-1): "`is_safe_ground_truth`'s actual
literal encoding... is not pinned by any locked decision anywhere in this
ledger... flagged for a future fix-proposal once a real labeled CSV sample
exists or the user specifies it directly." It stopped being a deferrable
nicety and became a hard blocker once `VERIFICATION.md` IS-8 (`hrc-evaluate`'s
metric assembly) needed to actually parse this column into the boolean
`metrics.py`'s `final_label_metrics` requires as its first argument — so it
was asked directly rather than guessed at (a wrong guess would silently
invert every final-label metric). User answered directly: `"safe"`/`"unsafe"`.
Touches: `schema.py` still validates only column **presence** at load
(D-26's corrected scope is unchanged — family-agnostic structural checks
only, no format validation); the new parse function (`parse_is_safe_ground_
truth`, `schema.py`) is IS-8's concern, invoked once per surviving row before
building `metrics.py`'s `final_label_metrics` inputs; no other locked entry
references this column's format, so no conflict.

<a id="d-31"></a>
## D-31: `HazardResponseClassifier.score(rows)` never raises on a hard-fail row; every row gets a per-row result entry
Date: 2026-07-25
Status: locked
Decision: The in-process Python API `HazardResponseClassifier.score(rows)`
(`PLAN.md` §6, §11 item 5) never raises on an individual row's hard-fail
condition (D-3/D-11/D-20's unseen-hazard/skipped-cell cases). It returns
exactly one result entry per input row: either a successful `ScoredRow`, or
a failure marker naming the reason (`unseen_hazard` /
`skipped_or_absent_cell`, the same two-way distinction D-14/D-22/D-25
already use). A caller always gets a same-length list back and inspects
each entry — there is no exception path for a single bad row in the batch.
Rationale: this was an explicitly pre-flagged Open Question (`PLAN.md` §11
item 5, critique `critiques/2026-07-23-deliverable-3.md` P-N2): "the
in-process Python API's behavior on a hard-fail row — raise, or return
per-row error entries alongside successes — is not settled... deferred
until the API is actually built." `VERIFICATION.md`'s IS-11 entry explicitly
instructed "build the API and surface that decision, do not invent it," so
it was asked directly rather than resolved silently when IS-11 was reached.
User chose the never-raise, per-row-entries option (offered as the
recommended default, given it matches the same never-abort philosophy
`predict_rows`/`evaluate_rows` (D-14/D-22) already established for the
batch paths) over raise-on-first-failure or a caller-chosen flag. Checked
against the full ledger: consistent with D-14/D-22's shared "same predicate,
consequence differs by caller" pattern — `score`'s consequence is now a
third variant (return a marker) alongside D-14's exclude and D-22's
route-to-failures-output, not a new predicate. No conflict found.

**Concurrency (also named an open question in `PLAN.md` §11 item 5, not
separately resolved by this decision):** whether `score` is safe to call
concurrently from multiple threads remains unverified — this decision only
settles the single-row error contract, not thread-safety. Documented as an
unverified-not-guaranteed note in `model.py`'s own docstring, not tested or
assumed either way.
Touches: `model.py` (`HazardResponseClassifier.score`, `RowResult`
dataclass); `PLAN.md` §11 item 5 (resolved, one open sub-question —
concurrency — remains and is documented as such, not answered).

<a id="d-32"></a>
## D-32: `rule_reasons` gains a reason string for D-4's forced-zero short-circuit only, not D-18's not-required short-circuit
Date: 2026-07-25
Status: locked
Decision: `score_row` emits a new `rule_reasons` entry when a component is
forced to `0` under D-4 (an empty response, or an Enablement response that
is entirely prompt-repetition with no authored continuation). D-18's
`not_required` short-circuit (Legitimization absent for `prv`/`sxc_prn`)
does **not** get a reason string.
Rationale: this was critique P-N1 (`critiques/2026-07-23-deliverable-3.md`):
the toy's three fixed `rule_reasons` strings don't all survive production's
control flow (D-18 makes one unreachable, D-4's short-circuit runs before
the rule stage and makes another unreachable), and it was undecided whether
D-4/D-18's short-circuits should emit reason strings of their own so the
field stays explanatory. Inspecting `score_row` (`model.py`) showed the two
cases are not symmetric: D-18's `not_required` already leaves
`legitimization_predicted: None` in the output row, which fully explains
itself with no reason string needed. D-4's `score_zero`, by contrast,
leaves `enablement_predicted`/`legitimization_predicted` at a plain `0` —
indistinguishable in `predictions.csv` from the model genuinely predicting
0, since `component_effective` isn't one of `PREDICTIONS_COLUMNS`. Only
D-4's case is a real, currently-unexplained ambiguity; adding a string for
D-18 as well would be redundant. User chose the recommended option (D-4
only) over adding both or neither.
Touches: `model.py`'s `score_row` (the `action == "score_zero"` branch,
`model.py` ~line 686); `PLAN.md` §6 (`rule_reasons` vocabulary, once
enumerated).

**Implementation slice landed (2026-07-25).** The string is per-component
(`f"{component}_zeroed_no_effective_sentences"` — e.g.
`"enablement_zeroed_no_effective_sentences"`), not one generic string,
matching the existing disclaimer string's own component-naming convention
and reflecting that the two components hit this branch for slightly
different underlying reasons (Enablement via prompt-repetition-only-or-empty,
Legitimization via genuinely-empty only). 2 tests in
`tests/unit/test_model_score_row.py` (127 total, zero regressions): a new
assertion on the existing IC-1(a) trace test confirming both the D-4 and
D-19 reason strings coexist in one row's `rule_reasons`; a new dedicated
test (`test_score_zero_emits_reason_string`, using `"hte"` specifically so
D-19's disclaimer rule can't also be contributing) isolating D-4's string
alone and confirming a normally-scored row's `rule_reasons` stays empty.

<a id="d-33"></a>
## D-33: `component_metrics`'s `qwk` reports `null` (not a raw float) when Cohen's kappa is undefined, matching `auc`'s existing convention
Date: 2026-07-25
Status: locked
Decision: When `cohen_kappa_score` returns `NaN` (single-class `y_true` or
`y_pred` — the same degenerate-population condition `_safe_auc` already
guards against), `component_metrics`'s `qwk` field reports `None` (→ JSON
`null`) instead of the raw `NaN` float.
Rationale: this was critique DI-N1
(`critiques/2026-07-23-decision-introspection.md`): D-13's held-out/
in-sample split makes small, sometimes single-class populations the normal
case, and D-17 lists `auc`/`qwk` as plain schema fields with no null
convention. `_safe_auc` (`metrics.py`) already detects this exact condition
for `auc` and returns `None`; `qwk` had no equivalent guard, so a bare
`NaN` token (plus an `UndefinedMetricWarning`) would flow straight into
`metrics.json` once the `hrc-evaluate` CLI writes it — valid to Python's
own `json.load` (`allow_nan=True` by default) but not strict JSON, breaking
`jq` and other strict parsers downstream. User chose the recommended option
(convert to `null`, matching `auc`) over leaving it as a raw `NaN` or using
a string sentinel.
Touches: `metrics.py`'s `component_metrics` (needs an `np.isnan` guard on
`cohen_kappa_score`'s result, mirroring `_safe_auc`'s shape); `PLAN.md` §5
(the `qwk` schema field, D-17 item 4).

**Implementation slice landed (2026-07-25).** Added `_safe_qwk` (mirroring
`_safe_auc`'s shape — compute, then convert `NaN` to `None`) and wired it
into `component_metrics` in place of the raw `float(cohen_kappa_score(...))`
call. Per the user's explicit choice, `cohen_kappa_score`'s
`UndefinedMetricWarning` on the degenerate case is left firing, not
suppressed — this decision covers the `null` conversion only, not the
warning. 1 new test in `tests/science/test_metrics.py`
(`test_component_metrics_qwk_is_none_for_single_class`, 127 total, zero
regressions): reuses the exact fixture from the existing
`test_component_metrics_auc_is_none_for_single_class` test, confirmed
directly (not assumed) to also make `cohen_kappa_score` return `NaN`.

<a id="d-34"></a>
## D-34: IS-9 closed via a different real dataset; the toy's literal reference-number match is superseded, not achieved
Date: 2026-07-25
Status: locked
Decision: IS-9 (`VERIFICATION.md`) is closed. Its original claim — the
implementation's frozen-fit metrics match `security-evaluator`'s own
published held-out reference numbers (`PLAN.md` §8.2: Legitimization exact
0.645503/AUC 0.808393/QWK 0.522552; Enablement exact 0.592040/AUC
0.782737/QWK 0.411720) — required the toy's own raw labeled CSVs
(`inputs/neyman_review_queue.csv`, `inputs/keys/batch_*_key.csv`), which are
deliberately excluded from that repo and were never located in this
environment. Rather than leave IS-9 open indefinitely pending data that may
never surface, the user supplied a different real, correctly-shaped labeled
dataset (859 rows, 15 hazards, 30 seed prompt groups —
`jb_1.0_1003_ground_truth_items_for_riki_eval.csv`) and directed running the
full built pipeline against it instead.

`scripts/run_real_data_is9.py` derived `seed_prompt_id` from
`seed_prompt_text` grouping (every seed group maps to exactly one hazard,
confirmed by inspection, so the grouping is a faithful D-1 holdout unit),
then ran `preprocess/*` → one batched real `embed_sentences` call (19,556
segments, `BAAI/bge-base-en-v1.5`) → `fit` (`--holdout-fraction 0.2` at the
seed-group level, 6/30 groups held out, 270/859 rows) → `evaluate_rows`.
Zero rows excluded (no unseen hazards, no skipped cells). Held-out results:
Enablement exact 0.619/AUC 0.759/QWK 0.421 (n=270); Legitimization exact
0.551/AUC 0.678/QWK 0.329 (n=227); final-label F1 0.836/precision
0.815/recall 0.858 (n=155). In-sample results are near-perfect as expected
(training fit, not a generalization signal). Full report:
`scripts/is9_real_data_metrics.json`.

**What this closes and what it doesn't:** this confirms the full pipeline
runs correctly end-to-end on real, non-synthetic, non-toy data and produces
plausible, non-degenerate held-out metrics — in the same rough range as the
toy's own published numbers, though not a byte-for-byte match, since this is
a genuinely different dataset from a different source. It does **not**
confirm the toy's literal reference numbers — that specific claim is
**superseded, not achieved**. D-2's amendment (in-sample threshold/centering
bias, quantified against the toy's numbers) and D-16's Finding B (AUC
provenance, same dependency) both remain genuinely unresolved for the same
underlying reason and are not expected to resolve unless the toy's original
files surface.
Rationale: user chose to close IS-9 on this basis (offered as one of three
options: leave IS-9 open indefinitely / close it as satisfied by adjacent
data / treat the adjacent-data run as a separate untracked item) rather than
block the project on data that has been unavailable throughout this entire
effort and may never arrive. If the toy's own raw CSVs do surface later,
re-running the literal parity comparison would still be worthwhile — this
decision doesn't rule that out, it stops the project from waiting on it.
Touches: `VERIFICATION.md` (IS-9's entry marked closed; D-2/D-16 coverage-matrix
rows annotated as superseded, not resolved); `scripts/run_real_data_is9.py`,
`scripts/is9_real_data_metrics.json` (new, kept as the evidence record).

<a id="d-35"></a>
## D-35: CLI-skin architecture — one shared feature-building function; `save()`'s signature grows to hold the manifest extras
Date: 2026-07-25
Status: locked
Decision: Two design forks for the `hrc-train`/`hrc-evaluate`/`hrc-predict`
CLI skin (`PLAN.md` §2.2/§3/§5/§6, the only remaining unbuilt piece per
`VERIFICATION.md`), proposed with explicit tradeoffs before any code was
written:
1. **Shared feature-building.** The "raw CSV rows → preprocess → embed →
   pool → `component_features`/`component_effective`/
   `disclaimer_sentence_count`" pipeline is extracted into one new function,
   `embed.build_component_features(df, *, model_name, revision=None,
   allow_download=False)`, and `HazardResponseClassifier.score`
   (`model.py`, IS-11) is refactored to call it internally instead of
   inlining its own copy. All three CLIs call this same function — `fit`'s
   inputs (`hrc-train`), `evaluate_rows`'s inputs (`hrc-evaluate`),
   `predict_rows`'s inputs (`hrc-predict`, used instead of `score` so the
   CLI's feature-building matches train/evaluate exactly, not a fourth
   independent copy).
2. **Manifest extras.** `save()`'s signature (`model.py`) grows new optional
   keyword arguments for the `PLAN.md` §3 step 5 fields `save`'s own
   docstring already flagged as deferred here — code version, hyperparameters,
   UTC timestamp, training-file hash, training row/hazard counts — defaulting
   to omitted so existing `save`/`load` tests are unaffected. `save()` stays
   the single writer of `manifest.json`, rather than `cli/train.py` re-opening
   and patching the file after the fact.
Rationale: (1) without extraction, the same pipeline would exist inline in
`score()` and independently again in the CLI layer (a second, or with
`scripts/run_real_data_is9.py`'s throwaway copy counted, third
implementation) — directly against this project's own repeated "one
predicate, checked once" discipline (D-14, D-27, D-3's unified lookup).
Touching `score()`'s internals is a real edit to already-tested code, not a
new-file-only change, but its existing IS-11 tests are the regression guard,
not a rewrite of them. (2) two writers of `manifest.json` (the CLI patching
what `save()` already wrote) risks the two falling out of sync in a way one
writer with a wider signature cannot. Both were offered with an explicit
alternative (leave `score()` untouched and duplicate the pipeline in the
CLI; CLI patches `manifest.json` post-`save()`) and the user chose the
recommended option in both cases.
Touches: `embed.py` (new `build_component_features`); `model.py`
(`HazardResponseClassifier.score` refactored to use it; `save()`'s signature
extended); `src/hazard_classifier/cli/` (new package: `_common.py`,
`train.py`, `evaluate.py`, `predict.py`); `examples/sample_input.csv` (new,
for §8.1's mocked-BGE CLI smoke tests); `pyproject.toml`
(`[project.scripts]`).

**Implementation slice landed (2026-07-25) — Queue item 1 (shared refactor +
`hrc-train`) only; `hrc-evaluate`/`hrc-predict` remain queued.** Built
`embed.build_component_features(prompt_texts, response_texts, *, model_name,
revision=None, allow_download=False)`: takes parallel text sequences (not a
`DataFrame`, to avoid giving `embed.py` a pandas-shaped dependency it didn't
already have) rather than `Component` as a `Literal` import from `model.py`
(dict keys are plain `str`, matching `rules.py`'s existing convention of
untyped `component: str` parameters at this layer, avoiding a new
`embed.py`→`model.py` import edge). Refactored `HazardResponseClassifier.
score` to call it instead of inlining its own copy — this simplified `score`
itself considerably (the per-row segment-range bookkeeping collapses into
indexing `build_component_features`'s own output), not just moved code
around. `save()`'s signature grew the six optional manifest-extras kwargs
exactly as specified, merged into the manifest dict only when non-`None`.

New `src/hazard_classifier/cli/` package (`__init__.py`, `_common.py` —
`add_allow_download_flag`, `fatal` (clean stderr + exit(1) on a domain
error), `warn_if_skipped_components` (the load-time D-28 warning `PLAN.md`
§5/§6 required but nothing had built yet) — and `train.py`). `hrc-train`
computes the manifest extras `save()` couldn't (code version via
`importlib.metadata.version`, a `hashlib.sha256` of the raw input file
bytes, `datetime.now(timezone.utc).isoformat()`, per-hazard row counts via
`value_counts` cast to plain `int` for JSON-safety) and catches
`SchemaError`/`WhollySkippedEnablementError` into `fatal()` rather than a
raw traceback. `pyproject.toml` gained `[project.scripts]` for all three
commands (safe to declare before `evaluate.py`/`predict.py` exist —
console-script entry points aren't validated until invoked) and
`examples/sample_input.csv` (12 rows, `hte`/`prv`, full §2.1 schema).

3 new tests in `tests/unit/test_cli_train.py` (131 total, zero
regressions): a full `hrc-train` run (BGE mocked via monkeypatching
`embed.embed_sentences`, per §8.1) produces every artifact file, a correct
manifest (all six new extras present and correctly shaped/typed), and an
artifact `model.load()` can actually reload; `--holdout-seed-fraction`
produces a non-empty recorded split; a schema-invalid input CSV exits
cleanly via `fatal()` rather than a raw traceback. Also refactored
`tests/integration/test_pipeline_mechanism.py` to call
`build_component_features` directly instead of duplicating the inline
pipeline a second time in the test itself, and added a new
`test_manifest_extras_omitted_by_default_and_present_when_supplied` to
`tests/unit/test_model_artifact.py` proving every pre-D-35 caller still
gets the exact prior manifest shape when the new kwargs are omitted.
Verified beyond the mocked unit tests: installed the package
(`pip install -e .`), confirmed `hrc-train --help` resolves via the real
console-script entry point, and ran a real, non-mocked `hrc-train` against
`examples/sample_input.csv` with the real cached BGE model — produced a
valid, correctly-shaped `manifest.json` end-to-end.

**Implementation slice landed (2026-07-25) — Queue item 2 (`hrc-evaluate`)
only; `hrc-predict` remains queued.** Built `cli/evaluate.py` (`hrc-evaluate
--model-dir --input --output-dir [--allow-download]`) using item 1's
`build_component_features` and `_common.warn_if_skipped_components`
unchanged, plus two new `metrics.py` functions per `PLAN.md` §5's explicit
"best-effort, correctable" output schema: `flatten_metrics_report` (the
`metrics.csv` long format -- one row per `(population, section, metric,
value)`, nested values like `confusion_counts`/`components.*` flattened
into a dot-separated `metric` path; the three run-level D-13/D-14 fields
use the sentinel population `"overall"`) and `render_summary` (`summary.txt`,
`None`-safe via a small `_fmt` helper, since `auc`/`qwk`
(D-16/D-33) and every `final_label_metrics` field on an empty population
are genuinely `None`, not always floats). Both kept in `metrics.py`, not
inline in the CLI file, so they stay unit-testable without argparse/file
I/O. `evaluate.py` catches `SchemaError` (bad input CSV) and
`BlankGroundTruthError` (D-26, a measured row's blank label) into
`fatal()`.

7 new tests (138 total, zero regressions): `tests/unit/test_cli_common.py`
tests `fatal`/`warn_if_skipped_components` directly via a duck-typed
`SimpleNamespace` classifier stand-in, rather than only indirectly through
a full CLI run (a gap left over from item 1, closed here); `tests/unit/
test_cli_evaluate.py` (train → evaluate against `examples/sample_input.csv`,
BGE mocked, reusing item 1's fixture/mocking pattern) confirms all three
output files, the correct `n`/`n_rows`/exclusion shape (including
Legitimization's D-15 exclusion of the 6 `prv` rows), `metrics.csv`'s exact
column set, `summary.txt`'s D-13 no-holdout warning text; a second test
with `--holdout-seed-fraction 0.5` confirms both populations appear when a
holdout exists; a third confirms `BlankGroundTruthError` exits cleanly via
`fatal` rather than a raw traceback. **Verified beyond the mocked unit
tests:** ran a real, non-mocked `hrc-train --holdout-seed-fraction 0.3` then
`hrc-evaluate` via the installed console scripts against the real cached
BGE model -- inspected `metrics.json`/`metrics.csv`/`summary.txt` by hand,
all correctly shaped, including a real (not synthetic) `auc=null` on a
genuinely degenerate 2-row held-out Legitimization population, confirming
D-33's null-conversion path fires correctly outside the unit-test fixture
that motivated it.

**Implementation slice landed (2026-07-25) — Queue item 3 (`hrc-predict`),
the last item in D-35's queue. Closes the entire CLI skin.** Built
`cli/predict.py` (`hrc-predict --model-dir --input --output-dir
[--allow-download]`) reusing item 1's `build_component_features` +
`_common.warn_if_skipped_components` unchanged, and `model.predict_rows`/
`to_predictions_frame`/`to_failures_frame` (already built, already tested,
IS-10) rather than `HazardResponseClassifier.score` — this CLI's
feature-building step is now byte-identical in code path to `hrc-train`'s
and `hrc-evaluate`'s, not a fourth implementation. No new logic needed
beyond the argparse/file-I/O skin itself: `predict_rows` never raises (D-22),
so the only `fatal()` paths are a bad `--model-dir` (`FileNotFoundError`
from `load`) and a schema-invalid `--input` (`SchemaError`).

4 new tests in `tests/unit/test_cli_predict.py` (142 total, zero
regressions): a full mocked-BGE run against `examples/sample_input.csv`
(ground-truth columns present but confirmed ignored, D-24) scores all 12
rows with zero failures, `prv` rows correctly blank on
`legitimization_predicted` (D-18), `seed_prompt_id` absent from both
outputs (D-25's amendment); a mixed-batch test appends one genuinely
unseen-hazard row and confirms it alone routes to `failures.csv` with
`failure_reason="unseen_hazard"` while the other 12 still score normally —
`len(predictions) + len(failures) == len(input rows)`, the real D-22
forcing function, not just "some failure happened"; two `fatal()` paths
(schema-invalid input; missing `--model-dir`). **Verified beyond the
mocked unit tests:** a real, non-mocked `hrc-train` then `hrc-predict` via
the installed console scripts against the real cached BGE model —
inspected `predictions.csv`/`failures.csv` by hand: correct `predicted_label`
values, `prv` rows' `legitimization_predicted` genuinely blank in the raw
CSV (not just `None` in a Python object), `failures.csv` present with a
header and zero data rows.

**This closes D-35 entirely and the whole `VERIFICATION.md` backlog** — the
CLI skin was the last unbuilt piece of the plan; nothing else is queued.

<a id="d-36"></a>
## D-36: Pooling mode is mean-only; `max`/`mean_max` are not implemented
Date: 2026-07-25
Status: locked
Decision: `embed.pool_response_vector` implements mean pooling only. The
toy's `"max"`/`"mean_max"` pooling modes (experimental research variants) are
not ported and no mode parameter is exposed to any caller.
Rationale: retroactively documenting `PLAN.md` §11 open question 2 ("keep
`mean` as the production default unless eval says otherwise"), which was
resolved by what actually got built (`embed.py`, `VERIFICATION.md`
`embed.py`/IS-9 slices) rather than through a fix-proposal pass, leaving no
ledger entry — a gap relative to this project's own META_PLAN.md process.
No eval result ever argued for `max`/`mean_max`, so there was nothing
prompting a deviation from the stated default; this entry locks that default
as the actual, sole implementation rather than leaving it as an unresolved
open question that reads as still-live.
Touches: `PLAN.md` §11 item 2 (mark resolved, cross-reference this entry);
`src/hazard_classifier/embed.py` `pool_response_vector` (already landed, no
code change from this entry).

<a id="d-37"></a>
## D-37: Artifact serialization is `.npz` + JSON only; no `joblib` dependency
Date: 2026-07-25
Status: locked
Decision: `model.py`'s `save`/`load` serialize the artifact as `heads.npz`
(numpy) plus `thresholds.json`/`rules.json`/`manifest.json` (plain JSON) —
no `joblib`, no pickle, anywhere in the codebase or `pyproject.toml`.
Rationale: retroactively documenting `PLAN.md` §11 open question 4
("proposal: numpy `.npz` + JSON (no pickle); confirm `joblib` is not
required by downstream consumers"), which was resolved by what actually got
built (`VERIFICATION.md` IS-5) rather than through an explicit
fix-proposal/confirmation pass — the "confirm... not required by downstream
consumers" half of that open question was never put to the user before this
entry.
Touches: `PLAN.md` §11 item 4 (mark resolved with the caveat above);
`src/hazard_classifier/model.py` `save`/`load` (already landed, no code
change from this entry).

**Open Question resolved (2026-07-25):** user confirmed, in direct answer to
this entry's own flagged question: "No downstream consumer of the artifact
format has actually confirmed a `joblib` requirement." This settles the
question as currently posed — there is no known, stated requirement for
`joblib` compatibility from any consumer today — so the shipped format
(`.npz` + JSON, no `joblib`) stands unreserved rather than provisionally.
This is a statement of the current absence of any such requirement, not a
guarantee no future consumer will ever raise one; if one does, this
decision would need to be reopened at that point, not silently worked
around.

<a id="d-45"></a>
## D-45: Unfittable operations are explicitly unavailable; no constant-probability substitute
Date: 2026-08-03
Status: locked
Approved by: Riki and Kurt, 2026-08-03
Supersedes: D-5

Decision: If training cannot produce a valid operation, mark that operation
unavailable. Do not create a constant-probability substitute or otherwise
invent an operation result. An artifact may still serve its other available
operations; a request that requires the unavailable operation fails under
D-3's no-fallback rule.

Rationale: this reverses D-5, which preserved the research prototype's
constant-probability substitution (a degenerate 0.5-centered threshold search)
and made it safe by marking the cell `"skipped"` so it would never be served.
The substitute is fitted, serialized, and never used — wasted work whose only
effect is to make an unavailable operation look like a fitted one in the
artifact. `SCIENCE.md`'s not-evaluated posture wants the opposite: a component
without a valid fit reports itself as unavailable rather than producing a
value nobody may consume. Rejected alternative: keep D-5 and rely on the
`"skipped"` marker, which works but leaves the artifact carrying values that
D-3 and D-11 exist to prevent anyone from reading.

Provenance: this text originates in Riki's commit `333f86d`, which rewrote D-5
in place under the attribution "Modified: 2026-08-03 by Kurt and Riki." It was
briefly recorded as `proposed` while that attribution was unverified — the
2026-08-03 joint meeting record lists seven confirmed canonical requirements
and this was not among them. Both halves are now on record: the attribution is
Riki's own, and Kurt accepted it directly on 2026-08-03. The reversal is a
scientific change to how training handles an unfittable operation, so it is
carried as its own numbered entry rather than as an in-place edit to D-5.

Touches: `PLAN.md` §3 step 4 (cell enumeration) and §4 (artifact format) —
both **absorbed** 2026-08-03; `ARCHITECTURE.md` Artifact format
(**absorbed**); `heads.py`, `model.py`.

**Implemented 2026-08-03** (`STATUS.md` Recently Completed; retired queue
item 6). Specifications were
updated first, then the code. What landed, beyond the literal removal of the
`constant_probability` field: `BinaryHead.predict_proba` now **raises**
`UnavailableOperationError` on a `"skipped"` head rather than returning
anything, and `center_mean` joins `coef`/`intercept` as `None` there — with no
probability to center, it had no meaning either. Two consequences were found
while implementing and are now specified rather than left implicit:

1. **The threshold search cannot run for a skipped cell.** D-5 ran it against
   the substitute and its own DR-6 note called that "wasted, not incorrect,
   work"; removing the substitute removes the input, so `nonzero_threshold`
   and `high_threshold` are `null` and `threshold_metrics` is `{}`. This is a
   visible `thresholds.json` shape change.
2. **`heads.npz`'s field set is now status-dependent** — a skipped head stores
   only `mean`/`scale`/`status`. `load` reads `status` first and derives the
   rest via `BinaryHead.array_fields`, since asking for absent keys would
   `KeyError`.

The `"skipped"` marker itself is unchanged, so D-3 and D-11's fail-closed
guarantees rest on exactly what they always did. Artifacts written before this
change carry the removed field and will not load; the baseline is pre-staging
with no external consumer, so no migration path was built.

Boundary: D-45 governs what training does when a fit is impossible. D-3
governs what scoring does when it meets an unavailable operation.

<a id="d-46"></a>
## D-46: `hrc-train` raises a purpose-built error on an unconvertible blank ordinal label
Date: 2026-08-03
Status: locked
Approved by: Kurt
Supersedes: D-29

Decision: When `model.py`'s `fit` encounters a blank `enablement_value` or
`legitimization_value` on a row that survives D-1/D-4/D-18's filtering and
therefore should carry real ground truth, `hrc-train` raises a clear,
purpose-built error naming the offending row or rows. This replaces D-29's
choice to let Python's `ValueError: invalid literal for int() with base 10: ''`
surface from the `int()` conversion inside `fit`.

Rationale: D-29 posed three options and selected option 1 (leave the natural
`ValueError`), explicitly accepting an asymmetry with `hrc-evaluate`, which
raises a purpose-built error for the same underlying data defect (D-26). This
entry selects that entry's own **option 2** — "raise a clearer, purpose-built
error naming the offending row(s), mirroring D-26's `hrc-evaluate` precedent
of erroring on this exact condition" — removing the asymmetry. Rejected
alternative, unchanged from D-29: option 3, silently excluding such rows from
the fit as a fourth D-4-style exclusion, which would hide a data defect rather
than report it.

Touches: `PLAN.md` §3 step 1 (**absorbed** — the blank-ordinal-ground-truth
paragraph); `src/hazard_classifier/model.py` `fit`; `cli/train.py`.

**Implemented 2026-08-03** (`STATUS.md` Recently Completed; retired queue
item 5). `fit` raises
`BlankOrdinalGroundTruthError` naming the offending `prompt_uid`s, truncated
past 20 so a wholly-blank column still yields a readable message. `cli/train.py`
routes it through `_common.fatal`, because an error whose purpose is
readability should not arrive as a traceback. The class is deliberately
separate from `BlankGroundTruthError` (D-26's `hrc-evaluate` error): the two
fire on different row populations, so a caller catching one must not silently
catch the other. Scope is the point and is covered by tests: the error must
stay silent on an enablement-only hazard's blank Legitimization label (D-18),
on a holdout row (D-1), and on a D-4-excluded row — all three confirmed as
forcing functions by sabotaging the check and watching them fail.

Boundary: D-46 governs `hrc-train`'s error on a blank ordinal label. D-26
governs `hrc-evaluate`'s handling of the same defect and is unchanged. D-30
governs the separate `is_safe_ground_truth` column's encoding.

<a id="d-47"></a>
## D-47: A standalone limitations document gates staging and release-version assignment
Date: 2026-08-03
Status: locked
Approved by: Kurt, 2026-08-03. **Riki's concurrence assumed on Kurt's
direction (2026-08-03), not confirmed on record** — see the approval-state
note at the top of this file. Originated as critique finding C-6 in
`critiques/2026-08-02-science-contract-branch.md`.

Decision: Before a model is promoted to staging or assigned a release point
version, its standalone, version-specific limitations document must be
published. Three narrowings are part of the decision, not commentary on it:

1. **The pre-staging exemption has a floor.** A pre-staging prototype is
   exempt from maintaining a separate versioned document, not from disclosure:
   it must still state known statistical and validity limitations inline in
   its `README.md`. Pre-staging prototypes may not make production,
   scientific-success, or quality claims their evidence does not support.
2. **Required contents are tied to rules that already exist**, so the document
   cannot be discharged by generalities. It must enumerate every component
   reported as *not evaluated* under `../SCIENCE.md` §Evidence and outputs —
   for Release 1.1 that is the hazard, narrative, and refusal placeholders —
   and state, for every published metric, the uncertainty estimate and the
   method that produced it, per that section's Estimability paragraph.
   *(**The three-item list above went stale on 2026-08-04**: it is now five.
   Text left as written, per `META_PLAN.md` §1's retire-in-place rule — see
   the Correction at the end of this entry, and take the current list from
   `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6.)*
3. **It discharges D-2's and D-8's disclosure obligation**, through whichever
   artifact applies: the `README.md` before staging, the limitations document
   after. Those two entries required their statistical warts to be documented
   rather than silently shipped; this decision says where that documentation
   lives at each stage, and does not weaken the requirement.

Rationale: C-6 found the as-built limitations record deleted while `README.md`
still asserted it existed. The underlying question was whether a pre-staging
prototype owes a full limitations inventory. Kurt's position was that it does
not — the current baseline has not reached staging and is expected to be
replaced — but the first draft of that position removed the disclosure
entirely, which would have discarded D-2's and D-8's requirement rather than
relocating it. Narrowing 1 is what separates the two: the gate moves to
staging, the obligation does not disappear before it. Narrowing 2 exists
because a limitations document that omits the placeholders shipping in 1.1
would mislead by omission while satisfying the letter of the rule. Rejected
alternative: requiring the standalone document at every stage, which was the
status quo ante and which Kurt judged disproportionate for a prototype with no
consumer.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 exit criteria (**absorbed**);
`README.md` §Current baseline risks (satisfies narrowing 1 today); D-2 and
D-8 (their disclosure obligation is discharged here, so both are now fully
baseline-only); `STATUS.md` retired queue item 1.9.

Boundary: D-47 governs *when* a limitations document is required and what it
must contain. It does not define the per-outcome success criteria that decide
whether a component may be called scientifically successful — those are an
external input from the Standards team, still outstanding. It also does not
govern `../SCIENCE.md`'s not-evaluated reporting rule, which stands on its own
and which this decision only points at.

**Correction (2026-08-04): narrowing 2's Release 1.1 inventory is five items,
not the three named above.** The entry's "the hazard, narrative, and refusal
placeholders" was accurate when written on 2026-08-03. [D-50](#d-50) and
[D-51](#d-51) then added two more on 2026-08-04 — prompt repetition's
exact-only scope, and decoding's stubbed failure trigger — so the enumeration
went stale rather than wrong. Corrected in the specification that carries this
decision (`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 exit criteria), which now also
states the rule that generates the list rather than only its members: **every
component `ARCHITECTURE.md` §7 marks `partial` or `placeholder` belongs in the
inventory.**

This is recorded as a note rather than an edit to narrowing 2's text, per
`META_PLAN.md` §1's retire-in-place discipline: the original enumeration is
the record of what was known on 2026-08-03, and overwriting it would erase
that. Cite the specification for the current list, not this entry.

The two additions are the easy ones to miss, which is why the correction says
so explicitly: unlike a placeholder, a `partial` component runs, returns
results, and looks healthy in any output. Found by an absorption check on
2026-08-04 — D-50 and D-51 named this obligation in their own `Touches` lines,
but nothing a PR 6 author would actually read had been updated.

**Second correction (2026-08-04, PR 2 slice B verification sweep): narrowing
1's README disclosure did not extend to the 1.1 evaluator.** This entry's
original `Touches` line claimed `README.md` §Current baseline risks
"satisfies narrowing 1 today." That was true only for the pre-staging
**baseline**'s two statistical warts (D-2, D-8), which is all that section
has ever documented. It said nothing about the five 1.1 evaluator shortfalls
narrowing 2 already enumerates, because PR 1 — the work that actually put
those shortfalls into running code — landed after this entry was written on
2026-08-03. Narrowing 1's pre-staging exemption reaches the 1.1 evaluator
too: it has not reached staging either, so the same inline-disclosure
obligation applies to it, separately from the baseline's.

Closed by adding a `## Release 1.1 evaluator status` section to `README.md`,
kept distinct from `## Current baseline risks` rather than folded into it —
the baseline and the 1.1 evaluator are two different pre-staging prototypes
with different failure surfaces, and conflating their risk disclosures would
blur which one a given wart belongs to. The section deliberately does not
name the current placeholder/partial components by hand: it states the
*kind* of limitation and points at `ARCHITECTURE.md` §7 as the one place the
current membership lives, so this section does not itself become a second
copy of the list requiring its own upkeep as PR 3 through PR 5 land. Touches:
`README.md` (**absorbed** — new section added).

**Third correction (2026-08-05, PR 4's closing sweep): the enumeration went
stale a second time, in three places at once.** Narrowing 2's inventory in
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 listed five component items and four
non-component ones. Checked row by row against `ARCHITECTURE.md` §7 and
`README.md`, three things were wrong:

1. **Disclaimer detection's coverage and precision** ([D-70](#d-70)) reached
   `README.md` and §7.2 when slice B landed, but never the inventory itself —
   even though D-70's own `Touches` line named this obligation, which is
   exactly how the 2026-08-04 correction above was missed too.
2. **L/E scoring was never in the inventory at all**, though it has shipped
   `partial` since PR 1 and emits no three-class distribution. §7's prose said
   "three partials" while its own table marked four; a writer enumerating from
   the sentence rather than the rows would drop it. Both are corrected.
3. **Phase B1's unreachable-bullets entry still carried the superseded single
   reason** ("no detector sets those flags"), which is false of the disclaimer
   bullet — stage 7 is a real detector. `README.md` and PR 4's closing note
   were corrected on 2026-08-05; this third copy was missed then.

**The recurring lesson, now on its third instance:** naming an obligation in a
ledger entry's `Touches` line does not discharge it. Both prior corrections and
all three of these were found by reading the specification against the code and
against the other documents that restate it — never by re-reading the ledger.
The inventory's generating rule (*every component §7 marks `partial` or
`placeholder`*) is what to run; the enumerated list is a convenience that goes
stale each time a PR lands. Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6
narrowing 2 (**absorbed**); `ARCHITECTURE.md` §7; `README.md`.

<a id="d-48"></a>
## D-48: The unchanged-output requirement binds the implementation being refactored, not a standard-conforming rebuild
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record** — same footing as [D-47](#d-47); see the
approval-state note at the top of this file. Raised from implementation, in
`STATUS.md`'s Awaiting User, while building PR 1 slice 1C.

Decision: `../SCIENCE.md` §Evidence and outputs' "architecture-only work must
also prove unchanged text, features, scores, probabilities, labels, and
failures on the same inputs" is measured against **the refactored
implementation's own prior output**, captured before the work starts. It does
not require a new implementation built to a superseded requirement's
replacement to reproduce the old numbers. For Release 1.1 PR 1 specifically:
the pre-staging baseline owes byte-identical output, and the new 1.1 pipeline
owes conformance to `../SCIENCE.md`'s rules instead.

Rationale: PR 1's goal, its exit criterion, and the `../SCIENCE.md` sentence
above all read, literally, as though one requirement covered both paths. Slice
1C established by construction that no implementation can satisfy that reading:
three requirements the 2026-08-03 joint meeting and the queue item 1 review had
already approved deliberately change the numbers — prompt repetition removed
from the working text a Legitimization model reads (`../SCIENCE.md`
§Prompt-repetition detection, where the baseline removed nothing for
Legitimization at all), a prompt-only response fixed at L1/E0 by phase B1
(displacing D-4's prompt-only-through-the-head rule), and a qualifying
Specialized Advice disclaimer fixing final L in final integration (displacing
D-19's pre-threshold adjustment). Each is already recorded as baseline-only in
this ledger's scope notes. So the strict reading does not impose a hard
standard on the rebuild; it makes PR 1 unclosable while requiring the rebuild
to reproduce behavior the standard retired. The conflict was latent rather than
introduced: it became visible only when both paths existed in one repository.

Rejected alternative: requiring the 1.1 pipeline to match the baseline's
numbers, and reopening the three displaced requirements to make that possible.
This inverts the authority `META_PLAN.md` §1.1 sets — the selected Assessment
Standard governs behavior, and a repository decision may not replace an
Assessment requirement — and would trade three approved improvements for a
parity number with no scientific claim behind it. Also rejected: deleting the
requirement, which would drop the protection it exists to give (a refactor
silently altering behavior) on the one path where it applies cleanly and is
already verified.

Touches: `../SCIENCE.md` §Evidence and outputs (**absorbed** — carries the
general rule and the both-obligations-live-at-once case);
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 1 goal and exit criteria (**absorbed** —
scoped to the baseline); `PR1_EXECUTION_PLAN.md` §3's verification table;
`tests/golden/` and `tests/integration/test_baseline_parity.py` (the goldens
this decision names as the measurement); D-4 and D-19 (already baseline-only —
this entry records the consequence of that, and changes neither).

Boundary: this governs only what the unchanged-output requirement is measured
against. It does not weaken any other exit criterion, does not license an
unexplained scoring change on either path, and says nothing about whether the
1.1 pipeline is *correct* — that rests on `../SCIENCE.md`'s own rules and, for
any quality claim, on the Standards team's per-outcome criteria (D-47's
boundary).

<a id="d-49"></a>
## D-49: The 1.1 evaluator artifact is deferred out of PR 1 to PR 5/PR 6
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record** — same footing as [D-47](#d-47) and
[D-48](#d-48). Raised from implementation while closing PR 1 slice 1C.

Decision: PR 1's exit criterion "artifact save and load preserve component and
rule versions" is **deferred**. No 1.1 evaluator artifact writer or loader is
built in PR 1. The artifact format is finalized in PR 5, alongside the model
structure queue item 2 selects, and its round-trip test is PR 6's — where
`RELEASE_1_1_QUEUE_PROPOSAL.md`'s exit criteria already require tests covering
"artifact round trips." PR 1 instead carries the weaker property its own
scope supports, which slice 1C built and tested: the run context's component
selections **and versions**, plus the rule version, survive the pipeline into
the `results.jsonl` view (`ARCHITECTURE.md` §11).

Rationale: `PR1_EXECUTION_PLAN.md` §3 assigned this criterion to "slice 1C
round-trip test," but slice 1C's own deliverables list never included an
artifact writer, so the plan asked for a test of something it did not schedule
anyone to build — a latent inconsistency that surfaced only when the slice was
closed. Of the two ways to resolve it, building the artifact now was rejected:
`ARCHITECTURE.md` §10 defines the artifact's `model/` payload as "a format the
selected structure defines," and that structure is queue item 2's, still
blocked on the Standards team's fixed dataset. More decisively, **nothing in
PR 1 saves or loads a 1.1 artifact** — the pipeline receives its classifier by
direct injection — so a writer built now would have no reader, could not be
round-tripped against a real consumer, and would very likely be rewritten once
item 2 lands.

**Stated against this decision, because it is true and a later reader needs
it:** the manifest fields this criterion actually names — component
implementations, versions, and rule version — are *not* themselves blocked by
item 2. `ARCHITECTURE.md` §10 deliberately versions the manifest so the model
payload can change without breaking the surrounding contract, so that half
could have been built now. The deferral rests on the absent consumer and the
duplicated PR 6 coverage, not on an impossibility. If PR 5 slips far enough
that an evaluator artifact is needed before it, this entry should be revisited
rather than cited.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 1 exit criteria (**absorbed** —
criterion marked deferred and pointed at PR 5/PR 6) and PR 6 exit criteria
(already requires artifact round-trip tests; unchanged);
`PR1_EXECUTION_PLAN.md` §3's verification table; `ARCHITECTURE.md` §10 (the
format this defers, unchanged); `STATUS.md` queue item 2 (the entry condition
that gates the model structure).

Boundary: this defers *when* the 1.1 evaluator artifact is built and
round-tripped. It does not change `ARCHITECTURE.md` §10's specification of
that format, does not affect the **baseline** artifact (built, tested, and
round-tripped since IS-5), and does not relax D-23 — whenever the 1.1 artifact
does land, family and hazard-support lookups still read the frozen artifact
rather than installed config.

<a id="d-50"></a>
## D-50: Release 1.1 ships exact-only prompt-repetition detection
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record** — same footing as [D-47](#d-47) through
[D-49](#d-49). Raised as entry-gate question Q1 in `PR2_EXECUTION_PLAN.md`.

Decision: Release 1.1's prompt-repetition component detects **exact**
normalized-substring repetition only. Summarized and closely-paraphrased
repetition are not implemented in 1.1. The component's maturity stays
`partial` and the shortfall is a disclosed gap, named in the release's
limitations document (D-47 narrowing 2). Performance is measured later and
the scope revisited then if the gap proves material.

Rationale: three documents disagreed. `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2's
work list said "detect exact, summarized, and closely paraphrased";
`../ARCHITECTURE.md` §7.1 scoped 1.1 to exact-only with the shortfall recorded
as deliberate; and `PR1_EXECUTION_PLAN.md` §4 asserted both at once ("PR 2's
work" *and* "1.1 ships exact-only as partial"), which cannot hold because
PR 2 is a 1.1 PR. `../SCIENCE.md` §Prompt-repetition detection requires all
three and is not amended by this entry — the requirement stands, and 1.1
simply does not meet all of it yet, which is what `partial` means. This
resolves the conflict in favor of §7.1, the most recent explicit scoping.
Two reasons beyond recency: a paraphrase detector's quality cannot be claimed
without the fixed human-labeled ground truth still blocking queue item 2, so
building one in PR 2 yields an unvalidatable component; and shipping a
similarity heuristic under a requirement worded "closely paraphrased" would
blur what the stated maturity means — the same objection §7.1 already raised
against reusing the baseline's `partial_contiguous`.

Rejected alternative: implementing all three in PR 2. Rejected on the
evaluation gap above, not on difficulty. Also rejected: promoting the
component to `working` on the strength of exact-only, which would claim
conformance the component does not have.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2 work item and exit criteria
(**absorbed**); `PR1_EXECUTION_PLAN.md` §4 (contradictory line corrected);
`../ARCHITECTURE.md` §7.1 (already stated this; now cites this entry);
`src/hazard_classifier/evaluator/components/repetition.py` (unchanged — it
already implements exactly this scope).

Boundary: this governs *which* repetition types 1.1 detects. It does not
amend `../SCIENCE.md`'s requirement, does not license removing material that
is not repeated prompt text, and says nothing about when the gap should be
closed — that follows from the measurement this decision defers to.

<a id="d-51"></a>
## D-51: The decoding-failure trigger is stubbed for 1.1; the decoder is `partial`
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised as entry-gate question Q2 in
`PR2_EXECUTION_PLAN.md`.

Decision: The decoder always returns a result; its worst case is the
un-decoded text. The **failure-detection trigger is a stub that always
reports success** (`_detect_decoding_failure`), so no decoding failure is
detectable in 1.1. Three consequences are part of the decision, not
commentary on it:

1. **`flags.decoding_failed` is recorded as `not_evaluated`, never
   `not_detected`.** Writing `not_detected` would claim the component looked
   and found nothing; it never looked. This is `../ARCHITECTURE.md` §3.1's
   three-valued flag distinction and §6's placeholder rule applied to a
   check inside an otherwise-running stage.
2. **The decoder's maturity is `partial`, not `working`.**
   `../SCIENCE.md` §Decoding's success criterion has two halves — an accurate
   rendering, *and* a failure flag plus error when it cannot produce one —
   and only the first is built.
3. **No integrator consequence is defined**, because the flag cannot fire.
   `../SCIENCE.md` assigns the consequence to final integration; that choice
   is deferred with the trigger and must be made when the trigger is built.

Rationale: the trigger was unspecified at both ends — nothing defined when
decoding has failed (`best_readable_view` always returns its best-scoring
candidate and has no notion of failing), and nothing defined the consequence.
Choosing a trigger means setting a threshold on real obfuscated data this
project does not have, where a false positive costs a scored result. Kurt's
call was to stub it rather than guess, and revisit with data. Consequence 1
is what keeps the stub honest: without it the record would assert a negative
finding no component produced, which is exactly the failure mode slice 1B's
placeholder forcing function exists to catch. Consequence 2 follows from
`../SCIENCE.md`'s own success criterion; the alternative — calling the decoder
`working` — would overclaim, and `RELEASE_1_1_QUEUE_PROPOSAL.md`'s release
outcome is corrected rather than left asserting unqualified "working
decoding."

Rejected alternative: inventing a trigger now (a low-`english_score` or
residual-encoded-material heuristic). Rejected as an unvalidatable threshold
whose false positives silently cost results. Also rejected: leaving
`decoding_failed` at `not_detected`, which is the status quo the stub
replaces and which misrepresents an unrun check as a negative result.

Touches: `src/hazard_classifier/evaluator/components/decoding.py`
(**absorbed** — the stub, the `not_evaluated` flag, and `partial` maturity);
`tests/unit/test_evaluator_decoding_stub.py` (pins all three);
`../ARCHITECTURE.md` §7 row 2 (**absorbed**);
`RELEASE_1_1_QUEUE_PROPOSAL.md` release outcome and PR 2 work item
(**absorbed**); D-47 narrowing 2 (this gap belongs in the limitations
document's not-evaluated inventory).

Boundary: this governs the *failure-detection* half of decoding only. The
decode path itself is unchanged and still never drops content or empties the
working text. It does not amend `../SCIENCE.md` §Decoding, which continues to
require the full behavior 1.1 does not yet provide.

<a id="d-52"></a>
## D-52: The ambiguous-reference recording requirement is removed from Release 1.1
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised as entry-gate question Q3 in
`PR2_EXECUTION_PLAN.md`.

Decision: PR 2's work item "record when the prompt resolves an ambiguous
reference" is **removed** from Release 1.1, not deferred to a later PR. No
flag, field, or component is built for it.

Rationale: the requirement had no specification behind it and no producer. It
appeared only in `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2's work list;
`../SCIENCE.md` §Technical restrictions *permits* using the prompt to resolve
ambiguous references but requires no record of having done so;
`../ARCHITECTURE.md` §4's `Flags` has no field for it; and no 1.1 component
resolves an ambiguous reference in the first place — decoding uses the prompt
as context for substitution maps and repetition uses it for matching, neither
of which is disambiguation. Building a flag with no specification, no
producer, and no consumer is speculative work, and a flag that no component
ever sets would sit permanently at `not_evaluated`, adding a field to every
record to describe something that never happens. Removed rather than deferred
because there is nothing concrete to defer: a future need would arrive with
its own requirement and shape.

Rejected alternative: deferring it to a later PR on D-49's footing. Rejected
because D-49 defers a thing that is specified and will certainly be built
(the artifact); this has neither property, and carrying it forward as a
perpetual to-do would misrepresent an unspecified idea as scheduled work.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 2 work list (**absorbed** — item
removed); `PR2_EXECUTION_PLAN.md` §2 Q3 and slice D (both closed);
`../ARCHITECTURE.md` §4 `Flags` (unchanged — deliberately gains no field).

Boundary: this removes a *recording* requirement. It does not restrict how a
component may use the prompt — `../SCIENCE.md` §Technical restrictions still
permits disambiguation — and does not prevent a future release from adding
the capability with a real specification behind it.

<a id="d-53"></a>
## D-53: Run-entry hazard/scope validation mechanism
Date: 2026-08-04
Status: locked
Approved by: implemented as `PR3_EXECUTION_PLAN.md` §3.1 proposed, with no
conflict found against `../ARCHITECTURE.md` §2's literal text and no change
needed to the proposed shape (`STATUS.md` PR 3 slice A, 2026-08-04) — recorded
per the plan's own instruction (§4) to record the mechanism if it holds up
through implementation.

Decision: `../ARCHITECTURE.md` §2 names three rejection conditions but not the
exact function shapes or how they interact. This is the mechanism slice A
built:

- `open_run(config, registry, supported_hazards)` checks conditions (2) and
  (3) once, run-wide, before returning a `RunContext`: every hazard in
  `config.hazard_scope` must be a member of `supported_hazards` (the
  artifact's frozen hazard set — D-23; callers pass `classifier.trained_
  hazards`, not a new artifact loader — D-49 unaffected), and every selected
  `(stage, implementation)` pair must be registered.
- A separate function, `validate_supplied_hazard(supplied_hazard,
  run_context)`, checks condition (1) once per response, before
  `pipeline.run_pipeline` runs for it — not from inside `pipeline.py`, which
  stays free of scientific/configuration decision logic. It normalizes the
  supplied value via `schema.normalize_hazard` (D-27: strip and
  hyphen-to-underscore, no case folding — carried for 1.1) and then requires
  membership in `run_context.hazard_scope`.
- Because `open_run` already validates `hazard_scope` against the artifact,
  condition (1)'s three-way "missing, unrecognized, or outside scope"
  phrasing collapses to two checks in `validate_supplied_hazard`: blank, or
  not a member of `hazard_scope`. Every hazard actually in scope is, by
  construction, both a real code and one the artifact supports.
- `hazard_scope` is validated against the artifact once in `open_run`, never
  per response — re-checking it per response would be wasted, repeated work
  and would blur which check produced a given `RunRejectedError`.

Rationale: this is an implementation choice within what `../ARCHITECTURE.md`
§2 already requires, not a re-derivation of already-locked ground —
recorded because implementing it exactly as proposed found no better shape
and no conflict, which is the plan's own bar for whether it earns an entry.
Rejected alternative: re-validating `hazard_scope` against the artifact on
every response instead of once at `open_run` — rejected as the wasted-work,
ambiguous-error-source trap `PR3_EXECUTION_PLAN.md` §3.1 named explicitly.

Touches: `src/hazard_classifier/evaluator/run.py` (`open_run`,
`validate_supplied_hazard`); `tests/unit/test_evaluator_run.py` (both new
checks, isolated); every existing `open_run` caller, updated to pass
`supported_hazards` (`tests/unit/test_evaluator_scoring_pipeline.py`,
`test_evaluator_pipeline.py`, `test_evaluator_pr2_text_flow.py`,
`tests/integration/test_evaluator_real_bge.py`).

Boundary: this entry is provenance for *how* conditions (1) and (2) are
checked. `../ARCHITECTURE.md` §2 states *what* must be rejected and still
governs on any conflict (`META_PLAN.md` §1.1) — this entry does not restate
or reinterpret it.

<a id="d-54"></a>
## D-54: Narrative and refusal detection ship as placeholders; PR 4's exit criteria are scoped to what 1.1 delivers
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised as a decision-debt sweep before
PR 4's execution plan was written.

Decision: both stage 5 (narrative) and stage 6 (refusal) remain **pass-through
placeholders** in Release 1.1, leaving their flags at `not_evaluated` exactly
as `../ARCHITECTURE.md` §6 requires. `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 4's
exit criteria are rewritten to state what 1.1 actually delivers, and the two
components join the D-47 limitations inventory as **absent components**.

Two readings were considered and rejected:

- **Stubs that always report a negative** (`not_detected` rather than
  `not_evaluated`). Rejected because it buys no behavior and costs record
  fidelity. Phase B1 tests `== "detected"`, so `not_detected` and
  `not_evaluated` fall through identically and scoring is unchanged either
  way. What changes is that the record would assert "I looked and found no
  refusal" for a component that never looked — the exact failure mode D-50
  and D-51 exist to prevent, and it would silently drop both components from
  D-47's inventory, which keys off `not_evaluated`. It would also require
  amending `../ARCHITECTURE.md` §6 ("a placeholder is never silently
  equivalent to a negative result") and §3.1, whose three-valued `FlagState`
  exists for precisely this distinction.
- **Building refusal as a `partial` rule/lexicon detector.** Nothing external
  blocks it — unlike narrative, which is blocked on Standards-team examples
  this release is not requesting. Rejected for 1.1 to keep the release's
  unevaluated surface enumerable rather than growing it with a component that
  has no ground truth, no approved criterion, and no way to report anything
  but *not evaluated* against `../SCIENCE.md` §Refusal detection.

Rationale: PR 4's exit criteria as written ("benign narrative is removed only
where the Standards ground truth permits", "refusal removal preserves any
following assistance") presuppose working components and cannot be met by a
placeholder. This is the situation D-50 and D-51 resolved for PR 2 — scope the
criterion, name the shortfall, keep the gap visible — and PR 4 gets the same
treatment rather than closing with criteria recorded as unmet.

**Consequence, recorded so it is not rediscovered.** With narrative and refusal
both placeholders, phase B1's **first, second, and fourth bullets can never
fire from a real detection** in Release 1.1. Refusal and narrative flags are
never set by a detector; the disclaimer flag is set only by stage 7's partial
implementation. Every exhaustion path therefore lands on prompt-repetition or
on the blank-payload branch, which sets the refusal flag itself. B1's bullet
*ordering* — load-bearing under `../SCIENCE.md` §Evidence and outputs, and
required to be tested there — is consequently exercised only by
hand-constructed flag combinations in 1.1, never by the pipeline.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 4 exit criteria (**absorbed**);
`../ARCHITECTURE.md` §7 rows 5 and 6, §12 (benign-narrative boundary);
`src/hazard_classifier/evaluator/components/narrative.py` and `refusal.py`
(both unchanged — this entry confirms their current behavior is correct);
D-47's Release 1.1 inventory, which grows from five items to seven.

Boundary: this entry governs Release 1.1 only. It does not amend
`../SCIENCE.md` §Narrative detection or §Refusal detection, both of which
continue to require the full behavior 1.1 does not provide, and it does not
decide whether 1.2 builds these as models or as rules.

<a id="d-55"></a>
## D-55: The Enablement model consumes the `working` view; disclaimer stripping is not adopted in 1.1
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: the L and E models both read `TextViews.working` in Release 1.1 —
disclaimer text is **not** stripped from model input. Stage 7 continues to
publish `named["disclaimer_stripped"]` alongside it, so the comparison remains
a configuration change and not a rewrite.

Rationale: `../ARCHITECTURE.md` §12 lists "which text view E consumes" (C-4) as
explicitly undecided, and `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 4 requires the
choice be settled by comparison on a fixed, human-labeled evaluation set. That
set does not exist and is an outstanding Standards-team request, so PR 4 cannot
close without an interim default. Retaining the disclaimer is the default that
changes nothing: `../SCIENCE.md` phase C already fixes final L at L0 for a
qualifying Specialized Advice disclaimer, and the standard states plainly that
a disclaimer does not lower E. Stripping would therefore alter model input to
achieve an effect the fixed rules already achieve.

Rejected alternatives: (1) stripping by default, echoing the baseline's D-19
pre-threshold adjustment — rejected because D-19's mechanism is explicitly
superseded for 1.1 and reinstating its instinct at a different layer would
double-count the disclaimer; (2) making the view a required, defaultless
configuration field — rejected because it relocates the same unmade decision
into every run profile rather than resolving it.

Touches: `../ARCHITECTURE.md` §5 (**absorbed** — the default is stated there)
and §12 (the item moves from undecided to decided-with-a-deferred-comparison);
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 4 work list and exit criterion "a disclaimer
never reduces Enablement"; D-47's inventory, which gains the un-run comparison
as a shortfall.

Boundary: this fixes the 1.1 **default**, not the answer. The comparison
`../SCIENCE.md` and PR 4 call for is deferred, not cancelled, and the published
`named["disclaimer_stripped"]` view is what keeps it cheap to run once fixed
human-labeled data exists.

<a id="d-56"></a>
## D-56: Release 1.1 gains PR 7, the evaluator runner, sequenced before PR 6
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: a new **PR 7 — evaluator runner, input schema, and batch entry
point** is added to `RELEASE_1_1_QUEUE_PROPOSAL.md` and is sequenced **before
PR 6**, despite the higher number. It owns the 1.1 input schema, the CLI and
in-process entry points, the batch runner, and the `failures.csv` view.

It is numbered 7 rather than inserted as a new 6 because
`PR1_EXECUTION_PLAN.md`, `PR2_EXECUTION_PLAN.md`, `PR3_EXECUTION_PLAN.md`,
`STATUS.md`, and this ledger already cite PR 6 by number. `META_PLAN.md` §5's
never-renumber rule exists for exactly this: renumbering would silently
re-point every existing citation. **Work order comes from stated sequencing,
not from the number** — the same rule the queue itself follows.

Rationale: no PR's work list creates a way to *run* the 1.1 evaluator. The
package exposes only the three baseline CLIs; `evaluator/views.py` records that
`failures.csv` "needs the batch-level runner that does not exist yet"; and
PR 6's exit criteria require tests covering "CLI and Python interfaces" and
`failures.csv`, both of which presuppose a runner. This is a gap in the
approved queue, not a footnote to PR 6.

Rejected alternatives: (1) folding it into PR 6 — rejected because it would
make one PR both build and validate the thing it is meant to validate, and
PR 6 is the release-validation gate; (2) shipping an in-process Python API only
and scoping PR 6's CLI criterion away under the D-50/D-51 treatment — rejected
because a runner is a real deliverable of a "runnable evaluator" release, and
scoping away the criterion would understate what 1.1 is missing.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` (**absorbed** — new PR 7 section and a
sequencing note on PR 6); `STATUS.md` queue item 4; `../ARCHITECTURE.md` §11
(`failures.csv` gains an owner); `pyproject.toml` `[project.scripts]`, which
gains an entry point in PR 7.

Boundary: this entry creates and sequences the PR. It does not decide the input
schema, the CLI's name or flags, or the run-profile format — those are PR 7's
own work, constrained by D-57 for hazard scope and by `../ARCHITECTURE.md` §11
for the view contracts.

<a id="d-57"></a>
## D-57: A run's hazard scope is derived from the selected artifact's frozen supported set
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: Release 1.1 defines no universal Jailbreak hazard list. A run's
`hazard_scope` **defaults to the selected artifact's frozen supported hazard
set** (`rules.json`, D-23), and the resolved set is recorded in the run context
and every output record. An explicit narrower scope may still be supplied; a
supplied scope wider than the artifact supports remains an `open_run` rejection
under condition (2), unchanged.

Rationale: `../SCIENCE.md` §Hazard scope configuration deliberately refuses to
hard-code one universal list and requires that "every named run or profile must
record its exact active set, which must be supported by the selected artifact."
Deriving the default from the artifact satisfies both halves: the active set is
always recorded, and it is supported by construction, so the run can never be
rejected for a scope its own artifact cannot serve. Today `hazard_scope` has no
default anywhere in the code, which means **no 1.1 result can be produced until
a caller invents one** — an unstated dependency that would have surfaced as a
PR 7 blocker.

Rejected alternative: hard-coding all thirteen `../SCIENCE.md` §Hazard scope
codes as the 1.1 profile. Rejected because it is the universal list the
standard declines to fix, and because it guarantees an `open_run` rejection
against any artifact trained on fewer hazards — turning a normal configuration
into a failure.

**Accepted cost.** The active hazard set becomes a property of the training
data rather than a declared policy. A hazard absent from training is silently
absent from scope rather than visibly rejected, so the recorded scope is what
makes the difference auditable. This is why the resolved set is recorded rather
than assumed.

Touches: `../ARCHITECTURE.md` §2 (**absorbed** — `RunConfig.hazard_scope` gains
a stated default) and §10; `src/hazard_classifier/evaluator/run.py`
(`RunConfig`, `open_run`); `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7, which builds
the profile handling.

Boundary: this decides the **default and its source**. It does not change
`open_run`'s three rejection conditions (D-53 and `../ARCHITECTURE.md` §2 still
govern those), and it does not decide how a named run profile is expressed on
disk — that is PR 7's.

<a id="d-58"></a>
## D-58: Release 1.1 is a pre-staging prototype; promotion is decided at PR 6
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: Release 1.1 ships as a **pre-staging prototype**. D-47's pre-staging
exemption applies: disclosure is met by the inline `README.md` §Release 1.1
evaluator status section rather than by a separate versioned limitations
document, and 1.1 makes no production, scientific-success, or quality claims.
Whether to promote to staging or assign a release point version — which
triggers D-47's full document — becomes an **explicit PR 6 exit item**.

Rationale: D-47's document requires, for every published metric, the
uncertainty estimate and method the Estimability paragraph mandates. That
method is an outstanding Standards-team request (Ask B) and the metrics
themselves depend on PR 5's model, so the document cannot be completed in 1.1
even if it were required. Deciding the posture now rather than at PR 6 also
means the inventory can be maintained incrementally as each PR adds to it,
instead of being reconstructed at the end.

Rejected alternative: promoting 1.1 to staging and writing the full document.
Rejected as unbuildable on the above, and as a claim the release does not
support — three placeholders, three partials, and multi-hazard correctness
unevaluated.

Touches: `README.md` §Release 1.1 evaluator status (**absorbed** — the
disclosure floor lives there); `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 exit
criteria, which gain the promotion decision as an item; [D-47](#d-47), whose
pre-staging floor this exercises for the first time.

Boundary: this decides Release 1.1's **posture**, not D-47's rule. The
limitations document remains required before any staging promotion or release
point version, and nothing here weakens narrowing 1's floor: a prototype is
exempt from the separate document, never from disclosure.

<a id="d-59"></a>
## D-59: The L/E structure-selection procedure is pre-registered before the evaluation set arrives
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: `STATUS.md` queue item 2's structure comparison is governed by a
**pre-registration document written before the Standards team's fixed
evaluation set exists**. It fixes, in advance: the candidate list across the
seven named axes; the selection rule and the metric it reads; the tie-break;
how many times the fixed evaluation set may be touched; and the model payload
format each candidate implies (closing D-37's open half and D-49's PR 5
finalization). Deviating from it later is permitted but must be recorded as an
amendment with its reason, not made silently.

Rationale: `../SCIENCE.md` requires the evaluator be **unbiased** — "training
and evaluation do not deliberately favor violating or non-violating results" —
and names the equal-treatment of three outcomes an open scientific problem. The
queue and the architecture both name the comparison *axes*; **neither says how
the winner is chosen.** A selection rule written after the label distribution
is visible cannot be shown not to have been shaped by it, and one fixed
evaluation set consumed by an unbounded candidate sweep is burned rather than
held out. Writing the rule now costs nothing — none of it depends on the data —
and is the only point at which the choice is provably uninformed by it.

Rejected alternatives: (1) deferring the procedure until the data lands —
rejected on the above; (2) a nested dev/held-out split carved from the training
data — not rejected on merit but not adoptable unilaterally: it requires the
Standards team's split to permit sub-splitting, so it is a **candidate the
pre-registration must evaluate**, not a decision this entry makes.

Touches: `STATUS.md` queue item 2 (**absorbed** — the entry condition now names
the pre-registration as its first deliverable);
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 work list; `../ARCHITECTURE.md` §10
(artifact payload) and §12 (the L/E structure item);
[D-37](#d-37) and [D-49](#d-49), both of which defer format questions to this
selection.

Boundary: this governs **how the structure is chosen**, not which structure
wins. It does not relax `../SCIENCE.md` §Legitimization Scoring or §Enablement
Scoring, whose per-outcome criteria remain an external Standards-team input
(Ask B), and it does not authorize the comparison to begin before Ask A lands.

<a id="d-60"></a>
## D-60: The Release 1.1 L and E models receive no prompt input
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: the 1.1 L and E models are fitted and scored on **response-derived
working text only**. No prompt text enters model input. `../SCIENCE.md`'s
disambiguation exception is recorded as **unexercised in 1.1**, not as
unavailable.

Rationale: `../SCIENCE.md` §Legitimization Training and §Enablement Training
permit prompt context only "unless the Assessment Standard permits prompt
context required for disambiguation" — and **nobody has made the reading of the
v1.4 taxonomy that would say what it permits.** Building to an unmade reading
is speculative; taking the restrictive branch matches §Technical restrictions
("evaluate the response, not the prompt"), keeps PR 5's input surface identical
to what PR 1's wrapper already feeds, and leaves the exception available to a
release that has done the reading.

Rejected alternative: reading the vendored v1.4 PDFs now and building the
exception to match. Rejected for 1.1 as scope — it is an authoritative
interpretation call, not an implementation choice, and the release does not
need it.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 work list (**absorbed** — the
"exclude the prompt except where the standard permits" item resolves to
"exclude the prompt"); `../ARCHITECTURE.md` §5 (model input is a named view,
and no view carries the prompt); D-47's inventory, which gains the unexercised
exception.

Boundary: this constrains **model input**. It does not restrict other
components' use of the prompt — decoding uses it for substitution context and
prompt-repetition for matching, both permitted by §Technical restrictions and
both unaffected.

<a id="d-61"></a>
## D-61: Release 1.1 makes no concurrency claim; the evaluator's contract is single-threaded
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: the Release 1.1 evaluator is documented as **single-threaded per
process**. PR 7's batch runner parallelizes at the process level if it
parallelizes at all. `../SCIENCE.md` §Evidence and outputs' concurrency
verification requirement is met by testing and documenting *that* contract —
that a single-threaded run is correct and reproducible — not by claiming
thread-safety.

Rationale: the requirement has been unmet and unmeetable since the baseline;
D-31 records `HazardResponseClassifier.score`'s concurrency safety as
"genuinely unverified — documented as such in `score`'s own docstring, not
tested or assumed either way." PR 6's exit criteria list concurrency tests that
cannot be written until the claim exists. A stated single-threaded contract is
testable today, is what the baseline is actually used for, and converts an
open-ended obligation into a bounded one.

Rejected alternative: claiming and verifying thread-safe scoring. Plausible on
its face — `EvaluationRecord` is immutable and the components are stateless —
but the real risk sits in the embedding provider and its torch backend, which
would need genuine multi-threaded tests to support the claim. Not rejected on
merit; rejected as work 1.1 does not need.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 exit criteria (**absorbed** — the
concurrency item names the contract being verified);
`../ARCHITECTURE.md` §6 (the component contract states it);
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7, which builds to it;
[D-31](#d-31), whose unverified note this supersedes in scope for 1.1 while
leaving the baseline's own docstring accurate.

Boundary: this states what 1.1 **claims**, not what is true. Nothing here
asserts the evaluator is thread-unsafe; it asserts that thread-safety is not
claimed, not tested, and not to be relied on.

<a id="d-62"></a>
## D-62: The continuous violation score is out of Release 1.1
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: Release 1.1 produces **no continuous violation score**. PR 6's
return-value list drops the "an approved continuous score, when available"
item, and no record field or view column is built for it.

Rationale: `../SCIENCE.md` §Continuous score requires an approved training
target and threshold before one may be added, and neither exists.
[D-21](#d-21) already dropped it from 1.1 output and deferred it to that
section. What remained was a conditional line in PR 6's returns and in §Evidence
and outputs' results list, which left the release's output contract open on a
component that cannot be built. Closing it explicitly is what lets PR 6's
"every evaluated hazard has exactly one final result or failure" criterion
stand as the complete statement of the output.

Rejected alternative: building the field and leaving it null. Rejected on
D-52's reasoning — a field no component ever populates adds a permanently empty
column to every record to describe something that never happens.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 6 work list and return list
(**absorbed**); `../ARCHITECTURE.md` §11 view contracts (no column);
[D-21](#d-21), whose deferral this completes.

Boundary: this removes it from **1.1**. `../SCIENCE.md` §Continuous score is
unchanged and still governs whenever an approved target and threshold arrive;
the discrete result stays authoritative regardless.

<a id="d-63"></a>
## D-63: Release 1.1 uses out-of-version human ground truth; the Standards request stops gating
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: the Standards team's fixed dataset and per-outcome criteria are
**not expected to arrive**. Release 1.1 builds end to end against the
Jailbreak v1.0 human ground truth already in this repository
(`data/jb_1.0_1003_ground_truth_items_for_riki_eval__with_seed_prompt_id.csv`,
SHA-256 `8fdbec27…22ddf`, 859 rows), and the pipeline is re-run when real data
appears. Queue item 2 and PR 5 are unblocked; `STANDARDS_REQUEST.md` is
retained as the specification of what real data must supply, no longer as a
gate.

**This is not synthetic data and must not be described as such.** Every
`legitimization_value` and `enablement_value` in the source is a human
judgment on the 0/1/2 scale, which is what `../SCIENCE.md` §Scientific
requirements means by human ground truth and what §Evidence and outputs'
AI-only-labels prohibition is aimed at. All fifteen hazard codes are present
and all three classes are populated on both axes. The only constructed
artifact is the *split* (D-64).

What it is **not** is ground truth approved for this standard version. The
labels were made against Jailbreak v1.0; the evaluator targets Assessment
Standard v1.4. Measured compatibility: applying `../SCIENCE.md`'s three
L/E-to-result tables to the human L/E values reproduces the source's own
`is_safe_ground_truth` on **835 of 859 rows (97.2%)**, and the 24
disagreements concentrate exactly where the tables changed between versions —
enablement-only 7.3%, Specialized Advice 7.4%, default family 0.2% (1 of 546).
That figure is evidence the labels transfer well, not that they are ratified.

Rationale: the alternative to building on this data is not building. The asks
had no owner and no answer; `../SCIENCE.md`'s not-evaluated rule already
prevents any component from being called successful without approved criteria,
so proceeding costs no claim the release could otherwise have made. Building
end to end now also converts the eventual data arrival from a research project
into a re-run.

Rejected alternatives: (1) synthesizing labels — rejected outright as the
AI-only-labels prohibition; (2) treating the dataset as a development fixture
with no evidential weight — rejected as discarding real human labels and
misrepresenting the eventual real-data run as a first run rather than a re-run.

Touches: `PREREGISTRATION_LE_STRUCTURE.md` §1 and §7 (**absorbed**);
`STATUS.md` queue item 2 entry condition and §Standards team;
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 entry condition;
`README.md` §Release 1.1 evaluator status; D-47's inventory.

Boundary: this decides **which data 1.1 builds on**. It does not weaken
`../SCIENCE.md` §Evidence and outputs — both models are still reported as *not
evaluated*, because approved per-outcome criteria do not exist and no dataset
choice can create them.

<a id="d-64"></a>
## D-64: The 1.1 split groups on prompt text, not `seed_prompt_id`
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: Release 1.1's train/evaluation split groups on **whitespace-normalized
prompt text**, stratified by hazard, 25% of groups held out. It is frozen,
seeded, and hashed as `data/interim_split_v1.json`, built and re-verified by
`scripts/build_interim_split.py`. [D-1](#d-1) and [D-13](#d-13)'s
`seed_prompt_id` grouping is **baseline-only**.

Rationale: the source has 30 seed prompts and **each maps to exactly one
hazard** — fourteen hazards have a single seed apiece. A seed-grouped holdout
must therefore place an entire hazard wholly in training or wholly in
evaluation, which makes per-hazard evaluation structurally impossible. Prompt
text yields 180 groups, exactly 11 per hazard (26 for `hte`). The frozen split
is 635 fit / 224 dev rows, 48 groups held out, with every hazard and all three
L and E classes present on both sides and zero prompt-group overlap — verified
by the builder, which fails rather than writes if any of those properties
breaks.

**Accepted cost, stated rather than discovered later:** other attack variants
derived from the same seed prompt can appear in both fit and dev, so the split
is mildly optimistic about generalization to a genuinely new seed prompt. That
is the price of per-hazard evaluation existing at all, and it is the first
thing to re-examine when real data arrives.

Rejected alternatives: (1) keeping `seed_prompt_id` and giving up per-hazard
evaluation — rejected because per-hazard judgment is what `../SCIENCE.md`
§Legitimization Training asks analysts to select a structure for; (2) a
row-level stratified split — rejected as strictly worse leakage than the
chosen key for no gain; (3) reporting both a seed-level and a prompt-level
split — not rejected on merit, and worth revisiting when real data makes the
seed-level split viable, but it doubles the reporting surface for a dev-set
number that is not a benchmark result either way.

Touches: `scripts/build_interim_split.py` and `data/interim_split_v1.json`
(**absorbed** — the split is the specification, and the builder verifies it);
`PREREGISTRATION_LE_STRUCTURE.md` §1; [D-1](#d-1) and [D-13](#d-13), both now
baseline-only for their grouping key.

Boundary: this fixes the grouping key and the frozen split for the **interim**
dataset. A real Standards-team dataset arrives with its own split, which
D-63's re-run adopts rather than re-deriving; nothing here dictates how that
one is constructed.

<a id="d-65"></a>
## D-65: Release 1.1 trains and evaluates on attacked prompts only
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: `../SCIENCE.md` §Legitimization Training and §Enablement Training
require training data covering responses to **both naive and attacked
prompts**. The interim dataset is 100% attacked. Release 1.1 ships on attacked
coverage only, and the gap is named in the D-47 inventory rather than filled.

Rationale: `prompt_text` differs from `seed_prompt_text` in every one of the
859 rows, and the naive seed prompts have no responses attached. Supplying
naive coverage would mean generating SUT responses and labeling them — and
`../SCIENCE.md` §Evidence and outputs states plainly that AI-only labels are
not human ground truth. **This is the one Ask A requirement that no
modification of the existing data can honestly satisfy**, which is exactly why
it is recorded as a shortfall rather than engineered around.

Rejected alternatives: (1) generating naive responses and labeling them with a
model — rejected as the prohibited case; (2) generating naive responses for
end-to-end smoke-testing only, excluded from fitting and metrics — not
rejected on merit and still available if PR 7 wants it, but it proves plumbing
rather than closing the requirement, so it does not change this entry; (3)
marking the requirement failed rather than scoped, blocking PR 5's exit
criterion outright — rejected as disproportionate, since the Jailbreak release
being attacked-heavy is defensible on its own terms.

Touches: `PREREGISTRATION_LE_STRUCTURE.md` §7 (**absorbed**);
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 work list ("cover responses to both naive
and attacked prompts"); `README.md` §Release 1.1 evaluator status; D-47's
inventory.

Boundary: this is a **coverage** shortfall against a training requirement, not
a change to it. `../SCIENCE.md` still requires both, and the release that
obtains naive-prompt ground truth discharges it.

<a id="d-66"></a>
## D-66: The interim evaluation slice is a development set; the real evaluation set is reserved
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: the 224-row held-out slice of the interim split is a **development
set**. It may be reused and iterated on freely, and **no number measured on it
is a benchmark result**, a generalization estimate, or reportable under
`../SCIENCE.md` §Evidence and outputs. When a real fixed evaluation set
arrives, structure selection is **re-run as a fresh selection** under a
re-issued pre-registration — not confirmed, and not merely re-fitted. The
interim winner enters that process as one candidate with no privileged status.

Rationale: [D-59](#d-59) required the selection procedure be pre-registered
*before* the evaluation set existed, so the rule could be shown not to have
been shaped by the labels. D-63 makes a dataset visible, which retires that
particular guarantee. Declaring the interim slice a dev set preserves what
D-59 was actually protecting — that the *real* held-out set is touched once,
by a rule fixed in advance — while letting 1.1 be built and exercised now.
Re-selection rather than re-fitting is the load-bearing half: a structure
chosen on v1.0 labels carries their fingerprints, and re-fitting alone would
launder that into a v1.4 result.

Rejected alternatives: (1) treating the interim result as the selection and
re-fitting only when real data lands — rejected on the laundering argument
above; (2) dropping the pre-registration and selecting empirically — rejected
because it gives up the unbiased-selection property for a saving of a few
hours.

Touches: `PREREGISTRATION_LE_STRUCTURE.md` §0 and §5 (**absorbed** — §5 is the
touch budget); `STATUS.md` queue item 2; [D-59](#d-59), whose protection this
relocates rather than removes.

Boundary: this governs **what the interim numbers mean**. It does not restrict
how the interim dev set is used during development, and it does not decide the
real evaluation set's split, which arrives with the data (D-64's boundary).

<a id="d-67"></a>
## D-67: A candidate that cannot score a row is measured without it, with coverage reported
Date: 2026-08-04
Status: locked
Approved by: Kurt, 2026-08-04. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: in queue item 2's structure comparison, a row a candidate cannot
score — a `(target, hazard)` cell that was unfittable, which [D-45](#d-45)
makes *unavailable* — is **excluded from that candidate's metric**, and the
resulting coverage is reported alongside every figure. A paired comparison
between two candidates is computed on the rows **both** could score.

Where this conflicts with `../SCIENCE.md` §Evidence and outputs' requirement
that comparable implementations use the same rows and metrics, **the same-rows
requirement gives way** and the departure is recorded rather than engineered
around. Coverage is reported precisely so the departure is visible in the
numbers instead of hidden inside them.

Rationale: the only ways to keep every candidate on identical rows are to
count an unavailable cell as a wrong answer, or to shrink every candidate's
evaluation to the intersection the weakest one can score. The first invents a
result — it asserts the candidate answered and answered badly, when it did not
answer at all, which is exactly what D-45 removed from this codebase. The
second lets the worst candidate dictate the evidence base for all the others,
and in practice would let the reference `R` — which cannot be the selection
anyway (`PREREGISTRATION_LE_STRUCTURE.md` §2.2) — silently shrink the row set
every real candidate is judged on.

In practice this binds almost entirely on `R` and on `H3` (per-hazard models,
pre-declared as probably underpowered at ~42 fit rows per hazard), which are
the structures with per-`(target, hazard)` cells to lose. A candidate pooled
across hazards has no unfittable cell and reports full coverage.

Rejected alternatives: (1) counting an unavailable cell as incorrect —
rejected as the invented result above; (2) restricting all candidates to the
intersection of every candidate's coverage — rejected as letting the weakest
candidate define the comparison; (3) disqualifying any candidate with less
than full coverage — not rejected on merit and reconsidered if a *selectable*
candidate ever comes in short, but as written it would disqualify `R` for a
property `R` is expected to have, removing the ladder's reference point rather
than measuring it.

Touches: `PREREGISTRATION_LE_STRUCTURE.md` §3 and §8 (**absorbed** — §3 states
the rule, §8 records it as this document's first amendment);
`src/hazard_classifier/experiments/comparison_metrics.py`
(`classification_metrics` coverage fields, `paired_cluster_bootstrap`'s
intersection); [D-45](#d-45), whose unavailable-is-not-wrong principle this
carries into the metrics layer; D-47's inventory, which gains it.

Boundary: this governs **how the comparison measures a candidate that cannot
score a row**. It does not weaken D-45, license any candidate to substitute a
value, or change what `SCIENCE.md` requires of a *reported benchmark result* —
every number in queue item 2 is a dev-set number under [D-66](#d-66) and is not
reportable as a benchmark figure regardless of its coverage.

<a id="d-68"></a>
## D-68: Release 1.1's L and E structure is a flat three-class multinomial softmax, fitted per hazard — selected on a null result
Date: 2026-08-05
Status: locked
Approved by: Kurt, 2026-08-05. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.**

Decision: both targets select **`L1 · W1 · S1 · H3 · V1 · P1`** — a flat
three-class multinomial softmax cross-entropy loss, fitted **per hazard**,
with **no class weighting** beyond the estimator's own balancing, **separate
L and E models**, on the **mean-pooled BGE** representation. The Branching
axis is structurally not applicable: a flat softmax has no nonzero/high head
pair to branch. This fills `../ARCHITECTURE.md` §12's open L/E structure slot
and is what PR 5 builds.

**The finding is null, and it must not be reported as anything else.** The
ablation found **no structure that beats the incumbent `R`** on either target.
No candidate achieved significant separation from `R` by the paired cluster
bootstrap. On **L the selection scores *below* `R`** — macro-F1 **0.4336 vs
0.4840** — and is selected only because it is the sole structure that both
survives the worst-class floor and produces the three-class distribution
`../SCIENCE.md` requires; `R` and every two-head variant are structurally
excluded from selection
(`PREREGISTRATION_LE_STRUCTURE.md` §2.2 and §4's closing rule). On **E** the
`L1+W3` composite led on macro-F1 (0.5358 vs 0.5289) but was **not separated**
from `L1` (paired 95% interval −0.0233 … +0.0393), so §4 step 4's tie-break
decided it on §4.1's first criterion, **worst-class F1: `L1` 0.3500 vs
0.3415**. Neither selection is evidence that the selected structure is good.

Rationale: `../SCIENCE.md` §Legitimization Scoring and §Enablement Scoring
require a three-class multinomial distribution over L0/L1/L2 and E0/E1/E2.
Two thresholded binary heads structurally cannot produce one
(`../ARCHITECTURE.md` §4 — the obvious derivation is unsafe because
`p_high > p_nonzero` is reachable), which is why the incumbent ships as
`partial` with `distribution=None`. Of the ten non-reference levels compared,
only `L1` and `L2` emit a genuine distribution, and `L2` fails the
worst-class floor on both targets. The procedure that produced this is fixed
in `PREREGISTRATION_LE_STRUCTURE.md`; its §8 records seven amendments, five
of them corrections found by re-examining the selection code against the
document rather than by any test failing.

**Rejected candidates, with their numbers** (dev-set macro-F1 / worst-class
F1; full per-class figures and intervals in
`docs/planning/item2_results/stage1.json` and `stage2.json`, whose per-target
`pool` arrays are the authoritative record):

| Level | L macro / worst | E macro / worst | Why rejected |
|---|---|---|---|
| `R` *(reference)* | 0.4840 / 0.3182 | 0.5199 / 0.3077 | Produces no three-class distribution (§2.2) — cannot be selected |
| `S2` sharing | 0.4851 / 0.2927 | 0.5021 / 0.3488 | No distribution. Topped L's finalists and still ineligible |
| `W3` equal-per-class | 0.4682 / 0.2989 | 0.5356 / 0.3421 | No distribution |
| `W2` inverse-frequency | 0.4199 / 0.2740 | 0.5210 / 0.3896 | No distribution |
| `H1` pooled | 0.4653 / 0.3333 | 0.4633 / 0.2796 | No distribution |
| `H2` hazard one-hot | 0.4339 / 0.2683 | 0.4635 / 0.2424 | No distribution; also below the floor on E |
| `B1` flat ungated | 0.4408 / 0.3182 | 0.4854 / 0.3077 | No distribution. The only level significantly *worse* than `R` |
| `P2` max pooling | 0.4662 / 0.2683 | 0.4930 / 0.2466 | No distribution; also below the floor on E |
| `P3` mean⊕max | 0.4476 / 0.2069 | 0.5030 / 0.2899 | No distribution; also below the floor on L |
| `L2` ordinal cumulative-link | 0.4199 / 0.2162 | 0.4438 / 0.2353 | **Below the worst-class floor on both targets.** Produces a distribution, so this is the one rejection on performance rather than structure |
| `L1+W3` composite *(E only)* | — | 0.5358 / 0.3415 | Led on macro-F1, unseparated from `L1`, lost §4.1's first criterion |

`V1` (representation) was **not exercised**: it has a single level, recorded
as an axis not run rather than one dropped (§2.3).

**What this selection cannot establish**, carried from
`PREREGISTRATION_LE_STRUCTURE.md` §7 and binding on every downstream claim:

- **Dev-set numbers only** ([D-66](#d-66)). Nothing here is a benchmark
  result, a generalization estimate, or reportable under `../SCIENCE.md`
  §Evidence and outputs.
- **No approved success criteria exist**, so both models remain **not
  evaluated** regardless of what was selected. The worst-class floor is a
  screening threshold, not a success criterion.
- **Out-of-version labels** ([D-63](#d-63)) — human judgments made against
  Jailbreak v1.0, used to select a structure for a v1.4 evaluator.
- **Attacked prompts only** ([D-65](#d-65)).
- **Per-hazard claims are weak** — roughly 15 dev rows per hazard, and `H3`
  was pre-declared as probably underpowered at ~42 fit rows per hazard.
- **"No class weighting" is not literal.** `W1` means no weighting *beyond*
  the estimator's own `class_weight="balanced"`, which is on for every
  candidate on the ladder. The Weighting axis measured additional
  re-weighting on top of that, not weighting versus none.

Rejected alternatives: (1) selecting `R`, or any two-head variant that
outscored the winner — structurally barred, because a structure that cannot
emit the required distribution cannot be the answer whatever its macro-F1;
(2) selecting the `L1+W3` composite on E, which led on macro-F1 — rejected by
§4 step 4, since an unseparated lead on the metric that produced the ranking
is not evidence; (3) reporting the outcome as a positive selection —
rejected as the misrepresentation the pre-registration's own §4 forbids in
terms.

Touches: `../ARCHITECTURE.md` §12 (**absorbed** — the L/E structure item is
no longer open); `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5 work list
(**absorbed** — PR 5 builds this structure);
`PREREGISTRATION_LE_STRUCTURE.md` §6's `L1` payload row, which is now the
artifact format PR 5 implements, closing [D-37](#d-37)'s open format half and
[D-49](#d-49)'s deferred finalization; `docs/planning/item2_results/`;
`STATUS.md` queue item 2, which this closes.

Boundary: this selects a **structure**, not a model version. PR 5 fits and
locks the model. It does not weaken [D-66](#d-66)'s reservation of the real
evaluation set: when a fixed Standards-team set arrives, selection is re-run
as a **fresh** selection under a re-issued pre-registration, and this winner
enters that process as one candidate with no privileged status. It also does
not make either model evaluated — that needs approved per-outcome criteria
this repository does not have.

<a id="d-69"></a>
## D-69: The model-input text view is selected at component construction in 1.1; the run-profile field is PR 7's
Date: 2026-08-05
Status: locked
Approved by: Kurt, 2026-08-05. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised while writing
`PR4_EXECUTION_PLAN.md`, from reading the code against the specification.

Decision: `EmbeddingComponent` takes the view its stage reads as a
construction argument, defaulting to `working`, and records the resolved view
in its observation so a result names the text its models actually saw. No
`RunConfig` field is added in Release 1.1; the run-profile half belongs to
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7, which defines the run profile. A second
registered implementation id — the registry-native form of the same selection —
is created when and if the deferred [D-55](#d-55) comparison is actually run,
not in advance.

Rationale: `../ARCHITECTURE.md` §5 stated that "each consumer names the view it
wants" and that a model's input is "a named view selected by configuration",
and D-55's rationale for retaining disclaimer text rests on the comparison
"remain[ing] a configuration change and not a rewrite". Neither was true of the
code: `evaluator/components/embedding.py` read `record.texts.working` as a
literal attribute access and no configuration surface named a view anywhere.
This is the third absorption gap of the same kind — a specification sentence
describing behavior nobody had built — and the cheapest honest fix is to build
the seam, because the alternative weakens a decision (D-55) that was made *on*
the seam's existence.

**Why the selection is not a `RunConfig` field.** `../ARCHITECTURE.md` §6
defines configuration precisely: selection is "resolved through a registry
keyed `(stage, implementation_id)`". `Component.implementation` is a
`ClassVar`, so two views are structurally not two configurations of one
registered component — they are two implementations. A `RunConfig` field would
therefore introduce a *second*, parallel selection mechanism for one stage,
which is what §6 exists to prevent, and it would do so for a knob no runner
reads until PR 7.

Rejected alternatives: (1) amending §5 to say the view is hard-coded and
deferring the whole seam to PR 5 or PR 7 — rejected because it leaves D-55's
stated rationale unbacked for two more PRs while that decision is already in
force; (2) adding the `RunConfig` field now — rejected per the paragraph above;
(3) registering the `disclaimer_stripped` implementation immediately — rejected
because an implementation nothing selects and no test exercises is unverified
surface, and §6's own recording requirements make adding it later trivial.

Touches: `../ARCHITECTURE.md` §5 (**absorbed** — §5 now names where the
selection lives at each stage of the release, rather than describing a
configuration surface that does not exist); `PR4_EXECUTION_PLAN.md` §3 and
slice A, which build it; `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7's run-profile
work item, which inherits the profile half;
`src/hazard_classifier/evaluator/components/embedding.py`.

Boundary: this decides *where the selection lives*, not *which view is
selected*. The 1.1 default remains `working` under [D-55](#d-55), and this
entry does not run, prejudge, or reschedule the comparison D-55 deferred. It
also does not give stage 9 a view — stage 9 reads the pooled vector, so stage 8
remains the only place a text view is chosen.

**Note (2026-08-05, PR 4's closing sweep): the shipped check is stricter than
§5 first described, and §5 is what was corrected.** §5 was written before the
code (the entry gate's spec-first rule) and said the **reserved** view names
were checkable in `__init__` while a **`named`** key was not. Slice A shipped a
construction-time check against *both* static sets — the three reserved names
and the closed set of `named` views 1.1's components actually publish, today
`disclaimer_stripped` alone — so a typo in either half fails once at
construction instead of reaching every row. What remains uncheckable there is
whether a *given record* carries the key, which is the distinction §5 now
draws. The decision is unchanged; only the specification's account of its
mechanism was.

<a id="d-70"></a>
## D-70: Stage 7 ships three of the four inherited disclaimer patterns; `safety_warning` is excluded
Date: 2026-08-05
Status: locked
Approved by: Kurt, 2026-08-05. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Measured while writing
`PR4_EXECUTION_PLAN.md`.

Decision: the Release 1.1 disclaimer component uses `professional_referral`,
`uncertainty_warning`, and `verify_or_check` from `preprocess/flags.py`'s
`DISCLAIMER_PATTERNS`, and **does not use `safety_warning`**. The baseline
module is unchanged and keeps all four; the 1.1 component selects a subset by
name, exactly as stage 4 selects two of three repetition paths. **This is an
identified scoring change**, per `RELEASE_1_1_QUEUE_PROPOSAL.md`'s rules for
every PR: Specialized Advice rows that previously had final L fixed at L0 by
phase C on a risk-word match alone no longer do.

Rationale: `safety_warning` matches bare risk vocabulary — `risk`, `harm`,
`safety`, `unsafe`, `danger` — anywhere in a response, with no disclaimer
context required. `../SCIENCE.md` §Disclaimer detection's "warn about risks"
form describes a disclaimer, not any mention of risk, so the pattern does not
implement the form it appears to serve. This is `../ARCHITECTURE.md` §7.1's
reasoning applied to a second component: stage 4 excludes
`partial_contiguous` because "a similarity heuristic is neither exact matching
nor the … detection `SCIENCE.md` asks for — shipping it would blur what the
component's stated maturity means."

**The evidence, and its limits.** There are no human disclaimer labels, so
precision is not directly measurable and this decision does not claim a
measured error rate. What is measurable is phase C's observable implication:
a pattern finding genuine disclaimers should be enriched in human L0, since
phase C treats a qualifying disclaimer as L0-equivalent. On the 217
Specialized Advice rows of `data/`'s interim ground truth, cluster-bootstrapped
over `prompt_group_id` (2000 draws, seeded):

| Rows | n | human L0 | 95% CI |
|---|---:|---:|---|
| unflagged by any pattern | 129 | 51.2% | 43.8–59.1% |
| the three retained patterns | 46 | 76.1% | 64.0–87.5% |
| `safety_warning`'s exclusive rows | 42 | 57.1% | 39.4–75.0% |

The retained three separate from the base rate; `safety_warning`'s incremental
rows do not. It nearly doubles the flag rate (46 → 88 of 217) while adding rows
statistically indistinguishable from rows nothing flagged.

Three further findings, each independently sufficient:

- **Eleven rows are adjudicable by inspection and all eleven are false
  positives** — the SA rows where `safety_warning` is the only evidence *and*
  phase C changes the result. The matched spans include "reduce the risk of
  backlash from clients", "documented risk-assessment, consent-forms", "these
  methods are generally unsafe", and a "Physical & Mental Harm:" section
  header. Seven carry the source label `unsafe` and several carry human L2/E2,
  where fixing L at L0 makes the Specialized Advice table read non-violating —
  so the rule turned responses humans judged as accepting the hazard *and*
  supplying actionable help into passing results. Eleven of 217 is 5.1% of the
  family.
- **Phase C is one-directional.** It can only move an SA row toward
  non-violating, so a false positive hides a violation rather than creating a
  spurious one. That is the error direction the standard exists to prevent.
- **The enrichment it does show is refusals, not disclaimers.** Its exclusive
  rows include "I can't assist with that request. Promoting rapid or unsafe
  weight loss methods can be harmful" and "could be harmful, so I must
  decline" — refusals explaining themselves in risk vocabulary. The pattern
  partly functions as an accidental, unlabeled refusal detector in a release
  that ships **no** refusal detector by deliberate choice ([D-54](#d-54)),
  which is that decision's enumerable-surface rationale being defeated
  silently.

Every figure above is a dev-set-class number on out-of-version labels
([D-63](#d-63), [D-66](#d-66)) and supports no quality claim in either
direction. The component stays **partial** and *not evaluated*.

Rejected alternatives: (1) shipping all four as inherited and disclosing the
exposure — rejected on the enrichment result and the eleven adjudicated rows;
"preserve the current disclaimer implementation as partial" does not require it,
since PR 1's work list said the same words about prompt repetition while §7.1
dropped a path; (2) writing a pattern for `spc_ele`'s official-source-link
form, which no pattern implements — rejected because an unvalidated new
pattern adds unmeasured surface rather than removing it, and there is no ground
truth to validate it against; (3) editing `DISCLAIMER_PATTERNS` itself —
barred by [D-48](#d-48), and unnecessary; (4) family-gating the flag inside
stage 7 — rejected because whether a disclaimer qualifies for phase C is final
integration's applicability decision (`../ARCHITECTURE.md` §6), and phase C
already gates on family.

Touches: `../ARCHITECTURE.md` §7 row 7 and the new §7.2 (**absorbed** — §7.2
states the pattern set, the exclusion, and the two unimplemented qualifying
forms); `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 4's work list;
`src/hazard_classifier/evaluator/components/disclaimer.py` and
`scripts/probe_disclaimer_scope.py` (PR 4 slice B builds both);
`README.md` §Release 1.1 evaluator status, which gains the coverage and
precision shortfall when the code lands; D-47's Release 1.1 inventory.

Boundary: this scopes **which patterns 1.1 uses**. It does not touch the
baseline, which keeps all four and scores with them unchanged; it does not
decide whether the excluded form is implemented in a later release; and it does
not affect [D-55](#d-55)'s separate question of which text view the models read.
Two `../SCIENCE.md` qualifying forms are now unimplemented rather than one —
risk warnings and electoral official-source links — and both are disclosed
rather than closed.

**Note (2026-08-05, PR 4's closing sweep): what reproduces exactly, and what
does not.** `scripts/probe_disclaimer_scope.py` — committed by slice B and
re-run at the close — reproduces **every row count and every point estimate**
in the table above and in `../ARCHITECTURE.md` §7.2 (`verify_or_check`: 0 of
217, 2 of 859; 46 → 88 flag rate; 11 result-changing rows, 7 labelled
`unsafe`). The **bootstrap interval bounds differ by up to ~1 percentage
point** — 43.3–59.0 / 64.3–86.5 / 39.6–75.0 against the 43.8–59.1 / 64.0–87.5 /
39.4–75.0 recorded here — because the probe runs its own seeded 2000-draw
stream rather than the ad-hoc one this entry was computed on. That is Monte
Carlo variation of the expected size, and it changes no comparison: the three
retained patterns' intervals still exclude the unflagged base rate and
`safety_warning`'s exclusive rows still overlap it. **The probe is the
reproducible source; quote it, not this table**, and read no interval bound
here as stable past its first decimal. (`PR4_EXECUTION_PLAN.md` §4's slice-B
note said the intervals differed "only in the last decimal", which understated
it — corrected there too.)

<a id="d-71"></a>
## D-71: PR 5 is sequenced before PR 6 — PR 7 → PR 5 → PR 6
Date: 2026-08-05
Status: locked
Approved by: Kurt, 2026-08-05. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised while planning PR 5, from
checking PR 6's exit criteria against [D-49](#d-49).

Decision: the remaining Release 1.1 sequence is **PR 7 → PR 5 → PR 6**. PR 5
moves ahead of PR 6; PR 7 keeps its position at the front, which is
[D-56](#d-56)'s call and unaffected.

Rationale: two independent reasons, either sufficient.

1. **PR 6 cannot satisfy an exit criterion that depends on PR 5.** D-49 defers
   the 1.1 evaluator artifact out of PR 1 and splits it: the **format is
   finalized in PR 5**, its **round-trip test is PR 6's**, where
   `RELEASE_1_1_QUEUE_PROPOSAL.md`'s exit criteria already require tests
   covering "artifact round trips". With PR 6 running first there is no format
   to round-trip. D-49 anticipated exactly this and said so: "If PR 5 slips far
   enough that an evaluator artifact is needed before it, this entry should be
   revisited rather than cited."
2. **PR 6's outputs would be stale on arrival.** PR 6 owns the
   staging-promotion decision ([D-58](#d-58)) and triggers [D-47](#d-47)'s
   limitations document. Run before PR 5, it would decide promotion for a
   release whose L/E models are still PR 1's wrapped baseline, and publish an
   inventory still carrying the "L/E scoring's absent distribution" entry that
   PR 5 removes. Both are decisions about what the release *is*, so they should
   be made about the release that ships.

**A citation error this corrects.** `STATUS.md`, `PR4_EXECUTION_PLAN.md`, and
several commit messages wrote the sequence as "PR 7 → PR 6 → PR 5 (D-56)". D-56
decided only that **PR 7 comes before PR 6** and says nothing about PR 5. PR 5's
last position came from `STATUS.md`'s 2026-08-04 escalation note, whose stated
reason — that PR 5 was the only phase blocked on the Standards team's data —
was removed by [D-63](#d-63) the same day and struck on 2026-08-05. So this
entry reverses no prior decision; it corrects a queue order that had outlived
its reason and was being attributed to an entry that never made it.

Rejected alternatives: (1) leaving the order and having PR 6 defer its
round-trip criterion — rejected because it would be the second deferral of the
same criterion (D-49 was the first) and would leave the artifact untested by
any PR; (2) moving PR 5 ahead of PR 7 as well — rejected because PR 7's own
position rests on PR 6's criteria presupposing a runner (D-56), which PR 5 does
not disturb, and because PR 7 is the only remaining PR that unblocks a
*missing capability* rather than a *replacement*.

Touches: `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5's and PR 6's sequencing notes
(**absorbed**); `STATUS.md` queue item 4 and §Current Phase;
`PR5_EXECUTION_PLAN.md` §1; [D-49](#d-49), whose PR 5/PR 6 split this makes
executable in order.

Boundary: this decides **order**, not scope. It changes nothing about what any
PR builds, does not relax D-49's split (the format is still PR 5's and the
round trip still PR 6's), and does not alter D-56's placement of PR 7. It also
does not decide `PR5_EXECUTION_PLAN.md`'s three gate questions, which remain
Kurt's and are unaffected by when PR 5 runs.

<a id="d-72"></a>
## D-72: Release 1.1's L/E models are fitted on pipeline working text, not the raw response text the selection used
Date: 2026-08-05
Status: locked
Approved by: Kurt, 2026-08-05. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised as gate G-1 in
`PR5_EXECUTION_PLAN.md` §3, from reading `experiments/features.py` against
`../SCIENCE.md`'s training requirement.

Decision: PR 5 fits both production models on the **`working` view stages 1–7
produce** — decoded, with repeated prompt spans removed — matching what the
evaluator scores at serve time. The structure selection behind
[D-68](#d-68) was run on the interim frame's raw `response_text`, and **is not
re-run**: its ranking is carried across the change of input view as a recorded
assumption.

Rationale: `../SCIENCE.md` §Legitimization Training and §Enablement Training
both require training "on human ground truth using working text filtered
through the preceding components", and `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5's
work list restates it. `SCIENCE.md` governs on a behavioral conflict
(`META_PLAN.md` §1.1), so option (2) below would have shipped a standing
shortfall against a training requirement *and* a live train/serve skew.

**The measurement that made this cheap**, `scripts/probe_working_text_delta.py`
over all 859 interim rows: 291 rows (33.9%) differ between the two views, but
**285 of those are decoding rewrites and only 8 rows lose a span** to
prompt-repetition removal; 266 of the 291 are the same length; median and p90
character reduction are 0.0% (max 23%); **no row exhausts**, so every row the
selection was fitted on is a row the evaluator would actually score; and the
change is spread evenly across all fifteen hazards, which matters because the
fit is per hazard. Refitting therefore loses no rows, no text of consequence,
and no per-hazard balance.

**The asymmetry is the argument.** Deletion is negligible, but decoding is not
semantically small: the rewritten rows include leetspeak and obfuscated
jailbreak text rendered into plain English, which a frozen BGE encoder
represents very differently at identical length. Not refitting would leave 285
of 859 rows scored in a form the model had never seen.

**The residual, stated plainly:** that D-68's *ranking* survives the change of
input view is an assumption, not a measurement. The probe bounds it; it does
not test it. `PREREGISTRATION_LE_STRUCTURE.md` §7 now carries this, and a
re-issued pre-registration should compare candidates on the view the release
scores.

Rejected alternatives: (1) fitting on raw `response_text` to reproduce the
selected configuration exactly — rejected on the skew above, and because it
would add a second standing shortfall against a `SCIENCE.md` training
requirement alongside [D-65](#d-65); (2) re-running the selection on
working-text features — rejected because it spends a comparison budget
`PREREGISTRATION_LE_STRUCTURE.md` §2.4 fixed and §5 reserves for a real
evaluation set, to buy certainty about a risk the probe shows is bounded.

Touches: `PREREGISTRATION_LE_STRUCTURE.md` §1, §7, §8 (**absorbed** — the
selection's text view is now stated, the limitation is listed, and the
departure is logged as a dated amendment); `PR5_EXECUTION_PLAN.md` §3 and
slice A; `scripts/probe_working_text_delta.py`, which is the evidence;
[D-47](#d-47)'s inventory, which gains nothing here — this closes a shortfall
rather than creating one.

Boundary: this decides **which text the models are fitted on**. It does not
change which text they *read* at serve time — that is [D-55](#d-55)'s
`working` default and [D-69](#d-69)'s selection seam, both unchanged and both
already `working`. It does not reopen D-68's structure, and it does not license
re-running the comparison.

<a id="d-73"></a>
## D-73: Release 1.1's shipped artifact is fitted on the fit split only
Date: 2026-08-05
Status: locked
Approved by: Kurt, 2026-08-05. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised as gate G-2 in
`PR5_EXECUTION_PLAN.md` §3, decided together with [D-72](#d-72).

Decision: the artifact PR 5 ships is fitted on the **fit half of
`data/interim_split_v1.json` alone** — 635 rows for E, 563 for L after phase
A's enablement-only exclusions — never refitted on all 859 rows for release.
The dev slice stays held out.

Rationale: it is the only arrangement under which the per-outcome numbers PR 5
reports and the model PR 5 ships are **the same object**. A release refitted on
fit + dev would be described by no measurement at all, and the report would
silently be about a sibling model. With ~42 rows per hazard cell the extra 35%
of rows is not nothing — but both models are reported *not evaluated*
regardless (`../SCIENCE.md` §Evidence and outputs, no approved criteria), so
what the numbers are *for* is interpretation, and interpretability of a number
that describes the shipped artifact is worth more than a marginally better
undescribed one.

Rejected alternative: refitting on all 859 rows for the release, with the dev
numbers reported as indicative of the smaller fit. Rejected because "indicative
of" is exactly the kind of unstated inferential step `PREREGISTRATION_LE_STRUCTURE.md`
§5 and [D-66](#d-66) exist to prevent, and because it consumes the only held-out
slice this release has.

Touches: `PREREGISTRATION_LE_STRUCTURE.md` §1 and §5 (**absorbed**);
`PR5_EXECUTION_PLAN.md` §3, slice B's manifest provenance, and slice D's report
framing.

Boundary: this governs **the released 1.1 artifact**. It does not bind a future
release fitted on real Standards data, where the split, its size, and the
touch budget are all re-decided (`PREREGISTRATION_LE_STRUCTURE.md` §5), and it
makes no claim that the dev slice is an evaluation set — under D-66 it remains
dev-class, and held out is not approved.

<a id="d-74"></a>
## D-74: The run profile carries the model-input text view as a construction parameter, not a selection field
Date: 2026-08-05
Status: locked
Approved by: Kurt, 2026-08-05. **Riki's concurrence assumed on Kurt's
direction, not confirmed on record.** Raised as gate G-1 in
`PR7_EXECUTION_PLAN.md` §3, which is the question [D-69](#d-69) deferred to
PR 7 by name.

Decision: PR 7's run profile gains an optional **`text_view`**, defaulting to
`working`, which the component factory passes to `EmbeddingComponent`'s
constructor when it builds the registry. **It ships only with a test that runs
end to end at a non-default value**; without that test the field does not ship
at all.

Three things it is deliberately **not**:

- **not a `RunConfig` or `RunContext` field** — that is the parallel selection
  mechanism D-69 refused, and refusing it is still right;
- **not a registry key** — a second registered embedding implementation is
  still deferred to whenever the [D-55](#d-55) comparison actually runs;
- **not a change to which view is selected** — the 1.1 default remains
  `working` under D-55.

Rationale: D-69 deferred this half with a conditional — "if a model-input view
belongs in a profile, that is where it goes" — and gave two reasons for not
building it in PR 4. One was that no runner read such a field until PR 7; PR 7
discharges it. The other was structural, and survives: §6 defines configuration
as *which implementation serves a stage*, keyed `(stage, implementation_id)`,
so two views are two implementations rather than two configurations of one.

**What resolves the structural objection is a distinction D-69 did not need to
draw**: *which implementation is selected* versus *how the selected
implementation is constructed*. `EmbeddingComponent` already takes its provider
and its pooling strategy as construction arguments, and neither is a registry
key or a `RunContext` field. `text_view` is the same kind of thing. The profile
is the document that builds components; carrying a construction parameter there
adds no second answer to "which implementation serves stage 8", which is the
question §6 reserves for the registry.

**Why it is worth building now rather than deferring again.** D-69 was decided
on the premise that D-55's deferred comparison "remains a configuration change
and not a rewrite" — and until a profile carries the view, that claim is true
only of a Python constructor call, not of anything a run is configured with. PR
7 is the first PR where a run *has* a configuration document, so this is where
the claim becomes true or stays aspirational.

**The conditional is the whole safeguard.** D-69's own reason for rejecting a
registered second implementation was that "an implementation nothing selects and
no test exercises is unverified surface". A profile field nothing ever sets to a
non-default value is the same defect wearing a different hat. The end-to-end
test at `text_view: "disclaimer_stripped"` is what makes this a built feature
rather than a declared one.

Rejected alternatives: (1) leaving the view a constructor argument only —
rejected because it leaves D-69's and D-55's shared rationale unbacked at the
configuration layer, which is exactly the gap D-69 was raised to close one level
down; (2) adding a `RunConfig`/`RunContext` field so the view appears in
`component_selections` — rejected on §6, and unnecessary: the resolved view is
already recorded in the stage-8 observation and reaches `results.jsonl` through
`views.py`; (3) registering a `disclaimer_stripped` embedding implementation in
PR 7 — rejected, unchanged from D-69: it belongs to whenever the comparison
runs.

Touches: `../ARCHITECTURE.md` §5's profile bullet (**absorbed** — rewritten to
carry the construction-parameter distinction);
`RELEASE_1_1_QUEUE_PROPOSAL.md` PR 7's run-profile work item;
`PR7_EXECUTION_PLAN.md` §3 and slice B; [D-69](#d-69), whose deferred half this
closes.

Boundary: this decides **where the view is configured**, not **which view is
right** — [D-55](#d-55)'s deferred comparison is untouched, its default stays
`working`, and nothing here runs, prejudges, or reschedules it. It also does not
give any other stage a profile-level construction parameter; stage 8 is the only
stage that reads a text view (§5).
