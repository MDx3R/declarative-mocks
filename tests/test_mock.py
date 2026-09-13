"""Integration tests for DeclarativeMock."""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from unittest.mock import MagicMock, Mock, NonCallableMagicMock

import pytest

from dmock import (
    ANY_ARGS,
    ANY_KWARGS,
    Anything,
    AnythingOfType,
    ConfigurationError,
    DeclarativeMock,
    MatchedBy,
    UnexpectedCallError,
    UnsatisfiedExpectationError,
    in_order,
)
from dmock._exceptions import (
    BlockedCallError,
    NoMatchingCallError,
    UnregisteredCallError,
)


# ---------------------------------------------------------------------------
# Spec fixture
# ---------------------------------------------------------------------------


class MyService(ABC):
    @abstractmethod
    def process_order(self, order_id: int) -> str: ...
    @abstractmethod
    async def aprocess_order(self, order_id: int) -> str: ...
    @abstractmethod
    def do_something(self) -> str: ...
    @abstractmethod
    def greet(self, name: str) -> str: ...

    @property
    def value(self) -> int:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Basic dispatch
# ---------------------------------------------------------------------------


class TestBasicDispatch:
    def test_returns_configured_value(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 123).returns("ok")

        # Act
        result = mock.process_order(123)

        # Assert
        assert result == "ok"

    async def test_async_returns_configured_value(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", 123).returns("ok")

        # Act
        result = await mock.aprocess_order(123)

        # Assert
        assert result == "ok"

    def test_raises_exception_instance(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").raises(ValueError("boom"))

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            mock.do_something()

    def test_raises_exception_type(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").raises(ValueError)

        # Act & Assert
        with pytest.raises(ValueError, match=r".*"):
            mock.do_something()

    def test_runs_callable_receives_call_args(self) -> None:
        # Arrange
        received: list[object] = []

        def capture(name: object) -> None:
            received.append(name)

        mock = DeclarativeMock(MyService)
        mock.expect("greet", Anything()).runs(capture)

        # Act
        mock.greet("hi")

        # Assert
        assert received == ["hi"]

    def test_runs_returns_callable_result(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("greet", Anything()).runs(
            lambda name: name.upper()  # pyright: ignore
        )

        # Act
        result = mock.greet("hi")

        # Assert
        assert result == "HI"

    def test_default_outcome_delegates_to_mock(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something")

        # Act
        result = mock.do_something()

        # Assert
        assert isinstance(result, (Mock, MagicMock, NonCallableMagicMock))

    def test_chained_returns_consumed_in_order(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("a").returns("b")

        # Act
        first = mock.do_something()
        second = mock.do_something()

        # Assert
        assert first == "a"
        assert second == "b"

    def test_last_outcome_repeats_beyond_list(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("a").returns("b").at_least(1)

        # Act
        first = mock.do_something()
        second = mock.do_something()
        third = mock.do_something()

        # Assert
        assert first == "a"
        assert second == "b"
        assert third == "b"


# ---------------------------------------------------------------------------
# Whitelist proxy
# ---------------------------------------------------------------------------


class TestWhitelistProxy:
    def test_call_without_expect_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.process_order(1)

    def test_attribute_access_without_expect_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            _ = mock.process_order

    def test_nonexistent_attr_raises_attribute_error(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act & Assert
        with pytest.raises(AttributeError):
            _ = mock.nonexistent

    def test_repr_works_without_expect(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act
        result = repr(mock)

        # Assert
        assert "MyService" in result

    def test_dunder_passthrough_via_getattr(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act
        cls = mock.__class__

        # Assert
        assert cls is not None


# ---------------------------------------------------------------------------
# Order and selection (per-name)
# ---------------------------------------------------------------------------


class TestOrderAndSelection:
    def test_first_matching_non_exhausted_wins(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("one")
        mock.expect("process_order", 2).returns("two")

        # Act
        two = mock.process_order(2)
        one = mock.process_order(1)

        # Assert
        assert two == "two"
        assert one == "one"

    def test_exhausted_expectation_skipped(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("first").once()
        mock.expect("process_order", 1).returns("second").once()

        # Act
        first = mock.process_order(1)
        second = mock.process_order(1)

        # Assert
        assert first == "first"
        assert second == "second"

    def test_order_same_args_registration_order(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("alpha").once()
        mock.expect("do_something").returns("beta").once()

        # Act
        first = mock.do_something()
        second = mock.do_something()

        # Assert
        assert first == "alpha"
        assert second == "beta"

    def test_never_blocks_matching_call(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").never()

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.do_something()

    def test_never_after_once_guards_extra_calls(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.expect("do_something").never()

        # Act
        result = mock.do_something()

        # Assert
        assert result == "ok"

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.do_something()

    def test_different_methods_independent_order(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("processed")
        mock.expect("do_something").returns("done")

        # Act
        done = mock.do_something()
        processed = mock.process_order(1)

        # Assert
        assert done == "done"
        assert processed == "processed"


# ---------------------------------------------------------------------------
# Unexpected calls (with expectations registered)
# ---------------------------------------------------------------------------


class TestUnexpectedCallsWithExpectations:
    def test_unmatched_args_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 99).returns("x")

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.process_order(1)

    def test_all_exhausted_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.do_something()


# ---------------------------------------------------------------------------
# Error diagnostics
# ---------------------------------------------------------------------------


class TestErrorDiagnostics:
    def test_unregistered_name(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            mock.do_something()
        assert type(exc_info.value) is UnregisteredCallError
        assert str(exc_info.value) == (
            "Unexpected call: 'do_something' has no registered expectation."
        )

    def test_args_mismatch_lists_candidate(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 99).returns("x")

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            mock.process_order(1)
        assert type(exc_info.value) is NoMatchingCallError
        assert str(exc_info.value) == (
            "Unexpected call: 'process_order' called with args=(1,), kwargs={} "
            "- no matching non-exhausted expectation.\n"
            "Candidates:\n"
            "  Expectation(process_order(99)) - args mismatch\n"
            "Call history:\n"
            "  1. process_order(1)"
        )

    def test_exhausted_lists_candidate_with_counts(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            mock.do_something()
        assert type(exc_info.value) is NoMatchingCallError
        assert str(exc_info.value) == (
            "Unexpected call: 'do_something' called with args=(), kwargs={} "
            "- no matching non-exhausted expectation.\n"
            "Candidates:\n"
            "  Expectation(do_something()) - exhausted (1/1 calls)\n"
            "Call history:\n"
            "  1. do_something()\n"
            "  2. do_something()"
        )

    def test_multiple_candidates_mix_exhausted_and_mismatch(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("a").once()
        mock.expect("process_order", 2).returns("b")
        mock.process_order(1)

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            mock.process_order(3)
        assert type(exc_info.value) is NoMatchingCallError
        assert str(exc_info.value) == (
            "Unexpected call: 'process_order' called with args=(3,), kwargs={} "
            "- no matching non-exhausted expectation.\n"
            "Candidates:\n"
            "  Expectation(process_order(1)) - exhausted (1/1 calls)\n"
            "  Expectation(process_order(2)) - args mismatch\n"
            "Call history:\n"
            "  1. process_order(1)\n"
            "  2. process_order(3)"
        )

    def test_blocked_by_prerequisite_uses_shared_format(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        init = mock.expect("do_something").returns("a").once()
        mock.expect("process_order", 1).returns("b").not_before(init)

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            mock.process_order(1)
        assert type(exc_info.value) is BlockedCallError
        assert str(exc_info.value) == (
            "Out-of-order call: 'process_order' called with args=(1,), kwargs={}\n"
            "  Expectation(process_order(1)) - blocked by do_something "
            "(expected exactly 1 call(s), got 0)\n"
            "Call history:\n"
            "  1. process_order(1)"
        )

    def test_verify_reports_expected_and_got(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").twice()
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnsatisfiedExpectationError) as exc_info:
            mock.verify()
        assert str(exc_info.value) == (
            "Unsatisfied expectations:\n"
            "  Expectation(do_something()) - expected exactly 2 call(s), got 1\n"
            "Call history:\n"
            "  1. do_something()"
        )

    def test_verify_at_least_uses_quantifier_description(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").at_least(2)
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnsatisfiedExpectationError) as exc_info:
            mock.verify()
        assert str(exc_info.value) == (
            "Unsatisfied expectations:\n"
            "  Expectation(do_something()) - expected at least 2 call(s), got 1\n"
            "Call history:\n"
            "  1. do_something()"
        )


# ---------------------------------------------------------------------------
# Quantifier verification via verify()
# ---------------------------------------------------------------------------


class TestAssertExpectations:
    def test_all_satisfied_passes(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.do_something()

        # Act
        mock.verify()

    def test_unsatisfied_once_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()

        # Act & Assert
        with pytest.raises(UnsatisfiedExpectationError):
            mock.verify()

    def test_maybe_uncalled_passes(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").maybe()

        # Act
        mock.verify()

    def test_never_uncalled_passes(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").never()

        # Act
        mock.verify()

    def test_at_least_not_met_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").at_least(2)
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnsatisfiedExpectationError):
            mock.verify()

    def test_between_satisfied(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").between(1, 3)
        mock.do_something()
        mock.do_something()

        # Act
        mock.verify()

    def test_mixed_satisfied_and_unsatisfied_lists_all(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.expect("process_order", 1).returns("x").once()
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnsatisfiedExpectationError) as exc_info:
            mock.verify()
        assert "process_order" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Matchers through dispatch
# ---------------------------------------------------------------------------


class TestMatchersThroughDispatch:
    @pytest.mark.parametrize("order_id", [42, 0])
    def test_anything_matcher_dispatches(self, order_id: int) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", Anything()).returns("matched").at_least(1)

        # Act
        result = mock.process_order(order_id)

        # Assert
        assert result == "matched"

    @pytest.mark.parametrize("order_id", [1, 2])
    def test_any_args_any_kwargs_dispatches(self, order_id: int) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", ANY_ARGS, ANY_KWARGS).returns("wild").at_least(1)

        # Act
        result = mock.process_order(order_id)

        # Assert
        assert result == "wild"

    def test_matched_by_dispatches(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect(
            "process_order", MatchedBy(lambda x: isinstance(x, int) and x > 0)
        ).returns("positive")

        # Act
        result = mock.process_order(5)

        # Assert
        assert result == "positive"

    def test_anything_of_type_dispatches(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("greet", AnythingOfType(str)).returns("hello")

        # Act
        result = mock.greet("world")

        # Assert
        assert result == "hello"


# ---------------------------------------------------------------------------
# Multiple methods
# ---------------------------------------------------------------------------


class TestMultipleMethods:
    def test_independent_methods_expectations(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("p")
        mock.expect("do_something").returns("d")

        # Act
        processed = mock.process_order(1)
        done = mock.do_something()

        # Assert
        assert processed == "p"
        assert done == "d"

    def test_expect_nonexistent_method_raises_attribute_error(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act & Assert
        with pytest.raises(AttributeError):
            mock.expect("nonexistent")


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


class TestRepr:
    def test_repr_contains_spec_name(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act
        result = repr(mock)

        # Assert
        assert result == "DeclarativeMock(spec=MyService)"


# ---------------------------------------------------------------------------
# Reserved DSL names
# ---------------------------------------------------------------------------


class TestReservedDslNames:
    @pytest.mark.parametrize("name", ["expect", "property", "verify"])
    def test_spec_attribute_matching_dsl_raises(self, name: str) -> None:
        # Arrange
        spec = type("CollidingSpec", (), {name: lambda: None})

        # Act & Assert
        with pytest.raises(ConfigurationError, match=name):
            DeclarativeMock(spec)

    def test_ordinary_spec_still_constructs(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok")

        # Act
        result = mock.do_something()

        # Assert
        assert result == "ok"


# ---------------------------------------------------------------------------
# Async dispatch
# ---------------------------------------------------------------------------


class TestAsyncDispatch:
    def test_async_method_is_coroutine_function(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", 1).returns("ok")

        # Act
        result = inspect.iscoroutinefunction(mock.aprocess_order)

        # Assert
        assert result is True

    async def test_async_raises_exception(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", 123).raises(ValueError("async-boom"))

        # Act & Assert
        with pytest.raises(ValueError, match="async-boom"):
            await mock.aprocess_order(123)

    async def test_async_runs_sync_callable(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", Anything()).runs(
            lambda x: f"sync-{x}"  # pyright: ignore
        )

        # Act
        result = await mock.aprocess_order(7)

        # Assert
        assert result == "sync-7"

    async def test_async_runs_async_callable(self) -> None:
        # Arrange
        async def async_fn(x: object) -> str:
            return f"async-{x}"

        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", Anything()).runs(async_fn)

        # Act
        result = await mock.aprocess_order(9)

        # Assert
        assert result == "async-9"

    async def test_async_default_outcome(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", 1)

        # Act
        result = await mock.aprocess_order(1)

        # Assert
        assert isinstance(result, (Mock, MagicMock, NonCallableMagicMock))

    async def test_async_chained_returns(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", ANY_ARGS).returns("first").returns("second")

        # Act
        first = await mock.aprocess_order(1)
        second = await mock.aprocess_order(1)

        # Assert
        assert first == "first"
        assert second == "second"

    async def test_async_whitelist_blocks_without_expect(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            await mock.aprocess_order(1)


# ---------------------------------------------------------------------------
# Property stubs
# ---------------------------------------------------------------------------


class TestPropertySupport:
    def test_basic_property_access_returns_value(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.property("value", 123)

        # Act
        result = mock.value

        # Assert
        assert result == 123

    def test_property_with_none_value(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.property("value", None)

        # Act
        result = mock.value

        # Assert
        assert result is None

    def test_property_nonspec_name_raises_attribute_error(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)

        # Act & Assert
        with pytest.raises(AttributeError):
            mock.property("nonexistent", 42)

    def test_property_does_not_require_call(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.property("value", 99)

        # Act
        result = mock.value

        # Assert
        assert result == 99

    def test_verify_passes_with_only_properties(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.property("value", 7)

        # Act
        mock.verify()

    def test_property_after_expect_same_name_raises_configuration_error(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok")

        # Act & Assert
        with pytest.raises(ConfigurationError):
            mock.property("do_something", "stub")

    def test_expect_after_property_same_name_raises_configuration_error(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.property("value", 1)

        # Act & Assert
        with pytest.raises(ConfigurationError):
            mock.expect("value")

    def test_multiple_properties_on_different_names(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        mock.property("value", 42)
        mock.expect("do_something").returns("done")

        # Act
        value = mock.value
        done = mock.do_something()

        # Assert
        assert value == 42
        assert done == "done"


# ---------------------------------------------------------------------------
# not_before
# ---------------------------------------------------------------------------


class TestNotBefore:
    def test_not_before_satisfied_allows_call(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        mock.expect("process_order", 1).returns("b").not_before(a)

        # Act
        mock.do_something()
        result = mock.process_order(1)

        # Assert
        assert result == "b"

    def test_not_before_unsatisfied_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        mock.expect("process_order", 1).returns("b").not_before(a)

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="do_something"):
            mock.process_order(1)

    def test_not_before_multiple_deps_all_satisfied(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        b = mock.expect("greet", "hi").returns("b").once()
        mock.expect("process_order", 1).returns("c").not_before(a, b)

        # Act
        mock.do_something()
        mock.greet("hi")
        result = mock.process_order(1)

        # Assert
        assert result == "c"

    def test_not_before_multiple_deps_one_unsatisfied(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        b = mock.expect("greet", "hi").returns("b").once()
        mock.expect("process_order", 1).returns("c").not_before(a, b)
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="greet"):
            mock.process_order(1)

    def test_not_before_chain_transitive(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        b = mock.expect("greet", "hi").returns("b").once().not_before(a)
        mock.expect("process_order", 1).returns("c").not_before(b)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.process_order(1)

        # Act
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.process_order(1)

        # Act
        mock.greet("hi")
        result = mock.process_order(1)

        # Assert
        assert result == "c"

    def test_not_before_cross_mock(self) -> None:
        # Arrange
        mock1 = DeclarativeMock(MyService)
        mock2 = DeclarativeMock(MyService)
        a = mock1.expect("do_something").returns("a").once()
        mock2.expect("process_order", 1).returns("b").not_before(a)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock2.process_order(1)

        # Act
        mock1.do_something()
        result = mock2.process_order(1)

        # Assert
        assert result == "b"

    def test_not_before_maybe_uncalled_satisfies_dep(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").maybe()
        mock.expect("process_order", 1).returns("b").not_before(a)

        # Act
        result = mock.process_order(1)

        # Assert
        assert result == "b"

    def test_not_before_never_uncalled_satisfies_dep(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").never()
        mock.expect("process_order", 1).returns("b").not_before(a)

        # Act
        result = mock.process_order(1)

        # Assert
        assert result == "b"

    def test_not_before_never_violated_blocks_dep(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").never()
        mock.expect("process_order", 1).returns("b").not_before(a)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock.do_something()

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="do_something"):
            mock.process_order(1)

    def test_not_before_cycle_raises_config_error(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a")
        b = mock.expect("process_order", 1).returns("b")
        a.not_before(b)

        # Act & Assert
        with pytest.raises(ConfigurationError, match=r"[Cc]ycle"):
            b.not_before(a)

    def test_not_before_self_dep_raises_config_error(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a")

        # Act & Assert
        with pytest.raises(ConfigurationError, match=r"[Cc]ycle"):
            a.not_before(a)

    def test_not_before_returns_self_for_chaining(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        b = mock.expect("process_order", 1)

        # Act
        result = b.not_before(a).returns("b")

        # Assert
        assert result is b

    def test_not_before_does_not_affect_verify(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        mock.expect("process_order", 1).returns("b").once().not_before(a)

        # Act & Assert
        with pytest.raises(UnsatisfiedExpectationError):
            mock.verify()


# ---------------------------------------------------------------------------
# in_order
# ---------------------------------------------------------------------------


class TestInOrder:
    def test_in_order_enforces_sequence(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        b = mock.expect("process_order", 1).returns("b").once()
        c = mock.expect("greet", "hi").returns("c").once()
        in_order(a, b, c)

        # Act
        mock.do_something()
        mock.process_order(1)
        result = mock.greet("hi")

        # Assert
        assert result == "c"

    def test_in_order_violation_raises(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()
        b = mock.expect("process_order", 1).returns("b").once()
        c = mock.expect("greet", "hi").returns("c").once()
        in_order(a, b, c)
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="process_order"):
            mock.greet("hi")

    def test_in_order_single_arg_noop(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").once()

        # Act
        in_order(a)

        # Assert
        assert list(a.requires) == []

    def test_in_order_empty_noop(self) -> None:
        in_order()

    def test_in_order_cross_mock(self) -> None:
        # Arrange
        mock1 = DeclarativeMock(MyService)
        mock2 = DeclarativeMock(MyService)
        a = mock1.expect("do_something").returns("a").once()
        b = mock2.expect("process_order", 1).returns("b").once()
        in_order(a, b)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            mock2.process_order(1)

        # Act
        mock1.do_something()
        result = mock2.process_order(1)

        # Assert
        assert result == "b"

    def test_in_order_with_quantifiers(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        a = mock.expect("do_something").returns("a").times(2)
        b = mock.expect("process_order", 1).returns("b").once()
        in_order(a, b)

        # Act
        mock.do_something()

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="do_something"):
            mock.process_order(1)

        # Act
        mock.do_something()
        result = mock.process_order(1)

        # Assert
        assert result == "b"
