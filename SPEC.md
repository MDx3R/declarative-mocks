# SPEC — behavioral specification (declarative-mocks)

This document describes **what** the library must do from a tester's perspective. It does not prescribe internal implementation.

## Purpose

The library provides a **declarative** layer over `unittest.mock` (typically `Mock` with `spec=…`) so tests can express **ordered expectations**, **return values**, **exceptions**, **side effects**, and **call-count constraints** in a fluent API.

## Core principles

1. **Order matters (per-name)** — expectations for the same attribute name are consumed in the order they were registered. Expectations for different method names are independent and may be called in any order.
2. **Whitelist proxy** — any call to a spec method without a prior `expect()` registration raises `UnexpectedCallError`. The mock is strict by default; regular methods do not fall through to `unittest.mock` defaults. Exception: dunder methods (e.g. `__repr__`, `__str__`) delegate to the internal Mock when not explicitly registered via `expect()`.
3. **Explicit beats implicit** — an expectation without arguments means "called with no arguments", not "any arguments". To accept arbitrary values, matchers such as `Anything` / `Anything()`, or variadic wildcards `ANY_ARGS` / `ANY_KWARGS`, must be used explicitly.
4. **Positional vs keyword** — matching distinguishes positional-only, keyword-only, and mixed call shapes as in Python: the same value passed positionally vs by keyword is not interchangeable unless the DSL explicitly allows it.
5. **Sync and async** — async methods on the spec are detected automatically (via `AsyncMock` detection on the internal Mock child) and return awaitables. The same DSL (`returns`, `raises`, `runs`, quantifiers) applies to both sync and async methods.

## Expectation registration

- `expect(name, …)` registers an expectation for an attribute (usually a method name) on the mock.
- Arguments after the name describe **expected** call arguments (positional and keyword), possibly using matchers.
- Multiple `returns(…)` / `raises(…)` / `runs(…)` on one expectation define a **sequence** of outcomes for matching calls (order of chained outcomes matters).

## Quantifiers and call counts

Quantifiers constrain how many times a given expectation (or chained block) may match:

- **Implicit** — if not specified, the quantifier defaults to exactly the number of chained outcomes (minimum 1).
- **maybe()** — explicitly optional: if the expectation is never called, it still passes verification.
- **once(), twice(), times(n)** — exact counts.
- **at_least(n), at_most(n), between(min, max)** — bounds.
- **never()** — matching this expectation must not occur; any matching call raises `UnexpectedCallError` immediately.

**Invalid combinations** (e.g. applying two incompatible quantifiers to the same expectation) **must** fail fast at configuration time when possible, or raise a clear error at verification time.

## Outcomes

- **returns(value)** — return a single Python value for a matching call. Tuples are returned as tuples; no unpacking is performed.
- **raises(exc)** — raise an exception instance or type. If a type is passed, it is instantiated with no arguments before raising.
- **runs(func)** — call `func(*args, **kwargs)` with the actual call arguments; the return value of `func` becomes the call result.
- **No explicit outcome** — delegates to the internal `unittest.mock.Mock` child (returns a `Mock` object).

## Verification

- **assert_expectations()** performs a final pass: all registered expectations must be satisfied (call counts and ordering rules as specified). Raises `UnsatisfiedExpectationError` listing every unsatisfied expectation.

## Exhaustion

When all outcomes of an expectation are consumed and the quantifier limit is reached, the expectation is **exhausted**. Further calls that would match an exhausted expectation skip it and look for the next matching non-exhausted expectation. If none exists, `UnexpectedCallError` is raised.

## Edge cases (must be defined and tested)

- No `expect` registered before a call to a regular method — raises `UnexpectedCallError` (whitelist semantics).
- Duplicate or conflicting quantifiers on the same expectation — raises `ConfigurationError` at configuration time.
- All expectations exhausted before `assert_expectations()` is called — may still pass if all were satisfied within their quantifier bounds.

## Non-goals (for this document)

- Exact class names and internal algorithms.
- Full parity with every feature of third-party mock libraries unless explicitly added to REFERENCE.md later.
- Global cross-method ordering (`InOrder` / `NotBefore`) — planned but not yet implemented.
