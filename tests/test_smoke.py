"""Smoke tests until the public API is implemented."""

from __future__ import annotations

import dmock


def test_package_importable() -> None:
    """The dmock package must be importable."""
    assert dmock.__doc__ is not None
