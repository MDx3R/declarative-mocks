from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@runtime_checkable
class Matcher(Protocol):
    """Predicate used in expectation arguments.

    Implement :meth:`matches` to add a custom matcher. Built-in matchers already
    satisfy this protocol.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> class Prefix:
        ...     def __init__(self, prefix: str) -> None:
        ...         self.prefix = prefix
        ...
        ...     def matches(self, value: object) -> bool:
        ...         return isinstance(value, str) and value.startswith(self.prefix)
        ...
        ...     def __repr__(self) -> str:
        ...         return f"Prefix({self.prefix!r})"
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Prefix("k")).returns("ok")
        Expectation(fetch(Prefix('k')))
        >>> mock.fetch("key")
        'ok'
    """

    def matches(self, value: object) -> bool:
        """Return whether `value` satisfies this matcher."""
        ...


class _AnythingMatcher:
    """Matches any single value. Use the :data:`~dmock.Anything` singleton.

    ``Anything`` and ``Anything()`` are equivalent.

    Examples:
        >>> from dmock import Anything, DeclarativeMock
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Anything).returns("ok")
        Expectation(fetch(Anything))
        >>> mock.fetch("whatever")
        'ok'
    """

    def matches(self, value: object) -> bool:
        """Return True for every `value`."""
        return True

    def __call__(self) -> _AnythingMatcher:
        """Return this matcher so ``Anything`` and ``Anything()`` both work."""
        return self

    def __repr__(self) -> str:
        return "Anything"


Anything = _AnythingMatcher()


class AnythingOfType:
    """Matches a value that is an instance of the given type.

    Args:
        expected_type: Type accepted by ``isinstance``.

    Examples:
        >>> from dmock import AnythingOfType, DeclarativeMock
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", AnythingOfType(str)).returns("ok")
        Expectation(fetch(AnythingOfType(str)))
        >>> mock.fetch("a")
        'ok'
    """

    def __init__(self, expected_type: type) -> None:
        self._expected_type = expected_type

    def matches(self, value: object) -> bool:
        """Return whether `value` is an instance of the expected type."""
        return isinstance(value, self._expected_type)

    def __repr__(self) -> str:
        return f"AnythingOfType({self._expected_type.__name__})"


class MatchedBy:
    """Matches when a user-supplied predicate returns True.

    Args:
        predicate: Called with the actual argument; a true result is a match.

    Examples:
        >>> from dmock import DeclarativeMock, MatchedBy
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> def is_short(value: object) -> bool:
        ...     return isinstance(value, str) and len(value) == 1
        >>> _ = mock.expect("fetch", MatchedBy(is_short)).returns("ok")
        >>> mock.fetch("a")
        'ok'
    """

    def __init__(self, predicate: Callable[[Any], bool]) -> None:
        self._predicate = predicate

    def matches(self, value: object) -> bool:
        """Return whether `predicate` accepts `value`."""
        return self._predicate(value)

    def __repr__(self) -> str:
        return f"MatchedBy({self._predicate!r})"


class _AnyArgsSentinel:
    """Sentinel matching any number of positional arguments.

    Pass :data:`~dmock.ANY_ARGS` among the positional arguments of
    :meth:`~dmock.DeclarativeMock.expect`.

    Examples:
        >>> from dmock import ANY_ARGS, ANY_KWARGS, DeclarativeMock
        >>> class Service:
        ...     def fetch(self, *args: object, **kwargs: object) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", ANY_ARGS, ANY_KWARGS).returns("ok")
        Expectation(fetch(ANY_ARGS, ANY_KWARGS))
        >>> mock.fetch("a", "b", extra=1)
        'ok'
    """

    def __repr__(self) -> str:
        return "ANY_ARGS"


class _AnyKwargsSentinel:
    """Sentinel matching any keyword arguments.

    Pass :data:`~dmock.ANY_KWARGS` among the positional arguments of
    :meth:`~dmock.DeclarativeMock.expect` (it is a sentinel, not a keyword).

    Examples:
        >>> from dmock import ANY_KWARGS, DeclarativeMock
        >>> class Service:
        ...     def fetch(self, key: str, **kwargs: object) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", "a", ANY_KWARGS).returns("ok")
        Expectation(fetch('a', ANY_KWARGS))
        >>> mock.fetch("a", extra=1)
        'ok'
    """

    def __repr__(self) -> str:
        return "ANY_KWARGS"


ANY_ARGS = _AnyArgsSentinel()
ANY_KWARGS = _AnyKwargsSentinel()
