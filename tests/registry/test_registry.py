"""Tests for MockRegistry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from unittest.mock import patch

import pytest

from dmock import UnsatisfiedExpectationError
from dmock._mock import DeclarativeMock
from dmock._registry import MockRegistry


class _Service(ABC):
    @abstractmethod
    def do_something(self) -> str: ...


class TestMockRegistry:
    def test_init_registers_the_mock(self) -> None:
        # Arrange
        spec = _Service

        # Act
        mock = DeclarativeMock(spec)

        # Assert
        assert MockRegistry().mocks == [mock]

    def test_add_appends_the_mock(self) -> None:
        # Arrange
        mock = DeclarativeMock(_Service)

        # Act
        MockRegistry.add(mock)

        # Assert
        assert MockRegistry().mocks == [mock, mock]

    def test_clear_drops_mocks_without_verifying(self) -> None:
        # Arrange
        _ = DeclarativeMock(_Service)

        # Act
        MockRegistry.clear()

        # Assert
        assert MockRegistry().mocks == []

    def test_verify_is_still_callable_manually(self) -> None:
        # Arrange
        mock = DeclarativeMock(_Service)
        mock.expect("do_something").returns("ok").once()
        mock.do_something()

        # Act
        mock.verify()

        # Assert
        assert mock in MockRegistry().mocks

    def test_manual_verify_still_raises_when_unmet(self) -> None:
        # Arrange
        mock = DeclarativeMock(_Service)
        mock.expect("do_something").returns("ok").once()

        # Act & Assert
        with pytest.raises(UnsatisfiedExpectationError):
            mock.verify()

    def test_teardown_verifies_and_clears(self) -> None:
        # Arrange
        mock = DeclarativeMock(_Service)
        mock.expect("do_something").returns("ok").once()
        mock.do_something()

        # Act
        MockRegistry.teardown()

        # Assert
        assert MockRegistry().mocks == []

    def test_second_teardown_is_a_noop(self) -> None:
        # Arrange
        MockRegistry.teardown()

        # Act
        MockRegistry.teardown()

        # Assert
        assert MockRegistry().mocks == []


class TestMockRegistryObservations:
    def test_teardown_clears_before_verify_and_stops_on_error(self) -> None:
        # Arrange
        first = DeclarativeMock(_Service)
        second = DeclarativeMock(_Service)
        first.expect("do_something").returns("ok").once()
        second.expect("do_something").returns("ok").once()
        observed_sizes: list[int] = []
        verified: list[int] = []

        def observe(self: DeclarativeMock[_Service]) -> None:
            observed_sizes.append(len(MockRegistry().mocks))
            verified.append(id(self))
            raise UnsatisfiedExpectationError((), ())

        # Act & Assert
        with (
            patch.object(DeclarativeMock, "verify", observe),
            pytest.raises(UnsatisfiedExpectationError),
        ):
            MockRegistry.teardown()

        assert observed_sizes == [0]
        assert verified == [id(first)]
        assert MockRegistry().mocks == []

    def test_mock_created_during_verify_is_outside_the_snapshot(self) -> None:
        # Arrange
        original = DeclarativeMock(_Service)
        original.expect("do_something").returns("ok").once()
        seen: list[tuple[object, ...]] = []
        created: list[DeclarativeMock[_Service]] = []

        def observe(mock: DeclarativeMock[_Service]) -> None:
            seen.append(tuple(MockRegistry().mocks))
            created.append(DeclarativeMock(_Service))
            assert mock is original
            raise UnsatisfiedExpectationError((), ())

        # Act
        with (
            patch.object(DeclarativeMock, "verify", observe),
            pytest.raises(UnsatisfiedExpectationError),
        ):
            MockRegistry.teardown()

        # Assert
        assert seen == [()]
        assert original not in MockRegistry().mocks
        assert MockRegistry().mocks == created

        # Act
        MockRegistry.teardown()

        # Assert
        assert MockRegistry().mocks == []
