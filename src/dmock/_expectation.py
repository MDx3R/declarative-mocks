from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Generic, Self, final, overload

from dmock._exceptions import ConfigurationError, ExceededCallError
from dmock._matchers import (
    _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
    _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
)
from dmock._protocols import P, R
from dmock._types import (
    AtLeast,
    Between,
    DefaultOutcome,
    ExactlyN,
    Never,
    RaiseOutcome,
    ReturnOutcome,
    RunOutcome,
)


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence
    from typing import Any

    from dmock._types import Outcome, Quantifier


@final
class Expectation(Generic[P, R]):
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
    """

    def __init__(
        self,
        method_name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
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
        self._requires: list[Expectation[Any, Any]] = []

    # -- Fluent outcome builders --

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
            >>> mock.expect("fetch", "a").returns("A")
            Expectation(fetch('a'))
            >>> mock.fetch("a")
            'A'
        """
        self._append_outcome(ReturnOutcome(value), repeat)
        return self

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
        self._append_outcome(RaiseOutcome(exc), repeat)
        return self

    @overload
    def runs(self, func: Callable[P, R], *, repeat: int = 1) -> Self: ...

    @overload
    def runs(self, func: Callable[P, Awaitable[R]], *, repeat: int = 1) -> Self: ...

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
        self._append_outcome(RunOutcome(func), repeat)
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
        return self._set_quantifier(ExactlyN(1))

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
        return self._set_quantifier(ExactlyN(2))

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
        return self._set_quantifier(ExactlyN(n))

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
        return self._set_quantifier(AtLeast(n))

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
        return self._set_quantifier(Between(0, n))

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
        return self._set_quantifier(Between(lo, hi))

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
        self._optional = True
        return self

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
        return self._set_quantifier(Never())

    def not_before(self, *expectations: Expectation[Any, Any]) -> Self:
        """Require that every `expectations` item is satisfied before this one.

        Args:
            *expectations: Prerequisites that must meet their own quantifiers.

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
        for req in expectations:
            if self._is_reachable_from(req):
                raise ConfigurationError(
                    f"Cycle detected: adding {req!r} as a prerequisite of "
                    f"{self!r} would create a circular dependency."
                )

            self._requires.append(req)

        return self

    def _is_reachable_from(self, source: Expectation[Any, Any]) -> bool:
        """Return True if `self` is reachable by following `_requires` from `source`."""
        visited: set[int] = set()
        queue: deque[Expectation[Any, Any]] = deque([source])
        while queue:
            node = queue.popleft()
            node_id = id(node)
            if node_id in visited:
                continue

            visited.add(node_id)
            if node is self:
                return True

            queue.extend(node._requires)  # noqa: SLF001

        return False

    @property
    def requires(self) -> Sequence[Expectation[Any, Any]]:
        """Prerequisites that must be satisfied before this expectation can match."""
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
        """Effective call-count constraint, defaulting to the outcome count."""
        if self._quantifier is not None:
            return self._quantifier

        return ExactlyN(max(1, len(self._outcomes)))

    @property
    def is_quantifier_locked(self) -> bool:
        """Return whether an explicit quantifier has been set."""
        return self._quantifier is not None

    @property
    def method_name(self) -> str:
        """Spec attribute this expectation intercepts."""
        return self._method_name

    # -- Internal (called by DeclarativeMock) --

    def matches(
        self,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> bool:
        """Return whether `args` and `kwargs` match this expectation."""
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
        """Record a match and return the next outcome.

        Raises:
            ExceededCallError: If this call exceeds the quantifier upper bound.
        """
        q = self.quantifier
        self._calls += 1
        if q.is_exceeded(self._calls):
            raise ExceededCallError(self._method_name, self._calls, q.max_calls)

        if not self._outcomes:
            return DefaultOutcome()

        index = min(self._calls - 1, len(self._outcomes) - 1)
        return self._outcomes[index]

    def is_optional(self) -> bool:
        """Return whether :meth:`maybe` was applied."""
        return self._optional

    def is_satisfied(self) -> bool:
        """Return whether the quantifier constraint is already met."""
        if self._calls == 0 and self.is_optional():
            return True

        return self.quantifier.is_satisfied(self._calls)

    def is_exhausted(self) -> bool:
        """Return whether no further matching calls are allowed."""
        return self.quantifier.is_exhausted(self._calls)

    @property
    def call_count(self) -> int:
        """Number of times this expectation has been consumed."""
        return self._calls

    def __repr__(self) -> str:
        args_parts = [repr(a) for a in self._expected_args]
        if self._has_any_args:
            args_parts.insert(0, "ANY_ARGS")

        kwargs_parts = [f"{k}={v!r}" for k, v in self._expected_kwargs.items()]
        if self._has_any_kwargs:
            kwargs_parts.append("ANY_KWARGS")

        all_parts = ", ".join(args_parts + kwargs_parts)
        return f"Expectation({self._method_name}({all_parts}))"


def in_order(*expectations: Expectation[Any, Any]) -> None:
    """Link `expectations` so each one requires the previous to be satisfied first.

    Equivalent to calling ``expectations[i].not_before(expectations[i - 1])``
    for every consecutive pair. Passing 0 or 1 expectations is a no-op.

    Args:
        *expectations: Ordered expectations to chain.

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
    for i in range(1, len(expectations)):
        expectations[i].not_before(expectations[i - 1])
