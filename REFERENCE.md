# REFERENCE — DSL surface (declarative-mocks)

Catalog of the **public** DSL. Names match the intended API; adjust only if SPEC.md is updated accordingly.

Import package: **`dmock`**.

## Main type

### `DeclarativeMock(spec=…, …)`

Constructs a mock object (backed by `unittest.mock` with `spec=`) that exposes the fluent expectation API below. Parameters follow the design goal: preserve standard `Mock` semantics where possible while adding expectations.

**Usage sketch:**

```python
from dmock import DeclarativeMock

mock = DeclarativeMock(MyService)
```

## Expectations

### `mock.expect(name, /, *args, **kwargs)`

Registers an expectation for attribute `name`. Absence of `args`/`kwargs` after `name` means **no arguments** to the call, not a wildcard.

**Examples:**

```python
mock.expect("process_order", 123).returns("processed")
mock.expect("process_order", order_id=123).returns("processed")
```

### `… .returns(value)`

Declares a return value for the next matching call (or part of a chain — see chaining).

### `… .raises(exc)`

Declares that the next matching call raises `exc`.

### `… .runs(func)`

Runs `func` for side effect / computation; may be combined with `returns` depending on chaining rules.

## Chaining multiple outcomes

Repeated `returns` / `raises` / `runs` on the same `expect` line define a **sequence** of responses to successive matching calls. Order is significant.

**Example:**

```python
mock.expect("do_something").returns("ok").returns("ok").returns("fail")
```

## Quantifiers

Applied after outcomes where the grammar allows:

| Method            | Meaning (informal)                    |
| ----------------- | ------------------------------------- |
| `maybe()`         | Optional / non-strict repeat per SPEC |
| `once()`          | Exactly one matching call             |
| `twice()`         | Exactly two                           |
| `times(n)`        | Exactly `n`                           |
| `at_least(n)`     | Minimum `n`                           |
| `at_most(n)`      | Maximum `n`                           |
| `between(lo, hi)` | Inclusive range                       |
| `never()`         | Must not match                        |

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
mock.expect("process_order", Anything()).returns("processed")
```

Variadic calls (any `*args` / `**kwargs` shape):

```python
from dmock import ANY_ARGS, ANY_KWARGS

mock.expect("process_order", ANY_ARGS, ANY_KWARGS).returns("processed")
```

## Assertions

### `mock.assert_expectations()`

Final verification: expectations and counts must be satisfied; failures must be actionable (message points to the offending expectation or call).

---

For behavioral rules (ordering, edge cases, errors), see [SPEC.md](SPEC.md).
