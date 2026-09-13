# REFERENCE - DSL surface (declarative-mocks)

Catalog of the **public** DSL. Import package: **`dmock`**.

Public names: `DeclarativeMock`, `Expectation`, `in_order`, `Anything`, `AnythingOfType`, `MatchedBy`, `Matcher`, `ANY_ARGS`, `ANY_KWARGS`, `DeclarativeMockError`, `UnexpectedCallError`, `UnsatisfiedExpectationError`, `ConfigurationError`.

## Main type

### `DeclarativeMock(spec, /, **kwargs)`

Constructs a whitelist mock that wraps `unittest.mock.Mock(spec=spec, **kwargs)` internally (composition, not inheritance). `spec` is positional-only; additional keyword arguments are forwarded to `unittest.mock.Mock`.

Every spec method call must be preceded by a matching `expect()` registration; calls without one raise `UnexpectedCallError`. Dunder methods (e.g. `__repr__`) delegate to the internal Mock unless explicitly registered.

Async methods on the spec are detected automatically: `expect()` and all outcomes (`returns`, `raises`, `runs`, quantifiers) work identically for async methods. The caller must `await` the call. The installed wrapper is a nested `async def`, so `inspect.iscoroutinefunction(mock.async_method)` is true on every supported Python (3.11-3.14).

The names `expect`, `property`, and `verify` are reserved for the DSL. If the spec defines any of them, `DeclarativeMock(spec)` raises `ConfigurationError` at construction time (the real attribute would otherwise be shadowed by the DSL method).

**Usage sketch:**

```python
from dmock import DeclarativeMock

mock = DeclarativeMock(MyService)
mock.expect("process_order", 123).returns("processed")
result = mock.process_order(123)  # "processed"
mock.verify()
```

## Expectations

### `mock.expect(name, /, *args, **kwargs)`

Registers an expectation for attribute `name`. Absence of `args`/`kwargs` after `name` means **no arguments** to the call, not a wildcard.

Raises `AttributeError` if `name` is not on the spec. Returns an `Expectation` for chaining outcomes and quantifiers.

**Examples:**

```python
mock.expect("process_order", 123).returns("processed")
mock.expect("process_order", order_id=123).returns("processed")
```

### `… .returns(value)`

Declares a return value for the next matching call. Returns a single Python object; tuples are returned as tuples without unpacking.

### `… .raises(exc)`

Declares that the next matching call raises `exc`. If `exc` is an exception type (not an instance), it is instantiated with no arguments before raising.

### `… .runs(func)`

Calls `func(*args, **kwargs)` with the actual call arguments when this expectation matches. The return value of `func` becomes the result of the call.

Chaining `runs` then `returns` schedules **two** outcomes for **two** successive calls, not a side effect plus a return on the same call.

On an async spec method, `func` may be sync or `async def`. The dispatcher awaits awaitable results.

## Chaining multiple outcomes

Repeated `returns` / `raises` / `runs` on the same `expect` line define a **sequence** of responses to successive matching calls. Order is significant.

If you omit a quantifier, the count is exactly the number of chained outcomes (minimum 1). The last outcome repeats only when the quantifier allows more calls than outcomes (for example `.at_least(1)` or `.times(n)` with `n` greater than the sequence length).

**Example:**

```python
mock.expect("do_something").returns("ok").returns("ok").returns("fail")
```

## Quantifiers

**One** quantifier per `expect(...)` chain. It applies to the whole expectation, not to the last outcome. A second quantifier on the same chain raises `ConfigurationError`.

| Method            | Meaning                                              |
| ----------------- | ---------------------------------------------------- |
| `once()`          | Exactly one matching call                            |
| `twice()`         | Exactly two                                          |
| `times(n)`        | Exactly `n`                                          |
| `at_least(n)`     | Minimum `n`, no upper bound                          |
| `at_most(n)`      | Between 0 and `n` inclusive                          |
| `between(lo, hi)` | Inclusive range                                      |
| `never()`         | Must not match; any matching call raises immediately |

If no quantifier is set, the expectation defaults to `ExactlyN(max(1, len(outcomes)))`.

**Example:**

```python
mock.expect("do_something").returns("ok").times(3)
```

### `… .maybe()`

Not a quantifier. Marks the expectation optional: zero calls still pass `verify()` and count as satisfied for `not_before`. May be combined with a quantifier (`.once().maybe()`).

## Matchers (argument predicates)

