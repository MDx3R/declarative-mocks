[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

# declarative-mocks

**Declare mock behavior as ordered expectations** - readable tests with explicit call patterns, return sequences, and side effects, built on `unittest.mock`.

## Features

---

- **Fluent expectations** - register calls with arguments (positional vs keyword aware), matchers (`Anything`, `ANY_ARGS` / `ANY_KWARGS`, …), and outcomes in order.
- **Return sequences** - chain multiple `.returns()` / `.raises()` / `.runs()` for successive matching calls.
- **Call-count controls** - one quantifier per `expect(...)` (`.once()`, `.times(n)`, `.between(min, max)`, `.never()`, and more).
- **Spec-backed mocks** - aligned with `Mock(spec=…)` semantics for safer, clearer tests.
- **Async without ceremony** - `expect()` on `async def` methods is the same DSL; `runs()` accepts both sync and async callables.
- **No extra runtime dependencies** - only the standard library at runtime.

## Installation

---

The first PyPI release is being prepared. Until then, install from source:

```bash
poetry install
```

The intended published command:

```bash
pip install declarative-mocks
```

## The idea: before and after

---

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

## How it compares

---

The goals are the same as above: a strictly typed expectation DSL, a whitelist mock you construct, call order as a graph, and async wrapping every method in AsyncMock yourself. Against [mockito-python](https://github.com/kaste/mockito-python) and [flexmock](https://github.com/flexmock/flexmock) that looks like this.

### Static analysis

That only matters if you type-check tests. Tests deserve the same quality bar as production code - maybe more, now that agents write so much of the suite.

`mockito-python` is strong on features, but the installed package has **no `py.typed` marker and no `.pyi` stubs**. Then `mypy tests` fails on `import mockito` (`missing library stubs or py.typed marker`) unless you set `ignore_missing_imports = True`. That is [issue #58](https://github.com/kaste/mockito-python/issues/58): the reporter was already ignoring the package; the maintainer called full typing “some significant work.” The ignore makes mypy succeed by treating mockito as `Any`, so `when` / `thenReturn` / `verify` themselves are not checked.

`flexmock` **is** typed (`py.typed` since 0.11.3), but it addresses methods **by string** (`should_receive("fetch_user")`), so the name is still not checked statically.

`dmock` is the only one of the three that is **strictly typed** (`py.typed`) **and** uses real attribute names on the mock (`mock.fetch_user(...)`), validated against the spec at construction/`expect()` time.

### Shorter setup and verify

With dmock you write the call once. `verify()` does not repeat it:

```python
mock.expect("fetch_user", 1).returns(user).once()
# … exercise code …
mock.verify()
```

mockito splits **configuration and verification** into two expressions that repeat the call:

```python
when(service).fetch_user(1).thenReturn(user)
# … exercise code …
verify(service, times=1).fetch_user(1)
```

flexmock uses a four-link chain and a string method name:

```python
flexmock(service).should_receive("fetch_user").with_args(1).and_return(user).once()
```

### A whitelist mock you construct

`DeclarativeMock(MyService)` is an object you **hold and pass in**. Unregistered calls fail immediately. Nothing on live modules or instances is rewritten.

mockito's usual `when(obj)` **does** rewrite methods on `obj` (module, class, or instance). The docs say you must `unstub()` afterwards, or use `with` / a pytest fixture, or stubs leak into later tests. `mock()` can create an injectable dummy instead, but it still sits in the same global registry.

flexmock also replaces attributes on existing objects (`should_receive`). Restore is automatic under pytest and unittest - there is no `unstub()` you call by hand.

### Call order as a dependency graph

`.not_before(...)` and `in_order(...)` are checked **at the violating call**, not after the fact at `verify()`. Dependencies may cross mock instances. Cycles are rejected at configuration time with `ConfigurationError`.

### Async without caveats

This argument holds **against flexmock**, not against mockito.

flexmock still has **no first-class async API** (no `async` / `await` / `coroutine` in the changelog or API reference). The documented workaround is to return an `AsyncMock` or `asyncio.Future` yourself.

mockito added first-class async/await stubbing in **2.0.0**. Their remaining caveat: introspection metadata such as `inspect.iscoroutinefunction` on stub wrappers is implemented **only on Python 3.12+**.

`dmock` installs a real nested `async def` dispatcher, so `inspect.iscoroutinefunction(mock.aprocess_order)` is true on **every supported Python** (3.11-3.14).

## Usage examples

---

### 1. Nested return values (successive `.returns()`)

Each `.returns()` applies to the next matching call in order - handy for paginated or multi-step flows without a hand-built `side_effect` list.

```python
from dmock import DeclarativeMock

api = DeclarativeMock(ApiClient)
api.expect("next_page").returns({"items": [1], "cursor": "a"})
api.expect("next_page").returns({"items": [2], "cursor": None})

# first call → first dict; second call → second dict
```

### 2. Outcome sequences with `.runs()` and `.returns()`

Chained outcomes apply to **successive matching calls**, not to a single call. `.runs(fn).returns(value)` means: first call runs `fn` (its return value is the result); second call returns `value`. A quantifier (`.once()`, `.at_least(n)`, …) applies to the **whole** `expect(...)` chain, not to the last outcome. A second quantifier on the same chain raises `ConfigurationError`.

If you omit a quantifier, the count is exactly the number of chained outcomes (minimum 1). `.runs(fn)` alone is **one** call; a second match is unexpected. The last outcome repeats only when the quantifier allows more calls than outcomes - for example `.runs(fn).at_least(1)` to run the callable on every matching call.

```python
from dmock import DeclarativeMock

calc = DeclarativeMock(Calculator)
calc.expect("price", 100).runs(lambda x: x - 1).returns(99)

assert calc.price(100) == 99   # from the lambda
assert calc.price(100) == 99   # from .returns(99)
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

### 5. Async methods

`expect()` on an `async def` spec method needs no extra type. Await the call as usual. `runs()` accepts a sync callable or an `async def`; both work.

```python
from dmock import Anything, DeclarativeMock

mock = DeclarativeMock(MyService)
mock.expect("aprocess_order", Anything()).returns("ok")
assert await mock.aprocess_order(1) == "ok"

mock.expect("aprocess_order", Anything()).runs(lambda order_id: f"sync-{order_id}")
assert await mock.aprocess_order(7) == "sync-7"

async def async_fn(order_id: int) -> str:
    return f"async-{order_id}"

mock.expect("aprocess_order", Anything()).runs(async_fn)
assert await mock.aprocess_order(9) == "async-9"
```

For full DSL details and edge cases, see **`SPEC.md`** and **`REFERENCE.md`**.

## Limitations & non-goals

---

- **No signature binding.** `expect("method", …)` checks that `method` exists on the spec, not that the argument list matches the real signature.
- **No automatic `verify()`.** You call `verify()` yourself.
- **No spies and no patching.** The library does not wrap live objects, modules, or `sys.modules`. Construct a `DeclarativeMock` and pass it in.
- **Not thread-safe.** Concurrent use of one mock from multiple threads is out of scope.

## Development

---

```bash
poetry install
ruff check .
ruff format --check .
mypy src tests
pytest
pytest --cov --cov-report=term-missing
```

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for setup, commits, and tests. Agents follow **[AGENTS.md](AGENTS.md)**.

## License

MIT
