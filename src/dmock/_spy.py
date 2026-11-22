from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Generic, Never, Self, final, overload

from dmock._exceptions import (
    BlockedCallError,
    ConfigurationError,
    DeclarativeMockError,
    NoMatchingCallError,
    UnsatisfiedObservationError,
)
from dmock._interaction import Interaction, Mediator
from dmock._protocols import T
from dmock._registry import SpyRegistry
from dmock._types import (
    ConditionCheck,
    DefaultOutcome,
    RaiseCheck,
    RaiseOutcome,
    RecordedCall,
    ReturnCheck,
    ReturnOutcome,
)


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Concatenate

    from dmock._interaction import Expectation, Observation
    from dmock._matchers import (
        _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
        _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
    )
    from dmock._protocols import P, R
    from dmock._types import (
        Outcome,
    )

    class _Base(Any):  # type: ignore[misc]
        pass

else:

    class _Base:
        pass


@dataclass(frozen=True, slots=True)
class _ObservationLookup(Generic[T]):
    matched: Observation[T, ..., object] | None
    rejected: tuple[Observation[T, ..., object], ...]


_RESERVED_DSL_NAMES: frozenset[str] = frozenset({"observe", "verify"})


class SpyMediator(Generic[T], Mediator[T]):
    def __init__(self, mock: DeclarativeSpy[T]) -> None:
        self._mock = mock

    def mediate(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Expectation[T, Any, Any] | Observation[T, Any, Any]:
        return self._mock.observe(name, args, kwargs)


@final
class DeclarativeSpy(Generic[T], _Base):
    @overload
    def __new__(cls, obj: type[T], /) -> Never: ...
    @overload
    def __new__(cls, obj: T, /) -> Self: ...
    def __new__(cls, obj: T | type[T], /) -> Self:
        return object.__new__(cls)

    def __init__(self, obj: T, /) -> None:
        if isinstance(obj, type):
            raise ConfigurationError(f"Object {obj!r} has to be an instance, not type.")

        self.__obj = obj
        colliding = sorted(name for name in _RESERVED_DSL_NAMES if hasattr(obj, name))
        if colliding:
            names = ", ".join(repr(name) for name in colliding)
            raise ConfigurationError(
                f"Object {obj!r} has reserved DSL name(s) {names}. "
                "Rename those attributes on the object."
            )

        self.__observations: list[Observation[T, ..., object]] = []
        self.__hooked: set[str] = set()
        self.__calls: list[RecordedCall] = []
        SpyRegistry.add(self)

    # -- Public DSL --

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        any_args: _AnyArgsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], R],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], R],
        any_args: _AnyArgsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], R],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P], R],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Observation[T, P, R]: ...

    @overload
    def observe(
        self,
        name: str,
        /,
        *args: object,
        **kwargs: object,
    ) -> Observation[T, ..., object]: ...

    def observe(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Any:
        resolved = self.__spec_attribute_name(name)
        attr = getattr(self.__obj, resolved)  # spec validation
        # TODO: add something similar to dmock
        if not callable(attr):
            raise ConfigurationError(
                f"Cannot register observation for non-callable attribute "
                f"'{resolved}' of {type(self.__obj).__name__!r} "
                f"(got {type(attr).__name__}: {attr!r})"
            )

        exp: Observation[T, ..., object] = Interaction[T, ..., object].observation(
            SpyMediator(self), resolved, args, kwargs
        )
        self.__observations.append(exp)
        self.__hooked.add(resolved)
        return exp

    def verify(self) -> None:
        unsatisfied = [e for e in self.__observations if not e.is_satisfied()]
        if not unsatisfied:
            return

        raise UnsatisfiedObservationError(unsatisfied, self.__calls)

    # -- Interception --

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self.__obj, name)  # AttributeError if not on spec
        if name not in self.__hooked:
            return attr

        if inspect.iscoroutinefunction(attr) or inspect.iscoroutinefunction(
            getattr(attr, "__call__", None)  # noqa: B004
        ):

            @wraps(attr)
            async def async_dispatcher(*args: object, **kwargs: object) -> object:
                try:
                    result = await attr(*args, **kwargs)
                except BaseException as exc:
                    self.__dispatch(name, exc, *args, **kwargs)
                    raise
                else:
                    self.__dispatch(name, result, *args, **kwargs)
                    return result

            return async_dispatcher

        if callable(attr):

            @wraps(attr)
            def dispatcher(*args: object, **kwargs: object) -> object:
                try:
                    result = attr(*args, **kwargs)
                except BaseException as exc:
                    self.__dispatch(name, exc, *args, **kwargs)
                    raise
                else:
                    self.__dispatch(name, result, *args, **kwargs)
                    return result

            return dispatcher

        return attr

    # -- Internal dispatch --

    def __dispatch(
        self, name: str, result: object, /, *args: object, **kwargs: object
    ) -> None:
        call = RecordedCall(name, args, dict(kwargs))
        self.__calls.append(call)

        lookup = self.__lookup_observation(name, args, kwargs)
        if lookup.matched is None:
            raise NoMatchingCallError(call, lookup.rejected, self.__calls)

        exp = lookup.matched
        blocked = [req for req in exp.requires if not req.is_satisfied()]
        if blocked:
            raise BlockedCallError(call, exp, blocked, self.__calls)

        self.__apply_outcome(exp.consume(), name, result, args, kwargs)

    def __lookup_observation(
        self,
        name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> _ObservationLookup[T]:
        candidates = tuple(e for e in self.__observations if e.method_name == name)
        for exp in candidates:
            if not exp.is_exhausted() and exp.matches(args, kwargs):
                return _ObservationLookup(exp, ())

        return _ObservationLookup(None, candidates)

    def __apply_outcome(  # noqa: C901, PLR0912
        self,
        outcome: Outcome,
        name: str,
        result: object,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        condition: Callable[[], bool]
        match outcome:
            case ReturnOutcome():
                if not result == outcome.value:
                    # TODO: add exception
                    raise DeclarativeMockError()

                return
            case RaiseOutcome():
                exc = outcome.exception
                if isinstance(exc, type):
                    if not isinstance(result, exc):
                        # TODO: add exception
                        raise DeclarativeMockError()
                elif not (isinstance(result, type(exc)) and str(result) == str(exc)):
                    # TODO: add exception
                    raise DeclarativeMockError()

                return
            case ReturnCheck():
                if not result == outcome.value:
                    # TODO: add exception
                    raise DeclarativeMockError()

                if outcome.func is None:
                    return

                condition = outcome.func
            case RaiseCheck():
                exc = outcome.exception
                if isinstance(exc, type):
                    if not isinstance(result, exc):
                        # TODO: add exception
                        raise DeclarativeMockError()
                elif not (isinstance(result, type(exc)) and str(result) == str(exc)):
                    # TODO: add exception
                    raise DeclarativeMockError()

                if outcome.func is None:
                    return

                condition = outcome.func
            case ConditionCheck():
                condition = outcome.func
            case DefaultOutcome():
                return
            case _:
                raise AssertionError(
                    f"Expected code to be unreachable, but got: {outcome}"
                )

        if condition():
            return

        # TODO: add exception
        raise DeclarativeMockError()

    def __spec_attribute_name(self, name: object) -> str:
        """Return the spec attribute name for a string or callable."""
        if isinstance(name, str):
            return name

        attr_name = getattr(name, "__name__", None)
        if isinstance(attr_name, str):
            return attr_name

        raise ConfigurationError(f"Cannot resolve a spec attribute name from {name!r}.")

    def __repr__(self) -> str:
        return f"DeclarativeSpy(obj={self.__obj!r})"


@overload
def dspy(spec: type[T], /) -> Never: ...
@overload
def dspy(spec: T, /) -> DeclarativeSpy[T]: ...
def dspy(spec: T, /) -> DeclarativeSpy[T]:
    return DeclarativeSpy(spec)
