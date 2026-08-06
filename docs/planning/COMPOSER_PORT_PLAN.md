# Porting the shared embedding and L/E scoring into a Composer DAG

**Written** 2026-08-06. **Status:** plan, nothing built.

**Goal.** Reuse two components of this evaluator — stage 8 (shared embedding,
`ARCHITECTURE.md` §8) and stage 9 (L and E scoring, §7 row 9) — inside a
`Composer` DAG in `modelplane-flights`, wrapped by modelbench's
`SafetyDAGAnnotator`. Everything else in that DAG — decoding, refusal detection,
and final integration — is written by others and is **not** ported from here.

This document is an outbound port plan, not a release item. It changes nothing
about Release 1.1's scope, and it is not in
`RELEASE_1_1_QUEUE_PROPOSAL.md`'s queue.

**Repos.** Paths below are prefixed by repo where ambiguous; unprefixed paths are
relative to this repo.

| Repo | Role | Changes |
|---|---|---|
| `hazard-response-classifier` (here) | source of the two components | small: a serve-only surface (§6 phase 1) |
| `modelbench` | framework: `Composer`, `DAGAnnotator`, node types | **none** |
| `modelplane-flights` | where the port lives | all new code, **on a new branch off `main`** |

`modelplane` is out of scope; its relevant parts now live in modelbench.

---

## 1. Decisions taken

Decided by Kurt, 2026-08-06, before any code.

| # | Decision |
|---|---|
| D-1 | This repo is installed as a **git dependency**; the new nodes are thin adapters that call `EmbeddingComponent` and `MultinomialPerHazardScorer` **unchanged**. No code from here is copied. |
| D-2 | The ported evaluator is a **separate DAG alongside** the existing LLM-scorer DAG, sharing its decoder and refusal detector — not a replacement for, and not an added member of, the existing ensemble. |
| D-3 | **Stage 4 (prompt-repetition removal) is ported too**, so the text the models see at serve time is the `working` view they were fit on (`ARCHITECTURE.md` §5, D-55; the artifact manifest records `text_view: "working"`). |
| D-4 | The `release_1_1_le` artifact is **committed into modelplane-flights** (~900 KB, 5 files). `artifacts/` is gitignored here, so the artifact has no distributable home today. |

---

## 2. What already fits, and what does not

### Fits

- **Hazard vocabulary is identical.** `artifacts/release_1_1_le/rules.json`
  `supported_hazards` is exactly the 15 codes carried by
  `modelplane-flights/evaluators/security/batch_2_human_and_1.0_labels_with_gt.csv`
  (`cse, dfm, hte, ipv, iwp, ncr, prv, spc_ele, spc_fin, spc_hlt, spc_lgl, src,
  ssh, sxc_prn, vcr`). No mapping layer, and D-57's artifact-derived
  `hazard_scope` needs no narrowing.
- **Score vocabulary is identical.** The DAG's existing `PromptEngineeredNode`
  scorers emit an ordinal their arbiter reads with `int(...)`. Stage 9 decides by
  `argmax` over three classes and labels `L0/L1/L2`, `E0/E1/E2` — the same 0/1/2.
- **A rudimentary final integrator already exists there.**
  `EnablementLegitimizationSafetyArbiterEnsemble.model_label` applies a
  hazard-family table (`spc_*` / `prv`+`sxc_prn` / default) that is phase A plus
  the L/E-to-result table in miniature. It has no phase C and no failure state,
  but with a **single** sut uid its vote degenerates correctly
  (`num_unsafe >= num_safe` gives unsafe on 1/0, safe on 0/1), so the ported DAG
  reuses the class unchanged.
- **`SafetyDAGAnnotator` needs no work.** Wrapping is
  `SafetyDAGAnnotator(uid, dag)`; the DAG's `verdict_type` is already `Safety`.
- **Python versions are compatible** (modelbench `>=3.12`, this repo `>=3.11`).

### Does not fit

- **The component signature.** Components here are
  `run(record: EvaluationRecord) -> EvaluationRecord` (`ARCHITECTURE.md` §6);
  Composer nodes are `run(ctx: EvalContext) -> NodeOutput`. Every node in §4 is
  an adapter across that boundary.
