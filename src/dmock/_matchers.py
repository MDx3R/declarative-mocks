from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections.abc import Collection, Container, Mapping, Sequence, Set, Sized
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, SupportsFloat, TypeAlias, cast


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    Predicate = Callable[[Any], bool]


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

if TYPE_CHECKING:
    from typing import Any

    class _Base(Any):  # type: ignore[misc]
        pass

else:

    class _Base:
        pass


class Matcher(ABC, _Base):
    """Predicate used in expectation arguments.

    Implement :meth:`matches` to add a custom matcher. Built-in matchers already
    satisfy this protocol. Use ``&``, ``|``, and ``~`` to combine matchers.

    Examples:
        >>> from dmock import DeclarativeMock, Matcher
        >>> class Prefix(Matcher):
        ...     def __init__(self, prefix: str, /) -> None:
        ...         self.prefix = prefix
        ...
        ...     def matches(self, value: object, /) -> bool:
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

    @abstractmethod
    def matches(self, value: object, /) -> bool:
        """Return whether `value` satisfies this matcher."""

    def __eq__(self, value: object, /) -> bool:
        """Return whether `value` satisfies this matcher.

        Args:
            value: Object to test. Positional-only.

        Returns:
            Result of :meth:`matches`.

        Examples:
            >>> from dmock import Anything
            >>> Anything == "key"
            True
            >>> "key" == Anything
            True
        """
        return self.matches(value)

    def __ne__(self, value: object, /) -> bool:
        """Return whether `value` does not satisfy this matcher.

        Args:
            value: Object to test. Positional-only.

        Returns:
            The inverse of :meth:`matches`.

        Examples:
            >>> from dmock import Equals
            >>> Equals("a") != "b"
            True
            >>> "a" != Equals("b")
            True
        """
        return not self.matches(value)

    def __hash__(self) -> int:
        """Return ``0`` so every matcher shares a hash.

        Equality follows :meth:`matches`, which is not tied to identity, so a
        value-based hash would be inconsistent.

        Returns:
            The constant ``0``.

        Examples:
            >>> from dmock import Anything
            >>> hash(Anything)
            0
        """
        return 0

    def __invert__(self) -> Matcher:
        """Return a matcher that matches when this one does not.

        ``~matcher`` is :class:`Not` of this matcher.

        Returns:
            A :class:`Not` wrapping this matcher.

        Examples:
            >>> from dmock import Equals
            >>> ~Equals("a")
            Not(Equals('a'))
            >>> (~Equals("a")) == "b"
            True
        """
        return Not(self)

    def __and__(self, other: object) -> object:
        """Return a matcher that requires both sides to match.

        A non-matcher `other` is wrapped in :class:`Equals`. ``left & right``
        is :class:`And`.

        Args:
            other: Matcher, or a plain object compared with ``==``.

        Returns:
            An :class:`And` matcher.

        Examples:
            >>> from dmock import GreaterThan, LessThan
            >>> GreaterThan(0) & LessThan(10)
            And(GreaterThan(0), LessThan(10))
            >>> (GreaterThan(0) & LessThan(10)) == 5
            True
        """
        if not isinstance(other, Matcher):
            other = Equals(other)

        return And(self, other)

    def __rand__(self, other: object) -> object:
        """Return a matcher that requires both sides to match.

        Used when the left operand is not a :class:`Matcher`. A matcher on
        the left is handled by :meth:`__and__`.

        Args:
            other: Plain object compared with ``==``.

        Returns:
            An :class:`And` matcher, or ``NotImplemented`` when `other` is
            already a :class:`Matcher`.

        Examples:
            >>> from dmock import Equals
            >>> 1 & Equals(1)
            And(Equals(1), Equals(1))
            >>> (1 & Equals(1)) == 1
            True
        """
        if not isinstance(other, Matcher):
            return And(Equals(other), self)

        return NotImplemented

    def __or__(self, other: object) -> object:
        """Return a matcher that requires either side to match.

        A non-matcher `other` is wrapped in :class:`Equals`. ``left | right``
        is :class:`Or`.

        Args:
            other: Matcher, or a plain object compared with ``==``.

        Returns:
            An :class:`Or` matcher.

        Examples:
            >>> from dmock import Equals
            >>> Equals(1) | 2
            Or(Equals(1), Equals(2))
            >>> (Equals(1) | 2) == 2
            True
        """
        if not isinstance(other, Matcher):
            other = Equals(other)

        return Or(self, other)

    def __ror__(self, other: object) -> object:
        """Return a matcher that requires either side to match.

        Used when the left operand is not a :class:`Matcher`. A matcher on
        the left is handled by :meth:`__or__`.

        Args:
            other: Plain object compared with ``==``.

        Returns:
            An :class:`Or` matcher, or ``NotImplemented`` when `other` is
            already a :class:`Matcher`.

        Examples:
            >>> from dmock import Equals
            >>> 1 | Equals(2)
            Or(Equals(1), Equals(2))
            >>> (1 | Equals(2)) == 1
            True
        """
        if not isinstance(other, Matcher):
            return Or(Equals(other), self)

        return NotImplemented


class _AnythingMatcher(Matcher):
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

    def matches(self, value: object, /) -> bool:
        """Return True for every `value`."""
        return True

    def __call__(self) -> _AnythingMatcher:
        """Return this matcher so ``Anything`` and ``Anything()`` both work."""
        return self

    def __repr__(self) -> str:
        return "Anything"


Anything = _AnythingMatcher()


class _NeverMatcher(Matcher):
    """Matches no value. Use the :data:`~dmock.Nothing` or :data:`~dmock.Never` singleton.

    ``Never``, ``Never()``, ``Nothing``, and ``Nothing()`` are equivalent.
    An expectation argument of ``Never`` does not match any call.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Never, Nothing
        >>> Never is Nothing
        True
        >>> Never() is Never
        True
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Never).returns("ok").maybe()
        Expectation(fetch(Never))
        >>> Never.matches("a")
        False
    """

    def matches(self, value: object, /) -> bool:
        """Return False for every `value`."""
        return False

    def __call__(self) -> _NeverMatcher:
        """Return this matcher so ``Never`` and ``Never()`` both work."""
        return self

    def __repr__(self) -> str:
        return "Never"


Nothing = Never = _NeverMatcher()


class AnythingOfType(Matcher):
    """Matches a value that is an instance of the given type.

    Args:
        expected: Type accepted by ``isinstance``.
        exact: When True, the value's type must be `expected` itself.

    Examples:
        >>> from dmock import AnythingOfType, DeclarativeMock, AnythingOfType
        >>> True == AnythingOfType(int)
        True
        >>> True == AnythingOfType(int, exact=True)
        False
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", AnythingOfType(str)).returns("ok")
        Expectation(fetch(AnythingOfType(str, exact=False)))
        >>> mock.fetch("a")
        'ok'
    """

    def __init__(self, expected: type, /, *, exact: bool = False) -> None:
        self._expected = expected
        self._exact = exact

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is an instance of the expected type."""
        return (
            type(value) is self._expected
            if self._exact
            else isinstance(value, self._expected)
        )

    def __repr__(self) -> str:
        return f"AnythingOfType({self._expected.__name__}, exact={self._exact})"


