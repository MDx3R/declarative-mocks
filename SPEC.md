# SPEC — behavioral specification (declarative-mocks)

This document describes **what** the library must do from a tester’s perspective. It does not prescribe internal implementation.

## Purpose

The library provides a **declarative** layer over `unittest.mock` (typically `Mock` / `AsyncMock` with `spec=…`) so tests can express **ordered expectations**, **return values**, **exceptions**, **side effects**, and **call-count constraints** in a fluent API.

## Core principles

1. **Order matters** — expectations for the same attribute name are consumed in the order they were registered unless the specification says otherwise.
2. **Explicit beats implicit** — an expectation without arguments means “called with no arguments”, not “any arguments”. To accept arbitrary values, matchers such as `Anything` / `Anything()`, or variadic wildcards `ANY_ARGS` / `ANY_KWARGS`, must be used explicitly.
3. **Positional vs keyword** — matching distinguishes positional-only, keyword-only, and mixed call shapes as in Python: the same value passed positionally vs by keyword is not interchangeable unless the DSL explicitly allows it.
4. **Sync and async** — the mock should support both synchronous and asynchronous callables on the spec where applicable (exact rules follow `unittest.mock` + library behavior).

## Expectation registration

- `expect(name, …)` registers an expectation for an attribute (usually a method name) on the mock.
- Arguments after the name describe **expected** call arguments (positional and keyword), possibly using matchers.
- Multiple `returns(…)` / `raises(…)` / `runs(…)` on one expectation define a **sequence** of outcomes for matching calls (order of chained outcomes matters).

## Quantifiers and call counts

Quantifiers constrain how many times a given expectation (or chained block) may match:

- **Implicit / maybe** — if not specified otherwise, later calls may fall through to the next expectation or default mock behavior as defined by the library.
- **maybe()** — explicitly optional behavior within the rules of the library.
- **once(), twice(), times(n)** — exact counts.
- **at_least(n), at_most(n), between(min, max)** — bounds.
- **never()** — matching this expectation must not occur (or must fail immediately when violated; exact error type is implementation-defined but must be deterministic).

**Invalid combinations** (e.g. applying two incompatible quantifiers to the same expectation) **must** fail fast at configuration time when possible, or raise a clear error at verification time.

## Outcomes

- **returns(value)** — return a value for a matching call.
- **raises(exc)** — raise an exception instance or type per library rules.
- **runs(callable)** — invoke a callable for effect; may be combined with `returns` per chaining rules (e.g. run then return).

## Verification

- **assert_expectations()** (or equivalent) performs a final pass: all registered expectations must be satisfied (call counts, unmatched expectations, and ordering rules as specified).

## Edge cases (must be defined and tested)

- No `expect` registered before a call — behavior follows `unittest.mock` defaults unless the library documents stricter rules.
- Duplicate or conflicting quantifiers on the same expectation.
- Exhausting all chained `returns` for a call pattern — what happens on further calls (error vs fallback).
- Async methods: awaiting and exception propagation must match documented behavior.

## Non-goals (for this document)

- Exact class names and internal algorithms.
- Full parity with every feature of third-party mock libraries unless explicitly added to REFERENCE.md later.
