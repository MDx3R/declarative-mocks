from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    Predicate = Callable[[Any], bool]


class Check:
    def __init__(self, /, *predicates: Predicate) -> None:
        self._predicates = predicates

    def __call__(self, value: Any) -> bool:
        return all(p(value) for p in self._predicates)

    def __invert__(self) -> Check:
        return CheckNot(self)

    def __and__(self, other: Predicate) -> Check:
        if not isinstance(other, Check):
            other = Check(other)

        return CheckAnd(self, other)

    def __rand__(self, other: Predicate) -> Check:
        if not isinstance(other, Check):
            return CheckAnd(self, other)

        return NotImplemented

    def __or__(self, other: Predicate) -> Check:
        if not isinstance(other, Check):
            other = Check(other)

        return CheckOr(self, other)

    def __ror__(self, other: Predicate) -> Check:
        if not isinstance(other, Check):
            return CheckOr(other, self)

        return NotImplemented

    def __repr__(self) -> str:
        return "{}({})".format(
            type(self).__name__, ", ".join(map(repr, self._predicates))
        )


class CheckNot(Check):
    def __init__(self, /, *predicates: Predicate) -> None:
        self._predicates = predicates

    def __call__(self, value: Any) -> bool:
        return not any(p(value) for p in self._predicates)


class CheckAnd(Check):
    def __init__(self, /, *predicates: Predicate) -> None:
        self._predicates = predicates

    def __call__(self, value: Any) -> bool:
        return all(p(value) for p in self._predicates)


class CheckOr(Check):
    def __init__(self, /, *predicates: Predicate) -> None:
        self._predicates = predicates

    def __call__(self, value: Any) -> bool:
        return any(p(value) for p in self._predicates)
