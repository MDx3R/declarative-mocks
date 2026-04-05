from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


@runtime_checkable
class Matcher(Protocol):
    def matches(self, value: object) -> bool: ...


class _AnythingMatcher:
    """Matches any single value."""

    def matches(self, value: object) -> bool:
        return True

    def __call__(self) -> _AnythingMatcher:
        return self

    def __repr__(self) -> str:
        return "Anything"


Anything = _AnythingMatcher()


class AnythingOfType:
    """Matches a value that is an instance of the given type."""

    def __init__(self, expected_type: type) -> None:
        self._expected_type = expected_type

    def matches(self, value: object) -> bool:
        return isinstance(value, self._expected_type)

    def __repr__(self) -> str:
        return f"AnythingOfType({self._expected_type.__name__})"


class MatchedBy:
    """Matches when a user-supplied predicate returns True."""

    def __init__(self, predicate: Callable[[Any], bool]) -> None:
        self._predicate = predicate

    def matches(self, value: object) -> bool:
        return self._predicate(value)

    def __repr__(self) -> str:
        return f"MatchedBy({self._predicate!r})"


class _AnyArgsSentinel:
    """Sentinel: match any number of positional args."""

    def __repr__(self) -> str:
        return "ANY_ARGS"


class _AnyKwargsSentinel:
    """Sentinel: match any keyword args."""

    def __repr__(self) -> str:
        return "ANY_KWARGS"


ANY_ARGS = _AnyArgsSentinel()
ANY_KWARGS = _AnyKwargsSentinel()
