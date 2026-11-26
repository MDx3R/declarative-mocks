"""Composable predicate checks for declarative spy observations."""

from __future__ import annotations

from dmock.checks._check import Check, CheckAnd, CheckNot, CheckOr


__all__ = [
    "Check",
    "CheckAnd",
    "CheckNot",
    "CheckOr",
]
