"""Release 1.1 L/E model training (`docs/planning/PR5_EXECUTION_PLAN.md`).

Three modules, split so that fitting is testable without an encoder and
without the pipeline:

- `multinomial` -- the estimator [D-68](../../../docs/planning/DECISIONS.md#d-68)
  selected, and the fitted, pure-NumPy model it produces. Takes an already
  embedded feature matrix; imports no component and reads no text.
- `features` -- the serve-time feature path: stages 1-7 produce the `working`
  view, stage 8 embeds and pools it ([D-72](../../../docs/planning/DECISIONS.md#d-72)).
- `release` -- the one entry point that ties them to the frozen interim split
  ([D-73](../../../docs/planning/DECISIONS.md#d-73)).

**Separate from the baseline's `model.py`, deliberately** (D-48). The 1.1
fitter writes no `heads.npz` and no `thresholds.json`, and nothing here
extends `model.fit`/`save`/`load` -- those keep serving the three baseline
CLIs unchanged.
"""
