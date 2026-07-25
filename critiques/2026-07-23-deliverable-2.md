# Critique pass: PLAN.md §5 — Deliverable 2 (`hrc-evaluate`)

Date: 2026-07-23
Mechanism: critique (META_PLAN §2)
Scope: PLAN.md §5 ("Deliverable 2 — Performance measurement, `hrc-evaluate`"),
cross-referencing §2.1 (input schema), §3 step 4/5 (the fit logic `--cv` reuses
and the manifest it writes), §4 (artifact/manifest format), §6 (`hrc-predict`'s
now-fully-specified fail-closed machinery), §8.1/§8.2 (determinism + parity),
and §11 open questions. Science/math/engineering problems only; no fixes
proposed. §5 is the least-specified deliverable in the plan (~15 lines) and was
drafted before §6 and D-3/D-4/D-5/D-10/D-11 were locked, so several findings are
"a later decision created an obligation §5 never took up."

Ledger check against `DECISIONS.md` (D-1…D-11): no locked decision resolves any
finding below. The decisions most adjacent are D-1 (holdout-seed exclusion,
whose *entire stated purpose* is to let `hrc-evaluate` measure generalization —
E-1), D-2 (in-sample threshold bias — E-1's footgun), D-3/D-4/D-5/D-11
(`hrc-predict` fail-closed contract, specified only for the *predict* path, not
the *evaluate* path — E-2), and DR-4's finding that AUC is rank-based on centered
probabilities (E-5). None of these state how `hrc-evaluate` behaves; §5 is where
that behavior would live and it is silent. §11 open question 3
(specialized-advice hazards excluded from the headline) is *related* to E-3 but
is itself still unresolved ("Confirm this holds"), so it does not settle E-3.

Reference: no toy source re-read was needed beyond what the two prior critiques
already established; this pass is against the plan + ledger.

---

## blocks-correctness

### E-1. §5 never wires up the generalization measurement D-1 exists to produce, and its default path is an in-sample footgun

D-1's sole rationale is that holdout-seed rows "exist solely so `hrc-evaluate`
can measure generalization to unseen prompt families," and §3 step 4 says the
holdout is reserved "so `hrc-evaluate`'s generalization numbers are never
computed on rows the artifact trained on." That workflow requires `hrc-evaluate`
to know *which* rows of an eval CSV are the held-out ones. The split ids are
recorded only in the artifact's `manifest.json` (§3 step 5), keyed by
`seed_prompt_id`. But §5's default path is described as "load artifact + labeled
eval CSV → … → metrics report" over the whole CSV; it never says `hrc-evaluate`
reads the manifest's holdout split, filters to it, or partitions the report by
holdout membership. As written, the capability D-1 was locked to enable does not
exist end-to-end: nothing connects the reserved split to the metric that is
supposed to be computed on it.

The flip side is a correctness footgun, not just an omission. Because thresholds
and `center_mean` are fit **in-sample** on the training rows (D-2, near-separated
in-sample probabilities, in-sample AUC approaching 1.0), running the frozen
default path against the training CSV — the most obvious first thing a user does
— silently reports the D-2-optimistic numbers, not generalization numbers, with
nothing in §5 warning against it or separating in-sample rows from held-out
rows. §5 gives the reader no way to tell an honest eval CSV from a leaked one.

### E-2. Whether `hrc-evaluate` inherits §6's fail-closed / short-circuit machinery is undefined, and both readings are wrong for a metrics tool

§6 now fully specifies `hrc-predict`'s predict path as a hard contract: unseen
hazard ⇒ raise/error unconditionally (D-3/D-11), empty/echo-only ⇒ score 0
(D-4), non-empty response against a `"skipped"` cell ⇒ raise/error
(D-5/D-3/D-11). §5 says `hrc-evaluate` does "frozen-head predict → component
ordinals → v1.4 combination" without stating whether that is literally the same
predict path. Both resolutions are defective and §5 picks neither:

- **If it reuses §6's path verbatim** (e.g. calls `HazardResponseClassifier`'s
  raising `predict`/`score`), then a *single* eval row carrying an unseen hazard,
  or a non-empty response landing on a skipped cell, raises and aborts the entire
  metrics run. Real eval CSVs — especially the `--holdout-seed-fraction` split of
  unseen prompt families, and any CSV whose hazard set is a superset of the
  artifact's — will routinely contain such rows, so the natural implementation
  crashes on exactly the data it exists to score.
- **If it uses a more permissive path** (score the row anyway to keep the batch
  going), then the reported metrics no longer reflect what the deployed model
  actually does, defeating the "measure a *trained artifact*" goal — a skipped
  cell scored through its degenerate constant-probability parameters is precisely
  the behavior D-5/D-3 forbid in production.

Downstream of that, the per-row **metric accounting** for a row production would
refuse to score is unspecified: silently exclude it from the denominator, count
it as an error, or count it as a wrong prediction — three different headline
numbers. §5 says nothing, and the choice materially moves every rate.

### E-3. The "common denominator" for false-safe / false-unsafe rates is undefined, and its membership is unspecified

