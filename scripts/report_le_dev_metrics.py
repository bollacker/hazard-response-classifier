#!/usr/bin/env python3
"""PR 5 slice D: the per-outcome report for Release 1.1's L and E models
(`docs/planning/PR5_EXECUTION_PLAN.md` §8).

Scores the **dev slice** with the shipped artifact and reports every outcome
separately -- L0, L1, L2, E0, E1, E2 -- with per-class precision, recall, and
F1, each carrying a cluster-bootstrap interval over `prompt_group_id`.

**Every number this writes is reported *not evaluated*, and that is not a
footnote.** `SCIENCE.md` §Legitimization Scoring and §Enablement Scoring make
a model scientifically successful only against **approved per-outcome
criteria on a fixed, human-labeled evaluation set**. No such criteria exist
(`STANDARDS_REQUEST.md` Ask B, [D-63](../docs/planning/DECISIONS.md#d-63)),
so no figure here can be read as success or failure. Four further bounds ride
along, and all four are properties of the *data*, not of this script:

- **Dev-class only** ([D-66](../docs/planning/DECISIONS.md#d-66)). The held-out
  slice is a development set. Nothing measured on it is a benchmark result or
  a generalization estimate.
- **Out-of-version labels** (D-63): human judgments made against Jailbreak
  v1.0, used for a v1.4 evaluator.
- **Attacked prompts only** ([D-65](../docs/planning/DECISIONS.md#d-65)).
  `SCIENCE.md` requires naive coverage too; no row supplies it.
- **The structure was selected on a null result**
  ([D-68](../docs/planning/DECISIONS.md#d-68)). No candidate beat the
  incumbent, and on Legitimization the selected structure scored below it.

**Why per class and not one number.** A single accuracy figure hides a rare
class: on this data a majority-class predictor scores 0.569 on L and 0.636 on
E while being useless on the two classes that matter
(`PREREGISTRATION_LE_STRUCTURE.md` §3). `SCIENCE.md` requires all three
outcomes be treated as **equally important**, which is why accuracy appears
here only as a labelled diagnostic and macro-F1 is never reported without its
worst class beside it (`QUEUE_ITEM_2_EXECUTION_PLAN.md` §10 lesson 5).

**Why precision and recall, not F1 alone.** They fail in opposite directions
and F1 cannot say which. A class at F1 0.30 built from precision 0.90 /
recall 0.18 is a model that rarely claims the class and is usually right when
it does; at 0.18 / 0.90 it is the opposite model. For a safety classifier
those are not interchangeable.

**Per-hazard figures are weak by construction** and are reported as intervals
only, never as point estimates: roughly 15 dev rows per hazard
(`PREREGISTRATION_LE_STRUCTURE.md` §7).

This writes both outputs so they cannot drift: a JSON record and the Markdown
report generated from it.

Run:  python scripts/build_release_artifact.py        # once, if needed
      python scripts/report_le_dev_metrics.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hazard_classifier.evaluator.artifact import load_artifact  # noqa: E402
from hazard_classifier.evaluator.training.features import build_pipeline_features  # noqa: E402
from hazard_classifier.experiments.comparison_metrics import (  # noqa: E402
    BOOTSTRAP_SEED,
    N_RESAMPLES,
    Predictions,
    classification_metrics,
    cluster_bootstrap_interval,
    macro_f1_score,
    per_class_f1,
    per_class_precision,
    per_class_recall,
    worst_class_f1_score,
)
from hazard_classifier.interim_data import (  # noqa: E402
    INTERIM_SPLIT,
    legitimization_rows,
    load_interim,
)

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = REPO / "artifacts" / "release_1_1_le"
DEFAULT_JSON = REPO / "docs" / "planning" / "pr5_results" / "dev_metrics.json"
DEFAULT_MARKDOWN = REPO / "docs" / "planning" / "PR5_DEV_METRICS.md"

TARGETS = ("legitimization", "enablement")
_PREFIX = {"legitimization": "L", "enablement": "E"}
_LABEL_COLUMN = {
    "legitimization": "legitimization_value",
    "enablement": "enablement_value",
}

NOT_EVALUATED = (
    "NOT EVALUATED. No approved per-outcome success criteria exist "
    "(SCIENCE.md §Legitimization/Enablement Scoring, STANDARDS_REQUEST.md Ask B), "
    "so no figure below is a success or a failure. Dev-set numbers (D-66) on "
    "out-of-version labels (D-63), attacked prompts only (D-65), from a structure "
    "selected on a null result (D-68)."
)

UNCERTAINTY_METHOD = (
    "Cluster bootstrap over prompt_group_id, resampling whole groups rather than "
    "rows (rows sharing a prompt are correlated, so a row-level bootstrap would "
    "understate the interval), percentile 95% interval, "
    f"{N_RESAMPLES} resamples, seed {BOOTSTRAP_SEED}."
)

# Below this many groups a cluster bootstrap has too few distinct resamples to
# describe sampling variability at all: with 3 groups there are only
# C(3+3-1, 3) = 10 distinct multisets, so the "interval" is an enumeration of
# a handful of reshufflings of three clusters. **A narrow interval there means
# fewer clusters, not more certainty** -- which is the reading a table invites
# and the reason this threshold is applied and marked rather than assumed
# obvious. Chosen as a readability threshold, not a statistical criterion; no
# approved uncertainty method exists to set one (STANDARDS_REQUEST.md Ask B).
MIN_GROUPS_FOR_A_MEANINGFUL_INTERVAL = 10


def _interval(y_true, predictions, groups, metric, n_resamples):
    return cluster_bootstrap_interval(
        y_true, predictions, groups, metric=metric, n_resamples=n_resamples
    ).as_dict()


def _per_outcome(y_true, predictions, groups, n_resamples) -> list[dict]:
    """One entry per class: support, and precision/recall/F1 each with its
    own interval. `SCIENCE.md`'s equal-importance requirement is what makes
    this the unit of reporting rather than a single averaged figure.
    """
    scored = np.asarray(predictions.scored, dtype=bool)
    y_scored = np.asarray(y_true)[scored]

    out = []
    for cls in range(3):
        out.append(
            {
                "class": cls,
                "support": int((y_scored == cls).sum()),
                "predicted": int((np.asarray(predictions.labels)[scored] == cls).sum()),
                "precision": _interval(
                    y_true, predictions, groups,
                    lambda yt, yp, k=cls: float(per_class_precision(yt, yp)[k]),
                    n_resamples,
                ),
                "recall": _interval(
                    y_true, predictions, groups,
                    lambda yt, yp, k=cls: float(per_class_recall(yt, yp)[k]),
                    n_resamples,
                ),
                "f1": _interval(
                    y_true, predictions, groups,
                    lambda yt, yp, k=cls: float(per_class_f1(yt, yp)[k]),
                    n_resamples,
                ),
            }
        )
    return out


def _per_hazard(y_true, predictions, groups, hazards, n_resamples) -> list[dict]:
    """Macro-F1 with an interval, per hazard. Deliberately **not** per class
    per hazard: ~15 dev rows per hazard cannot support nine figures, and
    reporting them would dress noise as detail. The interval is the finding.
    """
    y_true = np.asarray(y_true)
    hazards = np.asarray(hazards)
    labels = np.asarray(predictions.labels)
    scored = np.asarray(predictions.scored, dtype=bool)

    rows = []
    for hazard in sorted(set(hazards.tolist())):
        mask = hazards == hazard
        subset = Predictions(labels=labels[mask], scored=scored[mask])
        n_groups = int(len(set(np.asarray(groups)[mask].tolist())))
        entry = {
            "hazard": hazard,
            "n_dev_rows": int(mask.sum()),
            "n_scored": int(scored[mask].sum()),
            "n_groups": n_groups,
            # See MIN_GROUPS_FOR_A_MEANINGFUL_INTERVAL: with this few clusters
            # the bootstrap enumerates reshufflings rather than estimating
            # variability, so a narrow interval is a small-sample artifact.
            "interval_degenerate": n_groups < MIN_GROUPS_FOR_A_MEANINGFUL_INTERVAL,
        }
        if subset.scored.any():
            entry["macro_f1"] = _interval(
                y_true[mask], subset, np.asarray(groups)[mask], macro_f1_score, n_resamples
            )
        else:
            # D-45: the model had nothing to say about this hazard. Not zero.
            entry["macro_f1"] = None
            entry["unavailable"] = True
        rows.append(entry)
    return rows


def build_report(artifact_dir: pathlib.Path, *, n_resamples: int, allow_download: bool) -> dict:
    artifact = load_artifact(artifact_dir)
    dev = load_interim(split="eval")

    features = build_pipeline_features(dev, allow_download=allow_download)
    index = features.row_index()

    split_manifest = json.loads(INTERIM_SPLIT.read_text())
    report = {
        "report": "pr5_dev_metrics",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "not_evaluated": NOT_EVALUATED,
        "uncertainty_method": UNCERTAINTY_METHOD,
        "artifact": {
            "id": artifact.artifact_id,
            "version": artifact.artifact_version,
            "created_at": artifact.created_at,
            "fitted_on_split": artifact.models.provenance.split_half,
            "fitted_on_text_view": artifact.models.provenance.text_view,
        },
        "data": {
            "split_version": split_manifest["split_version"],
            "split_half_scored": "eval",
            "split_role_scored": "dev",
            "source_sha256": split_manifest["source_sha256"],
            "n_dev_rows": int(len(dev)),
            "n_rows_exhausted_before_scoring": len(features.exhausted_rows),
        },
        "targets": {},
    }

    for target in TARGETS:
        eligible = legitimization_rows(dev) if target == "legitimization" else dev
        positions = [index[str(uid)] for uid in eligible["prompt_uid"] if str(uid) in index]
        kept = eligible[eligible["prompt_uid"].astype(str).isin(set(index))]

        X = features.pooled[positions]
        y = kept[_LABEL_COLUMN[target]].to_numpy(dtype=np.int64)
        hazards = features.hazards[positions]
        groups = kept["prompt_group_id"].to_numpy()

        proba = getattr(artifact.models, target).predict_proba(X, hazards)
        predictions = Predictions.from_proba(proba)
        metrics = classification_metrics(y, predictions)

        report["targets"][target] = {
            "outcome_prefix": _PREFIX[target],
            "n_dev_rows": int(len(y)),
            "n_scored": metrics.n_scored,
            "coverage": metrics.coverage,
            "unavailable_hazards": sorted(getattr(artifact.models, target).unavailable_hazards),
            # Labelled a diagnostic on purpose: §3 forbids a single accuracy
            # figure from carrying any part of a judgment, because the class
            # balance makes a majority-class predictor look strong.
            "accuracy_diagnostic_only": metrics.accuracy,
            "macro_f1": _interval(y, predictions, groups, macro_f1_score, n_resamples),
            # Never reported without the macro, and never the macro without it.
            "worst_class_f1": _interval(
                y, predictions, groups, worst_class_f1_score, n_resamples
            ),
            "per_outcome": _per_outcome(y, predictions, groups, n_resamples),
            "per_hazard": _per_hazard(y, predictions, groups, hazards, n_resamples),
        }

    return report


def _ci(entry: dict) -> str:
    return f"{entry['point_estimate']:.3f} ({entry['ci_low']:.3f}–{entry['ci_high']:.3f})"


def _describe_outcomes(block: dict) -> list[str]:
    """State what the per-outcome table shows, **generated from the numbers**
    rather than written by hand, so the prose cannot drift from the figures it
    describes on a re-run.

    Deliberately descriptive and never evaluative: it says which outcome the
    model finds least often and how the errors are shaped, and stops. Whether
    that is acceptable is what approved criteria would decide, and they do not
    exist.
    """
    prefix = block["outcome_prefix"]
    outcomes = block["per_outcome"]
    weakest = min(outcomes, key=lambda o: o["recall"]["point_estimate"])
    name = f"{prefix}{weakest['class']}"
    recall = weakest["recall"]["point_estimate"]
    precision = weakest["precision"]["point_estimate"]
    found = int(round(recall * weakest["support"]))

    lines = [
        f"**Reading the table: {name} is the outcome the model finds least often.** "
        f"Recall {_ci(weakest['recall'])} — of {weakest['support']} dev rows that "
        f"truly are {name}, roughly {found} are labelled {name}. Precision on the "
        f"same class is {_ci(weakest['precision'])}."
    ]
    if precision > recall:
        lines.append(
            f"The two are asymmetric: the model **under-claims** {name}, and is more "
            "often right than wrong when it does claim it. F1 alone would not have "
            "shown which way round that was, which is why precision and recall are "
            "reported separately."
        )
    elif recall > precision:
        lines.append(
            f"The two are asymmetric: the model **over-claims** {name}, catching more "
            "of the class at the cost of being wrong more often when it does. F1 "
            "alone would not have shown which way round that was."
        )
    lines.append(
        "This is a description of the numbers, not a verdict on them. Whether it is "
        "acceptable is exactly what approved per-outcome criteria would decide, and "
        "they do not exist."
    )
    return ["- " + line for line in lines]


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    add = lines.append

    add("# PR 5 — per-outcome dev-set report for the Release 1.1 L and E models")
    add("")
    add("**Generated by `scripts/report_le_dev_metrics.py`. Do not edit by hand** —")
    add("edit the script and re-run it, so this file and")
    add("`pr5_results/dev_metrics.json` cannot drift apart.")
    add("")
    add(f"Generated {report['generated_at']}.")
    add("")
    add("## Both models are NOT EVALUATED")
    add("")
    add(f"> {report['not_evaluated']}")
    add("")
    add("This is not a footnote and it is not a hedge about precision. It is the")
    add("`SCIENCE.md` §Evidence and outputs rule: a model is scientifically")
    add("successful only against **approved per-outcome criteria on a fixed,")
    add("human-labeled evaluation set excluded from training**. The criteria do not")
    add("exist, so the question these numbers would answer has not been asked yet.")
    add("A reader who takes any figure below as evidence of quality — in either")
    add("direction — has read it wrongly.")
    add("")
    add("**Uncertainty method**, required alongside every reported figure")
    add("(`SCIENCE.md` §Evidence and outputs, Estimability):")
    add("")
    add(f"> {report['uncertainty_method']}")
    add("")

    artifact = report["artifact"]
    data = report["data"]
    add("## What was scored, and with what")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Artifact | `{artifact['id']}` version `{artifact['version']}` |")
    add(f"| Fitted on | the **{artifact['fitted_on_split']}** half (D-73), "
        f"`{artifact['fitted_on_text_view']}` text view (D-72) |")
    add(f"| Scored on | the **dev** half, held out from fitting — {data['n_dev_rows']} rows |")
    add(f"| Split | `{data['split_version']}` |")
    add(f"| Rows exhausted before stage 9 | {data['n_rows_exhausted_before_scoring']} |")
    add("")
    add("The artifact was fitted on the fit half alone (D-73), so **these numbers")
    add("describe the model that ships** rather than a differently-fitted sibling.")
    add("Held out is not the same as approved: under D-66 this slice remains a")
    add("development set.")
    add("")

    for target, block in report["targets"].items():
        prefix = block["outcome_prefix"]
        add(f"## {target.capitalize()} — **not evaluated**")
        add("")
        add(f"{block['n_scored']} of {block['n_dev_rows']} dev rows scored "
            f"(coverage {block['coverage']:.3f}).")
        if block["unavailable_hazards"]:
            add(f"Unavailable cells (D-45, never substituted): "
                f"{', '.join(block['unavailable_hazards'])}.")
        add("")
        add("### Each outcome separately")
        add("")
        add("Point estimate with a 95% cluster-bootstrap interval.")
        add("")
        add("| Outcome | Dev rows | Predicted | Precision | Recall | F1 |")
        add("|---|---:|---:|---|---|---|")
        for outcome in block["per_outcome"]:
            name = f"{prefix}{outcome['class']}"
            add(
                f"| **{name}** | {outcome['support']} | {outcome['predicted']} | "
                f"{_ci(outcome['precision'])} | {_ci(outcome['recall'])} | "
                f"{_ci(outcome['f1'])} |"
            )
        add("")
        add(f"- **Macro-F1** {_ci(block['macro_f1'])} — "
            f"**worst-class F1** {_ci(block['worst_class_f1'])}. The worst class is "
            "reported every time the macro is, because a respectable macro with a "
            "collapsed third class is exactly the failure equal importance forbids.")
        add(f"- Accuracy {block['accuracy_diagnostic_only']:.3f} — **a diagnostic "
            "only**, never part of a judgment: a majority-class predictor scores "
            "0.569 on L and 0.636 on E on this data while being useless on the two "
            "classes that matter.")
        add("")
        for line in _describe_outcomes(block):
            add(line)
        add("")
        add("### Per hazard — intervals only, and read the group count first")
        add("")
        add("Roughly 15 dev rows per hazard. **These are intervals, not point")
        add("estimates.** But the more important caution is the one a table like")
        add("this actively invites a reader to get backwards:")
        add("")
        add(f"> **A narrow interval here means fewer clusters, not more certainty.**")
        add(f"> The bootstrap resamples prompt *groups*, and almost every hazard has")
        add(f"> **3** of them. With 3 groups there are only 10 distinct resamples in")
        add(f"> existence, so the interval enumerates a handful of reshufflings")
        add(f"> instead of describing sampling variability. Rows marked † have fewer")
        add(f"> than {MIN_GROUPS_FOR_A_MEANINGFUL_INTERVAL} groups and their intervals")
        add(f"> should not be read as uncertainty estimates at all.")
        add("")
        add("The honest summary of this table is that **per-hazard reporting is not")
        add("supportable on this data** — it is included because `SCIENCE.md`")
        add("requires per-hazard judgments and their absence would be the more")
        add("misleading omission, not because any row of it means something.")
        add("")
        add("| Hazard | Dev rows | Groups | Macro-F1 (95% interval) |")
        add("|---|---:|---:|---|")
        for row in block["per_hazard"]:
            value = "— (no fitted cell, D-45)" if row["macro_f1"] is None else _ci(row["macro_f1"])
            marker = " †" if row.get("interval_degenerate") else ""
            add(
                f"| `{row['hazard']}` | {row['n_dev_rows']} | {row['n_groups']}{marker} | "
                f"{value} |"
            )
        add("")

    add("## What these numbers cannot establish")
    add("")
    add("Carried from `PREREGISTRATION_LE_STRUCTURE.md` §7, and binding on any")
    add("downstream claim:")
    add("")
    add("- **No approved success criteria exist**, so both models are *not")
    add("  evaluated* whatever the figures show. The worst-class floor the selection")
    add("  used was a screening threshold, not a success criterion.")
    add("- **Dev-set numbers only** (D-66). Not a benchmark result, not a")
    add("  generalization estimate, not reportable under `SCIENCE.md` §Evidence and")
    add("  outputs.")
    add("- **Out-of-version labels** (D-63) — Jailbreak v1.0 human judgments, used")
    add("  for a v1.4 evaluator. Measured table-level compatibility is 97.2%.")
    add("- **Attacked prompts only** (D-65). `SCIENCE.md` requires naive coverage")
    add("  too, and no row supplies it.")
    add("- **Residual leakage** (`PREREGISTRATION_LE_STRUCTURE.md` §1). Other attack")
    add("  variants of the same seed prompt appear on both sides of the split, so")
    add("  these figures are mildly optimistic about a genuinely new seed prompt.")
    add("- **The selection was measured on different text than the release fits on**")
    add("  (D-72, §7). That D-68's ranking survives the change of input view is an")
    add("  assumption the procedure did not test.")
    add("- **These figures are not comparable with D-68's**, and the difference is")
    add("  not evidence of anything. D-68 recorded macro-F1 0.4336 on L and 0.5289")
    add("  on E for the selected structure; those were fitted on raw `response_text`")
    add("  and these are fitted on working text (D-72). Same dev slice, different")
    add("  input view, **no paired test between them** — and the pre-registration")
    add("  reserves any such comparison for a re-issued selection (§5, D-66).")
    add("  A session that reads the difference as the refit having helped, or hurt,")
    add("  has manufactured a result the procedure did not produce.")
    add("- **The train/serve gap is open** — three of the components that filter the")
    add("  working view are placeholders in 1.1, so a re-fit is owed whenever")
    add("  narrative, refusal, or hazard detection is built. The artifact's manifest")
    add("  records the component set it was fitted against, so that is checkable.")
    add("")
    add("A distribution that sums to 1 is arithmetic. A per-hazard cell fitted on")
    add("roughly 42 rows returns three tidy numbers exactly as readily as a good one")
    add("would, and nothing in this report distinguishes the two.")
    add("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--out-json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--resamples", type=int, default=N_RESAMPLES)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()

    if not args.artifact.exists():
        parser.error(
            f"{args.artifact} does not exist. Build it first:\n"
            "  python scripts/build_release_artifact.py"
        )

    report = build_report(
        args.artifact, n_resamples=args.resamples, allow_download=args.allow_download
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2) + "\n")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(render_markdown(report))

    print(f"wrote {args.out_json.relative_to(REPO)}")
    print(f"wrote {args.out_md.relative_to(REPO)}")
    print()
    for target, block in report["targets"].items():
        prefix = block["outcome_prefix"]
        print(f"{target}: macro-F1 {_ci(block['macro_f1'])}  "
              f"worst-class {_ci(block['worst_class_f1'])}")
        for outcome in block["per_outcome"]:
            print(
                f"  {prefix}{outcome['class']}  n={outcome['support']:>3}  "
                f"P {_ci(outcome['precision'])}  R {_ci(outcome['recall'])}  "
                f"F1 {_ci(outcome['f1'])}"
            )
    print()
    print(NOT_EVALUATED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
