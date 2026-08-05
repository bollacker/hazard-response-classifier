# Queue item 2 execution plan — L/E structure selection

Written 2026-08-04, after the interim-data pivot ([D-63](DECISIONS.md#d-63)–
[D-66](DECISIONS.md#d-66)) made this item startable and D-59's pre-registration
was written. This is the working plan for `STATUS.md` **queue item 2**, and it
is written to be run from a clean session: everything a session needs is either
here or named here.

**Goal (from queue item 2):** compare candidate three-class loss, weighting,
sharing, hazard-conditioning, branching, representation, and pooling structures
on the same fixed evaluation set, and select the best-supported structure.
Treat the current prototype as a baseline, not the target.

**This item is analysis, not shipping.** Its deliverable is a *selected
structure plus a ledger entry recording it and the rejected candidates*. It
does not modify the Release 1.1 pipeline — see §2.

---

## 0. Read first

In this order. Do not skip — this project's failure mode is sessions
re-deriving settled ground, and this item has more settled ground in front of
it than any prior one.

| Doc | Why |
|---|---|
| `META_PLAN.md` | The process contract. §1.2 (**single-approver mode**, new), §3 (uncertainty protocol), §5 (queue rules) govern this work |
| `STATUS.md` — header, Queue item 2, Awaiting User | Live state. Item 2's entry is the authoritative statement of what this item owes |
| **`PREREGISTRATION_LE_STRUCTURE.md`** | **The specification for this item. It governs.** Written before any candidate was fitted, precisely so this session cannot choose the rule after seeing results. Read it end to end before writing code |
| `../SCIENCE.md` §Legitimization Training/Scoring, §Enablement Training/Scoring, §Evidence and outputs | Behavior. Governs on any conflict. The equal-importance requirement and the not-evaluated rule are the two that bind here |
| `../ARCHITECTURE.md` §4 (`Judgment.distribution`), §8 (embedding boundary), §10 (artifact), §12 | §4 explains why the incumbent cannot be the answer; §12 records that this item is what fills the open slot |
| `DECISIONS.md` D-59, D-63, D-64, D-65, D-66 | The five that define this item's data, split, procedure, and what its numbers mean. Also D-37 (no pickle) and D-45 (unfittable is unavailable, never substituted) |
| `PR3_EXECUTION_PLAN.md` | The template this plan follows, and the precedent for a "verify what's already built before building" slice |

Ledger entries are provenance, not authority (`META_PLAN.md` §1.1). Cite the
specification, not the entry.

## 1. Preconditions — all met as of 2026-08-04

- Queue item 2's entry condition is **met** (D-63). The Standards team's data
  is not coming; this runs on the Jailbreak v1.0 human ground truth in `data/`.
- The pre-registration exists and is approved.
- The frozen split exists: `data/interim_split_v1.json`, rebuilt and verified
  by `python scripts/build_interim_split.py --check`.
- Baseline is green: **298 tests**, `pytest` from the repo root.
- Environment: `pyenv activate airr`, or `~/.pyenv/versions/airr/bin/python`
  directly. (`python` alone fails on this machine — pyenv shim needs the env.)
- Nothing is in **Awaiting User** that blocks this scope.

**Run `--check` first, before anything else.** If the split does not reproduce,
stop: either the source CSV changed or the builder did, and every number this
item produces would be against an unknown split.

## 2. What this item is, and what it is not

Getting this boundary wrong is the largest risk in the plan, because the
natural momentum at the end of a successful comparison is to go implement the
winner.

**In scope:** an offline comparison harness, 28 fitted configurations (§5's
2026-08-04 correction), a
selection under the pre-registration's rule, a `DECISIONS.md` entry recording
the selected structure *and the rejected candidates*, and closing the item.

**Out of scope, all of it PR 5's:**

- Modifying `src/hazard_classifier/evaluator/components/scoring.py`. PR 1's
  `BaselineTwoHeadScorer` keeps shipping as `partial` until PR 5 replaces it.
- Producing a 1.1 model artifact, or touching `ARCHITECTURE.md` §10's format.
  The pre-registration §6 already states what each candidate implies; PR 5
  builds it.
- Training the production model. This item selects a *structure*; PR 5 fits and
  locks a *model version*.
- Any change to `hrc-train`/`hrc-evaluate`/`hrc-predict` or the baseline.

**Also out of scope: claiming performance.** Under D-66 every number here is a
**dev-set** number. It is not a benchmark result, not a generalization
estimate, and must not be written into `README.md` or described as model
quality anywhere. `SCIENCE.md` §Evidence and outputs still requires both models
be reported as *not evaluated*, because approved per-outcome criteria do not
exist and no comparison creates them.

---

## 3. Slice 0 — Close the split-reproduction trap (start here)

**There is a real defect in what the pivot session shipped, and this slice
fixes it before it can silently corrupt every downstream number.**

`data/interim_split_v1.json` records the eval **group ids** and a prose
description of the key — `"sha256(whitespace-normalized prompt_text)[:16]"` —
but **no row-level train/eval assignment**. To use the split, a consumer must
recompute the group id for every row. The only implementation of that recipe is
`_group_id` in `scripts/build_interim_split.py`: a private function, in a
directory that is not an importable package.

The failure mode is silent and severe: a session that reimplements the
normalization even slightly differently (say `.strip()` instead of
`" ".join(text.split())`) gets a *different* split, no error, and results that
cannot be compared to anything.

**Build:** `src/hazard_classifier/interim_data.py` — a small, tested module
that is the single source of truth for the interim dataset.

```python
INTERIM_SOURCE: Path        # the CSV, by name
INTERIM_SPLIT: Path         # interim_split_v1.json

def prompt_group_id(prompt_text: str) -> str: ...
def load_interim(*, split: str | None = None) -> pd.DataFrame: ...
    # returns the source CSV with: normalized `hazard` (D-27),
    # `prompt_group_id`, and `split` in {"train", "eval"}.
    # Verifies the source SHA-256 against the manifest and raises if it drifts.
def legitimization_rows(frame) -> pd.DataFrame: ...
    # excludes prv/sxc_prn via metrics.legitimization_eligible_mask
```

Then **move `_group_id` out of the script and import it from here**, so the
builder and every consumer share one implementation. Re-run
`build_interim_split.py --check` afterwards: it must still reproduce the frozen
manifest byte for byte. If it does not, the move changed behavior and the
manifest — not the code — is what to trust.

**Tests** (`tests/unit/test_interim_data.py`):

- `load_interim()` returns 859 rows; `split="train"` → 635, `split="eval"` →
  224; eval covers 48 distinct groups. These are the manifest's own numbers —
  assert against the manifest, not against literals, so the test tracks a
  re-frozen split.
- Every hazard appears in both splits; all three L and all three E classes
  appear in eval.
- No `prompt_group_id` appears in both splits.
- `legitimization_rows()` returns 763 rows and excludes exactly `prv` and
  `sxc_prn`.
- A tampered source file raises rather than silently splitting differently.

**Exit:** the split can be loaded one way, that way is tested, and the builder
still reproduces the frozen manifest.

---

## 4. Slice A — The comparison harness

No candidate results yet. Build the machinery and prove it is correct on data
whose answer is known.

Put it in `src/hazard_classifier/experiments/` — a new package, clearly
separate from the production pipeline, so nothing here is mistaken for shipping
code.

### 4.1 Features

One embedding pass over all 859 response texts, cached to disk as `.npy` keyed
by model name and revision. Re-embedding inside a many-configuration loop is the
defect `ARCHITECTURE.md` §8 names explicitly; it is also about a hundred times
slower.

**Gotcha:** `embed.embed_sentences` is **offline by default**
(`allow_download=False`). First run on a machine without the cached BGE weights
needs `allow_download=True`. Do that once, in the cache-building step, not
inside the comparison loop.

Pooling is an axis (`P1` mean, `P2` max, `P3` mean⊕max), so the cache stores
**per-sentence** vectors and pooling is applied downstream — otherwise `P2` and
`P3` require re-embedding.

### 4.2 Candidate interface

One protocol every candidate implements, so the ladder is a loop and not
twelve bespoke scripts:

```python
class Candidate(Protocol):
    name: str                      # e.g. "L1.W2.H2.B1.P1"
    def fit(self, X, y, hazards) -> None: ...
    def predict_proba(self, X, hazards) -> np.ndarray:   # (n, 3), rows sum to 1
```

Two rules from the pre-registration, enforced here rather than trusted:

- **No candidate may apply a `SCIENCE.md` fixed rule.** Applicability, phase C,
  and the result tables belong to final integration. A candidate that reads
  hazard family to decide an *outcome* (rather than to condition a *feature*)
  is disqualified. Add an assertion, not a comment.
- **Linear on frozen embeddings only.** Nothing fine-tunes an encoder
  (pre-registration §2.1 — this is what keeps D-37's no-pickle artifact
  constraint satisfiable).

**The reference `R` is the incumbent two-head mechanism** and needs care: it
fits per `(component, hazard)` and, on 635 fit rows across 15 hazards, some
cells will be unfittable. D-45 governs — an unfittable head is *unavailable*,
never substituted. The harness must record such a cell as unavailable and let
`R` score what it can, rather than crashing the ladder or inventing a
probability. If `R` cannot produce a distribution at all, that is expected:
§2.2 of the pre-registration says `R` cannot be the final selection anyway.

### 4.3 Metrics and uncertainty

- Per-class F1, macro-F1, worst-class F1 — computed separately for L and E.
- **Paired cluster bootstrap over `prompt_group_id`**, 1000 resamples, seeded.
  Two things go wrong if this is done casually, and both inflate confidence:
  - Resampling **rows** rather than groups understates the interval, because
    rows sharing a prompt are correlated.
  - Comparing two candidates' **marginal** intervals is a strictly weaker test
    than the interval on their **paired difference**. The pre-registration
    requires the paired form: compute the difference within each resample, on
    the same resampled groups.

### 4.4 Tests

- Metrics: hand-built confusion cases where macro-F1 and worst-class F1 are
  computable by hand.
- Bootstrap: a candidate compared against **itself** yields a difference
  interval containing zero and centred on zero. This is the single most
  valuable test here — it catches unpaired implementations immediately.
- Determinism: the same seed and inputs produce identical results twice.
- A degenerate candidate that predicts one class always scores exactly the
  majority-class figures from the pre-registration §3 table (L 0.569,
  E 0.636 accuracy; worst-class F1 = 0). This anchors the harness against
  known values.

**Exit:** harness is correct on known answers. No candidate has been ranked.

---

## 5. Slice B — Stage 1 ablation

From `R`, vary one axis at a time across all its levels: **10 non-reference
levels × 2 targets = 20 fits** (corrected 2026-08-04 —
`PREREGISTRATION_LE_STRUCTURE.md` §8: the original "12" did not match §2.3's
own table; the ten named levels are `L1, L2, W2, W3, S2, H1, H2, B1, P2, P3`).
Write every result to
`docs/planning/item2_results/stage1.json` — every configuration, its per-class
and macro F1, its worst-class F1, and its bootstrap interval against `R`.

**Record every candidate, including the bad ones.** The item's deliverable is a
ledger entry naming the *rejected* candidates; that record cannot be
reconstructed later from a results file that only kept the winners.

Expected findings to not be surprised by, pre-declared in the pre-registration:

- **`H3` (per-hazard) is probably underpowered** — ~42 fit rows per hazard over
  three classes. A poor `H3` means "not enough data per hazard here", not
  "hazard conditioning is wrong."
- **`V1` is the only representation level.** Comparing encoders is out of scope
  for 1.1; it is recorded as an axis not exercised, not as one dropped.

**Exit:** 20 results recorded, best level identified per axis.

## 6. Slice C — Stage 2 finalists and selection

Combine the best level of each axis into one composite, plus **at most 3**
hand-picked combinations where stage 1 suggests an interaction. **Maximum 4
finalists per target, 8 fits.** Running total: 28. That is the whole budget.

**Do not expand the budget.** An adaptive sweep on 224 dev rows produces a
selection rule that describes noise. If stage 2 is inconclusive, the tie-break
decides — that is what it is for. If a session genuinely believes the budget is
wrong, that is a pre-registration **amendment** (§8): dated, with its reason,
recorded in the document. Not a silent extra run.

Apply the pre-registration §4 selection rule exactly:

1. Disqualify on §2.1 constraints or the worst-class F1 floor of 0.25.
2. Rank survivors by macro-F1.
3. Select outright only if the **paired** bootstrap 95% interval against the
   next-ranked candidate excludes zero.
4. Otherwise apply §4.1's tie-break in order: higher worst-class F1 → fewer
   fitted parameters → closer to `R`.

**If nothing beats `R`, that is the finding, and it gets reported as one.**
`R` cannot be selected — two binary heads cannot produce the three-class
distribution `SCIENCE.md` requires — so the selection becomes the
highest-ranked candidate that produces a genuine distribution, and the entry
must say plainly that the ablation found no structure that beat the incumbent
on this data. Do not dress a null result as a positive selection.

**The distribution requirement excludes far more than `R`** (found
2026-08-05 while re-examining this slice; recorded in
`PREREGISTRATION_LE_STRUCTURE.md` §8). It is a *structural* property, so
every level that keeps `R`'s `L3` two-head loss inherits it: `W2`, `W3`,
`H1`, `H2`, `B1`, `P2`, `P3`, **and `S2`** all decide by threshold and return
a one-hot row. Only `L1` and `L2` qualify. A slice that enforces the
worst-class floor and the separation test but forgets this will select an
ineligible structure — the first implementation of this rule did exactly
that, selecting `S2` for L.

**§4 step 4 is not optional either.** "If separation fails, the candidates
are tied and §4.1 decides" — ranking first on macro-F1 does *not* settle it,
because macro-F1 produced the ranking. Applying §4.1 in order (worst-class F1
→ fewer fitted parameters → closer to `R`) can overturn the macro-F1 leader,
and on the E target it does.

**And steps 3–4 rank the *eligible* candidates, wherever the
never-selectable structures sit** (found 2026-08-05 by the second
independent review; recorded in `PREREGISTRATION_LE_STRUCTURE.md` §8). The
first tie-break implementation applied §4.1 only when the eligible leader
also topped the finalist ranking — so a strong-enough `R` would have
silently selected the unseparated macro leader by rank alone. The tie-break
now fires whenever separation between the top two eligible candidates
fails, in every outcome, including the null-result one.

**Outcome, 2026-08-05 (corrected). Both targets select `L1`, and neither
found a structure that beat `R`.**
**L → `L1`**, the only structure that both survives the floor and produces a
distribution, scoring *below* `R` (macro-F1 0.4336 vs 0.4840) — a null result.
**E → `L1`** on §4.1's first criterion: the `L1+W3` composite led on macro-F1
(0.5358 vs 0.5289) but was not separated from `L1`, and `L1` has the higher
worst-class F1 (0.3500 vs 0.3415). Both figures are dev-set numbers under
D-66. Full record in `docs/planning/item2_results/stage2.json`.

**Exit:** one selected structure per target, with its rationale and its
rejected alternatives written down. **Met** — `stage2.json` carries the
selection, the ranking, the candidates disqualified by the floor, and those
excluded for producing no distribution.

## 7. Slice D — Record the decision and close the item

**A `DECISIONS.md` entry is what this item owes the ledger**, and `STATUS.md`
item 2 says why: the dispositions half is reconstructible, the *reasoning and
the rejected candidates* are not.

The entry (**D-67** if nothing else has taken it — check the header's
"new decisions start at" line, and update it):

- Decision: the selected structure per target, named in the pre-registration's
  axis vocabulary.
- Rationale: the selection rule's output, including whether it was won outright
  or on tie-break, **and the rejected candidates with their numbers**.
- The honest scope: dev-set numbers, out-of-version labels, attacked-only
  coverage, no approved criteria — so the models remain *not evaluated*.
- `Touches`: mark what absorbed it — `ARCHITECTURE.md` §12's L/E structure item
  (which stops being open), `RELEASE_1_1_QUEUE_PROPOSAL.md` PR 5's work list,
  and `PREREGISTRATION_LE_STRUCTURE.md` §6's payload row for the winner.

**Under `META_PLAN.md` §1.2 (single-approver mode) the entry also owes a row in
`STATUS.md` §Assumed concurrence carrying its reversal scope.** That is not
optional and it is not bookkeeping — the table is Riki's batch-review agenda,
and an entry without reversal scope cannot be reviewed, because the reviewer
cannot see what saying no would cost.

Then close the item per `META_PLAN.md` §5: remove item 2 from the Queue, add it
under **Retired item numbers** with its closing date and where the record
lives, and **never reuse the number** — `DECISIONS.md` and `critiques/` cite
it. Add a Recently Completed entry.

---

## 8. Exit criteria → how each is verified

| Criterion | Verified by |
|---|---|
| The comparison ran on one fixed evaluation set | Slice 0's manifest check; every result carries `split_version: interim-v1` |
| Candidate structures compared across the seven axes | `stage1.json` has all 12 non-reference levels per target; representation recorded as not exercised |
| The best-supported structure selected, not the prototype by default | Slice C applies §4's rule; `R` structurally excluded from winning |
| The prototype treated as a baseline, not the target | `R` is the reference the ladder measures against |
| Reasoning and rejected candidates recorded | The D-67 entry, plus `stage1.json`/`stage2.json` |
| No unsupported quality claim | No number written to `README.md`; both models still *not evaluated* |
| Item closed correctly | Item 2 in Retired item numbers; number not reused |

## 9. Explicitly out of scope

- Everything in §2's "out of scope" list — most importantly, implementing the
  winner.
- Touching a real Standards-team evaluation set, if one appears mid-session.
  D-66 reserves it: selection is re-run fresh under a re-issued
  pre-registration, not confirmed by this one. **A session that finds new data
  should stop and raise it, not use it.**
- Revisiting D-63's choice to use out-of-version labels, D-64's split key, or
  D-65's attacked-only coverage. All three are locked with their reasoning; a
  session that thinks one is wrong raises it under Open Questions.
- Building `metrics.json` (`ARCHITECTURE.md` §11). It needs approved criteria
  and belongs to PR 5/PR 6.

## 10. Lessons carried forward

Written from what actually went wrong or nearly went wrong in the sessions that
produced this plan. These are not general advice; each one cost something here.

1. **Profile the data before designing anything against it.** The pivot session
   nearly adopted `seed_prompt_id` as the split key because D-1/D-13 specified
   it and it sounded right. Thirty seconds of profiling showed 30 seed prompts
   each mapping to exactly one hazard — a split on it makes per-hazard
   evaluation *structurally impossible*. The spec was correct for the baseline
   and wrong for this data.

2. **Verify every number before it goes into a document.** The pre-registration
   was first written with L class counts of 434/187/142 stated as 455/195/113 —
   plausible-looking, wrong, and it would have been quoted downstream. Compute,
   then write. This applies hardest to numbers that appear in a table and look
   authoritative.

3. **When a request contradicts a locked specification, raise it — do not
   quietly implement it.** A session was asked to stub narrative and refusal to
   "always return False." That contradicts `ARCHITECTURE.md` §6's rule that a
   placeholder is never silently equivalent to a negative result — while
   changing *no* behavior, since phase B1 tests `== "detected"`. Raising it
   took one exchange; implementing it would have amended three specs to buy
   nothing and would have dropped both components out of D-47's inventory.

4. **A decision that reaches no specification is not settled.** Two absorption
   gaps have been found this way (PR 2's README gap, D-47's narrowing-2 gap).
   When this item's entry lands, update `ARCHITECTURE.md` §12 and PR 5's work
   list in the same session — not "next time."

5. **Beware the component that runs, returns results, and looks healthy.**
   D-50 and D-51 exist because a stubbed trigger and a partial scope are
   invisible in output. The analytic version of the same failure: a selected
   structure with a good macro-F1 and a worst-class F1 of 0.26 has passed the
   floor and is still failing the equal-importance requirement in substance.
   Report the worst class every time you report a macro.

6. **Do not take a prior session's claim at face value; check it against the
   code.** PR 3's plan found most of its own work list already built by PR 1's
   architecture, and PR 3 became a verification pass. Conversely, `views.py`
   quietly recorded that `failures.csv` needed a runner that did not exist —
   for three PRs, until a sweep read it. Read the code, not just the docs about
   the code.

7. **One queue item per session, and retire by number.** `META_PLAN.md` §5.
   Numbers are stable identifiers that other documents cite; renumbering
   silently re-points every citation. New items continue from 7 — note that
   **PR 7 is a `RELEASE_1_1_QUEUE_PROPOSAL.md` PR number, not a queue item
   number**; the two schemes have collided before and §Retired item numbers
   documents three of them.

8. **Ledger entries never restate a specification's content.** `META_PLAN.md`
   §1.1's last bullet. This is why the single-approver mode amendment lives in
   `META_PLAN.md` §1.2 with only a `STATUS.md` row, and not as a D-entry.

9. **End with Open Questions, even if empty.** `META_PLAN.md` §3. If confidence
   in a recommendation is below ~90%, or it conflicts with a locked decision,
   or it depends on a tradeoff only Kurt can make — it goes there, and the
   session stops rather than resolving it.

## 11. When a slice raises something this plan did not anticipate

The pre-registration governs on any conflict with this plan; `SCIENCE.md`
governs on any behavioral conflict with either.

If a slice finds that a pre-registered choice is unworkable — a candidate that
cannot be fitted, a metric that is undefined on this data, a budget that
genuinely cannot answer the question — **do not improvise around it.** Record
it as a dated amendment in `PREREGISTRATION_LE_STRUCTURE.md` §8 with its
reason, or raise it under Open Questions if it needs Kurt. The whole value of a
pre-registration is that deviations are visible; an undocumented deviation
converts this item's result back into an ordinary unfalsifiable claim.
