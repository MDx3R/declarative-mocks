[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

# declarative-mocks

**Declare mock behavior as ordered expectations** - readable tests with explicit call patterns, return sequences, and side effects, built on `unittest.mock`.

## Features

- **Fluent expectations** - register calls with arguments (positional vs keyword aware), matchers (`Anything`, `ANY_ARGS` / `ANY_KWARGS`, …), and outcomes in order.
- **Return sequences** - chain multiple `.returns()` / `.raises()` / `.runs()` for successive matching calls.
- **Call-count controls** - quantifiers such as `.once()`, `.times(n)`, `.between(min, max)`, `.never()`, and more.
- **Spec-backed mocks** - aligned with `Mock(spec=…)` semantics for safer, clearer tests.
- **No extra runtime dependencies** - only the standard library at runtime.

## Installation

```bash
pip install declarative-mocks
```

For contributors cloning the repository:

```bash
poetry install
```

## The idea: before and after

**Before - `unittest.mock`:** behavior is spread across `return_value`, `side_effect`, and ad hoc assertions; ordering and “what happens on the third call?” are easy to lose in a long test.

```python
from unittest.mock import Mock

service = Mock(spec=MyService)
service.fetch_user.side_effect = [
    {"id": 1, "name": "Ada"},
    {"id": 1, "name": "Ada"},
    ConnectionError("retry"),
]
# … exercise code …
# Assertions about call order and counts are often manual and verbose.
```

**After - `dmock`:** the same story is **declared** next to the mock: ordered expectations, explicit outcomes, and a single verification step.

```python
from dmock import DeclarativeMock

service = DeclarativeMock(MyService)
service.expect("fetch_user").returns({"id": 1, "name": "Ada"}).returns({"id": 1, "name": "Ada"})
service.expect("fetch_user").raises(ConnectionError("retry"))
# … exercise code …
service.verify()
```

## Usage examples

### 1. Nested return values (successive `.returns()`)

Each `.returns()` applies to the next matching call in order - handy for paginated or multi-step flows without a hand-built `side_effect` list.

```python
from dmock import DeclarativeMock

api = DeclarativeMock(ApiClient)
api.expect("next_page").returns({"items": [1], "cursor": "a"})
api.expect("next_page").returns({"items": [2], "cursor": None})

# first call → first dict; second call → second dict
```

### 2. Side effects with `.runs()`

Combine a callable for **side effects** with a final return value when your DSL allows chaining `runs` + `returns`.

```python
from dmock import DeclarativeMock

calc = DeclarativeMock(Calculator)

# run side effect, then return
calc.expect("price", 100).runs(lambda x: None).returns(99)
```

### 3. Strict argument matching (positional vs keyword)

`expect("method")` with **no** extra args means “called with no arguments” - not “anything.” Use matchers when you need to accept arbitrary values.

```python
from dmock import Anything, DeclarativeMock

m = DeclarativeMock(Worker)

# any single positional arg
m.expect("run", Anything()).returns(0)

# keyword-specific expectation
m.expect("run", job_id=123).returns("queued")
```

### 4. Variadic arguments (`ANY_ARGS`, `ANY_KWARGS`)

To match **any** positional and keyword arguments (including none), use the dedicated wildcards instead of repeating `Anything()`.

```python
from dmock import ANY_ARGS, ANY_KWARGS, DeclarativeMock

m = DeclarativeMock(Worker)
m.expect("run", ANY_ARGS, ANY_KWARGS).returns(0)
```

For full DSL details and edge cases, see **`SPEC.md`** and **`REFERENCE.md`**.

## Development

```bash
poetry install
ruff check .
ruff format --check .
mypy src tests
pytest
pytest --cov --cov-report=term-missing
```

See **`AGENTS.md`** for the contributor and agent workflow.

## License

MIT
