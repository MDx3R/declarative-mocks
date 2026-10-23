"""Plugin tests. No registry-clearing fixture: teardown verifies these mocks."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pytest

from dmock import (
    Anything,
    AnythingOfType,
    DeclarativeMock,
    GreaterThan,
    Regex,
    in_order,
)


pytest_plugins = ["pytester"]


class Billing(ABC):
    @abstractmethod
    def quote(self, sku: str) -> int: ...

    @abstractmethod
    def charge(self, sku: str, amount: int) -> str: ...

    @abstractmethod
    def notify(self, address: str) -> None: ...


class TestPluginVerifiesLibraryBehavior:
    def test_matchers_and_in_order(self) -> None:
        # Arrange
        billing = DeclarativeMock(Billing)
        quoted = billing.expect("quote", Regex(r"^SKU-")).returns(15).once()
        charged = (
            billing.expect("charge", "SKU-1", GreaterThan(0)).returns("paid").once()
        )
        notified = billing.expect("notify", AnythingOfType(str)).returns(None).once()
        in_order(quoted, charged, notified)

        # Act
        quote = billing.quote("SKU-1")
        payment = billing.charge("SKU-1", quote)
        billing.notify("ada@example.com")

        # Assert
        assert quote == 15
        assert payment == "paid"

    def test_raises_with_anything_matcher(self) -> None:
        # Arrange
        billing = DeclarativeMock(Billing)
        billing.expect("quote", Anything()).raises(LookupError).once()

        # Act & Assert
        with pytest.raises(LookupError):
            billing.quote("missing")

    def test_next_case_is_not_failed_by_the_previous_mock(self) -> None:
        # Arrange
        billing = DeclarativeMock(Billing)
        billing.expect("quote", "SKU-2").returns(1).once()

        # Act
        result = billing.quote("SKU-2")

        # Assert
        assert result == 1


class TestPluginReportsTheTest:
    def test_unmet_expectation_fails_the_test(self, pytester: pytest.Pytester) -> None:
        # Arrange
        pytester.makepyfile(
            """
            from abc import ABC

            from dmock import AnythingOfType, DeclarativeMock, GreaterThan, in_order

            class Billing(ABC):
                def quote(self, sku: str) -> int: ...
                def charge(self, sku: str, amount: int) -> str: ...

            def test_forgets_to_charge() -> None:
                billing = DeclarativeMock(Billing)
                quoted = billing.expect("quote", AnythingOfType(str)).returns(10).once()
                charged = (
                    billing.expect("charge", "SKU-1", GreaterThan(0))
                    .returns("paid")
                    .once()
                )
                in_order(quoted, charged)
                billing.quote("SKU-1")
            """
        )

        # Act
        result = pytester.runpytest()

        # Assert
        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(["*Unsatisfied expectations*", "*charge*"])

    def test_satisfied_case_passes_and_does_not_leak(
        self, pytester: pytest.Pytester
    ) -> None:
        # Arrange
        pytester.makepyfile(
            """
            from dmock import DeclarativeMock, Regex

            class Billing:
                def quote(self, sku: str) -> int: ...

            def test_unmet_quote() -> None:
                billing = DeclarativeMock(Billing)
                billing.expect("quote", Regex(r"^SKU-")).returns(1).once()

            def test_later_quote_is_independent() -> None:
                billing = DeclarativeMock(Billing)
                billing.expect("quote", "SKU-9").returns(1).once()
                assert billing.quote("SKU-9") == 1
            """
        )

        # Act
        result = pytester.runpytest()

        # Assert
        result.assert_outcomes(failed=1, passed=1)

    def test_existing_failure_is_not_replaced(self, pytester: pytest.Pytester) -> None:
        # Arrange
        pytester.makepyfile(
            """
            from dmock import DeclarativeMock

            class Billing:
                def quote(self, sku: str) -> int: ...

            def test_assert_fails_before_verify() -> None:
                billing = DeclarativeMock(Billing)
                billing.expect("quote", "SKU-1").returns(1).once()
                assert False
            """
        )

        # Act
        result = pytester.runpytest()

        # Assert
        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(["*AssertionError*"])
        assert "Unsatisfied expectations" not in result.stdout.str()

    def test_failed_teardown_does_not_affect_the_next_test(
        self, pytester: pytest.Pytester
    ) -> None:
        # Arrange
        pytester.makepyfile(
            """
            import pytest

            from dmock import DeclarativeMock

            class Billing:
                def quote(self, sku: str) -> int: ...

            @pytest.fixture
            def unmet_after_the_call():
                yield
                billing = DeclarativeMock(Billing)
                billing.expect("quote", "left").returns(1).once()

            def test_teardown_finds_the_unmet_mock(unmet_after_the_call: None) -> None:
                assert unmet_after_the_call is None

            def test_following_quote_passes() -> None:
                billing = DeclarativeMock(Billing)
                billing.expect("quote", "SKU-9").returns(1).once()
                assert billing.quote("SKU-9") == 1
            """
        )

        # Act
        result = pytester.runpytest("-v")

        # Assert
        result.assert_outcomes(passed=2, errors=1)
        result.stdout.fnmatch_lines(
            [
                "*test_teardown_finds_the_unmet_mock* PASSED*",
                "*test_teardown_finds_the_unmet_mock* ERROR*",
                "*test_following_quote_passes* PASSED*",
                "*ERROR at teardown of test_teardown_finds_the_unmet_mock*",
                "*Unsatisfied expectations*",
            ]
        )
