from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from dmock._exceptions import ConfigurationError


if TYPE_CHECKING:
    from collections.abc import Callable


# -- Outcomes --


@dataclass(frozen=True, slots=True)
class ReturnOutcome:
    """Return `value` from a matching call."""

    value: object


@dataclass(frozen=True, slots=True)
class RaiseOutcome:
    """Raise `exception` from a matching call."""

    exception: BaseException | type[BaseException]


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """Call `func` with the actual arguments of a matching call."""

    func: Callable[..., object]


@dataclass(frozen=True, slots=True)
class DefaultOutcome:
    """Returned by consume() when no explicit outcome was registered.

    The dispatcher (DeclarativeMock) decides the actual return value,
    typically falling through to unittest.mock's default behavior.
    """


Outcome = ReturnOutcome | RaiseOutcome | RunOutcome | DefaultOutcome


# -- Recorded calls --


@dataclass(frozen=True, slots=True)
class RecordedCall:
    """A dispatched call stored for diagnostic messages."""

    name: str
    args: tuple[object, ...]
    kwargs: dict[str, object]


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

    @property
    def description(self) -> str:
        """Human-readable constraint used in error messages."""
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

    @property
    def description(self) -> str:
        return f"exactly {self.n} call(s)"


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

    @property
    def description(self) -> str:
        return f"at least {self.n} call(s)"


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

    @property
    def description(self) -> str:
        return f"between {self.lo} and {self.hi} call(s)"


@dataclass(frozen=True, slots=True)
class Never:
    """Expect zero calls; any call is a violation."""

    def is_satisfied(self, calls: int) -> bool:
        return calls == 0

    def is_exhausted(self, calls: int) -> bool:
        # Returns False intentionally: the dispatcher must keep this expectation
        # active so that a matching call can be routed here and raise in consume().
        return False

    @property
    def max_calls(self) -> int:
        return 0

    @property
    def description(self) -> str:
        return "never"
