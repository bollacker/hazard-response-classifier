# Critique pass: DECISIONS.md full-ledger introspection (D-1 – D-17)

Date: 2026-07-23
Mechanism: critique (META_PLAN §2)
Scope: all seventeen `DECISIONS.md` entries, read against each other for mutual
consistency. This is the second ledger-introspection pass; the first
(`critiques/2026-07-23-decision-review.md`, DR-1 – DR-7) covered D-1 – D-10 and
is fully resolved. This pass therefore concentrates on (a) D-11 – D-17, which
have never been cross-checked against anything, and (b) the older entries as
they now read *after* their amendments, since three of them (D-2, D-3/D-4 via
D-11, D-7) were edited in place and an amendment can create new interference of
its own. `PLAN.md` prose is cited only where it is needed to see a
decision-to-decision interaction; findings are about the ledger, not plan
quality.

Finding ids are band-prefixed and pass-tagged (`DI-C*` correctness, `DI-Q*`
quality, `DI-N*` nice-to-have) to avoid collision with the `C-`, `E-`, and `DR-`
ids already in use by the other three critiques.

Ledger check: this pass *is* the ledger check — for each finding below I name
the specific entries in tension. Verified that DR-1 – DR-7's accepted
resolutions are actually present in the ledger (D-7 amendment, D-11 + its
narrowing amendment, D-3/D-4/D-5 notes, D-2's DR-3 note and DR-7 typo fix) —
all applied; no finding below re-litigates them. Reference reads, used to check
ledger statements against the behavior they claim to describe:
`security-evaluator/code/scoring_common.py` (`fit_binary_head` L438-467,
`safe_auc` L650, `metric_summary` L656-707, `score_indices` L755-790) and
`code/run_bge_hazard_weighted_heads.py` (`fit_binary_head_weighted` L81-110,
`optimize_thresholds_for_hazard` L113-131, the per-target-hazard loop
L226-250). Also read the two committed implementation slices
(`src/hazard_classifier/metrics.py`, `rules.py`) as evidence of how the ledger
is actually being read by an implementer.

Severity bands: **blocks-correctness** = two locked decisions give
contradictory, undefined, or unimplementable instructions that an implementer
following the ledger literally will get wrong; **quality** = a real
cross-decision gap or a false statement in the ledger that should be reconciled
but does not by itself corrupt a result; **nice-to-have** = staleness or
under-specification that is harmless in behavior.

---

## blocks-correctness

### DI-C1. D-5's `"skipped"` trigger describes a mechanism the toy does not have, so the flag D-3/D-11/D-14/D-17 all key off has no well-defined firing condition

D-5 locks: "`(component, hazard)` cells with zero training rows keep the toy's
existing behavior — a constant-probability substitution that yields a
degenerate 0.5-centered threshold search — but each such cell is explicitly
marked as `skipped`." Four other locked decisions consume that marker: D-3
(fail closed on it), D-11 (its precedence relative to D-4), D-14
(`hrc-evaluate` excludes such rows), D-17 (`excluded_skipped_cell_count` is a
reported metric key). The marker is therefore load-bearing for both the
production error contract and the reported numbers.

But the toy has no per-cell substitution. Two distinct mechanisms are being
conflated:

- The constant-probability substitution (`fit_binary_head_weighted` L88-91)
  fires on `len(set(train_y)) < 2` — a **single-class label vector for the
  whole component**, evaluated over *all* training rows of that component, not
  over the target hazard's own rows. It is a component-wide, all-or-nothing
  condition: if it fires for a component it fires identically for every hazard
  in it.
- A hazard with **zero own rows** does not trigger it at all. The head is fit
  on `x[train_idx]` — every hazard's rows — with `sample_weight` merely
  down-weighting other hazards to 0.25 (L228-243). With zero own rows the
  weights are uniformly 0.25, which is an ordinary unweighted fit, and it
  produces a perfectly normal non-constant head. Thresholds then fall back to
  the pooled search (`optimize_thresholds_for_hazard` L121-131: `n_own >= 5`
  *and* ≥2 distinct own labels, else pool). Nothing is degenerate and nothing
  is skipped.

So D-5's stated trigger ("zero training rows") and D-5's stated consequence
("the constant-probability substitution") are conditions on different things,
and an implementer must pick one:

- Read as **zero own-hazard rows**: the cell is fully fittable in the toy, so
  marking it `skipped` and refusing to serve it is a new, stricter behavior
  than the toy's — an unrecorded break of D-2's parity mandate — and D-5's
  claim that the stored parameters are "the substitution values" (repeated in
  `PLAN.md` §4) is simply false; they are a real fitted head.
- Read as **single-class component-wide `train_y`**: then `status` is uniform
  across every cell in a component, D-14's per-row `excluded_skipped_cell_count`
  is either 0 or the entire eval set, and D-5's per-cell framing is
  meaningless.

The two readings differ in how many production rows hard-fail (D-3/D-11) and
how many eval rows are silently dropped from the headline (D-14) — i.e. they
change both the error contract and the reported metrics. DR-6 already flagged
D-5's "0.5-centered threshold search" phrasing as *stale under D-10*; this is a
different and larger problem — the description was never accurate, and four
later decisions were built on it.

### DI-C2. D-15 guarantees enablement-only rows stay in the headline; D-5 + D-3/D-11 + D-14, read literally, exclude every one of them

D-15 (locked) states that `prv`/`sxc_prn` rows "carry no legitimization ground
truth (§2.1)" and that "no legitimization prediction is produced for them"
(§1.1 item 3) — and guarantees they "remain in the final-label headline
population exactly as before."

But nothing in the ledger exempts those hazards from cell enumeration. D-5's
rule, as applied in `PLAN.md` §3 step 4, is "enumerate every `(component,
hazard)` cell implied by the training hazard set." A `(legitimization, prv)`
cell so enumerated necessarily has zero training rows (the label is blank/NA by
§2.1), so under D-5 it is marked `"skipped"`. D-3 and D-11's step 3 then say: a
non-empty/authored response landing on a `"skipped"` cell is not scored — hard
fail. D-14 converts that hard fail into "exclude the entire row — both
components *and the final label*" from every reported metric.

The consequences chain all the way out:

- `hrc-evaluate` excludes every non-empty `prv`/`sxc_prn` row, so D-15's
  guarantee that those rows keep contributing their `E`-only final label is
  violated by the very machinery D-15 was written alongside.
- Worse, `hrc-predict` (D-3/D-11, no D-14 escape hatch) would be **unable to
  score any enablement-only hazard in production at all** — it would raise on
  every authored response for `prv` and `sxc_prn`. That is a total loss of two
  hazard families, produced purely by the interaction of four locked entries,
  none of which says anything obviously wrong on its own.

The concept that would resolve this — a component that is *not required* for a
hazard family, and whose cell is therefore never consulted rather than
consulted-and-rejected — appears in `PLAN.md` §5's D-14 bullet as the
unexplained phrase "for either **required** component," but is defined nowhere
in the ledger. D-15 assumes that no-prediction path exists; D-3/D-5/D-11 assume
every enumerated cell is consulted. Both are locked.

### DI-C3. D-4 rows have no head probability, but D-14 keeps them in every metric and D-16 requires one per row

D-4 (locked, predict-time half): an empty or prompt-repetition-only response
"is not passed through the frozen head at all — it is scored as `0` directly."
D-14 (locked) is explicit that these rows are **not** an exclusion trigger:
they "score `0` for that component and remain in the metrics normally." D-16
(locked) requires the reported per-component AUC to be computed from "the high
head's centered probability" for the rows in the population.

For a D-4 row that quantity does not exist — the head was deliberately never
invoked. The ledger states all three of "keep the row," "produce no
probability," and "compute a probability-based metric over the rows," and
resolves none of them. An implementer must invent a value, and the plausible
choices are not close to each other:

- drop D-4 rows from the AUC only — then AUC silently has a different
  denominator from the exact/within-one/QWK/MAE reported beside it, with
  nothing in D-17's schema recording that;
- impute 0.0 (the toy's post-rule value — see DI-Q1) — pulls the AUC toward
  whatever fraction of the eval set is refusals, which §3 step 4's own D-4 note
  says is "common in production, not a rare corner case";
- impute the centered neutral 0.5 — a different number again.

This is already live, not hypothetical: the committed
`metrics.py::component_metrics(y_true, y_pred, high_prob)` takes a `high_prob`
array with one entry per row and no null handling, so the caller that does not
yet exist will have to fabricate the missing entries.

### DI-C4. D-14 says excluded rows never enter a population; D-17's schema files the excluded counts inside each population

D-14 (locked): "This exclusion check runs **before** D-13's held-out/in-sample
partitioning: an excluded row never enters either population, so D-13's
populations are computed only over rows that actually got scored."

D-17 (locked) §4: "`metrics.json` is a single object keyed by population
(`held_out`, `in_sample_unrecorded`) … Each population object has `n_rows`;
`excluded_row_count` with an `excluded_unseen_hazard_count` /
`excluded_skipped_cell_count` breakdown (D-14)."

These cannot both hold. To report an excluded-row count *per population* you
must partition the excluded rows by `seed_prompt_id` — i.e. run D-13's
partitioning on rows D-14 says never enter it. The schema as locked is
unimplementable without either (a) reversing D-14's stated ordering, or (b)
moving the excluded counts to the top level alongside `holdout_recorded`. D-17
was written as the pass that closed out D-14's deferred "exact schema"
placeholder, so this is the seam where the two were supposed to meet.

---

## quality

### DI-Q1. D-16's description of the toy's two AUCs is wrong on both counts, and the correct reading changes the number D-2/DR-4 kept as a tight parity target

D-16 (locked) states the toy "computes *two* AUCs per component —
`binary_present_auc` (nonzero head vs. `y > 0`) and `high_auc` (high head vs.
`y == 2`)" and pins production's "AUC" to "the **high head's** centered
probability … matching the toy's existing `high_auc` computation."

`metric_summary` (`scoring_common.py` L703-704) actually computes:

- `high_auc` from `adjusted_high` — the high probability **after**
  `apply_component_business_rules` (`score_indices` L768-777), i.e. after a
  disclaimer has zeroed specialized-advice legitimization and
  prompt-repetition has zeroed enablement;
- `binary_present_auc` from `adjusted_score` — the **combined, rule-adjusted
  component score** (`score_from_centered_probs`), not the nonzero head's
  centered probability at all.

So D-16's decision text and its rationale both assert facts about the reference
implementation that are not true, and the one that matters is the pre-rule /
post-rule distinction: "centered probability" (D-16's literal instruction) and
`adjusted_high` (D-16's stated reference) are the same array only for rows no
business rule touched. Choosing the literal instruction makes production's AUC
a different statistic from the ≈0.808 / ≈0.783 figures in `PLAN.md` §8.2 — the
one parity target DR-4 established should stay tight (D-2's amendment
explicitly exempts AUC from D-10's loosening on the grounds that it is
gate-invariant). It is gate-invariant; it is not rule-invariant, and no
decision addresses that. This also compounds DI-C3: under the post-rule
reading, D-4 rows *do* have a natural value (the rule-zeroed one), so the two
findings likely have a single answer.

### DI-Q2. D-7's amendment enumerates exactly two exclusions and thereby implicitly denies a third that must exist for legitimization

D-7's amendment (locked, from DR-1) pins `mean`/`scale` to "training rows net
of **BOTH** D-1's holdout-seed exclusion **AND** D-4's empty/echo-only
exclusion — i.e., over exactly the rows that survive both exclusions applied to
the raw training CSV, not 'all' rows in an unqualified sense." The emphatic
"exactly" was the point of the amendment, and `PLAN.md` §2.3 and §3 step 4 both
repeat the two-exclusion formulation.

For the legitimization component there is a third, mandatory exclusion:
enablement-only hazard rows carry no `legitimization_value` (§2.1: blank/NA),
and the toy drops them before embedding
(`run_bge_sentence_embeddings.py` L94) and before scoring
(`scoring_common.py` L223). They cannot be in the legitimization fit. Yet no
ledger entry records this as a training-row exclusion — D-15 covers only
`hrc-evaluate`'s *reporting*, and its own text is careful to say it is "a
restatement … not a new modeling change," so it cannot be read as the
authority for a fit-time row-set rule either.

An implementer following D-7's "exactly these two" instruction literally
includes `prv`/`sxc_prn` rows in legitimization's `mean`/`scale` (and, by the
same sentence's construction, `center_mean`) — which shifts the standardization
of every legitimization score. This is DR-1's failure mode one level down: the
amendment that fixed an omission created a closed enumeration that omits
something else.

### DI-Q3. D-12 asserts the generalization concept is "preserved instead via D-1's split," but no decision makes that split happen

D-12 (locked) drops grouped k-fold CV, resting on: "The
held-out-generalization *concept* the toy used grouped CV to approximate is
preserved instead via D-1's single reserved holdout-seed split." D-13 (locked)
then specifies what happens when there is no such split: everything lands in
`in_sample_unrecorded`, and `hrc-evaluate` warns that "no reported number for
this run is a verified generalization number."

Nothing anywhere sets `--holdout-seed-fraction`. D-1 is conditional ("when
`hrc-train --holdout-seed-fraction` is > 0"); `PLAN.md` §3's CLI line omits the
flag entirely and the following paragraph introduces it with "Optionally." So
the default training workflow produces an artifact for which D-13's warning
fires and D-12's asserted preservation does not occur. The toy's CV reporting
was unconditional; its replacement is opt-in with the opt defaulting off.

The same gap reaches §8.2: the parity figures are the toy's **heldout**
numbers, so reproducing them requires an artifact trained *with* a holdout
fraction — a precondition the parity decision (D-2, and D-10's amendment to it)
never states.

### DI-Q4. D-17's single `n_rows` per population cannot express the three different denominators the ledger already requires

Within one population, three distinct row counts are now in play:

- all scored rows (the enablement component's denominator);
- legitimization-eligible rows — enablement-only hazards excluded (D-15);
- final-label-eligible rows — specialized-advice hazards excluded (D-17 §3,
  `PLAN.md` §5).

D-17's schema reports one `n_rows` per population plus `final_label.n`. The
legitimization component's actual denominator is therefore reportable nowhere,
even though D-15 is the decision that made it differ, and a reader comparing
`components.enablement` to `components.legitimization` has no way to see that
they were computed over different row sets. (The committed `metrics.py`
mirrors this: `final_label_metrics` returns `n`, `component_metrics` returns
no count at all.)

### DI-Q5. D-17 (locked) depends on `PLAN.md` §11 open question 3, which is still open

D-17 §3 defines `N` as "the same final-label-eligible population used for
precision/recall/F1 in that split (**specialized-advice hazards excluded**, per
§5)." §11 open question 3 reads, unchanged: "The toy excludes them from the
final safe/unsafe headline and relies on `is_safe_ground_truth`. **Confirm this
holds for production reporting.**"

So a locked entry's denominator — the divisor under both headline safety rates
— is pinned to a question the plan still lists as unconfirmed. Either the
question is in fact settled and should be closed the way §11 item 1 was closed
by D-3/D-11, or it is genuinely open and D-17 §3 was locked prematurely. The
ledger gives no way to tell which, and D-15 quietly leans on the same
unconfirmed rule (it takes care to state that enablement-only rows stay in the
final-label population, without noting that specialized-advice rows do not).

---

## nice-to-have

### DI-N1. D-17's schema has no convention for undefined metrics, which D-13's split makes common

D-13 splits every population in two, so small held-out populations are the
normal case, and degenerate metrics follow: AUC is undefined on a single-class
population (the toy's `safe_auc` returns `None`; the committed `_safe_auc`
matches), and `cohen_kappa_score` returns `NaN` with an `UndefinedMetricWarning`
on a single-class input (already noted in `STATUS.md`'s log as accepted
behavior). D-17 lists `auc` and `qwk` as plain schema fields with no null
convention. Left unpinned, `json.dump` will emit a bare `NaN` token for QWK,
which is not valid strict JSON and will fail strict parsers downstream.

### DI-N2. D-12's Touches missed §2.1, which still advertises grouped CV

`PLAN.md` §2.1 describes `seed_prompt_id` as the "grouping key for held-out /
grouped CV." D-12 removed grouped CV from scope and its Touches list names
§1.1, §5, §9, and §10 — not §2.1. Harmless, but it is the schema table, which
is the first place an implementer looks.

### DI-N3. `status` is binary while D-2's `n_own >= 5` cliff creates a third regime the artifact cannot express

D-2 records the `n_own >= 5` cliff explicitly (5 own rows → hazard-specific
thresholds, 4 → pooled fallback). That produces three cell states, not two:
hazard-specific thresholds, pooled-fallback thresholds, and (under whichever
DI-C1 reading wins) skipped. §4's `status: "fit" | "skipped"` collapses the
first two, so a consumer reading `"fit"` cannot tell whether the served
thresholds were tuned for that hazard or borrowed from the pool — and D-3/D-11
treat both as fully serviceable. This may well be the intent; it is unrecorded
either way.

---

## Checked and cleared (no finding)

- **D-9/D-10 vs. D-13/D-14/D-16.** The monotonicity gate changes only the
  discrete combination, so it does not disturb D-13's partitioning, D-14's
  exclusion predicate, or D-16's retained probabilities. DR-4's gate-invariance
  argument for AUC survives the new entries intact (the separate rule-adjustment
  question in DI-Q1 is orthogonal to the gate).
- **D-6 (CPU-only) vs. everything added since.** No new decision introduces a
  device-dependent or nondeterministic path; §8.1's unconditional determinism
  claim still holds.
- **D-8 vs. D-7's amendment.** `class_weight="balanced"`'s
  `sample_weight`-blindness is orthogonal to which rows are eligible; narrowing
  the row set does not change the documented wart.
- **D-11's amended precedence vs. D-14.** Reusing the identical predicate and
  changing only the consequence is internally consistent; the unseen-hazard /
  skipped-cell precedence split carries over to `hrc-evaluate` without
  ambiguity (given DI-C1's definition question answered).
- **D-17 §1-§3 vs. the toy.** `safe = 1`, the labeled 2×2, and the shared
  denominator for false-safe/false-unsafe are mutually consistent and match the
  toy's README instruction; the committed `final_label_metrics` implements them
  faithfully.

---

## Open Questions

1. **DI-C1 — what does `"skipped"` actually mean?** Is a cell skipped when the
   target hazard has zero own rows (a state the toy fits normally, via
   other-hazard rows at 0.25 weight), or when the component's label vector is
   single-class (the only condition that actually triggers the toy's
   constant-probability substitution)? Every downstream fail-closed and
   exclusion behavior (D-3, D-11, D-14, D-17's counts) hangs on this. I am
   confident about what the toy does (~95%); I have no basis to choose which
   behavior you want in production.
2. **DI-C2 — are legitimization cells enumerated for `prv`/`sxc_prn` at all?**
   The clean resolution is that they are not — the component is *not required*
   for those hazards, so the cell is never consulted rather than
   consulted-and-rejected — which would also give `PLAN.md` §5's undefined
   "required component" phrase a definition. But that is a modeling/contract
   decision that changes D-5's enumeration rule and D-3/D-11's error contract,
   and only you can authorize it. Flagging with high confidence that the
   current literal reading is broken (~95%) and lower confidence about the
   intended shape of the fix.
3. **DI-C3 / DI-Q1 — one question, most likely one answer.** Should the
   reported AUC be computed from the **rule-adjusted** high probability (what
   the toy's `high_auc` actually uses, which both preserves §8.2 parity and
   gives D-4's head-less rows a natural value of 0), or from the **pre-rule**
   centered probability (D-16's literal text, which then needs a separate rule
   for D-4 rows)? Per META_PLAN §4 the *magnitude* of the difference is
   measurable rather than arguable — but only once §8.2's cached-embedding
   fixture exists, and the fixture data is not committed (confirmed in the
   earlier D-10 slice), so this cannot be settled by a small slice today.
4. **DI-Q2 — are enablement-only rows inside or outside legitimization's
   `mean`/`scale`/`center_mean` row set?** They have no legitimization label, so
   "outside" is nearly certain (~95%), but D-7's amendment was deliberately
   written as a closed two-item enumeration and I will not silently add a third
   item to a locked entry.
5. **DI-Q3 — should `--holdout-seed-fraction` have a non-zero default, and
   should the §8.2 parity harness require a holdout-trained artifact?** This is
   a cost/risk tradeoff (holding rows out shrinks an already-thin ~800-row
   training set, and interacts with D-2's `n_own >= 5` cliff and DI-C1's
   zero-row question) — squarely a call for you, not me.
6. **DI-Q5 — is §11 open question 3 settled?** If specialized-advice exclusion
   from the final-label headline is confirmed, §11 item 3 should be closed
   pointing at D-17 the way item 1 was closed pointing at D-3/D-11. If it is
   not settled, D-17 §3's denominator is provisional and should say so.


## User Responses

- DI-C1: Do what the toy does
- DI-C2: Go with the component is *not required* for those hazards, so the cell is never consulted rather than consulted-and-rejected 
- DI-C3: AUC computed from the **rule-adjusted** high probability
- DI-C4: (b) moving the excluded counts to the top level alongside holdout_recorded.
- DI-Q1: Compute the reported per-component AUC from adjusted_high — the high head's centered probability after apply_component_business_rules — not from the raw centered probability D-16's text currently names.
- DI-Q2: outside
- DI-Q3: Make the default zero
- DI-Q4: Record the legitimization component's actual denominator so that we can figure out later how to use it.
- DI-Q5: Yes. item 3 should be closed.

