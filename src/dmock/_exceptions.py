from __future__ import annotations


class DeclarativeMockError(Exception):
    """Base for all dmock errors."""


class UnexpectedCallError(DeclarativeMockError):
    """A call was made that matches no registered expectation."""


class UnsatisfiedExpectationError(DeclarativeMockError):
    """assert_expectations() found unmet quantifier constraints."""


class ConfigurationError(DeclarativeMockError):
    """Invalid expectation setup (e.g. duplicate/conflicting quantifiers)."""