- **Embedding is per-batch here, per-row there.** §8 requires one
  `provider.embed` call per record, shared across every evaluated hazard. That
  invariant is preserved by §4's node split (one embedding node feeding both
  scorers), but cross-*row* batching is lost — Composer is row-at-a-time.
- **modelbench carries no local-model dependency.** There is no `torch` or
  `sentence-transformers` anywhere in it, and it is a published package. This is
  why the port lives in flights and modelbench is untouched.

---

## 3. The slice and its dependency closure

Ported: `evaluator/components/embedding.py`, the `MultinomialPerHazardScorer`
half of `evaluator/components/scoring.py`, and — per D-3 —
`evaluator/components/{empty,decoding,repetition}.py`.

Transitive closure, all reached by import rather than copy:

```
embedding.py    -> preprocess/segment.py, embed.py (sentence-transformers, torch),
                   config.py, evaluator/{record,contract}.py
scoring.py      -> rules.py (resolve_component_action), evaluator/artifact.py
artifact.py     -> rules.hazard_family, training/multinomial.py (imports sklearn
                   at module scope), training/provenance.py, no_fixed_rules.py
repetition.py   -> preprocess/{decode,flags}.py
decoding.py     -> preprocess/decode.py
input_schema.py -> build_record(row, run_context)
run.py          -> RunConfig, RunContext, open_run
```

12 modules, ~2,700 lines, a large fraction of it docstring. Two warts the port
inherits and should not paper over:

- `evaluator/training/multinomial.py` imports `sklearn.linear_model` at module
  scope, so **loading an artifact pulls sklearn in at serve time** even though a
  fitted `MultinomialCell` is pure NumPy and no estimator survives a fit (D-37).
  Harmless, but it makes the serve-time dependency set larger than the serve-time
  code needs. Splitting the fitted class out of the fitter's module would fix it;
  that is a change here, not there.
- `evaluator/components/scoring.py` imports `hazard_classifier.rules`, whose
  neighbours include the baseline's fixed business rules. That adjacency is
  exactly why `assert_no_fixed_rule_import` runs at the foot of that module
  (`PREREGISTRATION_LE_STRUCTURE.md` §2.1). **The adapter must not defeat it** —
  a flights-side wrapper that reached into `rules.apply_legitimization_disclaimer_rule`
  would reintroduce the double-counting phase C exists to prevent.

---

## 4. Proposed DAG

```
jailbreak_decoder (existing, flights)
  └─> simple_refusal_detector (existing Router, flights)
        ├ True  -> Safety(is_safe=True)
        └ False -> hrc_text_prep (Router)
                     ├ exhausted -> Safety(is_safe=True)
                     └ ok        -> hrc_embedding (Enricher, Cacheable)
                                      ├-> hrc_legitimization_scorer (Enricher -> 0|1|2)
                                      └-> hrc_enablement_scorer     (Enricher -> 0|1|2)
                                            └-> hrc_safety_arbiter (Arbiter)
```

**`hrc_text_prep`** — builds an `EvaluationRecord` from the context, runs stages
1 (empty), 2 (decoding), 4 (prompt-repetition removal), and emits an
`updated_ctx` whose `response` is the resulting `working` text. It is a
**Router**, not an Enricher, because §3.1's exhaustion short-circuit maps
directly onto Composer routing: a response emptied by repetition removal has no
authored content, which phase B1 resolves to L0/E0 → non-violating. Routing it to
`Safety(is_safe=True)` reproduces that outcome **without giving this node a
scientific decision to make** — the §6 rule that a component records only what it
detected or removed still holds, because the routing table is the DAG's, not the
component's.

**`hrc_embedding`** — one `provider.embed` pass over the segmented working text,
mean-pooled; publishes the pooled vector as its `NodeOutput.value`. Both scorers
read it from `ctx._parent_outputs`, exactly as the existing arbiter reads its
parents. **This is what keeps §8's "embed once per record, share across every
evaluated hazard" true inside a per-node DAG** — re-embedding per scorer node
would be the same defect §8 names, wearing a different shape. It is also the one
node worth marking `CacheableNodeMixin`: deterministic, and the expensive one.