| Matcher                            | Role                                                                 |
| ---------------------------------- | -------------------------------------------------------------------- |
| `Anything()` / `Anything`          | Matches any single value where placed                                |
| `dmock.ANY_ARGS, dmock.ANY_KWARGS` | Wildcard matchers for any number of positional and keyword arguments |
| `AnythingOfType(type)`             | Value must be instance of `type`                                     |
| `MatchedBy(predicate)`             | Custom predicate on the value                                        |

`Matcher` is a public protocol with a single `matches(value) -> bool` method. Implement it to add a custom matcher; built-in matchers already satisfy it. `ANY_ARGS` and `ANY_KWARGS` are sentinels, not `Matcher`s.

**Examples:**

```python
mock.expect("process_order", Anything()).returns("processed").at_least(1)
```

Variadic calls (any `*args` / `**kwargs` shape):

```python
from dmock import ANY_ARGS, ANY_KWARGS

mock.expect("process_order", ANY_ARGS, ANY_KWARGS).returns("processed").at_least(1)
```

## Property stubs

### `mock.property(name, value, /)`

Registers a stub attribute `name` that returns `value` directly on attribute access. No call is needed (no `()`).

Raises `AttributeError` if `name` is not on the spec. Raises `ConfigurationError` if `name` is already registered via `expect()` (and `expect()` raises `ConfigurationError` if the name is already registered as a property stub).

Property stubs have no quantifiers and are not tracked by `verify()`.

**Example:**

```python
from dmock import DeclarativeMock

mock = DeclarativeMock(MyService)
mock.property("value", 123)
val = mock.value  # no call needed
assert val == 123
```

## Global call ordering

### `… .not_before(*expectations)`

Declares that this expectation must not be consumed until every listed expectation is satisfied (its quantifier constraint is met, including `maybe()` when never called). Returns `Self` for chaining.

Raises `ConfigurationError` if adding the dependency would create a cycle.

**Example - explicit prerequisite:**

```python
from dmock import DeclarativeMock

mock = DeclarativeMock(MyService)
init = mock.expect("do_something").returns("init").once()
work = mock.expect("process_order", 1).returns("done").not_before(init)

mock.do_something()       # satisfies init
mock.process_order(1)     # now allowed
```

### `in_order(*expectations)`

Top-level function that chains expectations so each one requires the previous to be satisfied first. Equivalent to calling `.not_before(prev)` on each expectation except the first. Zero or one argument is a no-op.

```python
from dmock import DeclarativeMock, in_order

mock = DeclarativeMock(MyService)
a = mock.expect("do_something").returns("a").once()
b = mock.expect("process_order", 1).returns("b").once()
c = mock.expect("greet", "world").returns("c").once()
in_order(a, b, c)

mock.do_something()
mock.process_order(1)
mock.greet("world")
mock.verify()
```

Calling expectations out of order raises `UnexpectedCallError`.

## Assertions

### `mock.verify()`

Final verification: all registered expectations must be satisfied according to their quantifiers. Raises `UnsatisfiedExpectationError` with a message listing every unsatisfied expectation as `Expectation(...) - expected <constraint>, got <n>`. Expectations marked `.maybe()` that were never called do not contribute to failures. When any calls were dispatched, the message also includes a call history.

## Errors

| Exception                     | When raised                                                                                                                                  |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `DeclarativeMockError`        | Base type for the three public errors below                                                                                                  |
| `UnexpectedCallError`         | A method is called without a matching registered expectation, or a `never()` expectation matches, or all matching expectations are exhausted |
| `UnsatisfiedExpectationError` | `verify()` finds one or more expectations not satisfied                                                                                      |
| `ConfigurationError`          | Invalid setup: conflicting quantifiers, reserved DSL names on the spec, `expect`/`property` clash, cycles in `not_before`                    |

`UnexpectedCallError` for a dispatched call includes the actual `args`/`kwargs`, then a **Candidates** list of registered expectations for that name with a reason for each: `args mismatch`, `exhausted (n/max calls)`, or `blocked by <method> (expected …, got …)`. Out-of-order calls use the `blocked by` form. Messages also include a **Call history** of prior (and the failing) dispatches. Matching and ordering rules are unchanged; only the text is richer. The public type to catch is `UnexpectedCallError`; the raised instance is a more specific subclass so the traceback names the case (unregistered, no match, blocked, exceeded). Those subclasses are not part of the public DSL.

`UnsatisfiedExpectationError` lists each unmet expectation as `Expectation(...) - expected <constraint>, got <n>`, where `<constraint>` is the quantifier description (`exactly 2 call(s)`, `at least 3 call(s)`, `between 1 and 4 call(s)`, `never`).

---

For behavioral rules (ordering, edge cases, errors), see [SPEC.md](SPEC.md).
