from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, assert_never, final, overload
from unittest.mock import AsyncMock, Mock

from dmock._exceptions import (
    BlockedCallError,
    ConfigurationError,
    NoMatchingCallError,
    UnregisteredCallError,
    UnsatisfiedExpectationError,
)
from dmock._expectation import Expectation
from dmock._protocols import T
from dmock._types import (
    DefaultOutcome,
    RaiseOutcome,
    RecordedCall,
    ReturnOutcome,
    RunOutcome,
)


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Concatenate

    from dmock._matchers import (
        _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
        _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
    )
    from dmock._protocols import ClassOf, P, PropertyOf, R
    from dmock._types import Outcome

    class _Base(Any):  # type: ignore[misc]
        pass

else:

    class _Base:
        pass


@dataclass(frozen=True, slots=True)
class _ExpectationLookup:
    matched: Expectation[..., object] | None
    rejected: tuple[Expectation[..., object], ...]


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


_RESERVED_DSL_NAMES: frozenset[str] = frozenset({"expect", "property", "verify"})


@final
class DeclarativeMock(Generic[T], _Base):
    """Whitelist proxy over ``unittest.mock.Mock`` with a fluent expectation DSL.

    Every spec method must be registered with :meth:`expect` before it is
    called. Dunder methods fall through to the internal ``Mock`` unless
    registered. The names ``expect``, ``property``, and ``verify`` are
    reserved: a spec that defines any of them raises
    :class:`~dmock.ConfigurationError` at construction.

    Args:
        spec: Class or protocol whose attributes are allowed. Positional-only.
        **kwargs: Forwarded to ``unittest.mock.Mock``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", "a").returns("A").once()
        Expectation(fetch('a'))
        >>> mock.fetch("a")
        'A'
        >>> mock.verify()
        >>> mock
        DeclarativeMock(spec=Service)
    """

    # `type[T]` is what callers should see. mypy treats that as a concrete subclass
    # and rejects an abstract class, so the second overload accepts any class object
    # (anything that has `mro`, actually) whose construction returns `T`.
    @overload
    def __init__(self, spec: type[T], /, **kwargs: object) -> None: ...

    @overload
    def __init__(self, spec: ClassOf[T], /, **kwargs: object) -> None: ...

    def __init__(self, spec: type[T] | ClassOf[T], /, **kwargs: object) -> None:
        self.__mock: Mock = Mock(spec=spec, **kwargs)
        colliding = sorted(
            name for name in _RESERVED_DSL_NAMES if hasattr(self.__mock, name)
        )
        if colliding:
            names = ", ".join(repr(name) for name in colliding)
            raise ConfigurationError(
                f"Spec {spec.__name__!r} defines reserved DSL name(s) {names}. "
                "Rename those attributes on the spec, or wrap a protocol without them."
            )

        self.__expectations: list[Expectation[..., object]] = []
        self.__hooked: set[str] = set()
        self.__properties: dict[str, object] = {}
        self.__calls: list[RecordedCall] = []

    # -- Public DSL --

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        any_args: _AnyArgsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], Coroutine[Any, Any, R]],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], R],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], R],
        any_args: _AnyArgsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], R],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P], R],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Expectation[P, R]: ...

    @overload
    def expect(
        self,
        name: str,
        /,
        *args: object,
        **kwargs: object,
    ) -> Expectation[..., object]: ...

    def expect(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Any:
        """Register an expectation for attribute `name` on the spec.

        `name` is an attribute name or the unbound method or property taken
        from the spec class. Absence of `*args` and `**kwargs` means a call
        with no arguments, not a wildcard. Use matchers such as
        :data:`~dmock.Anything` or :data:`~dmock.ANY_ARGS` to accept varying
        values.

        Args:
            name: Spec attribute to intercept. Positional-only.
            *args: Expected positional arguments, possibly matchers.
            **kwargs: Expected keyword arguments, possibly matchers.

        Returns:
            An :class:`~dmock.Expectation` for chaining outcomes and
            quantifiers.

        Raises:
            AttributeError: If `name` is not on the spec.
            ConfigurationError: If `name` is already a :meth:`property` stub,
                or a callable or property name cannot be resolved.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A")
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
        """
        resolved = self.__spec_attribute_name(name)
        getattr(self.__mock, resolved)  # spec validation
        if resolved in self.__properties:
            raise ConfigurationError(
                f"Cannot register expectation for {resolved!r}: "
                "a property stub is already registered for this name."
            )

        exp: Expectation[..., object] = Expectation(resolved, args, kwargs)
        self.__expectations.append(exp)
        self.__hooked.add(resolved)
        return exp

    @overload
    def property(self, name: PropertyOf[T, R], value: R, /) -> None: ...

    @overload
    def property(self, name: str, value: object, /) -> None: ...

    def property(self, name: str | object, value: object, /) -> None:
        """Register a stub attribute `name` that returns `value` on access.

        No call is required. Property stubs have no quantifiers and are not
        checked by :meth:`verify`.

        Args:
            name: Spec attribute to stub. Positional-only.
            value: Object returned on attribute access. Positional-only.

        Raises:
            AttributeError: If `name` is not on the spec.
            ConfigurationError: If `name` is already registered via
                :meth:`expect`, or a callable or property name cannot be
                resolved.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     value = 0
            >>> mock = DeclarativeMock(Service)
            >>> mock.property("value", 123)
            >>> mock.value
            123
            >>> mock.verify()
        """
        resolved = self.__spec_attribute_name(name)
        getattr(self.__mock, resolved)  # spec validation
        if resolved in self.__hooked:
            raise ConfigurationError(
                f"Cannot register property {resolved!r}: "
                "an expectation is already registered for this name."
            )

        self.__properties[resolved] = value

    def verify(self) -> None:
        """Verify that every registered expectation meets its quantifier.

        Raises:
            UnsatisfiedExpectationError: One or more expectations are unmet.
                The message lists each as ``expected <constraint>, got <n>``
                and includes the call history when any calls were dispatched.

        Examples:
            >>> from dmock import DeclarativeMock, UnsatisfiedExpectationError
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A").once()
            Expectation(fetch('a'))
            >>> try:
            ...     mock.verify()
            ... except UnsatisfiedExpectationError as exc:
            ...     "expected exactly 1 call(s), got 0" in str(exc)
            True
        """
        unsatisfied = [e for e in self.__expectations if not e.is_satisfied()]
        if not unsatisfied:
            return

        raise UnsatisfiedExpectationError(unsatisfied, self.__calls)

    # -- Interception --

    def __getattr__(self, name: str) -> Any:
        mock_attr = getattr(self.__mock, name)  # AttributeError if not on spec
        if _is_dunder(name):
            return mock_attr

        if name in self.__properties:
            return self.__properties[name]

        if name not in self.__hooked:
            raise UnregisteredCallError(name, self.__calls)

        if isinstance(mock_attr, AsyncMock):

            async def async_dispatcher(*args: object, **kwargs: object) -> object:
                result = self.__dispatch(name, *args, **kwargs)
                if inspect.isawaitable(result):
                    return await result
                return result

            return async_dispatcher

        def dispatcher(*args: object, **kwargs: object) -> object:
            return self.__dispatch(name, *args, **kwargs)

        return dispatcher

    # -- Internal dispatch --

    def __dispatch(self, name: str, /, *args: object, **kwargs: object) -> object:
        call = RecordedCall(name, args, dict(kwargs))
        self.__calls.append(call)

        lookup = self.__lookup_expectation(name, args, kwargs)
        if lookup.matched is None:
            raise NoMatchingCallError(call, lookup.rejected, self.__calls)

        exp = lookup.matched
        blocked = [req for req in exp.requires if not req.is_satisfied()]
        if blocked:
            raise BlockedCallError(call, exp, blocked, self.__calls)

        return self.__apply_outcome(exp.consume(), name, args, kwargs)

    def __lookup_expectation(
        self,
        name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> _ExpectationLookup:
        candidates = tuple(e for e in self.__expectations if e.method_name == name)
        for exp in candidates:
            if not exp.is_exhausted() and exp.matches(args, kwargs):
                return _ExpectationLookup(exp, ())

        return _ExpectationLookup(None, candidates)

    def __apply_outcome(
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
                return getattr(self.__mock, name)(*args, **kwargs)
            case _:
                assert_never(outcome)

    def __spec_attribute_name(self, name: object) -> str:
        """Return the spec attribute name for a string, property, or callable."""
        if isinstance(name, str):
            return name

        if isinstance(name, property):
            getter_name = (
                None
                if (getter := name.fget) is None
                else getattr(getter, "__name__", None)
            )
            if not isinstance(getter_name, str):
                raise ConfigurationError(
                    "Cannot resolve a property name: the property has no getter."
                )

            return getter_name

        attr_name = getattr(name, "__name__", None)
        if isinstance(attr_name, str):
            return attr_name

        raise ConfigurationError(f"Cannot resolve a spec attribute name from {name!r}.")

    def __repr__(self) -> str:
        spec_name = getattr(self.__mock, "_spec_class", type(None)).__name__
        return f"DeclarativeMock(spec={spec_name})"


@overload
def dmock(spec: type[T], /, **kwargs: object) -> DeclarativeMock[T]: ...
@overload
def dmock(spec: ClassOf[T], /, **kwargs: object) -> DeclarativeMock[T]: ...
def dmock(spec: type[T] | ClassOf[T], /, **kwargs: object) -> DeclarativeMock[T]:
    return DeclarativeMock(spec, **kwargs)
