# REFERENCE — DSL surface (declarative-mocks)

Catalog of the **public** DSL. Names match the intended API; adjust only if SPEC.md is updated accordingly.

Import package: **`dmock`**.

## Main type

### `DeclarativeMock(spec, /, **kwargs)`

Constructs a whitelist mock that wraps `unittest.mock.Mock(spec=spec, **kwargs)` internally (composition, not inheritance). `spec` is positional-only; additional keyword arguments are forwarded to `unittest.mock.Mock`.

Every spec method call must be preceded by a matching `expect()` registration; calls without one raise `UnexpectedCallError`. Dunder methods (e.g. `__repr__`) delegate to the internal Mock unless explicitly registered.

Async methods on the spec are detected automatically: `expect()` and all outcomes (`returns`, `raises`, `runs`, quantifiers) work identically for async methods. The only difference is that the caller must `await` the call.

**Usage sketch:**

```python
from dmock import DeclarativeMock

mock = DeclarativeMock(MyService)
mock.expect("process_order", 123).returns("processed")
result = mock.process_order(123)  # "processed"
mock.assert_expectations()
```

## Expectations

### `mock.expect(name, /, *args, **kwargs)`

Registers an expectation for attribute `name`. Absence of `args`/`kwargs` after `name` means **no arguments** to the call, not a wildcard.

Raises `AttributeError` if `name` is not on the spec.

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

## Chaining multiple outcomes

Repeated `returns` / `raises` / `runs` on the same `expect` line define a **sequence** of responses to successive matching calls. Order is significant. When the sequence is exhausted, the last outcome repeats (for unbounded quantifiers).

**Example:**

```python
mock.expect("do_something").returns("ok").returns("ok").returns("fail")
```

## Quantifiers

Applied after outcomes where the grammar allows:

| Method            | Meaning                                          |
| ----------------- | ------------------------------------------------ |
| `maybe()`         | Optional: 0 calls still satisfies this expectation |
| `once()`          | Exactly one matching call                        |
| `twice()`         | Exactly two                                      |
| `times(n)`        | Exactly `n`                                      |
| `at_least(n)`     | Minimum `n`, no upper bound                      |
| `at_most(n)`      | Between 0 and `n` inclusive                      |
| `between(lo, hi)` | Inclusive range                                  |
| `never()`         | Must not match; any matching call raises immediately |

If no quantifier is set, the expectation defaults to `ExactlyN(max(1, len(outcomes)))`.

**Example:**

```python
mock.expect("do_something").returns("ok").times(3)
```

## Matchers (argument predicates)

| Matcher                            | Role                                                                 |
| ---------------------------------- | -------------------------------------------------------------------- |
| `Anything()` / `Anything`          | Matches any single value where placed                                |
| `dmock.ANY_ARGS, dmock.ANY_KWARGS` | Wildcard matchers for any number of positional and keyword arguments |
| `AnythingOfType(type)`             | Value must be instance of `type`                                     |
| `MatchedBy(predicate)`             | Custom predicate on the value                                        |

**Examples:**

```python
mock.expect("process_order", Anything()).returns("processed").at_least(1)
```

Variadic calls (any `*args` / `**kwargs` shape):

```python
from dmock import ANY_ARGS, ANY_KWARGS

mock.expect("process_order", ANY_ARGS, ANY_KWARGS).returns("processed").at_least(1)
```

## Assertions

### `mock.assert_expectations()`

Final verification: all registered expectations must be satisfied according to their quantifiers. Raises `UnsatisfiedExpectationError` with a message listing every unsatisfied expectation. Expectations marked `.maybe()` that were never called do not contribute to failures.

## Errors

| Exception                    | When raised                                                            |
| ---------------------------- | ---------------------------------------------------------------------- |
| `UnexpectedCallError`        | A method is called without a matching registered expectation, or a `never()` expectation matches, or all matching expectations are exhausted |
| `UnsatisfiedExpectationError`| `assert_expectations()` finds one or more expectations not satisfied   |
| `ConfigurationError`         | Invalid expectation setup (e.g. duplicate/conflicting quantifiers)     |

## Not yet available

- **Global cross-method ordering** (`InOrder` / `NotBefore`) — planned for a future release.

---

For behavioral rules (ordering, edge cases, errors), see [SPEC.md](SPEC.md).
