from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Self

from dmock._exceptions import ConfigurationError, UnexpectedCallError
from dmock._matchers import (
    Matcher,
    _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
    _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
)
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
    from collections.abc import Callable, Sequence

    from dmock._types import Outcome, Quantifier


def _value_matches(expected: object, actual: object) -> bool:
    if isinstance(expected, Matcher):
        return expected.matches(actual)
    return expected == actual


class Expectation:
    """A single expected call - fluent builder for outcomes and quantifiers."""

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
        self._requires: list[Expectation] = []

    # -- Fluent outcome builders --

    def returns(self, value: object) -> Self:
        self._outcomes.append(ReturnOutcome(value))
        return self

    def raises(self, exc: BaseException | type[BaseException]) -> Self:
        self._outcomes.append(RaiseOutcome(exc))
        return self

    def runs(self, func: Callable[..., object]) -> Self:
        self._outcomes.append(RunOutcome(func))
        return self

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

    def not_before(self, *expectations: Expectation) -> Self:
        """Declare that this expectation must not be dispatched until all *expectations* are satisfied.

        Raises ConfigurationError if adding any requirement would create a cycle.
        """
        for req in expectations:
            if self._is_reachable_from(req):
                raise ConfigurationError(
                    f"Cycle detected: adding {req!r} as a prerequisite of "
                    f"{self!r} would create a circular dependency."
                )
            self._requires.append(req)
        return self

    def _is_reachable_from(self, source: Expectation) -> bool:
        """Return True if *self* is reachable by following _requires from *source*."""
        visited: set[int] = set()
        queue: deque[Expectation] = deque([source])
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
    def requires(self) -> Sequence[Expectation]:
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
            if not all(
                _value_matches(e, a)
                for e, a in zip(self._expected_args, args, strict=True)
            ):
                return False

        if not self._has_any_kwargs:
            if kwargs.keys() != self._expected_kwargs.keys():
                return False
            if not all(
                _value_matches(self._expected_kwargs[k], kwargs[k])
                for k in self._expected_kwargs
            ):
                return False

        return True

    def consume(self) -> Outcome:
        q = self.quantifier
        self._calls += 1
        if q.max_calls is not None and self._calls > q.max_calls:
            raise UnexpectedCallError(
                f"Unexpected call to {self._method_name!r}: "
                f"called {self._calls} time(s), "
                f"max allowed is {q.max_calls}."
            )
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
        return f"Expectation({self._method_name}({all_parts}))"


def in_order(*expectations: Expectation) -> None:
    """Link *expectations* so each one requires the previous to be satisfied first.

    Equivalent to calling ``expectations[i].not_before(expectations[i-1])`` for
    every consecutive pair.  Passing 0 or 1 expectations is a no-op.
    """
    for i in range(1, len(expectations)):
        expectations[i].not_before(expectations[i - 1])
