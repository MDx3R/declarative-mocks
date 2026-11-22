from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from dmock._interaction import Expectation, Observation
    from dmock._protocols import T
    from dmock._types import RecordedCall


class DeclarativeMockError(Exception):
    """Base for all dmock errors."""


class UnexpectedCallError(DeclarativeMockError):
    """A call matched no registered interaction.

    Raised at dispatch time: missing ``expect``, argument mismatch, exhausted
    interaction, out-of-order call, or ``never()``. Catch this type; the
    traceback may show a more specific subclass.
    """


class UnregisteredCallError(UnexpectedCallError):
    """Attribute has no registered interaction (whitelist miss)."""

    def __init__(self, name: str, history: Sequence[RecordedCall]) -> None:
        self.name = name
        self.history = tuple(history)
        super().__init__()

    def __str__(self) -> str:
        return _with_history(
            f"Unexpected call: {self.name!r} has no registered interaction.",
            self.history,
        )


class NoMatchingCallError(UnexpectedCallError):
    """Call matched no non-exhausted interaction for this name."""

    def __init__(
        self,
        call: RecordedCall,
        rejected: Sequence[Expectation[T, Any, Any] | Observation[T, Any, Any]],
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
            f"{header} - no matching non-exhausted interaction.\n"
            f"Candidates:\n{candidates}",
            self.history,
        )

    def _reason(self, exp: Expectation[T, Any, Any] | Observation[T, Any, Any]) -> str:
        if exp.is_exhausted():
            maximum = exp.quantifier.max_calls
            bound = "*" if maximum is None else str(maximum)
            return f"exhausted ({exp.call_count}/{bound} calls)"

        return "args mismatch"


class BlockedCallError(UnexpectedCallError):
    """Call matched an interaction whose prerequisites are not yet satisfied."""

    def __init__(
        self,
        call: RecordedCall,
        interaction: Expectation[T, Any, Any] | Observation[T, Any, Any],
        blocked: Sequence[Expectation[T, Any, Any] | Observation[T, Any, Any]],
        history: Sequence[RecordedCall],
    ) -> None:
        self.call = call
        self.interaction = interaction
        self.blocked = tuple(blocked)
        self.history = tuple(history)
        super().__init__()

    def __str__(self) -> str:
        reasons = "; ".join(self._blocked_reason(req) for req in self.blocked)
        return _with_history(
            f"Out-of-order call: {self.call.name!r} called with "
            f"args={self.call.args!r}, kwargs={self.call.kwargs!r}\n"
            f"  {self.interaction!r} - {reasons}",
            self.history,
        )

    @staticmethod
    def _blocked_reason(
        req: Expectation[T, Any, Any] | Observation[T, Any, Any],
    ) -> str:
        return (
            f"blocked by {req.method_name} "
            f"(expected {req.quantifier.description}, got {req.call_count})"
        )


class ExceededCallError(UnexpectedCallError):
    """A matching call exceeded the interaction's quantifier upper bound."""

    def __init__(self, method_name: str, calls: int, max_calls: int | None) -> None:
        self.method_name = method_name
        self.calls = calls
        self.max_calls = max_calls
        super().__init__()

    def __str__(self) -> str:
        return (
            f"Unexpected call to {self.method_name!r}: "
            f"called {self.calls} time(s), "
            f"max allowed is {self.max_calls or 0}."
        )


class UnsatisfiedExpectationError(DeclarativeMockError):
    """Raised by :meth:`~dmock.DeclarativeMock.verify` when a quantifier is unmet."""

    def __init__(
        self,
        expectations: Sequence[Expectation[T, Any, Any]],
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


class UnsatisfiedObservationError(DeclarativeMockError):
    """Raised by :meth:`~dmock.DeclarativeSpy.verify` when a quantifier is unmet."""

    def __init__(
        self,
        observations: Sequence[Observation[T, Any, Any]],
        history: Sequence[RecordedCall],
    ) -> None:
        self.observations = tuple(observations)
        self.history = tuple(history)
        super().__init__()

    def __str__(self) -> str:
        lines = "\n".join(
            f"  {obs!r} - expected {obs.quantifier.description}, got {obs.call_count}"
            for obs in self.observations
        )
        return _with_history(f"Unsatisfied observations:\n{lines}", self.history)


class ConfigurationError(DeclarativeMockError):
    """Invalid interaction setup (conflicting quantifiers, reserved names, cycles)."""


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
