from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, assert_never
from unittest.mock import AsyncMock, Mock

from dmock._exceptions import (
    BlockedCallError,
    ConfigurationError,
    NoMatchingCallError,
    UnregisteredCallError,
    UnsatisfiedExpectationError,
)
from dmock._expectation import Expectation
from dmock._types import (
    DefaultOutcome,
    RaiseOutcome,
    RecordedCall,
    ReturnOutcome,
    RunOutcome,
)


if TYPE_CHECKING:
    from typing import Any

    from dmock._types import Outcome

    class _Base(Any):  # type: ignore[misc]
        pass

else:

    class _Base:
        pass


@dataclass(frozen=True, slots=True)
class _ExpectationLookup:
    matched: Expectation | None
    rejected: tuple[Expectation, ...]


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


_RESERVED_DSL_NAMES: frozenset[str] = frozenset({"expect", "property", "verify"})


class DeclarativeMock(_Base):
    """Whitelist proxy over unittest.mock.Mock with a fluent expectation DSL."""

    def __init__(self, spec: type, /, **kwargs: object) -> None:
        self._mock: Mock = Mock(spec=spec, **kwargs)
        colliding = sorted(
            name for name in _RESERVED_DSL_NAMES if hasattr(self._mock, name)
        )
        if colliding:
            names = ", ".join(repr(name) for name in colliding)
            raise ConfigurationError(
                f"Spec {spec.__name__!r} defines reserved DSL name(s) {names}. "
                "Rename those attributes on the spec, or wrap a protocol without them."
            )

        self._expectations: list[Expectation] = []
        self._hooked: set[str] = set()
        self._properties: dict[str, object] = {}
        self._calls: list[RecordedCall] = []

    # -- Public DSL --

    def expect(self, name: str, /, *args: object, **kwargs: object) -> Expectation:
        """Register an expectation for attribute *name* on the spec.

        Raises AttributeError if *name* is not on the spec.
        Raises ConfigurationError if *name* is already registered as a property stub.
        Returns an Expectation builder for chaining outcomes and quantifiers.
        """
        getattr(self._mock, name)  # spec validation
        if name in self._properties:
            raise ConfigurationError(
                f"Cannot register expectation for {name!r}: "
                "a property stub is already registered for this name."
            )

        exp = Expectation(name, args, kwargs)
        self._expectations.append(exp)
        self._hooked.add(name)
        return exp

    def property(self, name: str, value: object, /) -> None:
        """Register a stub attribute *name* that returns *value* on access.

        Raises AttributeError if *name* is not on the spec.
        Raises ConfigurationError if *name* is already registered via expect().
        No quantifier tracking; always considered satisfied.
        """
        getattr(self._mock, name)  # spec validation
        if name in self._hooked:
            raise ConfigurationError(
                f"Cannot register property {name!r}: "
                "an expectation is already registered for this name."
            )

        self._properties[name] = value

    def verify(self) -> None:
        """Verify all registered expectations are satisfied.

        Raises UnsatisfiedExpectationError listing every unsatisfied expectation.
        """
        unsatisfied = [e for e in self._expectations if not e.is_satisfied()]
        if not unsatisfied:
            return

        raise UnsatisfiedExpectationError(unsatisfied, self._calls)

    # -- Interception --

    def __getattr__(self, name: str) -> Any:
        mock_attr = getattr(self._mock, name)  # AttributeError if not on spec
        if _is_dunder(name):
            return mock_attr

        if name in self._properties:
            return self._properties[name]

        if name not in self._hooked:
            raise UnregisteredCallError(name, self._calls)

        if isinstance(mock_attr, AsyncMock):

            async def async_dispatcher(*args: object, **kwargs: object) -> object:
                result = self._dispatch(name, *args, **kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result

            return async_dispatcher

        def dispatcher(*args: object, **kwargs: object) -> object:
            return self._dispatch(name, *args, **kwargs)

        return dispatcher

    # -- Internal dispatch --

    def _dispatch(self, name: str, /, *args: object, **kwargs: object) -> object:
        call = RecordedCall(name, args, dict(kwargs))
        self._calls.append(call)

        lookup = self._lookup_expectation(name, args, kwargs)
        if lookup.matched is None:
            raise NoMatchingCallError(call, lookup.rejected, self._calls)

        exp = lookup.matched
        blocked = [req for req in exp.requires if not req.is_satisfied()]
        if blocked:
            raise BlockedCallError(call, exp, blocked, self._calls)

        return self._apply_outcome(exp.consume(), name, args, kwargs)

    def _lookup_expectation(
        self,
        name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> _ExpectationLookup:
        rejected: list[Expectation] = []
        matched: Expectation | None = None
        for exp in self._expectations:
            if exp.method_name != name:
                continue

            if exp.is_exhausted() or not exp.matches(args, kwargs):
                rejected.append(exp)
                continue

            if matched is None:
                matched = exp

        return _ExpectationLookup(matched, tuple(rejected))

    def _apply_outcome(
        self,
        outcome: Outcome,
        name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> object:
        match outcome:
            case ReturnOutcome():
                return outcome.value
            case RaiseOutcome():
                exc = outcome.exception
                raise (exc() if isinstance(exc, type) else exc)
            case RunOutcome():
                return outcome.func(*args, **kwargs)
            case DefaultOutcome():
                return getattr(self._mock, name)(*args, **kwargs)
            case _:
                assert_never(outcome)

    def __repr__(self) -> str:
        spec_name = getattr(self._mock, "_spec_class", type(None)).__name__
        return f"DeclarativeMock(spec={spec_name})"