InstanceOf = AnythingOfType
"""Alias of :class:`InstanceOf`.

``InstanceOf(expected)`` constructs that matcher. ``exact`` defaults to
False, so a subclass matches. ``exact=True`` requires
``type(value) is expected``.

Examples:
    >>> from dmock import AnythingOfType, InstanceOf
    >>> InstanceOf is AnythingOfType
    True
    >>> True == InstanceOf(int)
    True
    >>> True == InstanceOf(int, exact=True)
    False
    >>> class Base:
    ...     pass
    >>> class Child(Base):
    ...     pass
    >>> Child() == InstanceOf(Base)
    True
    >>> Child() == InstanceOf(Base, exact=True)
    False
"""


class Equals(Matcher):
    """Matches a value equal to `expected`.

    Comparison uses ``==``.

    Args:
        expected: Object the value is compared with.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Equals
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Equals("a")).returns("ok")
        Expectation(fetch(Equals('a')))
        >>> mock.fetch("a")
        'ok'
    """

    def __init__(self, expected: object, /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` equals `expected`."""
        return value == self._expected

    def __repr__(self) -> str:
        return f"Equals({self._expected!r})"


class Not(Matcher):
    """Matches a value that is not equal to `expected`.

    Comparison uses ``!=``.

    Args:
        expected: Object the value must differ from.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Not
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Not("b")).returns("ok")
        Expectation(fetch(Not('b')))
        >>> mock.fetch("a")
        'ok'
    """

    def __init__(self, expected: object, /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is not equal to `expected`."""
        return value != self._expected

    def __repr__(self) -> str:
        return f"Not({self._expected!r})"


class Maybe(Matcher):
    """Matches ``None`` or a value equal to `expected`.

    Args:
        expected: Object accepted in addition to ``None``. Compared with ``==``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Maybe
        >>> class Service:
        ...     def fetch(self, key: str | None) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Maybe("a")).returns("ok")
        Expectation(fetch(Maybe('a')))
        >>> mock.fetch(None)
        'ok'
    """

    def __init__(self, expected: object, /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is ``None`` or equals `expected`."""
        return value is None or value == self._expected

    def __repr__(self) -> str:
        return f"Maybe({self._expected!r})"


class Is(Matcher):
    """Matches a value that is the same object as `expected`.

    Comparison uses ``is``.

    Args:
        expected: Object the value must be identical to.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Is
        >>> class Service:
        ...     def fetch(self, key: str | None) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Is(None)).returns("ok")
        Expectation(fetch(Is(None)))
        >>> mock.fetch(None)
        'ok'
    """

    def __init__(self, expected: object, /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is `expected`."""
        return value is self._expected

    def __repr__(self) -> str:
        return f"Is({self._expected!r})"


class MatchedBy(Matcher):
    """Matches when a user-supplied predicate returns `True`.

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

    def __init__(self, predicate: Predicate, /) -> None:
        self._predicate = predicate

    def matches(self, value: object, /) -> bool:
        """Return whether `predicate` accepts `value`."""
        return self._predicate(value)

    def __repr__(self) -> str:
        return f"MatchedBy({self._predicate!r})"


TRUTHY = MatchedBy(bool)
"""Matches a truthy value.

Examples:
    >>> from dmock import DeclarativeMock
    >>> from dmock import TRUTHY
    >>> class Service:
    ...     def fetch(self, key: str) -> str: ...
    >>> mock = DeclarativeMock(Service)
    >>> mock.expect("fetch", TRUTHY).returns("ok")
    Expectation(fetch(MatchedBy(<class 'bool'>)))
    >>> mock.fetch("a")
    'ok'
    >>> TRUTHY.matches("")
    False
"""
FALSY = MatchedBy(lambda x: not x)
"""Matches a falsy value.

Examples:
    >>> from dmock import DeclarativeMock
    >>> from dmock import FALSY
    >>> FALSY.matches("")
    True
    >>> FALSY.matches("a")
    False
    >>> class Service:
    ...     def fetch(self, key: str) -> str: ...
    >>> mock = DeclarativeMock(Service)
    >>> _ = mock.expect("fetch", FALSY).returns("ok")
    >>> mock.fetch("")
    'ok'
"""
NAIVE_DATETIME = MatchedBy(lambda x: isinstance(x, datetime) and x.tzinfo is None)
"""Matches a naive :class:`datetime.datetime`.

Returns `True` when ``tzinfo is None``. Aware datetimes and other types do not match.

Examples:
    >>> from datetime import datetime, timezone
    >>> from dmock import DeclarativeMock
    >>> from dmock import NAIVE_DATETIME
    >>> NAIVE_DATETIME.matches(datetime(2020, 1, 1))
    True
    >>> NAIVE_DATETIME.matches(datetime(2020, 1, 1, tzinfo=timezone.utc))
    False
    >>> class Service:
    ...     def fetch(self, when: datetime) -> str: ...
    >>> mock = DeclarativeMock(Service)
    >>> _ = mock.expect("fetch", NAIVE_DATETIME).returns("ok")
    >>> mock.fetch(datetime(2020, 1, 1))
    'ok'
"""
AWARE_DATETIME = MatchedBy(lambda x: isinstance(x, datetime) and x.tzinfo is not None)
"""Matches an aware :class:`datetime.datetime`.

Returns `True` when ``tzinfo is not None``. Naive datetimes and other types do not match.

Examples:
    >>> from datetime import datetime, timezone
    >>> from dmock import DeclarativeMock
    >>> from dmock import AWARE_DATETIME
    >>> AWARE_DATETIME.matches(datetime(2020, 1, 1, tzinfo=timezone.utc))
    True
    >>> AWARE_DATETIME.matches(datetime(2020, 1, 1))
    False
    >>> class Service:
    ...     def fetch(self, when: datetime) -> str: ...
    >>> mock = DeclarativeMock(Service)
    >>> _ = mock.expect("fetch", AWARE_DATETIME).returns("ok")
    >>> mock.fetch(datetime(2020, 1, 1, tzinfo=timezone.utc))
    'ok'
"""


class Empty(Matcher):
    """Matches a sized value whose length is zero.

    A value that is not :class:`collections.abc.Sized` does not match.
    ``EMPTY`` is an :class:`Empty` matcher.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import EMPTY
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", EMPTY).returns("ok")
        Expectation(fetch(Empty()))
        >>> mock.fetch("")
        'ok'
    """

    def matches(self, value: object, /) -> bool:
        """Return whether `value` has length zero."""
        if not isinstance(value, Sized):
            return False

        return len(value) == 0

    def __repr__(self) -> str:
        return "Empty()"


EMPTY = Empty()


class In(Matcher):
    """Matches a value that is a member of `expected`.

    Args:
        expected: Container the value must belong to.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import In
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", In(("a", "b"))).returns("ok")
        Expectation(fetch(In(('a', 'b'))))
        >>> mock.fetch("a")
        'ok'
    """

    def __init__(self, expected: Container[object], /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is a member of `expected`."""
        return value in self._expected

    def __repr__(self) -> str:
        return f"In({self._expected!r})"


class Contains(Matcher):
    """Matches a container that holds `expected`.

    A value that is not a :class:`collections.abc.Container` does not match.
    Strings are containers of substrings.

    Args:
        expected: Member that must be present.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Contains
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Contains("k")).returns("ok")
        Expectation(fetch(Contains('k')))
        >>> mock.fetch("key")
        'ok'
    """

    def __init__(self, expected: object, /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` contains `expected`."""
        if not isinstance(value, Container):
            return False

        return self._expected in value

    def __repr__(self) -> str:
        return f"Contains({self._expected!r})"


class Includes(Matcher):
    """Matches a container that holds every given item.

    A value that is not a :class:`collections.abc.Container` does not match.

    Args:
        *items: Members that must all be present.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Includes
        >>> class Service:
        ...     def fetch(self, keys: list[str]) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Includes("a", "b")).returns("ok")
        Expectation(fetch(Includes('a', 'b')))
        >>> mock.fetch(["a", "b", "c"])
        'ok'
    """

    def __init__(self, /, *items: object) -> None:
        self._items = items

    def matches(self, value: object, /) -> bool:
        """Return whether `value` contains every item."""
        if not isinstance(value, Container):
            return False

        return all(item in value for item in self._items)

    def __repr__(self) -> str:
        return f"Includes({', '.join(map(repr, self._items))})"


class CollectionOf(Matcher):
    """Matches a sequence, set, or mapping of the same kind as `expected`.

    Order matters for sequences. Sets and mappings ignore order. A different
    kind does not match. Values of the same kind match when their elements
    are equal, including when the concrete types differ.

    ``str``, ``bytes``, ``bytearray``, ``memoryview``, and
    :class:`collections.UserString` are sequences and are valid `expected`
    values. They match any sequence of the same elements in the same order.
    A ``str`` or :class:`collections.UserString` yields characters. ``bytes``,
    ``bytearray``, and a ``memoryview`` of a bytes buffer yield integers, so
    they match each other and a list of those integers.

    Args:
        expected: Sequence, set, or mapping to compare against.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import CollectionOf
        >>> (1, 2, 3) == CollectionOf([1, 2, 3])
        True
        >>> (1, 2, 3) == CollectionOf({1, 2, 3})
        False
        >>> "ab" == CollectionOf(["a", "b"])
        True
        >>> ["a", "b"] == CollectionOf("ab")
        True
        >>> b"ab" == CollectionOf(bytearray(b"ab"))
        True
        >>> [97, 98] == CollectionOf(b"ab")
        True
        >>> bytearray(b"ab") == CollectionOf(memoryview(b"ab"))
        True
        >>> from collections import UserString
        >>> UserString("ab") == CollectionOf("ab")
        True
        >>> "ab" == CollectionOf(UserString("ab"))
        True
        >>> "ab" == CollectionOf(b"ab")
        False
        >>> class Service:
        ...     def fetch(self, items: tuple[int, ...]) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", CollectionOf([1, 2, 3])).returns("ok")
        Expectation(fetch(CollectionOf([1, 2, 3])))
        >>> mock.fetch((1, 2, 3))
        'ok'
    """

    def __init__(self, expected: Collection[object], /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:  # noqa: PLR0911
        """Return whether `value` has the same kind and the same contents."""
        if not isinstance(value, Collection):
            return False

        value = cast("Collection[object]", value)
        if len(value) != len(self._expected):
            return False

        if type(value) is type(self._expected):
            return value == self._expected

        if isinstance(value, Sequence) and isinstance(self._expected, Sequence):
            return all(v == e for v, e in zip(value, self._expected, strict=True))

        if isinstance(value, Set) and isinstance(self._expected, Set):
            return all(v in self._expected for v in value)

        if isinstance(value, Mapping) and isinstance(self._expected, Mapping):
            value, self._expected = (
                cast("Mapping[object, object]", value),
                cast("Mapping[object, object]", self._expected),
            )
            return all(
                k in self._expected and value[k] == self._expected[k] for k in value
            )

        return False

    def __repr__(self) -> str:
        return f"CollectionOf({self._expected!r})"


class SequenceOf(Matcher):
    """Matches a sequence with the same elements in the same order.

    A set or mapping does not match. ``str``, ``bytes``, ``bytearray``,
    ``memoryview``, and :class:`collections.UserString` are sequences of
    their elements, as with :class:`CollectionOf`.

    Args:
        expected: Sequence to compare against.

    Raises:
        TypeError: `expected` is not a sequence.

    Examples:
        >>> from dmock import DeclarativeMock, SequenceOf
        >>> (1, 2) == SequenceOf([1, 2])
        True
        >>> "ab" == SequenceOf(["a", "b"])
        True
        >>> {1, 2} == SequenceOf([1, 2])
        False
        >>> class Service:
        ...     def fetch(self, items: tuple[int, ...]) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", SequenceOf([1, 2])).returns("ok")
        Expectation(fetch(SequenceOf([1, 2])))
        >>> mock.fetch((1, 2))
        'ok'
    """

    def __init__(self, expected: Sequence[object], /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is a sequence of the same elements."""
        if not isinstance(value, Sequence):
            return False

        return CollectionOf(self._expected).matches(cast("Sequence[object]", value))

    def __repr__(self) -> str:
        return f"SequenceOf({self._expected!r})"


