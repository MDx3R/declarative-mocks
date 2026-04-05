from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from dmock._exceptions import ConfigurationError


if TYPE_CHECKING:
    from collections.abc import Callable


# -- Outcomes --


@dataclass(frozen=True, slots=True)
class ReturnOutcome:
    value: object


@dataclass(frozen=True, slots=True)
class RaiseOutcome:
    exception: BaseException | type[BaseException]


@dataclass(frozen=True, slots=True)
class RunOutcome:
    func: Callable[..., object]


@dataclass(frozen=True, slots=True)
class DefaultOutcome:
    """Returned by consume() when no explicit outcome was registered.

    The dispatcher (DeclarativeMock) decides the actual return value,
    typically falling through to unittest.mock's default behavior.
    """


Outcome = ReturnOutcome | RaiseOutcome | RunOutcome | DefaultOutcome


# -- Quantifier protocol and concrete implementations --


class Quantifier(Protocol):
    """Protocol for call-count constraints on an Expectation."""

    def is_satisfied(self, calls: int) -> bool:
        """Return True when the observed call count meets the minimum requirement."""
        ...

    def is_exhausted(self, calls: int) -> bool:
        """Return True when no further calls are allowed."""
        ...

    @property
    def max_calls(self) -> int | None:
        """Upper bound on allowed calls; None means unbounded."""
        ...


@dataclass(frozen=True, slots=True)
class ExactlyN:
    """Expect exactly n calls (once, twice, times(n))."""

    n: int

    def __post_init__(self) -> None:
        if self.n < 1:
            raise ConfigurationError(
                f"ExactlyN requires n >= 1, got {self.n}. Use never() for 0 calls."
            )

    def is_satisfied(self, calls: int) -> bool:
        return calls >= self.n

    def is_exhausted(self, calls: int) -> bool:
        return calls >= self.n

    @property
    def max_calls(self) -> int:
        return self.n


@dataclass(frozen=True, slots=True)
class AtLeast:
    """Expect at least n calls; no upper bound."""

    n: int

    def __post_init__(self) -> None:
        if self.n < 1:
            raise ConfigurationError(f"AtLeast requires n >= 1, got {self.n}.")

    def is_satisfied(self, calls: int) -> bool:
        return calls >= self.n

    def is_exhausted(self, calls: int) -> bool:
        return False

    @property
    def max_calls(self) -> int | None:
        return None


@dataclass(frozen=True, slots=True)
class Between:
    """Expect between lo and hi calls (inclusive).

    Also used for at_most(n) = Between(0, n).
    """

    lo: int
    hi: int

    def __post_init__(self) -> None:
        if self.lo < 0 or self.lo > self.hi:
            raise ConfigurationError(
                f"Between requires 0 <= lo <= hi, got lo={self.lo}, hi={self.hi}."
            )

    def is_satisfied(self, calls: int) -> bool:
        return calls >= self.lo

    def is_exhausted(self, calls: int) -> bool:
        return calls >= self.hi

    @property
    def max_calls(self) -> int:
        return self.hi


@dataclass(frozen=True, slots=True)
class Never:
    """Expect zero calls; any call is a violation."""

    def is_satisfied(self, calls: int) -> bool:
        return calls == 0

    def is_exhausted(self, calls: int) -> bool:
        # Returns False intentionally: the dispatcher must keep this expectation
        # active so that a matching call can be routed here and raise in consume().
        # TODO: Revise after implementing dispatch
        return False

    @property
    def max_calls(self) -> int:
        return 0
