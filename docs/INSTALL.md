# Installation guide

## Requirements

- Python ≥3.11
- CPU only — no GPU/CUDA/MPS setup needed or used (`DECISIONS.md` D-6)

## Install

From the repo root:

```bash
pip install -e .
```

This installs the package and registers three console scripts —
`hrc-train`, `hrc-evaluate`, `hrc-predict` — via `pyproject.toml`'s
`[project.scripts]`. Runtime dependencies (`numpy`, `pandas`,
`scikit-learn`, `torch`, `sentence-transformers`) install automatically.

For running the test suite, also install the `dev` extra:

```bash
pip install -e ".[dev]"
```

## First run: the BGE model download

Every command that touches real embeddings uses
`BAAI/bge-base-en-v1.5` via `sentence-transformers`. Each CLI is **offline
by default** (`local_files_only=True`) — if the model isn't already cached
locally, you'll need `--allow-download` once:

```bash
hrc-train --input examples/sample_input.csv --output-dir /tmp/hrc-demo/model --allow-download
```

This downloads roughly 0.4GB once and caches it (the standard
`sentence-transformers`/Hugging Face cache location). Every subsequent
command — including on a different artifact — reuses the cached weights and
needs no network access and no `--allow-download` flag.

## Verify the install

```bash
hrc-train --help
hrc-evaluate --help
hrc-predict --help
```

Each should print its usage without error. To verify the full pipeline
works in this environment:

```bash
pip install -e ".[dev]"
pytest
```

151 tests should pass. Tests in `tests/integration/` use the real BGE model
(cached after the first run, same as above); `tests/unit/` and
`tests/science/` never touch the network or a real model.
