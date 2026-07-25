# Critiques

This directory holds **scoped analysis passes** over the plan and implementation.
Each file is a single critique covering a narrow scope (e.g., one deliverable, one
decision area) with no fixes proposed — only findings.

## File naming

`YYYY-MM-DD-<descriptive-scope>.md` — date-ordered, descriptive scope.

Example: `2026-07-23-deliverable-1.md` (a critique of Deliverable 1, written
2026-07-23).

## Structure (per META_PLAN §2)

- **Header:** title, date, mechanism, scope, reference reads.
- **Ledger check:** confirm `DECISIONS.md` has no locked entry that already
  covers this scope.
- **Organized by severity:**
  - `blocks-correctness` — issues that cause wrong behavior or violate the
    science.
  - `quality` — code clarity, maintainability, performance.
  - `nice-to-have` — refactorings, improvements, future-work notes.
- **Numbered findings** within each band (C-1, C-2, … for correctness; Q-1, Q-2
  for quality; N-1 for nice-to-have).
- **Scope:** science, math, and engineering only. No design opinions or style
  critique unless they affect behavior.
- **Self-contained:** a reader should understand the findings without chat
  history.
- **User Responses** (optional, added after user replies): answers to open
  questions. Responses that become decisions go to `DECISIONS.md`; clarifications
  that don't need locked-in decisions go here inline, making the critique a
  complete record of the analysis and its resolution.

## How they're used

- Each critique is written during a **critique pass** (per META_PLAN §2).
- Findings are picked up by **fix-proposal passes** (one issue at a time).
- Accepted fixes become entries in `DECISIONS.md`.
- `STATUS.md` tracks which critiques are queued and which have been addressed.

A critique is never a plan doc — it's an intermediate work product on the way
to a decision.