**`hrc_legitimization_scorer` / `hrc_enablement_scorer`** — each constructed with
a `target`, each calls `MultinomialPerHazardScorer.run(record)` and reads only
its own target's `Judgment` off the returned record. The duplicated call is one
matmul against a `(768, 3)` coefficient matrix; not worth a custom arbiter to
avoid. `Judgment.distribution` is available and should be recorded in the node's
output even though the arbiter consumes only the label.

**`hrc_safety_arbiter`** — `EnablementLegitimizationSafetyArbiterEnsemble` with a
single sut uid (e.g. `hrc-release-1.1-le`), unchanged.

### Carrying the record between nodes

`EvalContext.hash()` does `json.dumps(self.metadata)`, so **nothing
non-JSON-serializable may go in `metadata`** — not the `EvaluationRecord`, not
the pooled vector. Both travel in `NodeOutput.value`, which diskcache pickles.
Flags and the resolved hazard are JSON-clean and belong in metadata.

---

## 5. Open risks

1. **Which decoder produces `working`.** The artifact was fit with this repo's
   stage-2 decoder (`baseline_best_readable_view`, recorded in the manifest's
   `components` block). The DAG's `jailbreak_decoder` is a different,
   jailbreak-specific decoder (rot13, leetspeak, CodeChameleon, GPT-4-simulator).
   Recommendation: chain them — `jailbreak_decoder` first, since it handles
   obfuscation `preprocess/decode.py` cannot, then stage 2 on its output, which
   should approach a pass-through on already-decoded text. **This is a deviation
   from the training feature path** and must be recorded in the node's facts and
   measured (§6 phase 4), not assumed harmless.
