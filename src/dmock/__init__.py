"""Declarative wrapper around unittest.mock with a DSL for tests."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from dmock._interaction import Expectation, Observation, in_order
from dmock._mock import DeclarativeMock, dmock
from dmock._spy import DeclarativeSpy, dspy


try:
    __version__ = version("declarative-mocks")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+unknown"


__all__ = [
    "DeclarativeMock",
    "DeclarativeSpy",
    "Expectation",
    "Observation",
    "dmock",
    "dspy",
    "in_order",
]
