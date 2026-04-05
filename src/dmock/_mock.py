from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, assert_never
from unittest.mock import AsyncMock, Mock

from dmock._exceptions import (
    ConfigurationError,
    UnexpectedCallError,
    UnsatisfiedExpectationError,
)
from dmock._expectation import Expectation
from dmock._types import DefaultOutcome, RaiseOutcome, ReturnOutcome, RunOutcome


if TYPE_CHECKING:
    from dmock._types import Outcome


def _find_expectation(
    expectations: list[Expectation],
    name: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> Expectation | None:
    for exp in expectations:
        if exp.method_name != name:
            continue
        if exp.is_exhausted():
            continue
        if exp.matches(args, kwargs):
            return exp
    return None


def _apply_outcome(
    outcome: Outcome,
    mock: Mock,
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
            return getattr(mock, name)(*args, **kwargs)
        case _:
            assert_never(outcome)


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


if TYPE_CHECKING:
    from typing import Any

    class _Base(Any):  # type: ignore[misc]
        pass

else:

    class _Base:
        pass


class DeclarativeMock(_Base):
    """Whitelist proxy over unittest.mock.Mock with a fluent expectation DSL."""

    def __init__(self, spec: type, /, **kwargs: object) -> None:
        self._mock: Mock = Mock(spec=spec, **kwargs)
        self._expectations: list[Expectation] = []
        self._hooked: set[str] = set()
        self._properties: dict[str, object] = {}

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
                f"a property stub is already registered for this name."
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
                f"an expectation is already registered for this name."
            )
        self._properties[name] = value

    def assert_expectations(self) -> None:
        """Verify all registered expectations are satisfied.

        Raises UnsatisfiedExpectationError listing every unsatisfied expectation.
        """
        unsatisfied = [e for e in self._expectations if not e.is_satisfied()]
        if not unsatisfied:
            return
        lines = "\n".join(f"  {e!r}" for e in unsatisfied)
        raise UnsatisfiedExpectationError(f"Unsatisfied expectations:\n{lines}")

    # -- Interception --

    def __getattr__(self, name: str) -> Any:
        mock_attr = getattr(self._mock, name)  # AttributeError if not on spec
        if _is_dunder(name):
            return mock_attr
        if name in self._properties:
            return self._properties[name]
        if name not in self._hooked:
            raise UnexpectedCallError(
                f"Unexpected call: {name!r} has no registered expectation."
            )

        if isinstance(mock_attr, AsyncMock):

            async def async_dispatcher(*args: object, **kwargs: object) -> object:
                result = self._dispatch(name, *args, **kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result

            return async_dispatcher
        else:

            def dispatcher(*args: object, **kwargs: object) -> object:
                return self._dispatch(name, *args, **kwargs)

            return dispatcher

    # -- Internal dispatch --

    def _dispatch(self, name: str, /, *args: object, **kwargs: object) -> object:
        exp = _find_expectation(self._expectations, name, args, kwargs)
        if exp is None:
            raise UnexpectedCallError(
                f"Unexpected call: {name!r} called with args={args!r}, kwargs={kwargs!r} "
                f"- no matching non-exhausted expectation."
            )
        outcome = exp.consume()
        return _apply_outcome(outcome, self._mock, name, args, kwargs)

    def __repr__(self) -> str:
        spec_name = getattr(self._mock, "_spec_class", type(None)).__name__
        return f"DeclarativeMock(spec={spec_name})"
