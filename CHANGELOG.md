# Changelog

All notable changes to this project are documented in this file.

## [0.3.0] - 2026-10-18

- `expect` and `property` accept an unbound spec attribute (such as `Directory.lookup`, `Directory.value`) or a string name. The attribute form lets a type checker check the arguments and `.returns` / `.runs`. A string leaves the expectation lenient.
- `DeclarativeMock` is generic over the spec. Abstract classes and protocols are valid specs.
- `dmock(spec)` constructs a `DeclarativeMock`.
- Fix: a call stops at the first matching expectation that is not exhausted. A later expectation for the same name, including a matcher that would raise on the actual arguments, is tried only after the earlier one is exhausted.

## [0.2.0] - 2026-10-18

- Value, container, ordering, and text matchers, including `Equals`, `Contains`, `Range`, `LessThan`, `GreaterThan`, `Approx`, `StartsWith`, `Regex`, `TRUTHY`, `And`, and `Or`.
- Matcher operators: `==` and `!=` compare through `matches`, `~` is `Not`, and `&` / `|` build `And` / `Or`.
- README usage examples and the REFERENCE matcher catalog.

## [0.1.1] - 2026-09-13

- Document PyPI installation (`pip install declarative-mocks`) and add a version badge. This is a docs-only release so the project page matches GitHub.

## [0.1.0] - 2026-09-13

First release: a typed, gomock-inspired expectation DSL over `unittest.mock`.

- `DeclarativeMock(spec)` you construct and pass in; unregistered calls fail immediately.
- Fluent `expect` with positional vs keyword matching, matchers (`Anything`, `ANY_ARGS` / `ANY_KWARGS`, `MatchedBy`, …), and chained `.returns()` / `.raises()` / `.runs()`.
- One quantifier per expectation (`.once()`, `.times(n)`, `.at_least(n)`, `.maybe()`, `.never()`, …); call order via `.not_before()` and `in_order()`.
- Same DSL for sync and async spec methods; `verify()` checks counts at the end.
- Strict typing (`py.typed`), Python 3.11-3.14, no runtime dependencies.
