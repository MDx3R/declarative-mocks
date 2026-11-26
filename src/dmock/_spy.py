from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Generic, final, overload

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
from dmock.exceptions._exceptions import (
    BlockedCallError,
    ConfigurationError,
    DeclarativeMockError,
    NoMatchingCallError,
    UnsatisfiedObservationError,
)


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Concatenate, Never, Self

    from dmock._interaction import Expectation, Observation
    from dmock._protocols import P, R
    from dmock._types import (
        Outcome,
    )
    from dmock.matchers._matchers import (
        _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
        _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
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
    """Mediator that registers chained observations on a :class:`DeclarativeSpy`."""

    def __init__(self, mock: DeclarativeSpy[T]) -> None:
        self._mock = mock

    def mediate(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Expectation[T, Any, Any] | Observation[T, Any, Any]:
        """Forward a chained ``observe`` call to the underlying spy."""
        return self._mock.observe(name, *args, **kwargs)


@final
class DeclarativeSpy(Generic[T], _Base):
    """Pass-through spy proxy over a live object with an observation DSL.

    Unhooked attributes and methods delegate directly to the wrapped object.
    Methods registered via :meth:`observe` still execute on the real object,
    while their arguments, call counts, ordering, and results or exceptions are
    checked against the declared expectations.

    The names ``observe`` and ``verify`` are reserved: an object that defines
    either raises :class:`~dmock.ConfigurationError` at construction.

    Args:
        obj: Live object instance to wrap (not a class). Positional-only.

    Raises:
        ConfigurationError: If `obj` is a class/type, or defines a reserved DSL
            name (``observe`` or ``verify``).

    Examples:
        >>> from dmock import DeclarativeSpy
        >>> from dmock.matchers import AnythingOfType
        >>> class Service:
        ...     def fetch(self, key: str) -> str:
        ...         return key.upper()
        ...
        ...     def close(self) -> None:
        ...         pass
        >>> spy = DeclarativeSpy(Service())
        >>> spy.observe("fetch", "a").returns("A").once()
        Observation(fetch('a'))
        >>> spy.fetch("a")
        'A'
        >>> (
        ...     spy.observe(Service.fetch, AnythingOfType(str))
        ...     .returns("B")
        ...     .once()
        ...     .observe(Service.close)
        ...     .returns(None)
        ...     .once()
        ... )
        Observation(close())
        >>> spy.fetch("b")
        'B'
        >>> spy.close()
        >>> spy.verify()
        >>> spy
        DeclarativeSpy(obj=<...Service object...>)
    """

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
    ) -> Observation[T, ..., Any]: ...

    def observe(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Any:
        """Register an observation for callable attribute `name` on the wrapped object.

        `name` is a method name or an unbound method/callable taken from the
        wrapped object's class. Absence of `*args` and `**kwargs` means a call
        with no arguments, not a wildcard. Use matchers such as
        :data:`~dmock.Anything` or :data:`~dmock.ANY_ARGS` to accept varying
        values.

        Args:
            name: Callable attribute on the wrapped object. Positional-only.
            *args: Expected positional arguments, possibly matchers.
            **kwargs: Expected keyword arguments, possibly matchers.

        Returns:
            An :class:`~dmock.Observation` for chaining outcome checks and
            quantifiers.

        Raises:
            AttributeError: If `name` is not on the wrapped object.
            ConfigurationError: If `name` is not callable or cannot be
                resolved.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A")
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
        """
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
        """Verify that every registered observation meets its quantifier.

        Raises:
            UnsatisfiedObservationError: One or more observations are unmet.
                The message lists each as ``expected <constraint>, got <n>``
                and includes the call history when any calls were dispatched.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> from dmock.exceptions import UnsatisfiedObservationError
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").once()
            Observation(fetch('a'))
            >>> try:
            ...     spy.verify()
            ... except UnsatisfiedObservationError as exc:
            ...     "expected exactly 1 call(s), got 0" in str(exc)
            True
            >>> spy.fetch("a")
            'A'
        """
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

        # NOTE: should be unreachable as long as observe raises on a non-callable
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
        condition: Callable[[object], bool]
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

        if condition(result):
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
    """Create a :class:`DeclarativeSpy` wrapping `spec`.

    Convenience factory equivalent to ``DeclarativeSpy(spec)``.

    Args:
        spec: Live object instance to spy on (not a class). Positional-only.

    Returns:
        A new :class:`DeclarativeSpy` wrapping `spec`.

    Raises:
        ConfigurationError: If `spec` is a class/type or defines a reserved
            DSL name.

    Examples:
        >>> from dmock import dspy
        >>> class Service:
        ...     def fetch(self, key: str) -> str:
        ...         return key.upper()
        >>> spy = dspy(Service())
        >>> spy.observe("fetch", "a").returns("A").once()
        Observation(fetch('a'))
        >>> spy.fetch("a")
        'A'
        >>> spy.verify()
    """
    return DeclarativeSpy(spec)