class SetOf(Matcher):
    """Matches a set with the same elements.

    Order is ignored. A sequence or mapping does not match.

    Args:
        expected: Set to compare against.

    Raises:
        TypeError: `expected` is not a set.

    Examples:
        >>> from dmock import DeclarativeMock, SetOf
        >>> frozenset({1, 2}) == SetOf({2, 1})
        True
        >>> [1, 2] == SetOf({1, 2})
        False
        >>> class Service:
        ...     def fetch(self, items: set[int]) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", SetOf({1, 2})).returns("ok")
        Expectation(fetch(SetOf({1, 2})))
        >>> mock.fetch({2, 1})
        'ok'
    """

    def __init__(self, expected: Set[object], /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is a set of the same elements."""
        if not isinstance(value, Set):
            return False

        return CollectionOf(self._expected).matches(cast("Set[object]", value))

    def __repr__(self) -> str:
        return f"SetOf({self._expected!r})"


class MappingOf(Matcher):
    """Matches a mapping with the same keys and values.

    Key order is ignored. A sequence does not match. Extra keys do not match.

    Args:
        expected: Mapping to compare against.

    Raises:
        TypeError: `expected` is not a mapping.

    Examples:
        >>> from dmock import DeclarativeMock, MappingOf
        >>> {"b": 1, "a": 2} == MappingOf({"a": 2, "b": 1})
        True
        >>> {"a": 1, "b": 2} == MappingOf({"a": 1})
        False
        >>> class Service:
        ...     def save(self, item: dict[str, int]) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("save", MappingOf({"a": 1})).returns("ok")
        Expectation(save(MappingOf({'a': 1})))
        >>> mock.save({"a": 1})
        'ok'
    """

    def __init__(self, expected: Mapping[object, object], /) -> None:
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is a mapping of the same pairs."""
        if not isinstance(value, Mapping):
            return False

        return CollectionOf(self._expected).matches(
            cast("Mapping[object, object]", value)
        )

    def __repr__(self) -> str:
        return f"MappingOf({self._expected!r})"


class Attr(Matcher):
    """Matches an object that has an attribute named `attr`.

    Args:
        attr: Attribute name passed to ``hasattr``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Attr
        >>> class Item:
        ...     name = "n"
        >>> class Service:
        ...     def fetch(self, item: Item) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Attr("name")).returns("ok")
        Expectation(fetch(Attr('name')))
        >>> mock.fetch(Item())
        'ok'
    """

    def __init__(self, attr: str, /) -> None:
        self._attr = attr

    def matches(self, value: object, /) -> bool:
        """Return whether `value` has attribute `attr`."""
        return hasattr(value, self._attr)

    def __repr__(self) -> str:
        return f"Attr({self._attr!r})"


if TYPE_CHECKING:
    from typing import Any

    class _SupportsLT(Protocol):
        """Object that supports ``<``."""

        def __lt__(self, value: Any, /) -> bool:
            """Return whether `self` is strictly less than `value`."""
            ...

    class _SupportsGT(Protocol):
        """Object that supports ``>``."""

        def __gt__(self, value: Any, /) -> bool:
            """Return whether `self` is strictly greater than `value`."""
            ...

    class _SupportsLE(Protocol):
        """Object that supports ``<=``."""

        def __le__(self, value: Any, /) -> bool:
            """Return whether `self` is less than or equal to `value`."""
            ...

    class _SupportsGE(Protocol):
        """Object that supports ``>=``."""

        def __ge__(self, value: Any, /) -> bool:
            """Return whether `self` is greater than or equal to `value`."""
            ...


class Range(Matcher):
    """Matches a value strictly inside an interval.

    The interval is open: ``left < value < right``. Incomparable values raise
    ``TypeError``.

    Args:
        left: Exclusive lower bound.
        right: Exclusive upper bound.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Range
        >>> class Service:
        ...     def fetch(self, key: int) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Range(0, 10)).returns("ok")
        Expectation(fetch(Range(left=0, right=10)))
        >>> mock.fetch(5)
        'ok'
    """

    def __init__(self, left: _SupportsLT, right: _SupportsGT, /) -> None:
        self._left = left
        self._right = right

    def matches(self, value: Any, /) -> bool:
        """Return whether `value` is strictly inside the interval."""
        return bool(self._left < value < self._right)

    def __repr__(self) -> str:
        return f"Range(left={self._left!r}, right={self._right!r})"


class LessThan(Matcher):
    """Matches a value less than `expected`.

    Comparison uses ``<``. Incomparable values raise ``TypeError``.

    Args:
        expected: Exclusive upper bound that implements ``__gt__``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import LessThan
        >>> class Service:
        ...     def fetch(self, key: int) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", LessThan(3)).returns("ok")
        Expectation(fetch(LessThan(3)))
        >>> mock.fetch(2)
        'ok'
    """

    def __init__(self, expected: _SupportsGT, /) -> None:
        """Accept an exclusive upper bound that supports ``>``.

        ``matches`` evaluates ``value < expected``. When `value` does not
        implement that comparison, Python calls ``expected.__gt__(value)``.

        Args:
            expected: Exclusive upper bound. Must implement ``__gt__``.
        """
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is less than `expected`."""
        return value < self._expected

    def __repr__(self) -> str:
        return f"LessThan({self._expected!r})"


class GreaterThan(Matcher):
    """Matches a value greater than `expected`.

    Comparison uses ``>``. Incomparable values raise ``TypeError``.

    Args:
        expected: Exclusive lower bound that implements ``__lt__``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import GreaterThan
        >>> class Service:
        ...     def fetch(self, key: int) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", GreaterThan(3)).returns("ok")
        Expectation(fetch(GreaterThan(3)))
        >>> mock.fetch(4)
        'ok'
    """

    def __init__(self, expected: _SupportsLT, /) -> None:
        """Accept an exclusive lower bound that supports ``<``.

        ``matches`` evaluates ``expected < value``, so `expected` must
        implement ``__lt__``.

        Args:
            expected: Exclusive lower bound. Must implement ``__lt__``.
        """
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is greater than `expected`."""
        return self._expected < value

    def __repr__(self) -> str:
        return f"GreaterThan({self._expected!r})"


class LessEquals(Matcher):
    """Matches a value less than or equal to `expected`.

    Comparison uses ``<=``. Incomparable values raise ``TypeError``.

    Args:
        expected: Inclusive upper bound that implements ``__ge__``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import LessEquals
        >>> class Service:
        ...     def fetch(self, key: int) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", LessEquals(3)).returns("ok")
        Expectation(fetch(LessEquals(3)))
        >>> mock.fetch(3)
        'ok'
    """

    def __init__(self, expected: _SupportsGE, /) -> None:
        """Accept an inclusive upper bound that supports ``>=``.

        ``matches`` evaluates ``value <= expected``. When `value` does not
        implement that comparison, Python calls ``expected.__ge__(value)``.

        Args:
            expected: Inclusive upper bound. Must implement ``__ge__``.
        """
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is less than or equal to `expected`."""
        return value <= self._expected

    def __repr__(self) -> str:
        return f"LessEquals({self._expected!r})"


class GreaterEquals(Matcher):
    """Matches a value greater than or equal to `expected`.

    Comparison uses ``>=``. Incomparable values raise ``TypeError``.

    Args:
        expected: Inclusive lower bound that implements ``__le__``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import GreaterEquals
        >>> class Service:
        ...     def fetch(self, key: int) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", GreaterEquals(3)).returns("ok")
        Expectation(fetch(GreaterEquals(3)))
        >>> mock.fetch(3)
        'ok'
    """

    def __init__(self, expected: _SupportsLE, /) -> None:
        """Accept an inclusive lower bound that supports ``<=``.

        ``matches`` evaluates ``expected <= value``, so `expected` must
        implement ``__le__``.

        Args:
            expected: Inclusive lower bound. Must implement ``__le__``.
        """
        self._expected = expected

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is greater than or equal to `expected`."""
        return self._expected <= value

    def __repr__(self) -> str:
        return f"GreaterEquals({self._expected!r})"


class Approx(Matcher):
    """Matches a number close to `expected`.

    Comparison uses :func:`math.isclose`. Values without ``__float__`` do not
    match.

    Args:
        expected: Target number.
        rel_tol: Relative tolerance. Defaults to ``1e-9``.
        abs_tol: Absolute tolerance. Defaults to ``0``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Approx
        >>> class Service:
        ...     def fetch(self, key: float) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Approx(1.0)).returns("ok")
        Expectation(fetch(Approx(1.0, rel_tol=1e-09, abs_tol=0)))
        >>> mock.fetch(1.0)
        'ok'
    """

    def __init__(
        self,
        expected: SupportsFloat,
        /,
        rel_tol: SupportsFloat = 1e-9,
        abs_tol: SupportsFloat = 0,
    ) -> None:
        self._expected = expected
        self._rel_tol = rel_tol
        self._abs_tol = abs_tol

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is close to `expected`."""
        if not isinstance(value, SupportsFloat):
            return False

        return math.isclose(
            value,
            self._expected,
            rel_tol=self._rel_tol,
            abs_tol=self._abs_tol,
        )

    def __repr__(self) -> str:
        return (
            f"Approx({self._expected!r}, "
            f"rel_tol={self._rel_tol!r}, "
            f"abs_tol={self._abs_tol!r})"
        )


class StartsWith(Matcher):
    """Matches a string that starts with `prefix`.

    A non-string value does not match.

    Args:
        prefix: Prefix the value must start with.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import StartsWith
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", StartsWith("k")).returns("ok")
        Expectation(fetch(StartsWith('k')))
        >>> mock.fetch("key")
        'ok'
    """

    def __init__(self, prefix: str, /) -> None:
        self._prefix = prefix

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is a string starting with `prefix`."""
        return isinstance(value, str) and value.startswith(self._prefix)

    def __repr__(self) -> str:
        return f"StartsWith({self._prefix!r})"


class EndsWith(Matcher):
    """Matches a string that ends with `postfix`.

    A non-string value does not match.

    Args:
        postfix: Suffix the value must end with.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import EndsWith
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", EndsWith("ey")).returns("ok")
        Expectation(fetch(EndsWith('ey')))
        >>> mock.fetch("key")
        'ok'
    """

    def __init__(self, postfix: str, /) -> None:
        self._postfix = postfix

    def matches(self, value: object, /) -> bool:
        """Return whether `value` is a string ending with `postfix`."""
        return isinstance(value, str) and value.endswith(self._postfix)

    def __repr__(self) -> str:
        return f"EndsWith({self._postfix!r})"


class RegexMatch(Matcher):
    """Matches a string from the start, using ``re.match``.

    ``Regex`` is an alias of this class. A non-string value does not match.

    Args:
        expected: Pattern string or compiled :class:`re.Pattern`.
        flags: Flags for ``re.match``. Must be ``re.NOFLAG`` when `expected`
            is already compiled.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Regex, RegexMatch
        >>> Regex is RegexMatch
        True
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", RegexMatch(r"k.*")).returns("ok")
        Expectation(fetch(RegexMatch(expected='k.*', flags=re.NOFLAG)))
        >>> mock.fetch("key")
        'ok'
    """

    def __init__(
        self, expected: str | re.Pattern[str], /, flags: re.RegexFlag = re.NOFLAG
    ) -> None:
        self._expected = expected
        self._flags = flags

    def matches(self, value: object, /) -> bool:
        """Return whether `value` matches the pattern from the start."""
        if not isinstance(value, str):
            return False

        return bool(re.match(self._expected, value, self._flags))

    def __repr__(self) -> str:
        return f"RegexMatch(expected={self._expected!r}, flags={self._flags!r})"


Regex: TypeAlias = RegexMatch


class RegexSearch(Matcher):
    """Matches a string that contains a pattern, using ``re.search``.

    A non-string value does not match.

    Args:
        expected: Pattern string or compiled :class:`re.Pattern`.
        flags: Flags for ``re.search``. Must be ``re.NOFLAG`` when `expected`
            is already compiled.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import RegexSearch
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", RegexSearch("ey")).returns("ok")
        Expectation(fetch(RegexSearch(expected='ey', flags=re.NOFLAG)))
        >>> mock.fetch("key")
        'ok'
    """

    def __init__(
        self, expected: str | re.Pattern[str], /, flags: re.RegexFlag = re.NOFLAG
    ) -> None:
        self._expected = expected
        self._flags = flags

    def matches(self, value: object, /) -> bool:
        """Return whether the pattern occurs anywhere in `value`."""
        if not isinstance(value, str):
            return False

        return bool(re.search(self._expected, value, self._flags))

    def __repr__(self) -> str:
        return f"RegexSearch(expected={self._expected!r}, flags={self._flags!r})"


class RegexFullmatch(Matcher):
    """Matches a string that is the whole pattern, using ``re.fullmatch``.

    A non-string value does not match.

    Args:
        expected: Pattern string or compiled :class:`re.Pattern`.
        flags: Flags for ``re.fullmatch``. Must be ``re.NOFLAG`` when
            `expected` is already compiled.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import RegexFullmatch
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", RegexFullmatch(r"k.y")).returns("ok")
        Expectation(fetch(RegexFullmatch(expected='k.y', flags=re.NOFLAG)))
        >>> mock.fetch("key")
        'ok'
    """

    def __init__(
        self, expected: str | re.Pattern[str], /, flags: re.RegexFlag = re.NOFLAG
    ) -> None:
        self._expected = expected
        self._flags = flags

    def matches(self, value: object, /) -> bool:
        """Return whether `value` matches the pattern entirely."""
        if not isinstance(value, str):
            return False

        return bool(re.fullmatch(self._expected, value, self._flags))

    def __repr__(self) -> str:
        return f"RegexFullmatch(expected={self._expected!r}, flags={self._flags!r})"


class Args(Matcher):
    """Shared constructor for :class:`And` and :class:`Or`.

    Each argument may be a matcher or a plain object. Plain objects are
    compared with ``==``, so ``Or(1, 2)`` matches ``1``, including the
    reflected comparison ``1 == Or(1, 2)``. ``1 | Equals(2)`` builds that
    :class:`Or`.

    Args:
        *args: Values or matchers combined by the subclass.

    Examples:
        >>> from dmock import Equals, Or
        >>> 1 == Or(1, 2)
        True
        >>> (1 | Equals(2)) == 2
        True
    """

    def __init__(self, /, *args: object) -> None:
        self.args = args

    def __repr__(self) -> str:
        return "{}({})".format(type(self).__name__, ", ".join(map(repr, self.args)))


class And(Args):
    """Matches when every argument matches the value.

    ``left & right`` builds an :class:`And`. A non-matcher operand is wrapped
    in :class:`Equals`.

    Args:
        *args: Values or matchers that must all match. Plain objects are
            compared with ``==``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import And, GreaterThan, LessThan
        >>> class Service:
        ...     def fetch(self, key: int) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", And(GreaterThan(0), LessThan(10))).returns("ok")
        Expectation(fetch(And(GreaterThan(0), LessThan(10))))
        >>> mock.fetch(5)
        'ok'
    """

    def matches(self, value: object, /) -> bool:
        """Return whether every argument matches `value`."""
        return bool(all(a == value for a in self.args))


class Or(Args):
    """Matches when any argument matches the value.

    ``left | right`` builds an :class:`Or`. A non-matcher operand is wrapped
    in :class:`Equals`.

    Args:
        *args: Values or matchers of which one must match. Plain objects are
            compared with ``==``.

    Examples:
        >>> from dmock import DeclarativeMock
        >>> from dmock import Or
        >>> class Service:
        ...     def fetch(self, key: str) -> str: ...
        >>> mock = DeclarativeMock(Service)
        >>> mock.expect("fetch", Or("a", "b")).returns("ok")
        Expectation(fetch(Or('a', 'b')))
        >>> mock.fetch("b")
        'ok'
    """

    def matches(self, value: object, /) -> bool:
        """Return whether any argument matches `value`."""
        return bool(any(a == value for a in self.args))