2. **Hazard is mandatory here and optional there.** Stage 9 fails closed on an
   unknown hazard (`resolve_component_action` → `fail_unseen_hazard`; D-45's
   unavailable-is-unavailable, D-3's fail-closed). The flights arbiter does
   `ctx.metadata.get("hazard", "")` and silently falls into the default family,
   and `demo.csv` carries only `{"jailbreak": ...}` with no hazard at all. Decide
   explicitly whether a missing hazard raises (→ `FailedDAGOutput`) or routes to
   a failure verdict. **Raising is the honest default** and is what §2's
   run-entry rejection would have done.
3. **Threading.** §6 (D-61) makes no thread-safety claim and calls the embedding
   provider's backend "unverified under concurrency"; the flights notebook calls
   `dag.run_dataframe(..., n_jobs=-1)`, a `ThreadPoolExecutor`. Either verify or
   hold a lock around `provider.embed`. D-61's stated escape — parallelism at the
   process level — is not available inside a Composer.
4. **Offline weights.** `BgeEmbeddingProvider` defaults to `allow_download=False`
   (`local_files_only=True`, D-6's CPU-only choice). Any runner needs BGE
   pre-cached or the flag set.
5. **Cache key is process-unstable.** `EvalContext.hash()` uses Python's `hash()`
   on strings, which is `PYTHONHASHSEED`-randomized, so a persistent `DiskCache`
   gets no cross-process hits. Pre-existing in modelbench, but it costs far more
   once the cached node is a CPU embedding pass. A stable `cache_key` override on
   the embedding node (blake2b over the text) is the fix.
6. **Repo access.** `git@github.com:bollacker/hazard-response-classifier` is a
   personal repo on an SSH remote. If it is private, no CI can install it. Resolve
   before the dependency can be anything but a local editable install.
7. **Model quality is explicitly unestablished, and the port cannot change that.**
   The artifact's manifest carries the `not_evaluated` block for this reason:
   D-68 is a null result, the selected structure scores *below* the incumbent on
   Legitimization, and every figure behind it is a dev-set number (D-66) on
   out-of-version labels (D-63) from 635 feature rows. `SCIENCE.md` §Evidence and
   outputs requires both models to be reported **not evaluated**, and **that
   requirement travels with the components.** A verdict this DAG emits is not a
   validated one, and nothing downstream may present it as one.

---

## 6. Phases

### Phase 0 — make this repo installable
- Resolve repo access (risk 6).
- Confirm `pip install git+...@<sha>` yields a working
  `from hazard_classifier.evaluator...` import in a clean 3.12 venv.
- Pin a commit sha; the port depends on an immutable version, not `main`.
- **Exit:** a clean venv loads `artifacts/release_1_1_le` and scores one row.

### Phase 1 — a serve-only surface (here, small)
Optional but cheap, and it is what keeps the adapter thin and keeps flights out
of this package's internals:
- A public helper that builds a `RunContext` plus a registry for serve-time use
  only — stages 1/2/4/8/9, no runner, no CSV, no final integration.
  `profile.build_registry` and `input_schema.build_record` already do the work;
  what is missing is a **supported entry point**, so flights does not depend on
  module layout §3.2 explicitly warns is an enumeration that goes stale.
- Consider splitting `MultinomialCell`/`TargetModel` out of
  `training/multinomial.py` so serve time does not import sklearn (§3).
- **Exit:** flights imports only documented names.

### Phase 2 — the nodes (flights, new branch off `main`)
- New branch, e.g. `hrc-le-evaluator`.
- `evaluators/components/hrc_le.py`: `HrcTextPrep` (Router), `HrcEmbedding`
  (Enricher + `CacheableNodeMixin`), `HrcScorer` (Enricher, parameterized by
  target). Lazy imports of `hazard_classifier` so the module is importable
  without it installed.
- `evaluators/components/tests/test_hrc_le.py`, guarded with
  `pytest.importorskip("hazard_classifier")`.
- A dependency manifest on the branch — flights has none today — declaring
  `hazard-response-classifier @ git+...@<sha>`.
- Note: `.github/workflows/tests.yml` there still checks out `mlcommons/modelplane`
  and `uv sync`s in it before running the component tests. With modelplane out of
  scope that workflow needs revisiting; flag it rather than silently rewiring it.
- **Exit:** component tests pass locally and skip cleanly without this package.

### Phase 3 — the DAG and the artifact (flights, same branch)
- Commit `artifacts/release_1_1_le/` (5 files, ~900 KB) per D-4.
- `evaluators/security/hrc.py`, mirroring `security.py`'s builder shape:
  `build_hrc_jailbreak_dag(secrets, metadata_key, artifact_path, cache_path)`.
- `evaluators/security/hrc_end_to_end.ipynb`, mirroring `end_to_end.ipynb`:
  `dag.visualize()`, `visualize_run(ctx)` on the same demo contexts,
  `run_dataframe`.
- **Exit:** the notebook renders the DAG and scores the demo rows.

### Phase 4 — parity harness
The claim to establish is that the DAG produces **the same L and E ordinals** as
`hrc-run` on the same responses. Anything else means the port changed the science.
- Take a fixed sample from `batch_2_human_and_1.0_labels_with_gt.csv`.
- Run `hrc-run` on it directly; run the DAG on it; compare per row.
- Any mismatch is a text-view difference (risk 1) and must be **explained**, not
  tolerated — the same discipline `scripts/probe_disclaimer_scope.py` and
  `scripts/build_interim_split.py --check` apply: the numbers are checkable, not
  asserted.
- **Exit:** a documented agreement rate with the residual attributed.

### Phase 5 — comparison, and only then conclusions
- Run both DAGs (existing LLM ensemble, new port) over the same rows.
- Report agreement, and each against `ground_truth_is_safe`.
- **Exit:** a write-up carrying risk 7 **beside** the figures, not beneath them —
  §11's reason for refusing to ship `metrics.json` (D-80) applies unchanged here:
  a consumer reads keys, not caveats.

---

## 7. What this plan deliberately does not do

- Does not change modelbench.
- Does not port final integration (`evaluator/components/integration.py`), phases
  A–D, the `EvaluationRecord`-derived views (§11), or the batch runner. The
  arbiter is the DAG's, per the framing.
- Does not port stages 3, 5, 6, 7 (hazard detection, narrative, refusal,
  disclaimer). Three are placeholders in 1.1 by decision (D-54), and the DAG has
  its own refusal detector.
- Does not attempt to establish whether the L/E models are accurate. That is
  blocked on approved per-outcome criteria (D-63, D-77), which are not coming.
