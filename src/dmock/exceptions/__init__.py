"""Public exception hierarchy for declarative-mocks."""

from __future__ import annotations

from dmock.exceptions._exceptions import (
    ConfigurationError,
    DeclarativeMockError,
    UnexpectedCallError,
    UnsatisfiedExpectationError,
    UnsatisfiedObservationError,
)


__all__ = [
    "ConfigurationError",
    "DeclarativeMockError",
    "UnexpectedCallError",
    "UnsatisfiedExpectationError",
    "UnsatisfiedObservationError",
]
