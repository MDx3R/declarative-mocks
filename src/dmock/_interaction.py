from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import (
    TYPE_CHECKING,
    Generic,
    final,
    overload,
)

from dmock._protocols import P, R, T
from dmock._types import (
    AtLeast,
    Between,
    ConditionCheck,
    DefaultOutcome,
    ExactlyN,
    Never,
    RaiseCheck,
    RaiseOutcome,
    ReturnCheck,
    ReturnOutcome,
    RunOutcome,
)
from dmock.exceptions._exceptions import ConfigurationError, ExceededCallError
from dmock.matchers._matchers import (
    _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
    _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
)


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Sequence
    from typing import Any, Concatenate, Self

    from dmock._protocols import P2, R2, E
    from dmock._types import Outcome, Quantifier


class Expectation(ABC, Generic[T, P, R]):
    """A single expected call: fluent builder for outcomes and quantifiers.

    Constructed by :meth:`~dmock.DeclarativeMock.expect`. Chained ``returns`` /
    ``raises`` / ``runs`` are a sequence of outcomes for successive matching
    calls.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", "a").returns("first").returns("second")
        Expectation(fetch('a'))
        >>> mock.fetch("a")
        'first'
        >>> mock.fetch("a")
        'second'
        >>> mock.expect("fetch", "b").returns("ok", repeat=2)
        Expectation(fetch('b'))
        >>> mock.fetch("b")
        'ok'
        >>> mock.fetch("b")
        'ok'
        >>> mock.verify()
    """

    # -- Fluent outcome builders --

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: str,
        /,
        *args: object,
        **kwargs: object,
    ) -> Expectation[T, ..., Any]: ...

    @abstractmethod
    def expect(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Any:
        """Register a follow-up expectation ordered after this one.

        Delegates to the parent :class:`~dmock.DeclarativeMock` and
        automatically chains :meth:`not_before` on `self`, so the new
        expectation cannot match until this one is satisfied.

        Args:
            name: Spec attribute to intercept. Positional-only.
            *args: Expected positional arguments, possibly matchers.
            **kwargs: Expected keyword arguments, possibly matchers.

        Returns:
            A new :class:`Expectation` ordered after `self`.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def start(self) -> None: ...
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> _ = (
            ...     mock.expect("start")
            ...     .returns(None)
            ...     .once()
            ...     .expect("fetch", "a")
            ...     .returns("A")
            ... )
            >>> mock.start()
            >>> mock.fetch("a")
            'A'
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def returns(self, value: R, *, repeat: int = 1) -> Self:
        """Declare the return value for the next matching call.

        Args:
            value: Object returned as-is (tuples are not unpacked).
            repeat: How many successive calls receive this outcome. Must be
                at least 1.

        Returns:
            This expectation, for chaining.

        Raises:
            ConfigurationError: If `repeat` is less than 1.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A", repeat=2)
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
            >>> mock.fetch("a")
            'A'
        """
        ...

    @abstractmethod
    def raises(
        self,
        exc: BaseException | type[BaseException],
        *,
        repeat: int = 1,
    ) -> Self:
        """Declare that the next matching call raises `exc`.

        Args:
            exc: Exception instance, or a type instantiated with no arguments.
            repeat: How many successive calls raise `exc`. Must be at least 1.

        Returns:
            This expectation, for chaining.

        Raises:
            ConfigurationError: If `repeat` is less than 1.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").raises(KeyError)
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            Traceback (most recent call last):
                ...
            KeyError
        """
        ...

    @overload
    def runs(self, func: Callable[P, R], *, repeat: int = 1) -> Self: ...

    @overload
    def runs(self, func: Callable[P, Awaitable[R]], *, repeat: int = 1) -> Self: ...

    @abstractmethod
    def runs(self, func: Callable[P, R | Awaitable[R]], *, repeat: int = 1) -> Self:
        """Call `func` with the actual arguments for the next matching call.

        The return value of `func` becomes the result of that call. Chaining
        ``runs`` then ``returns`` schedules two outcomes for two successive
        calls, not a side effect plus a return on the same call.

        Args:
            func: Called as ``func(*args, **kwargs)`` of the matching invocation.
            repeat: How many successive calls invoke `func`. Must be at least 1.

        Returns:
            This expectation, for chaining.

        Raises:
            ConfigurationError: If `repeat` is less than 1.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> seen: list[str] = []
            >>> def capture(key: str) -> str:
            ...     seen.append(key)
            ...     return "from-runs"
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").runs(capture).returns("from-returns")
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'from-runs'
            >>> seen
            ['a']
            >>> mock.fetch("a")
            'from-returns'
        """
        ...

    # -- Fluent quantifiers --

    @abstractmethod
    def once(self) -> Self:
        """Require exactly one matching call.

        Returns:
            This expectation, for chaining.

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
        """
        ...

    @abstractmethod
    def twice(self) -> Self:
        """Require exactly two matching calls.

        Returns:
            This expectation, for chaining.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A").twice()
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
            >>> mock.fetch("a")
            'A'
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def times(self, n: int) -> Self:
        """Require exactly `n` matching calls.

        Args:
            n: Exact call count. Must be at least 1.

        Returns:
            This expectation, for chaining.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A").times(2)
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
            >>> mock.fetch("a")
            'A'
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def at_least(self, n: int) -> Self:
        """Require at least `n` matching calls, with no upper bound.

        Args:
            n: Minimum call count. Must be at least 1.

        Returns:
            This expectation, for chaining.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A").at_least(2)
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
            >>> mock.fetch("a")
            'A'
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def at_most(self, n: int) -> Self:
        """Allow between 0 and `n` matching calls, inclusive.

        Args:
            n: Maximum call count.

        Returns:
            This expectation, for chaining.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A").at_most(2)
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def between(self, lo: int, hi: int) -> Self:
        """Require between `lo` and `hi` matching calls, inclusive.

        Args:
            lo: Minimum call count.
            hi: Maximum call count.

        Returns:
            This expectation, for chaining.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A").between(1, 2)
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def maybe(self) -> Self:
        """Make this expectation optional: zero calls still pass :meth:`~dmock.DeclarativeMock.verify`.

        Returns:
            This expectation, for chaining.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").returns("A").maybe()
            Expectation(fetch('a'))
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def never(self) -> Self:
        """Forbid any matching call.

        A match raises :class:`~dmock.UnexpectedCallError` immediately.

        Returns:
            This expectation, for chaining.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> mock.expect("fetch", "a").never()
            Expectation(fetch('a'))
            >>> mock.verify()
        """
        ...

    @abstractmethod
    def not_before(
        self, *interactions: Expectation[T, P, R] | Observation[T, P, R]
    ) -> Self:
        """Require that every `interactions` item is satisfied before this one.

        Args:
            *interactions: Prerequisites that must meet their own quantifiers.

        Returns:
            This expectation, for chaining.

        Raises:
            ConfigurationError: If adding a requirement would create a cycle.

        Examples:
            >>> from dmock import DeclarativeMock
            >>> class Service:
            ...     def start(self) -> None: ...
            ...     def fetch(self, key: str) -> str: ...
            >>> mock = DeclarativeMock(Service)
            >>> init = mock.expect("start").returns(None).once()
            >>> mock.expect("fetch", "a").returns("A").not_before(init)
            Expectation(fetch('a'))
            >>> mock.start()
            >>> mock.fetch("a")
            'A'
            >>> mock.verify()
        """
        ...

    @property
    @abstractmethod
    def requires(self) -> Sequence[Expectation[T, Any, Any] | Observation[T, Any, Any]]:
        """Prerequisites that must be satisfied before this expectation can match."""
        ...

    # -- Effective quantifier (auto-adjust to outcome count when not set) --

    @property
    @abstractmethod
    def quantifier(self) -> Quantifier:
        """Effective call-count constraint, defaulting to the outcome count."""
        ...

    @property
    @abstractmethod
    def is_quantifier_locked(self) -> bool:
        """Return whether an explicit quantifier has been set."""
        ...

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Spec attribute this expectation intercepts."""
        ...

    # -- Internal (called by DeclarativeMock) --

    @abstractmethod
    def matches(
        self,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> bool:
        """Return whether `args` and `kwargs` match this expectation."""
        ...

    @abstractmethod
    def consume(self) -> Outcome:
        """Record a match and return the next outcome.

        Raises:
            ExceededCallError: If this call exceeds the quantifier upper bound.
        """
        ...

    @abstractmethod
    def is_optional(self) -> bool:
        """Return whether :meth:`maybe` was applied."""
        ...

    @abstractmethod
    def is_satisfied(self) -> bool:
        """Return whether the quantifier constraint is already met."""
        ...

    @abstractmethod
    def is_exhausted(self) -> bool:
        """Return whether no further matching calls are allowed."""
        ...

    @property
    @abstractmethod
    def call_count(self) -> int:
        """Number of times this expectation has been consumed."""
        ...


class Observation(ABC, Generic[T, P, R]):
    """A single observed call: fluent builder for result checks and quantifiers.

    Constructed by :meth:`~dmock.DeclarativeSpy.observe`. Chained
    ``returns`` / ``raises`` / ``condition`` are a sequence of checks for
    successive matching calls.

    Examples:
        >>> from dmock import DeclarativeSpy
        >>> from dmock.checks import Check
        >>> class Service:
        ...     def __init__(self) -> None:
        ...         self._values = iter(["first", "second", "ok", "ok"])
        ...
        ...     def fetch(self, key: str) -> str:
        ...         return next(self._values)
        >>> spy = DeclarativeSpy(Service())
        >>> spy.observe("fetch", "a").returns("first").returns("second")
        Observation(fetch('a'))
        >>> spy.fetch("a")
        'first'
        >>> spy.fetch("a")
        'second'
        >>> is_short = Check[str](str.islower) & (lambda v: len(v) == 2)
        >>> spy.observe("fetch", "b").returns("ok", condition=is_short, repeat=2)
        Observation(fetch('b'))
        >>> spy.fetch("b")
        'ok'
        >>> spy.fetch("b")
        'ok'
        >>> spy.verify()
    """

    # -- Fluent outcome builders --

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: str,
        /,
        *args: object,
        **kwargs: object,
    ) -> Observation[T, ..., Any]: ...

    @abstractmethod
    def observe(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Any:
        """Register a follow-up observation ordered after this one.

        Delegates to the parent :class:`~dmock.DeclarativeSpy` and
        automatically chains :meth:`not_before` on `self`, so the new
        observation cannot match until this one is satisfied.

        Args:
            name: Callable attribute on the wrapped object. Positional-only.
            *args: Expected positional arguments, possibly matchers.
            **kwargs: Expected keyword arguments, possibly matchers.

        Returns:
            A new :class:`Observation` ordered after `self`.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def start(self) -> None:
            ...         pass
            ...
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> _ = (
            ...     spy.observe("start")
            ...     .returns(None)
            ...     .once()
            ...     .observe("fetch", "a")
            ...     .returns("A")
            ... )
            >>> spy.start()
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def returns(
        self,
        value: R,
        *,
        condition: Callable[[R], bool] | None = None,
        repeat: int = 1,
    ) -> Self:
        """Assert the return value for the next matching call.

        Args:
            value: Expected return value (compared with ``==``).
            condition: Optional predicate called with the actual return value
                after `value` matches.
            repeat: How many successive calls expect this result. Must be
                at least 1.

        Returns:
            This observation, for chaining.

        Raises:
            ConfigurationError: If `repeat` is less than 1.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> from dmock.checks import Check
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A")
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> is_upper = Check[str](str.isupper) & (lambda v: len(v) == 1)
            >>> spy.observe("fetch", "b").returns("B", condition=is_upper, repeat=2)
            Observation(fetch('b'))
            >>> spy.fetch("b")
            'B'
            >>> spy.fetch("b")
            'B'
        """
        ...

    @overload
    def raises(
        self,
        exc: E,
        *,
        condition: Callable[[E], bool] | None = None,
        repeat: int = 1,
    ) -> Self: ...
    @overload
    def raises(
        self,
        exc: type[E],
        *,
        condition: Callable[[E], bool] | None = None,
        repeat: int = 1,
    ) -> Self: ...
    @abstractmethod
    def raises(
        self,
        exc: E | type[E],
        *,
        condition: Callable[[E], bool] | None = None,
        repeat: int = 1,
    ) -> Self:
        """Assert that the next matching call raises `exc`.

        Args:
            exc: Expected exception type (checked with ``isinstance``) or
                exception instance (also checks ``str(actual) == str(exc)``).
            condition: Optional predicate called with the raised exception
                after `exc` matches.
            repeat: How many successive calls expect `exc`. Must be at least 1.

        Returns:
            This observation, for chaining.

        Raises:
            ConfigurationError: If `repeat` is less than 1.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         raise KeyError(key)
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").raises(
            ...     KeyError, condition=lambda exc: exc.args == ("a",), repeat=2
            ... )
            Observation(fetch('a'))
            >>> spy.fetch("a")
            Traceback (most recent call last):
                ...
            KeyError: 'a'
            >>> spy.fetch("a")
            Traceback (most recent call last):
                ...
            KeyError: 'a'
        """
        ...

    @abstractmethod
    def condition(self, func: Callable[[Any], bool], *, repeat: int = 1) -> Self:
        """Assert that `func` returns ``True`` for the next matching call's outcome.

        `func` receives either the return value or the raised exception from
        the wrapped object.

        Args:
            func: Predicate called with the call's return value or raised
                exception.
            repeat: How many successive calls check `func`. Must be at least 1.

        Returns:
            This observation, for chaining.

        Raises:
            ConfigurationError: If `repeat` is less than 1.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> from dmock.checks import Check
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> seen: list[str] = []
            >>> def check_upper(value: str) -> bool:
            ...     seen.append(value)
            ...     return value.isupper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").condition(check_upper).returns("A")
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> seen
            ['A']
            >>> spy.fetch("a")
            'A'
            >>> is_single_upper = Check[str](str.isupper) & (lambda v: len(v) == 1)
            >>> spy.observe("fetch", "b").condition(is_single_upper, repeat=2)
            Observation(fetch('b'))
            >>> spy.fetch("b")
            'B'
            >>> spy.fetch("b")
            'B'
        """
        ...

    # -- Fluent quantifiers --

    @abstractmethod
    def once(self) -> Self:
        """Require exactly one matching call.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").once()
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def twice(self) -> Self:
        """Require exactly two matching calls.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").twice()
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def times(self, n: int) -> Self:
        """Require exactly `n` matching calls.

        Args:
            n: Exact call count. Must be at least 1.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").times(2)
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def at_least(self, n: int) -> Self:
        """Require at least `n` matching calls, with no upper bound.

        Args:
            n: Minimum call count. Must be at least 1.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").at_least(2)
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def at_most(self, n: int) -> Self:
        """Allow between 0 and `n` matching calls, inclusive.

        Args:
            n: Maximum call count.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").at_most(2)
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def between(self, lo: int, hi: int) -> Self:
        """Require between `lo` and `hi` matching calls, inclusive.

        Args:
            lo: Minimum call count.
            hi: Maximum call count.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").between(1, 2)
            Observation(fetch('a'))
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def maybe(self) -> Self:
        """Make this observation optional: zero calls still pass :meth:`~dmock.DeclarativeSpy.verify`.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").returns("A").maybe()
            Observation(fetch('a'))
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def never(self) -> Self:
        """Forbid any matching call.

        A match raises :class:`~dmock.UnexpectedCallError` immediately.

        Returns:
            This observation, for chaining.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> spy.observe("fetch", "a").never()
            Observation(fetch('a'))
            >>> spy.verify()
        """
        ...

    @abstractmethod
    def not_before(
        self, *interactions: Expectation[T, P, R] | Observation[T, P, R]
    ) -> Self:
        """Require that every `interactions` item is satisfied before this one.

        Args:
            *interactions: Prerequisites that must meet their own quantifiers.

        Returns:
            This observation, for chaining.

        Raises:
            ConfigurationError: If adding a requirement would create a cycle.

        Examples:
            >>> from dmock import DeclarativeSpy
            >>> class Service:
            ...     def start(self) -> None:
            ...         pass
            ...
            ...     def fetch(self, key: str) -> str:
            ...         return key.upper()
            >>> spy = DeclarativeSpy(Service())
            >>> init = spy.observe("start").returns(None).once()
            >>> spy.observe("fetch", "a").returns("A").not_before(init)
            Observation(fetch('a'))
            >>> spy.start()
            >>> spy.fetch("a")
            'A'
            >>> spy.verify()
        """
        ...

    @property
    @abstractmethod
    def requires(self) -> Sequence[Expectation[T, Any, Any] | Observation[T, Any, Any]]:
        """Prerequisites that must be satisfied before this observation can match."""
        ...

    # -- Effective quantifier (auto-adjust to outcome count when not set) --

    @property
    @abstractmethod
    def quantifier(self) -> Quantifier:
        """Effective call-count constraint, defaulting to the outcome count."""
        ...

    @property
    @abstractmethod
    def is_quantifier_locked(self) -> bool:
        """Return whether an explicit quantifier has been set."""
        ...

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Spec attribute this observation intercepts."""
        ...

    # -- Internal (called by DeclarativeMock) --

    @abstractmethod
    def matches(
        self,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> bool:
        """Return whether `args` and `kwargs` match this observation."""
        ...

    @abstractmethod
    def consume(self) -> Outcome:
        """Record a match and return the next outcome.

        Raises:
            ExceededCallError: If this call exceeds the quantifier upper bound.
        """
        ...

    @abstractmethod
    def is_optional(self) -> bool:
        """Return whether :meth:`maybe` was applied."""
        ...

    @abstractmethod
    def is_satisfied(self) -> bool:
        """Return whether the quantifier constraint is already met."""
        ...

    @abstractmethod
    def is_exhausted(self) -> bool:
        """Return whether no further matching calls are allowed."""
        ...

    @property
    @abstractmethod
    def call_count(self) -> int:
        """Number of times this observation has been consumed."""
        ...


class Mediator(Generic[T], ABC):
    """Internal bridge used by :class:`Interaction` to register chained interactions."""

    @abstractmethod
    def mediate(
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Expectation[T, Any, Any] | Observation[T, Any, Any]:
        """Register a new interaction on the parent mock or spy."""
        ...


@final
class Interaction(Expectation[T, P, R], Observation[T, P, R], Generic[T, P, R]):
    """Concrete fluent builder implementing both :class:`Expectation` and :class:`Observation`.

    Constructed via :meth:`expectation` or :meth:`observation` by
    :class:`~dmock.DeclarativeMock` and :class:`~dmock.DeclarativeSpy`.
    """

    def __init__(
        self,
        mediator: Mediator[T],
        interaction_name: str,
        method_name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        self._mediator = mediator
        self._interaction_name = interaction_name
        self._method_name = method_name
        self._has_any_args = any(isinstance(a, _AnyArgsSentinel) for a in args)
        self._has_any_kwargs = any(isinstance(a, _AnyKwargsSentinel) for a in args)
        self._expected_args = tuple(
            a for a in args if not isinstance(a, (_AnyArgsSentinel, _AnyKwargsSentinel))
        )
        self._expected_kwargs = dict(kwargs)
        self._outcomes: list[Outcome] = []
        self._quantifier: Quantifier | None = None
        self._optional: bool = False
        self._calls = 0
        self._requires: list[Expectation[T, P, R] | Observation[T, P, R]] = []

    # -- Builders --
    @classmethod
    def expectation(
        cls,
        mediator: Mediator[T],
        method_name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> Expectation[T, P, R]:
        """Construct an :class:`Interaction` representing an :class:`Expectation`."""
        return cls(
            mediator=mediator,
            interaction_name="Expectation",
            method_name=method_name,
            args=args,
            kwargs=kwargs,
        )

    @classmethod
    def observation(
        cls,
        mediator: Mediator[T],
        method_name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> Observation[T, P, R]:
        """Construct an :class:`Interaction` representing an :class:`Observation`."""
        return cls(
            mediator=mediator,
            interaction_name="Observation",
            method_name=method_name,
            args=args,
            kwargs=kwargs,
        )

    # -- Fluent outcome builders --

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: Callable[Concatenate[T, P2], R2],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Expectation[T, P2, R2]: ...

    @overload
    def expect(
        self,
        name: str,
        /,
        *args: object,
        **kwargs: object,
    ) -> Expectation[T, ..., object]: ...

    def expect(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Any:
        return self._mediator.mediate(name, *args, **kwargs).not_before(self)

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], Coroutine[Any, Any, R2]],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        any_kwargs: _AnyKwargsSentinel,
        /,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_args: _AnyArgsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        any_kwargs: _AnyKwargsSentinel,
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: Callable[Concatenate[T, P2], R2],
        /,
        *args: P2.args,
        **kwargs: P2.kwargs,
    ) -> Observation[T, P2, R2]: ...

    @overload
    def observe(
        self,
        name: str,
        /,
        *args: object,
        **kwargs: object,
    ) -> Observation[T, ..., Any]: ...

    def observe(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        name: str | Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> Any:
        return self._mediator.mediate(name, *args, **kwargs).not_before(self)

    def returns(
        self,
        value: R,
        *,
        condition: Callable[[R], bool] | None = None,
        repeat: int = 1,
    ) -> Self:
        if condition is not None:
            self._append_outcome(ReturnCheck(value, condition), repeat)
            return self

        self._append_outcome(ReturnOutcome(value), repeat)
        return self

    @overload
    def raises(
        self,
        exc: E,
        *,
        condition: Callable[[E], bool] | None = None,
        repeat: int = 1,
    ) -> Self: ...
    @overload
    def raises(
        self,
        exc: type[E],
        *,
        condition: Callable[[E], bool] | None = None,
        repeat: int = 1,
    ) -> Self: ...
    @overload
    def raises(
        self,
        exc: BaseException | type[BaseException],
        *,
        repeat: int = 1,
    ) -> Self: ...
    def raises(
        self,
        exc: BaseException | type[BaseException],
        *,
        condition: Callable[[Any], bool] | None = None,
        repeat: int = 1,
    ) -> Self:
        if condition is not None:
            self._append_outcome(RaiseCheck(exc, condition), repeat)
            return self

        self._append_outcome(RaiseOutcome(exc), repeat)
        return self

    @overload
    def runs(self, func: Callable[P, R], *, repeat: int = 1) -> Self: ...

    @overload
    def runs(self, func: Callable[P, Awaitable[R]], *, repeat: int = 1) -> Self: ...

    def runs(self, func: Callable[P, R | Awaitable[R]], *, repeat: int = 1) -> Self:
        self._append_outcome(RunOutcome(func), repeat)
        return self

    def condition(self, func: Callable[[Any], bool], *, repeat: int = 1) -> Self:
        self._append_outcome(ConditionCheck(func), repeat)
        return self

    def _append_outcome(self, outcome: Outcome, repeat: int) -> None:
        """Append `outcome` once per `repeat`.

        Raises:
            ConfigurationError: If `repeat` is less than 1.
        """
        if repeat < 1:
            raise ConfigurationError(f"repeat requires repeat >= 1, got {repeat}.")

        for _ in range(repeat):
            self._outcomes.append(outcome)

    # -- Fluent quantifiers --

    def once(self) -> Self:
        return self._set_quantifier(ExactlyN(1))

    def twice(self) -> Self:
        return self._set_quantifier(ExactlyN(2))

    def times(self, n: int) -> Self:
        return self._set_quantifier(ExactlyN(n))

    def at_least(self, n: int) -> Self:
        return self._set_quantifier(AtLeast(n))

    def at_most(self, n: int) -> Self:
        return self._set_quantifier(Between(0, n))

    def between(self, lo: int, hi: int) -> Self:
        return self._set_quantifier(Between(lo, hi))

    def maybe(self) -> Self:
        self._optional = True
        return self

    def never(self) -> Self:
        return self._set_quantifier(Never())

    def not_before(
        self, *interactions: Expectation[T, P, R] | Observation[T, P, R]
    ) -> Self:
        for req in interactions:
            if self._is_reachable_from(req):
                raise ConfigurationError(
                    f"Cycle detected: adding {req!r} as a prerequisite of "
                    f"{self!r} would create a circular dependency."
                )

            self._requires.append(req)

        return self

    def _is_reachable_from(
        self, source: Expectation[T, Any, Any] | Observation[T, Any, Any]
    ) -> bool:
        """Return True if `self` is reachable by following `_requires` from `source`."""
        visited: set[int] = set()
        queue: deque[Expectation[T, Any, Any] | Observation[T, Any, Any]] = deque(
            [source]
        )
        while queue:
            node = queue.popleft()
            node_id = id(node)
            if node_id in visited:
                continue

            visited.add(node_id)
            if node is self:
                return True

            queue.extend(node.requires)

        return False

    @property
    def requires(self) -> Sequence[Expectation[T, Any, Any] | Observation[T, Any, Any]]:
        return self._requires

    def _set_quantifier(self, q: Quantifier) -> Self:
        if self._quantifier is not None:
            raise ConfigurationError(
                f"Conflicting quantifiers on expectation for {self._method_name!r}."
            )

        self._quantifier = q
        return self

    # -- Effective quantifier (auto-adjust to outcome count when not set) --

    @property
    def quantifier(self) -> Quantifier:
        if self._quantifier is not None:
            return self._quantifier

        return ExactlyN(max(1, len(self._outcomes)))

    @property
    def is_quantifier_locked(self) -> bool:
        return self._quantifier is not None

    @property
    def method_name(self) -> str:
        return self._method_name

    # -- Internal (called by DeclarativeMock) --

    def matches(
        self,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> bool:
        if not self._has_any_args:
            if len(args) != len(self._expected_args):
                return False

            if not all(e == a for e, a in zip(self._expected_args, args, strict=True)):
                return False

        if not self._has_any_kwargs:
            if kwargs.keys() != self._expected_kwargs.keys():
                return False

            if not all(
                self._expected_kwargs[k] == kwargs[k] for k in self._expected_kwargs
            ):
                return False

        return True

    def consume(self) -> Outcome:
        q = self.quantifier
        self._calls += 1
        if q.is_exceeded(self._calls):
            raise ExceededCallError(self._method_name, self._calls, q.max_calls)

        if not self._outcomes:
            return DefaultOutcome()

        index = min(self._calls - 1, len(self._outcomes) - 1)
        return self._outcomes[index]

    def is_optional(self) -> bool:
        return self._optional

    def is_satisfied(self) -> bool:
        if self._calls == 0 and self.is_optional():
            return True

        return self.quantifier.is_satisfied(self._calls)

    def is_exhausted(self) -> bool:
        return self.quantifier.is_exhausted(self._calls)

    @property
    def call_count(self) -> int:
        return self._calls

    def __repr__(self) -> str:
        args_parts = [repr(a) for a in self._expected_args]
        if self._has_any_args:
            args_parts.insert(0, "ANY_ARGS")

        kwargs_parts = [f"{k}={v!r}" for k, v in self._expected_kwargs.items()]
        if self._has_any_kwargs:
            kwargs_parts.append("ANY_KWARGS")

        all_parts = ", ".join(args_parts + kwargs_parts)
        return f"{self._interaction_name}({self._method_name}({all_parts}))"


def in_order(
    *interactions: Expectation[T, Any, Any] | Observation[T, Any, Any],
) -> None:
    """Link `interactions` so each one requires the previous to be satisfied first.

    Equivalent to calling ``interactions[i].not_before(interactions[i - 1])``
    for every consecutive pair. Passing 0 or 1 interactions is a no-op.

    Args:
        *interactions: Ordered interactions to chain.

    Examples:
        >>> from dmock import DeclarativeMock, in_order
        >>> class Service:
        ...     def start(self) -> None: ...
        ...     def fetch(self, key: str) -> str: ...
        ...     def stop(self) -> None: ...
        >>> mock = DeclarativeMock(Service)
        >>> a = mock.expect("start").returns(None).once()
        >>> b = mock.expect("fetch", "a").returns("A").once()
        >>> c = mock.expect("stop").returns(None).once()
        >>> in_order(a, b, c)
        >>> mock.start()
        >>> mock.fetch("a")
        'A'
        >>> mock.stop()
        >>> mock.verify()
    """
    for i in range(1, len(interactions)):
        interactions[i].not_before(interactions[i - 1])
