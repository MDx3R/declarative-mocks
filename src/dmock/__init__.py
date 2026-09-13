"""Declarative wrapper around unittest.mock with a DSL for tests."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

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


try:
    __version__ = version("declarative-mocks")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"


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
