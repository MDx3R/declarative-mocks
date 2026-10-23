"""Registry of declarative mocks verified at the end of a test."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar


if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from dmock._mock import DeclarativeMock


class MockRegistry:
    """Live mocks to verify when a test finishes.

    :class:`~dmock.DeclarativeMock` registers itself on construction.
    :meth:`teardown` copies that list, replaces it with an empty one, then
    calls :meth:`~dmock.DeclarativeMock.verify` on the copy. Clearing first
    means a failed verify cannot leak mocks into the next test. A later
    :meth:`teardown` with nothing registered does nothing.

    :meth:`clear` drops registered mocks without verifying them. Tests that
    leave expectations unmet on purpose use it so a later ``teardown`` does
    not fail them again.

    Verification is fail-fast. If ``verify`` raises, mocks later in the copy
    are not checked. They have already been dropped from the registry.
    """

    _mocks: ClassVar[list[DeclarativeMock[Any]]] = []

    @property
    def mocks(self) -> Sequence[DeclarativeMock[Any]]:
        """Return a copy of the mocks registered right now.

        Read it from any instance (``MockRegistry().mocks``). The copy is a
        new list, so a later :meth:`add`, :meth:`clear`, or :meth:`teardown`
        does not change it.
        """
        return list(self._mocks)

    @classmethod
    def add(cls, mock: DeclarativeMock[Any]) -> None:
        """Remember `mock` until the next :meth:`teardown`."""
        cls._mocks.append(mock)

    @classmethod
    def clear(cls) -> None:
        """Drop every registered mock without calling ``verify``."""
        cls._mocks = []

    @classmethod
    def teardown(cls) -> None:
        """Verify every registered mock and forget them.

        Raises:
            UnsatisfiedExpectationError: A registered mock is unmet.
                Remaining mocks in this batch are not verified.
        """
        mocks = list(cls._mocks)
        cls._mocks = []

        for mock in mocks:
            mock.verify()
