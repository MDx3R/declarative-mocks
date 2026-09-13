# SPEC - behavioral specification (declarative-mocks)

This document describes **what** the library must do from a tester's perspective. It does not prescribe internal implementation.

## Purpose

The library provides a **declarative** layer over `unittest.mock` (typically `Mock` with `spec=…`) so tests can express **ordered expectations**, **return values**, **exceptions**, **side effects**, and **call-count constraints** in a fluent API.

## Core principles

1. **Order matters (per-name)** - expectations for the same attribute name are consumed in the order they were registered. Expectations for different method names are independent and may be called in any order.
2. **Whitelist proxy** - any call to a spec method without a prior `expect()` registration raises `UnexpectedCallError`. The mock is strict by default; regular methods do not fall through to `unittest.mock` defaults. Exception: dunder methods (e.g. `__repr__`, `__str__`) delegate to the internal Mock when not explicitly registered via `expect()`. The DSL names `expect`, `property`, and `verify` are reserved on `DeclarativeMock`; constructing a mock whose spec defines any of these attributes raises `ConfigurationError` immediately.
3. **Explicit beats implicit** - an expectation without arguments means "called with no arguments", not "any arguments". To accept arbitrary values, matchers such as `Anything` / `Anything()`, or variadic wildcards `ANY_ARGS` / `ANY_KWARGS`, must be used explicitly.
4. **Positional vs keyword** - matching distinguishes positional-only, keyword-only, and mixed call shapes as in Python: the same value passed positionally vs by keyword is not interchangeable unless the DSL explicitly allows it.
5. **Sync and async** - async methods on the spec are detected automatically. The installed wrapper is a nested `async def`, so `inspect.iscoroutinefunction` is true on every supported Python. The same DSL (`returns`, `raises`, `runs`, quantifiers) applies to both sync and async methods. `runs()` accepts a sync callable or an `async def`; when the spec method is async, an awaitable result is awaited.

## Expectation registration

- `expect(name, …)` registers an expectation for an attribute (usually a method name) on the mock.
- Arguments after the name describe **expected** call arguments (positional and keyword), possibly using matchers.
- Multiple `returns(…)`, `raises(…)`, or `runs(…)` on one expectation define a **sequence** of outcomes for successive matching calls. Order of chained outcomes matters. `.runs(fn).returns(value)` is two calls, not a side effect plus a return on the same call.

## Quantifiers and call counts

There is **one** quantifier per `expect(...)` chain. It constrains how many times that whole expectation may match, not an individual `.returns()` / `.runs()` / `.raises()`. A second quantifier on the same chain raises `ConfigurationError` at configuration time.

- **Implicit** - if not specified, the count is exactly the number of chained outcomes (minimum 1). A lone `.runs(fn)` is therefore one call; a second match is unexpected.
- **once(), twice(), times(n)** - exact counts.
- **at_least(n), at_most(n), between(min, max)** - bounds. `at_most(n)` allows zero calls.
- **never()** - matching this expectation must not occur; any matching call raises `UnexpectedCallError` immediately.

When the quantifier allows more calls than there are outcomes, the **last** outcome repeats.

`maybe()` is not a quantifier. It marks the expectation optional: zero calls still pass `verify()` (and count as satisfied for `not_before`). It may be combined with a quantifier (e.g. `.once().maybe()`).

## Outcomes

- **returns(value)** - return a single Python value for a matching call. Tuples are returned as tuples; no unpacking is performed.
- **raises(exc)** - raise an exception instance or type. If a type is passed, it is instantiated with no arguments before raising.
- **runs(func)** - call `func(*args, **kwargs)` with the actual call arguments; the return value of `func` becomes the call result.
- **No explicit outcome** - delegates to the internal `unittest.mock.Mock` child (returns a `Mock` object).

## Property stubs

- `property(name, value)` registers a **stub attribute** that returns `value` directly when the attribute is accessed on the mock (no call required).
- Same spec-validation as `expect()`: raises `AttributeError` if `name` is not on the spec.
- Property stubs have no quantifier tracking and are always considered satisfied; `verify()` ignores them.
- Registering a property stub for a name that already has an `expect()` registration (or vice versa) raises `ConfigurationError` immediately at configuration time.

## Verification

- **verify()** performs a final pass: all registered expectations must be satisfied (call counts as specified). Raises `UnsatisfiedExpectationError` listing every unsatisfied expectation with expected vs actual call counts. Diagnostic text does not change matching or dispatch rules.

## Exhaustion

An expectation is **exhausted** when its quantifier allows no further calls. Further calls that would match an exhausted expectation skip it and look for the next matching non-exhausted expectation. If none exists, `UnexpectedCallError` is raised. The error lists registered candidates for that name and why each was rejected (`args mismatch`, `exhausted`, or `blocked by` a prerequisite). This listing is diagnostic only; it does not change which expectation is selected.

Until the quantifier is exhausted, leftover calls reuse the last outcome.

## Edge cases (must be defined and tested)

- No `expect` registered before a call to a regular method - raises `UnexpectedCallError` (whitelist semantics).
- Duplicate or conflicting quantifiers on the same expectation - raises `ConfigurationError` at configuration time.
- All expectations exhausted before `verify()` is called - may still pass if all were satisfied within their quantifier bounds.

## Global call ordering

`not_before` and `in_order` add a **dependency graph** between `Expectation` objects. A dependent expectation can only be dispatched once all its prerequisites are satisfied.

- **`exp.not_before(*prerequisites)`** - declares that `exp` must not be consumed until every listed prerequisite satisfies its own constraint (`is_satisfied()` returns `True`). If a prerequisite is not yet satisfied when `exp` would otherwise match, `UnexpectedCallError` is raised immediately (same as any other unexpected call). Cyclic dependencies (A requires B, B requires A) are rejected at configuration time with `ConfigurationError`.
- **`in_order(*expectations)`** - convenience function that links consecutive expectations pairwise: `expectations[i].not_before(expectations[i-1])` for each `i ≥ 1`. Zero or one argument is a no-op.

**Semantics of "satisfied" for dependency purposes** - identical to `verify()`: the expectation's quantifier constraint is met (`is_satisfied()` returns `True`). Specifically:

- A `maybe()` expectation that was never called is considered satisfied.
- A `never()` expectation that was never called is considered satisfied; one that was called (a violation) is not.

Dependencies are a **dispatch-time guard only** and do not add new criteria to `verify()`. Unsatisfied prerequisites at the end of the test are caught by `verify()` through the normal quantifier check, not through dependency tracking.

Cross-mock dependencies (prerequisites on a different `DeclarativeMock` instance) are supported.

## Non-goals

- No signature binding: `expect("method", …)` checks that `method` exists on the spec, not that the argument list matches the real signature.
- No automatic `verify()` at teardown.
- No spies and no patching of live objects, modules, or `sys.modules`.
- Not thread-safe.
- Exact class names and internal algorithms.
