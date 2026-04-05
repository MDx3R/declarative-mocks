"""Declarative wrapper around unittest.mock with a DSL for tests."""

from __future__ import annotations

from dmock._exceptions import (
    ConfigurationError,
    DeclarativeMockError,
    UnexpectedCallError,
    UnsatisfiedExpectationError,
)
from dmock._expectation import in_order
from dmock._matchers import (
    ANY_ARGS,
    ANY_KWARGS,
    Anything,
    AnythingOfType,
    MatchedBy,
)
from dmock._mock import DeclarativeMock


__all__ = [
    "ANY_ARGS",
    "ANY_KWARGS",
    "Anything",
    "AnythingOfType",
    "ConfigurationError",
    "DeclarativeMock",
    "DeclarativeMockError",
    "MatchedBy",
    "UnexpectedCallError",
    "UnsatisfiedExpectationError",
    "in_order",
]
