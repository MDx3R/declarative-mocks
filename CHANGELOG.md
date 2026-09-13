# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-09-13

First release: a typed, gomock-inspired expectation DSL over `unittest.mock`.

- `DeclarativeMock(spec)` you construct and pass in; unregistered calls fail immediately.
- Fluent `expect` with positional vs keyword matching, matchers (`Anything`, `ANY_ARGS` / `ANY_KWARGS`, `MatchedBy`, …), and chained `.returns()` / `.raises()` / `.runs()`.
- One quantifier per expectation (`.once()`, `.times(n)`, `.at_least(n)`, `.maybe()`, `.never()`, …); call order via `.not_before()` and `in_order()`.
- Same DSL for sync and async spec methods; `verify()` checks counts at the end.
- Strict typing (`py.typed`), Python 3.11-3.14, no runtime dependencies.
