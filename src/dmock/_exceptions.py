from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence

    from dmock._expectation import Expectation
    from dmock._types import RecordedCall


class DeclarativeMockError(Exception):
    """Base for all dmock errors."""


class UnexpectedCallError(DeclarativeMockError):
    """A call was made that matches no registered expectation."""


class UnregisteredCallError(UnexpectedCallError):
    """Attribute has no registered expectation (whitelist miss)."""

    def __init__(self, name: str, history: Sequence[RecordedCall]) -> None:
        self.name = name
        self.history = tuple(history)
        super().__init__()

    def __str__(self) -> str:
        return _with_history(
            f"Unexpected call: {self.name!r} has no registered expectation.",
            self.history,
        )


class NoMatchingCallError(UnexpectedCallError):
    """Call matched no non-exhausted expectation for this name."""

    def __init__(
        self,
        call: RecordedCall,
        rejected: Sequence[Expectation],
        history: Sequence[RecordedCall],
    ) -> None:
        self.call = call
        self.rejected = tuple(rejected)
        self.history = tuple(history)
        super().__init__()

    def __str__(self) -> str:
        header = (
            f"Unexpected call: {self.call.name!r} called with "
            f"args={self.call.args!r}, kwargs={self.call.kwargs!r}"
        )
        candidates = "\n".join(
            f"  {exp!r} - {self._reason(exp)}" for exp in self.rejected
        )
        return _with_history(
            f"{header} - no matching non-exhausted expectation.\n"
            f"Candidates:\n{candidates}",
            self.history,
        )

    def _reason(self, exp: Expectation) -> str:
        if exp.is_exhausted():
            maximum = exp.quantifier.max_calls
            bound = "*" if maximum is None else str(maximum)
            return f"exhausted ({exp.call_count}/{bound} calls)"

        return "args mismatch"


class BlockedCallError(UnexpectedCallError):
    """Call matched an expectation whose prerequisites are not yet satisfied."""

    def __init__(
        self,
        call: RecordedCall,
        expectation: Expectation,
        blocked: Sequence[Expectation],
        history: Sequence[RecordedCall],
    ) -> None:
        self.call = call
        self.expectation = expectation
        self.blocked = tuple(blocked)
        self.history = tuple(history)
        super().__init__()

    def __str__(self) -> str:
        reasons = "; ".join(self._blocked_reason(req) for req in self.blocked)
        return _with_history(
            f"Out-of-order call: {self.call.name!r} called with "
            f"args={self.call.args!r}, kwargs={self.call.kwargs!r}\n"
            f"  {self.expectation!r} - {reasons}",
            self.history,
        )

    @staticmethod
    def _blocked_reason(req: Expectation) -> str:
        return (
            f"blocked by {req.method_name} "
            f"(expected {req.quantifier.description}, got {req.call_count})"
        )


class ExceededCallError(UnexpectedCallError):
    """A matching call exceeded the expectation's quantifier upper bound."""

    def __init__(self, method_name: str, calls: int, max_calls: int) -> None:
        self.method_name = method_name
        self.calls = calls
        self.max_calls = max_calls
        super().__init__()

    def __str__(self) -> str:
        return (
            f"Unexpected call to {self.method_name!r}: "
            f"called {self.calls} time(s), "
            f"max allowed is {self.max_calls}."
        )


class UnsatisfiedExpectationError(DeclarativeMockError):
    """verify() found unmet quantifier constraints."""

    def __init__(
        self,
        expectations: Sequence[Expectation],
        history: Sequence[RecordedCall],
    ) -> None:
        self.expectations = tuple(expectations)
        self.history = tuple(history)
        super().__init__()

    def __str__(self) -> str:
        lines = "\n".join(
            f"  {exp!r} - expected {exp.quantifier.description}, got {exp.call_count}"
            for exp in self.expectations
        )
        return _with_history(f"Unsatisfied expectations:\n{lines}", self.history)


class ConfigurationError(DeclarativeMockError):
    """Invalid expectation setup (e.g. duplicate/conflicting quantifiers)."""


def _with_history(message: str, history: Sequence[RecordedCall]) -> str:
    if not history:
        return message

    lines = "\n".join(
        f"  {index}. {_format_call(call)}"
        for index, call in enumerate(history, start=1)
    )
    return f"{message}\nCall history:\n{lines}"


def _format_call(call: RecordedCall) -> str:
    parts = [repr(a) for a in call.args]
    parts.extend(f"{key}={value!r}" for key, value in call.kwargs.items())
    return f"{call.name}({', '.join(parts)})"