§5 promises "false-safe and false-unsafe rates on a common denominator (the
README calls this out explicitly)." The plan never defines "common denominator,"
and it defers the definition to a README that does not exist (STATUS.md and the
D-2/D-8 fix-proposal notes repeatedly record "no project README exists yet"), so
there is no authoritative definition anywhere. Concretely unspecified:

- **Which rows are in the denominator.** §5 excludes specialized-advice
  (`spc_*`) hazards from the final-label headline, so presumably they are out —
  but are enablement-only hazards (`prv`, `sxc_prn`, judged by `E` only per §1.1)
  *in*? They carry an `is_safe_ground_truth` and produce a predicted label, so
  they can be scored, but nothing states whether they belong to the safety
  headline population.
- **Whether both rates truly share one denominator.** "Common denominator"
  reads as: false-safe = FN/N and false-unsafe = FP/N over the *same* N, rather
  than the textbook FN/(actual unsafe) and FP/(actual safe). That is a legitimate
  choice but it is the opposite of how the co-reported precision/recall/F1
  normalize, so the report would mix two conventions on the same page with no
  statement of which N is which.

The false-safe/false-unsafe pair is the headline safety metric a reader will
quote; leaving its population and normalization implicit is the same class of
"silent on exactly the number a reader quotes" gap that D-1 was locked to close.

### E-4. Component-metric row populations under blank / missing labels are unspecified — and one blank is guaranteed by the schema

§2.1 makes `legitimization_value` "blank/NA for enablement-only hazards," and
§1.1 item 2 says the legitimization branch skips those hazards entirely. So the
legitimization component's exact/within-one/AUC/QWK/MAE **must** be computed over
a population that excludes `prv`/`sxc_prn` rows — those rows have no
legitimization ground truth and no legitimization prediction. §5 lists the
per-component metrics but never states this exclusion, so an implementer
computing legitimization QWK/AUC over all rows either crashes on NaN labels or
silently contaminates the metric with rows that have no valid label.

More generally, §5 does not say whether the default frozen path requires
ground-truth for **all** rows or tolerates a partially-labeled CSV. If some
non-enablement-only row has a blank `enablement_value`, `legitimization_value`,
or `is_safe_ground_truth`, the behavior (error, skip-and-exclude, or count-as-
wrong) is undefined, and each choice changes the metric denominators.

### E-5. AUC as defined elsewhere in the plan is not computable from §5's stated pipeline

DR-4 established (and the user let stand) that "AUC" in this project is the
toy's rank-based `safe_auc` computed on the **centered head probabilities**,
which is why it is gate-invariant. A rank AUC requires the continuous per-row
probability. But §5's data flow is "frozen-head predict → **component ordinals**
→ v1.4 combination," and the metric list is reported off that flow. Component
ordinals are the discrete post-threshold 0/1/2 values; they discard the
continuous probability AUC needs. As described, the pipeline throws away its own
AUC input, so the listed AUC metric cannot be produced without §5 also retaining
the head probabilities it does not mention retaining. Relatedly, §5 does not say
*which* probability the per-component AUC ranks (the nonzero/binary-present head
vs. the high head) nor against which binarized label — the toy reports one AUC
per component, but §5 leaves the binarization unstated.

---

## quality

### E-6. `--cv` "reuses the training fit logic on folds" collides with the now-complex §3 fit, and overloads the word "holdout"

When §5's `--cv` bullet was drafted, "the training fit logic" was simpler. It now
carries D-1 holdout exclusion, D-4 empty/echo exclusion, D-5 skipped-cell
enumeration, D-7 standardization row-set rules, and D-10's gated grid search.
Composing per-fold refitting with all of that is unspecified in three ways:

- **Two different "holdout" concepts share the name.** D-1's holdout is a single
  reserved seed set excluded from the *deployed* artifact and recorded in the
  manifest; `--cv`'s per-fold test set is a rotating split with no relation to
  that reservation. §5's phrase "grouped cross-validation + held-out seed-prompt
  evaluation" uses "held-out seed-prompt" for what is now *also* D-1's train-time
  term, without saying whether `--cv` reuses the manifest's D-1 seed ids as one
  fold or re-derives its own split. They are almost certainly different things
  wearing one name.
- **Does `--holdout-seed-fraction` apply inside `--cv`?** Applying a train-time
  holdout reservation on top of per-fold train/test splitting would shrink each
  fold's training rows for no stated reason; ignoring it is probably intended but
  unstated.
- **Per-fold D-5 skipped cells.** A fold is smaller than the full data, so thin
  hazards that are fit on the full artifact will produce many more zero-training-
  row (`"skipped"`) cells per fold. How `--cv` scores test-fold rows landing on a
  cell that is skipped *for that fold* (exclude / error / count-as-wrong) is the
  same undefined accounting as E-2, now multiplied across folds.

### E-7. `--cv`'s relationship to the passed artifact and its fold determinism are unspecified

