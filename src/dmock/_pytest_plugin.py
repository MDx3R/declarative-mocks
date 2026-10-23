"""Verify declarative mocks from pytest's test report hook."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from _pytest._code import ExceptionInfo

from dmock._registry import MockRegistry


if TYPE_CHECKING:
    from collections.abc import Generator

    from _pytest.nodes import Item
    from _pytest.reports import TestReport
    from _pytest.runner import CallInfo


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo[None]) -> Generator[None]:
    """Verify mocks when the call finishes, and again after teardown.

    On the call phase a failed ``verify`` becomes the test failure. On the
    teardown phase every mock still registered — including ones created while
    fixtures were finalizing — is verified and dropped, and a failed
    ``verify`` is recorded on that phase's report. An exception the phase
    already raised stays in place (``call.excinfo`` is replaced only when it
    is empty). ``MockRegistry.teardown`` empties the registry before
    ``verify``, so a failure cannot leak into the next test.

    Args:
        item: Test item for which the hook is being called.
        call: Information about the current call phase.

    Yields:
        Control back to the pytest runner.
    """
    del item
    if call.when in {"call", "teardown"}:
        try:
            MockRegistry.teardown()
        except BaseException:
            call.excinfo = call.excinfo or ExceptionInfo.from_current()

    _report: TestReport | None = yield
