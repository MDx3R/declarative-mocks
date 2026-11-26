# Changelog

All notable changes to this project are documented in this file.

## [0.5.0] - 2026-11-26

- **Breaking**: Split the public API into `dmock` (`DeclarativeMock`, `DeclarativeSpy`, `Expectation`, `Observation`, `dmock`, `dspy`, `in_order`), `dmock.checks` (`Check`, `CheckAnd`, `CheckNot`, `CheckOr`), `dmock.matchers` (`Matcher`, `ANY_ARGS`, `ANY_KWARGS`, and all matchers), and `dmock.exceptions` (`DeclarativeMockError`, `UnexpectedCallError`, `UnsatisfiedExpectationError`, `UnsatisfiedObservationError`, `ConfigurationError`).
- Add `DeclarativeSpy` and `dspy(obj)` to wrap live object instances, pass through unhooked attributes and methods, and observe hooked sync or async calls via `.observe()` and `.verify()` (with automatic pytest verification).
- Add `Observation` outcome checks: `.returns(value, *, condition=None, repeat=1)`, `.raises(exc, *, condition=None, repeat=1)`, and `.condition(func, *, repeat=1)`, plus quantifiers, `.maybe()`, `.not_before()`, `in_order()`, and `UnsatisfiedObservationError`.
- Add `dmock.checks` (`Check`, `CheckNot`, `CheckAnd`, `CheckOr`) with `~`, `&`, and `|` operators for composing predicate checks.
- Add chained interactions: `Expectation.expect(...)` and `Observation.observe(...)` register a follow-up interaction ordered with `.not_before(self)`.
- Add Python 3.15 support.
- `Attr` accepts several attribute names and matches only when the object has every one.
- `Namespace` matches an object whose slots and instance attributes are exactly the given attributes. Class attributes and properties do not count.
- `PartialNamespace` matches an object that has the given slots and instance attributes. Class attributes and properties do not count. Extra attributes are ignored.

## [0.4.2] - 2026-10-31

- Fix the README quantifier example. `.returns()` takes `repeat`. `.times(n)` is the quantifier.

## [0.4.1] - 2026-10-31

- `CollectionOf` matches the same sequence, set, or mapping kind. Order matters for sequences only. `SequenceOf`, `SetOf`, and `MappingOf` match one kind.
- `AnythingOfType` matches an instance of a type. `exact=True` requires that exact type. `InstanceOf` is an alias.
- `HasLen` matches a sized value by its length. The length may be a matcher.
- `AnyOrder` matches the same items in any order. Each expected item is paired with a distinct element.
- `PartialMapping` matches a mapping that contains the given pairs. Extra keys are ignored.
- `IsNow` matches a datetime within `tolerance` of the current time.
- `IsUUID` matches a UUID or a UUID string, optionally of one version. `IS_UUID` accepts any version.
- `IsDataclass` matches a dataclass instance. `instance=False` matches a dataclass class or instance. `IS_DATACLASS` matches an instance.

## [0.4.0] - 2026-10-23

- pytest calls `verify()` when a test finishes. An unmet expectation fails that test. An exception the test already raised is kept. Mocks created while fixtures finalize are checked after teardown and do not leak into the next test.
- `.returns()`, `.raises()`, and `.runs()` take a keyword-only `repeat` (default 1). `repeat=n` queues that outcome n times. `repeat` less than 1 raises `ConfigurationError`.

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
