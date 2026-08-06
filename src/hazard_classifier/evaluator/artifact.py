"""The Release 1.1 evaluator artifact: writer and reader
(`docs/ARCHITECTURE.md` §10, `docs/planning/PREREGISTRATION_LE_STRUCTURE.md`
§6, `docs/planning/PR5_EXECUTION_PLAN.md` §6).

This is the deliverable [D-49](../../docs/planning/DECISIONS.md#d-49)
deferred out of PR 1 and into PR 5, and PR 6 round-trips it.

```
<artifact>/
  manifest.json      artifact identity, embedding, components, rule version,
                     and the full training provenance
  rules.json         hazard families, the frozen supported hazard set, and
                     the frozen rule constants
  model/
    cells.json       which (target, hazard) cells were fit, and each cell's
                     class order -- the authoritative index
    legitimization.npz
    enablement.npz   coef (n_features, 3), intercept (3,), mean, scale
```

**No `thresholds.json`.** `PREREGISTRATION_LE_STRUCTURE.md` §6 retains it
only for `L3`, the two-head structure the baseline uses; every other
candidate -- including the `L1` multinomial D-68 selected -- decides by
`argmax` over the distribution and has no thresholds to store. A writer that
emits an empty one is wrong, not harmless, so this module never writes the
file and `load_artifact` rejects an artifact that has one.

**No pickle, no `joblib`** ([D-37](../../docs/planning/DECISIONS.md#d-37)).
Nothing here unpickles an estimator: a cell is four plain arrays plus a class
list, and `load_artifact` reconstructs the pure-NumPy scorer from them.

**D-23 carries unchanged.** `rules.json` and the manifest's embedding block
are what serve time reads for hazard families, the supported hazard set, and
the encoder's identity -- never installed config, so an artifact always
scores consistently with itself.

**Separate from the baseline's `model.save`/`model.load`**
([D-48](../../docs/planning/DECISIONS.md#d-48)). Those keep writing
`heads.npz` and `thresholds.json` for the three baseline CLIs, untouched;
this is a new writer and a new reader, not a branch added to the old ones.

**`rules` is passed in, never constructed here.** The rule constants and the
rule version belong to the `RuleSet` a run actually uses
(`components/integration.py`), and `profile.py` already records that a
version typed into a file "could drift from it". Taking the object
structurally (`RuleSetLike`) rather than importing it keeps that discipline
*and* keeps this module free of `SCIENCE.md`'s fixed rules -- which matters
because slice C's scoring component is downstream of this reader.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Protocol

import numpy as np

from ..rules import hazard_family
from .no_fixed_rules import assert_no_fixed_rule_import
from .training.multinomial import N_CLASSES, MultinomialCell, TargetModel
from .training.provenance import ComponentRecord, FitProvenance, LEModels

__all__ = [
    "ARTIFACT_FORMAT",
    "ArtifactError",
    "RuleSetLike",
    "RuleConstants",
    "EvaluatorArtifact",
    "write_artifact",
    "load_artifact",
    "is_evaluator_artifact",
]

# The discriminator `profile.resolve_artifact` branches on: the baseline
# artifact's `manifest.json` has no `format` key at all, so its absence is
# what identifies a baseline directory rather than a guess about its shape.
ARTIFACT_FORMAT = "hrc-evaluator-1.1"

MANIFEST_FILENAME = "manifest.json"
RULES_FILENAME = "rules.json"
MODEL_DIRNAME = "model"
CELLS_FILENAME = "cells.json"

# Retained only for `L3` (§6). Named here so `load_artifact` can reject its
# presence by name instead of by a comment nobody runs.
_FORBIDDEN_FILENAME = "thresholds.json"

TARGETS = ("legitimization", "enablement")

# The structure D-68 selected, written into the manifest so an artifact says
# what it is without a reader consulting the ledger.
_MODEL_STRUCTURE = {
    "family": "multinomial_softmax_per_hazard",
    "selection": "L1 · W1 · S1 · H3 · V1 · P1",
    "decision": "argmax over the three-class distribution",
    "n_classes": N_CLASSES,
}

_NOT_EVALUATED = (
    "Both models are reported NOT EVALUATED (SCIENCE.md §Legitimization Scoring, "
    "§Enablement Scoring): no approved per-outcome success criteria exist. The "
    "structure selection behind this artifact (DECISIONS.md D-68) is a null result "
    "-- no candidate beat the incumbent, and on Legitimization the selected "
    "structure scored below it. Every figure behind it is a dev-set number (D-66) "
    "on out-of-version labels (D-63). Building this structure is not evidence it "
    "is good."
)


class ArtifactError(ValueError):
    """A structural problem with an artifact directory: a missing file, a
    file that must not exist, or a payload that does not match its index.
    """


class RuleSetLike(Protocol):
    """`components/integration.py`'s `RuleSet`, taken structurally.

    Only what `rules.json` needs. Taken as a protocol rather than imported so
    this module -- and everything downstream of it, including slice C's
    scorer -- carries none of `SCIENCE.md`'s fixed rules.
    """

    enablement_only_hazards: frozenset[str]
    specialized_advice_hazards: frozenset[str]
    version: str


@dataclasses.dataclass(frozen=True)
class RuleConstants:
    """`rules.json`, as loaded. D-23: this is what serve time reads for
    hazard families and hazard support, never installed config.
    """

    enablement_only_hazards: frozenset[str]
    specialized_advice_hazards: frozenset[str]
    supported_hazards: frozenset[str]
    hazard_family: Mapping[str, str]
    rule_version: str


@dataclasses.dataclass(frozen=True)
class EvaluatorArtifact:
    """A loaded 1.1 artifact: identity, the two fitted models with their
    provenance, and the frozen rule constants.
    """

    artifact_id: str
    artifact_version: str
    created_at: str
    models: LEModels
    rules: RuleConstants
    manifest: Mapping[str, object]


# --- writing --------------------------------------------------------------


def _cell_array_key(hazard: str, field: str) -> str:
    """`legitimization.npz`/`enablement.npz` key for one cell's array.

    Keys are **built**, never parsed: `model/cells.json` is the
    authoritative index of which cells exist, exactly as `thresholds.json`
    is for the baseline's `heads.npz`. Parsing keys would make a hazard code
    containing the separator a silent corruption instead of an impossibility.
    """
    return f"{hazard}::{field}"


_CELL_FIELDS = ("coef", "intercept", "mean", "scale")


def _target_payload(model: TargetModel) -> tuple[dict[str, np.ndarray], dict]:
    arrays: dict[str, np.ndarray] = {}
    cells: dict[str, dict] = {}
    for hazard, cell in sorted(model.cells.items()):
        arrays[_cell_array_key(hazard, "coef")] = np.asarray(cell.coef, dtype=np.float64)
        arrays[_cell_array_key(hazard, "intercept")] = np.asarray(cell.intercept, dtype=np.float64)
        arrays[_cell_array_key(hazard, "mean")] = np.asarray(cell.mean, dtype=np.float64)
        arrays[_cell_array_key(hazard, "scale")] = np.asarray(cell.scale, dtype=np.float64)
        cells[hazard] = {
            # §6's `H3` row: the artifact records which cells were fit, so
            # D-45's unfittable-is-unavailable rule survives serialization.
            # `fitted_classes` is the class order -- without it a reloaded
            # model silently mis-orders its columns, and a class the cell
            # never saw would read as a probability instead of a zero.
            "fitted_classes": [int(c) for c in cell.fitted_classes],
            "n_fit_rows": int(cell.n_fit_rows),
        }
    index = {
        "n_features": int(model.n_features),
        "n_fit_rows": int(model.n_fit_rows),
        "cells": cells,
        "unavailable_hazards": sorted(model.unavailable_hazards),
    }
    return arrays, index


def _provenance_payload(provenance: FitProvenance) -> dict:
    return {
        "source": provenance.source_path,
        "source_sha256": provenance.source_sha256,
        "split_file": provenance.split_path,
        "split_version": provenance.split_version,
        "split_half": provenance.split_half,
        "split_role": provenance.split_role,
        "text_view": provenance.text_view,
        "seed": provenance.seed,
        "estimator": dict(provenance.estimator),
        "n_feature_rows": provenance.n_feature_rows,
        "exhausted_excluded": [list(row) for row in provenance.exhausted_excluded],
    }


def write_artifact(
    directory: str | Path,
    models: LEModels,
    *,
    artifact_id: str,
    artifact_version: str,
    rules: RuleSetLike,
    created_at: str | None = None,
) -> Path:
    """Write `models` to `directory` in the 1.1 artifact format.

    `rules` supplies the frozen rule constants and the rule version; the
    supported hazard set is **derived from the fitted cells**, never supplied
    ([D-57](../../docs/planning/DECISIONS.md#d-57) makes `hazard_scope`
    default to it, so an artifact claiming support for a hazard it has no
    cell for would fail every row of that hazard at scoring time).

    `created_at` defaults to now, in UTC ISO-8601. It is the only
    non-deterministic field written, and it is a parameter so a golden
    fixture can be captured reproducibly.
    """
    directory = Path(directory)
    (directory / MODEL_DIRNAME).mkdir(parents=True, exist_ok=True)

    supported = models.supported_hazards
    if not supported:
        raise ArtifactError("refusing to write an artifact with no fitted cell on either target")

    manifest = {
        "format": ARTIFACT_FORMAT,
        "artifact_id": artifact_id,
        "artifact_version": artifact_version,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "model_structure": dict(_MODEL_STRUCTURE),
        "embedding": {
            "provider": models.provenance.embedding_provider,
            "provider_version": models.provenance.embedding_provider_version,
            "model_name": models.provenance.embedding_model_name,
            "model_revision": models.provenance.embedding_model_revision,
            "pooling": models.provenance.pooling,
        },
        # The stages that produced the training text, as they stood. See
        # `ComponentRecord`: this is what makes PR 5's standing "a re-fit is
        # owed when narrative, refusal, or hazard detection is built"
        # checkable against a run rather than remembered.
        "components": [dataclasses.asdict(record) for record in models.provenance.components],
        "rule_version": rules.version,
        "training": _provenance_payload(models.provenance),
        "not_evaluated": _NOT_EVALUATED,
    }

    # The two family sets are the **frozen rule constants**, written in full
    # rather than narrowed to this artifact's supported hazards (which is
    # what the baseline's `model.save` does). They are what a run's `RuleSet`
    # is rebuilt from, and a full set resolves the family of any hazard the
    # run evaluates; a narrowed one silently reclassifies anything outside
    # the intersection as `default` -- the one family whose L/E table
    # *requires* a Legitimization judgment. `hazard_family` below is the
    # separate, per-artifact record and is keyed by the supported set.
    rules_payload = {
        "enablement_only_hazards": sorted(rules.enablement_only_hazards),
        "specialized_advice_hazards": sorted(rules.specialized_advice_hazards),
        "supported_hazards": sorted(supported),
        "hazard_family": {
            hazard: hazard_family(
                hazard, rules.enablement_only_hazards, rules.specialized_advice_hazards
            )
            for hazard in sorted(supported)
        },
        "rule_version": rules.version,
    }

    cells_index = {"class_labels": list(range(N_CLASSES)), "targets": {}}
    for target in TARGETS:
        arrays, index = _target_payload(getattr(models, target))
        cells_index["targets"][target] = index
        np.savez(directory / MODEL_DIRNAME / f"{target}.npz", **arrays)

    _write_json(directory / MANIFEST_FILENAME, manifest)
    _write_json(directory / RULES_FILENAME, rules_payload)
    _write_json(directory / MODEL_DIRNAME / CELLS_FILENAME, cells_index)

    return directory


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# --- reading --------------------------------------------------------------


def is_evaluator_artifact(directory: str | Path) -> bool:
    """Whether `directory` is a 1.1 evaluator artifact rather than a baseline
    one. **This is `profile.resolve_artifact`'s dispatch test** -- the
    baseline manifest has no `format` key, so the two formats are told apart
    by a field rather than by guessing at directory contents.
    """
    manifest_path = Path(directory) / MANIFEST_FILENAME
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(manifest, dict) and manifest.get("format") == ARTIFACT_FORMAT


def _load_target(
    target: str, directory: Path, index: dict
) -> TargetModel:
    arrays = dict(np.load(directory / MODEL_DIRNAME / f"{target}.npz", allow_pickle=False))
    n_features = int(index["n_features"])

    cells: dict[str, MultinomialCell] = {}
    for hazard, cell_index in index["cells"].items():
        try:
            payload = {
                field: np.asarray(arrays[_cell_array_key(hazard, field)], dtype=np.float64)
                for field in _CELL_FIELDS
            }
        except KeyError as exc:
            raise ArtifactError(
                f"{target}.npz has no array {exc.args[0]!r}, but model/{CELLS_FILENAME} "
                f"lists {hazard!r} as a fitted cell"
            ) from exc

        cells[hazard] = MultinomialCell(
            hazard=hazard,
            mean=payload["mean"],
            scale=payload["scale"],
            coef=payload["coef"],
            intercept=payload["intercept"],
            fitted_classes=tuple(int(c) for c in cell_index["fitted_classes"]),
            n_fit_rows=int(cell_index["n_fit_rows"]),
        )
        if cells[hazard].n_features != n_features:
            raise ArtifactError(
                f"{target} cell {hazard!r} has {cells[hazard].n_features} features, but "
                f"model/{CELLS_FILENAME} declares {n_features}"
            )

    return TargetModel(
        target=target,  # type: ignore[arg-type]
        cells=cells,
        unavailable_hazards=frozenset(index["unavailable_hazards"]),
        n_features=n_features,
        n_fit_rows=int(index["n_fit_rows"]),
    )


def load_artifact(directory: str | Path) -> EvaluatorArtifact:
    """Load a 1.1 artifact `write_artifact` wrote.

    `model/cells.json` is the authoritative index of which cells exist; the
    `.npz` keys are rebuilt from it via `_cell_array_key`, never parsed --
    the same discipline `model.load` applies to `heads.npz` (D-45 made the
    stored field set depend on what was fitted, and an index is what keeps
    that honest).
    """
    directory = Path(directory)

    # Format first, thresholds second. A baseline artifact has *both* the
    # wrong format and a `thresholds.json`, and "this is not a 1.1 artifact"
    # is the message that tells its reader what to do; "it has thresholds"
    # would send them looking for a corrupted 1.1 artifact instead.
    manifest = _read_json(directory / MANIFEST_FILENAME)
    if manifest.get("format") != ARTIFACT_FORMAT:
        raise ArtifactError(
            f"{directory}/{MANIFEST_FILENAME} declares format {manifest.get('format')!r}, "
            f"expected {ARTIFACT_FORMAT!r}. A baseline artifact has no format field and is "
            "loaded by hazard_classifier.model.load instead."
        )

    if (directory / _FORBIDDEN_FILENAME).exists():
        raise ArtifactError(
            f"{directory}/{_FORBIDDEN_FILENAME} exists, but PREREGISTRATION_LE_STRUCTURE.md §6 "
            "retains thresholds only for the two-head structure (L3). A multinomial artifact "
            "decides by argmax and has no thresholds, so this artifact was written by "
            "something that should not have."
        )

    rules_payload = _read_json(directory / RULES_FILENAME)
    cells_index = _read_json(directory / MODEL_DIRNAME / CELLS_FILENAME)

    models_by_target = {
        target: _load_target(target, directory, cells_index["targets"][target])
        for target in TARGETS
    }

    training = manifest["training"]
    embedding = manifest["embedding"]
    provenance = FitProvenance(
        source_path=training["source"],
        source_sha256=training["source_sha256"],
        split_path=training["split_file"],
        split_version=training["split_version"],
        split_half=training["split_half"],
        split_role=training["split_role"],
        text_view=training["text_view"],
        embedding_provider=embedding["provider"],
        embedding_provider_version=embedding["provider_version"],
        embedding_model_name=embedding["model_name"],
        embedding_model_revision=embedding["model_revision"],
        pooling=embedding["pooling"],
        seed=int(training["seed"]),
        estimator=dict(training["estimator"]),
        components=tuple(ComponentRecord(**record) for record in manifest["components"]),
        n_feature_rows=int(training["n_feature_rows"]),
        exhausted_excluded=tuple(tuple(row) for row in training["exhausted_excluded"]),
    )

    models = LEModels(
        legitimization=models_by_target["legitimization"],
        enablement=models_by_target["enablement"],
        provenance=provenance,
    )

    supported = frozenset(rules_payload["supported_hazards"])
    if supported != models.supported_hazards:
        raise ArtifactError(
            f"{RULES_FILENAME} declares supported hazards {sorted(supported)}, but the fitted "
            f"cells cover {sorted(models.supported_hazards)}. D-57 makes hazard_scope default "
            "to this set, so a mismatch would either fail every row of a hazard the artifact "
            "claims or silently refuse one it can score."
        )

    return EvaluatorArtifact(
        artifact_id=str(manifest["artifact_id"]),
        artifact_version=str(manifest["artifact_version"]),
        created_at=str(manifest["created_at"]),
        models=models,
        rules=RuleConstants(
            enablement_only_hazards=frozenset(rules_payload["enablement_only_hazards"]),
            specialized_advice_hazards=frozenset(rules_payload["specialized_advice_hazards"]),
            supported_hazards=supported,
            hazard_family=dict(rules_payload["hazard_family"]),
            rule_version=str(rules_payload["rule_version"]),
        ),
        manifest=manifest,
    )


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise ArtifactError(f"{path} is missing; it is required by ARCHITECTURE.md §10")
    return json.loads(path.read_text(encoding="utf-8"))


assert_no_fixed_rule_import(sys.modules[__name__])
