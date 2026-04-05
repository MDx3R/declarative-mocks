# AGENTS.md — declarative-mocks

Instructions for AI coding agents and humans working in this repository.

## Project identity

| Item | Value |
|------|--------|
| Distribution name | `declarative-mocks` |
| Python import | `dmock` |
| Source | `src/dmock/` |
| Tests | `tests/` |

## Setup

```bash
poetry install
```

Activate the environment Poetry uses (e.g. `poetry shell` or `poetry run …`).

## Build / quality checks

Run from the repository root (prefer `poetry run` if the venv is not active):

```bash
ruff check .
ruff format --check .
mypy src
```

Pyright / Pylance uses [pyrightconfig.json](pyrightconfig.json). CLI (if installed):

```bash
pyright
```

## Tests

```bash
pytest
```

With coverage (matches [tool.coverage] in `pyproject.toml`):

```bash
pytest --cov --cov-report=term-missing
```

## Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## Documentation to read before behavioral changes

- [SPEC.md](SPEC.md) — behavior, ordering rules, edge cases.
- [REFERENCE.md](REFERENCE.md) — DSL surface (expectations, quantifiers, matchers).

Update SPEC/REFERENCE when user-visible behavior or the public DSL changes.

## Workflow (with agents)

1. Read SPEC.md and REFERENCE.md for context on expectations and DSL.
2. For non-trivial work: plan first (Cursor Plan mode or equivalent), then implement.
3. Implement with strict typing; keep public API consistent with SPEC/REFERENCE.
4. Add or update tests alongside code changes.
5. Before considering work done: `ruff check`, `ruff format` (or format check), `mypy src`, Pyright clean, `pytest` (and coverage when relevant).
6. Commit only after checks pass (or document intentional exceptions).

## Do not

- Add `Any` or untyped public APIs without project agreement.
- Use `print` for debugging in library code (use logging or tests).
- Skip updating SPEC.md / REFERENCE.md when changing documented behavior.
- Reference or rely on `examples/` for core library design unless the maintainer asks.

## Code style

- **Formatter / linter:** Ruff (includes isort-like import sorting).
- **Types:** mypy strict + Pyright strict; package is typed (`py.typed`).
- **Docstrings:** Google convention when documenting is required.