`hrc-evaluate` is invoked with an artifact, but `--cv` "reuses the training fit
logic on folds," i.e. it refits. §5 never says whether `--cv` loads/ignores the
supplied artifact, and if it refits, where the fit hyperparameters come from —
the artifact's `manifest.json` (`--other-hazard-weight`, model id+revision) or
CLI flags that could silently disagree with the artifact. Separately, grouped CV
(`StratifiedGroupKFold` in the toy) depends on a `random_state` for fold
assignment; §5 pins no CV seed, and §8.1's determinism claim is scoped to
"artifact parameters and scores," which does not obviously cover `--cv` fold
membership — so `--cv` metrics may not be reproducible run-to-run.

### E-8. §5 does not state that `hrc-evaluate` must embed with the artifact's pinned BGE id+revision

§4 pins the BGE model "by id + revision" in the manifest precisely so scoring
uses identical embeddings; the frozen heads are only valid against embeddings
from that exact revision. §5's default path includes "embed" but never says it
resolves the embedding model from the manifest (vs. re-resolving a possibly-newer
`BAAI/bge-base-en-v1.5` HEAD). If `hrc-evaluate` embeds with a different revision
than the artifact was trained on, every frozen-head score — and therefore every
reported metric — is computed on mismatched features. §5 also omits the
offline/`--allow-download` model-access surface that §3 step 3 spells out for
`hrc-train`, even though `hrc-evaluate` has the identical embedding dependency.

---

## nice-to-have

### E-9. `metrics.csv` / `metrics.json` / summary schema is unspecified, in contrast to §4's rigor

§4 specifies the artifact format field-by-field; §5's outputs are a bare
"`metrics.csv` / `metrics.json` + a short human-readable summary" with no column
or key list, no statement of the per-hazard vs. per-component vs. overall
breakdown structure, no indication whether the CSV and JSON carry the same data
in two shapes, and no authority rule if the three outputs ever disagree. This is
under-specification relative to the rest of the plan rather than a behavioral
bug, but it leaves any downstream consumer of `metrics.json` unable to code
against a contract.

### E-10. Final-label metric conventions are unpinned

§5 lists "precision/recall/F1 vs. `is_safe_ground_truth`" without fixing which
class is the positive (presumably `unsafe`, the detection target, but P/R/F1 are
asymmetric and flip meaning if `safe` is chosen), and lists per-component
"confusion counts" without pinning the shape (a 3×3 ordinal matrix?) or how its
denominator relates to rows excluded under E-2/E-4.

---

## Would be settled faster by implementation than analysis (META_PLAN §4)

Most findings here are specification gaps that a decision resolves, not empirical
questions. The one exception is E-1's magnitude: how far the frozen default
path's in-sample numbers (D-2) diverge from held-out numbers is measurable by
scoring the frozen artifact on training rows vs. the `--holdout-seed-fraction`
rows and comparing AUC/QWK. That is the same real-data quantification STATUS.md
already records as deferred (neither `security-evaluator` nor this repo has the
labeled CSV + embeddings committed), so it stays blocked on data, not on more
paper review.

---

## Open Questions

1. **E-2 safety posture (user call).** Should `hrc-evaluate` inherit §6's
   hard-fail contract (and thus abort on any unseen-hazard / skipped-cell eval
   row), or handle such rows gracefully to keep the batch going — and if the
   latter, are those rows excluded from denominators, counted as errors, or
   counted as wrong predictions? This is a product/safety tradeoff the ledger
   does not record; I will not pick it.

2. **E-1 intended workflow (design call, ~70% confidence).** My reading is that
   `hrc-evaluate` should read the manifest's D-1 holdout split and report
   generalization numbers on those rows automatically (partitioning in-sample vs.
   held-out). The alternative — the user manually extracts the holdout rows into
   a separate eval CSV — leaves unstated how they would do so from seed ids that
   live only in the manifest. Below the 90% bar; needs your intent before any
   fix-proposal on E-1.

3. **E-3 denominator membership (domain call).** Are enablement-only hazards
   (`prv`, `sxc_prn`) inside or outside the false-safe/false-unsafe headline
   denominator, and is it literally one shared denominator for both rates? This
   overlaps §11's still-open question 3 (specialized-advice exclusion "confirm
   this holds"), which is itself unresolved — so E-3 cannot be closed until that
   confirmation lands too.

4. **Is `--cv` still in scope at all? (below 90%).** If E-1's wiring is added so
   the frozen default path reports honest held-out generalization numbers, the
   `--cv` research path may be redundant with it. Whether you still want the
   per-fold `--cv` reporting (with all the E-6/E-7 composition cost it now
   carries against the locked §3 fit) or would drop it is a scope judgment only
   you can make.


## User Responses

 - E-2: hard fail samples should be excluded from all measurement. Just record and display the number excluded

 - E-1: Keep your reading.  Do not choose the manual alternative

 - E-3: The function that reads enablement and legitimization scores to generate a safe/unsafe label will ignore legitimization scores for those two hazards. Any fix can assume that will always be true.  So we don't care and don't need to report legitimization scores for those two hazards.

 - Drop --cv from scope

 - E-4: Exclude rows for enablement-only hazards

 - E-5: Retain head probabilities.  Choose the high head. 

 - E-8: Don't worry about it.  Assume a clean slate for each train/evaluate cycle

 - E-9: Make a guess.  We can correct later.

 - E-10: safe = 1 and unsafe = 0

 
