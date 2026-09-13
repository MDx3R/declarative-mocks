# Contributing

## Setup

---

```bash
poetry install
pre-commit install
```

Use `poetry run …` unless the Poetry env is already active.

## Checks

---

From the repository root:

```bash
ruff check .
ruff format --check .
mypy src tests
pytest
pytest --cov --cov-report=term-missing
```

Optional: `pre-commit run --all-files`, `pyright`.

Agents follow the same commands in [AGENTS.md](AGENTS.md).

## Commits

---

[Conventional Commits](https://www.conventionalcommits.org/): `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `style`. A `!` after the type marks a breaking change (`feat(dmock)!: …`).

## Tests

---

Add or update tests next to the change. `tests/test_mock.py` is the dispatch/integration suite; matcher and expectation units live in `tests/test_matchers.py` and `tests/test_expectation.py`.

**AAA** (`# Arrange`, `# Act`, `# Assert`) is for multi-step tests, mainly in `test_mock.py`:

- Every heading has a body. Do not leave an empty section.
- Split a fused assert: call under `# Act`, comparison under `# Assert`.
- Short predicate tests stay as plain `assert`s. No AAA headings.

## Docs

---

User-visible behavior or public DSL changes need [SPEC.md](SPEC.md) and [REFERENCE.md](REFERENCE.md) in the same change. README examples must stay consistent with those two.
