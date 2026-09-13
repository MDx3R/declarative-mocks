"""Smoke tests for the dmock package."""

from __future__ import annotations

import dmock


def test_package_importable() -> None:
    """The dmock package must be importable."""
    assert dmock.__doc__ is not None
