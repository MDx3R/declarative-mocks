from __future__ import annotations

from typing import TYPE_CHECKING, Generic, cast

from dmock._protocols import T


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeAlias

    Predicate: TypeAlias = Callable[[T], bool]


class Check(Generic[T]):
    """Composable predicate wrapper for spy result and exception checks.

    All predicates passed to ``Check(...)`` must return truthy values (AND
    semantics). Instances support ``~`` (negation), ``&`` (conjunction), and
    ``|`` (disjunction) with other ``Check`` instances or plain callables.

    Args:
        *predicates: One or more callables accepting a value and returning
            a boolean.

    Examples:
        >>> from dmock import Check
        >>> is_positive = Check(lambda x: x > 0)
        >>> is_even = Check(lambda x: x % 2 == 0)
        >>> (is_positive & is_even)(4)
        True
        >>> (is_positive & is_even)(3)
        False
        >>> (~is_positive)(-1)
        True
    """

    def __init__(self, /, *predicates: Predicate[T]) -> None:
        self._predicates = predicates

    def __call__(self, value: T) -> bool:
        """Return ``True`` if every predicate returns ``True`` for `value`."""
        return all(p(value) for p in self._predicates)

    def __invert__(self) -> CheckNot[T]:
        """Return a :class:`CheckNot` negating this check.

        Examples:
            >>> from dmock import Check
            >>> non_empty = ~Check(lambda s: s == "")
            >>> non_empty("hi")
            True
            >>> non_empty("")
            False
        """
        return CheckNot(self)

    def __and__(self, other: Predicate[T]) -> CheckAnd[T]:
        """Return a :class:`CheckAnd` requiring both `self` and `other`.

        Examples:
            >>> from dmock import Check
            >>> c = Check(lambda x: x > 0) & (lambda x: x < 10)
            >>> c(5)
            True
            >>> c(12)
            False
        """
        if not isinstance(other, Check):
            other = Check(other)

        return CheckAnd(self, cast("Check[T]", other))

    def __rand__(self, other: Predicate[T]) -> CheckAnd[T]:
        """Return a :class:`CheckAnd` when the left operand is a plain callable."""
        if not isinstance(other, Check):
            return CheckAnd(self, other)

        return NotImplemented

    def __or__(self, other: Predicate[T]) -> CheckOr[T]:
        """Return a :class:`CheckOr` requiring either `self` or `other`.

        Examples:
            >>> from dmock import Check
            >>> c = Check(lambda x: x < 0) | (lambda x: x > 10)
            >>> c(-1)
            True
            >>> c(5)
            False
        """
        if not isinstance(other, Check):
            other = Check(other)

        return CheckOr(self, cast("Check[T]", other))

    def __ror__(self, other: Predicate[T]) -> CheckOr[T]:
        """Return a :class:`CheckOr` when the left operand is a plain callable."""
        if not isinstance(other, Check):
            return CheckOr(other, self)

        return NotImplemented

    def __repr__(self) -> str:
        """Return a readable representation showing wrapped predicates."""
        return "{}({})".format(
            type(self).__name__, ", ".join(map(repr, self._predicates))
        )


class CheckNot(Check[T]):
    """Negated predicate: ``True`` when none of `predicates` match.

    Usually constructed with ``~check``.

    Args:
        *predicates: Predicates to negate.

    Examples:
        >>> from dmock import CheckNot
        >>> not_zero = CheckNot(lambda x: x == 0)
        >>> not_zero(1)
        True
        >>> not_zero(0)
        False
    """

    def __init__(self, /, *predicates: Predicate[T]) -> None:
        self._predicates = predicates

    def __call__(self, value: T) -> bool:
        """Return ``True`` if no predicate matches `value`."""
        return not any(p(value) for p in self._predicates)


class CheckAnd(Check[T]):
    """Conjunction predicate: ``True`` when all `predicates` match.

    Usually constructed with ``check & other``.

    Args:
        *predicates: Predicates that must all hold.

    Examples:
        >>> from dmock import CheckAnd
        >>> in_range = CheckAnd(lambda x: x >= 1, lambda x: x <= 5)
        >>> in_range(3)
        True
        >>> in_range(6)
        False
    """

    def __init__(self, /, *predicates: Predicate[T]) -> None:
        self._predicates = predicates

    def __call__(self, value: T) -> bool:
        """Return ``True`` if every predicate matches `value`."""
        return all(p(value) for p in self._predicates)


class CheckOr(Check[T]):
    """Disjunction predicate: ``True`` when any of `predicates` matches.

    Usually constructed with ``check | other``.

    Args:
        *predicates: Predicates of which at least one must hold.

    Examples:
        >>> from dmock import CheckOr
        >>> extreme = CheckOr(lambda x: x < 0, lambda x: x > 100)
        >>> extreme(150)
        True
        >>> extreme(50)
        False
    """

    def __init__(self, /, *predicates: Predicate[T]) -> None:
        self._predicates = predicates

    def __call__(self, value: T) -> bool:
        """Return ``True`` if at least one predicate matches `value`."""
        return any(p(value) for p in self._predicates)
