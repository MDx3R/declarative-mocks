"""Drop mocks in this suite before the plugin verifies the call phase."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from dmock._registry import MockRegistry


if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.runner import CallInfo


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(call: CallInfo[None]) -> Generator[None]:
    """Clear the registry before the plugin's call-phase verify.

    Yields:
        Control back to the pytest runner.
    """
    if call.when == "call":
        MockRegistry.clear()
    yield
