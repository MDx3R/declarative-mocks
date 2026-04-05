"""Integration tests for DeclarativeMock."""

from __future__ import annotations

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
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 123).returns("ok")
        assert mock.process_order(123) == "ok"

    async def test_async_returns_configured_value(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", 123).returns("ok")
        assert await mock.aprocess_order(123) == "ok"

    def test_raises_exception_instance(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").raises(ValueError("boom"))
        with pytest.raises(ValueError, match="boom"):
            mock.do_something()

    def test_raises_exception_type(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").raises(ValueError)
        with pytest.raises(ValueError, match=r".*"):
            mock.do_something()

    def test_runs_callable_receives_call_args(self) -> None:
        received: list[object] = []

        def capture(name: object) -> None:
            received.append(name)

        mock = DeclarativeMock(MyService)
        mock.expect("greet", Anything()).runs(capture)
        mock.greet("hi")
        assert received == ["hi"]

    def test_runs_returns_callable_result(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("greet", Anything()).runs(
            lambda name: name.upper()  # pyright: ignore
        )
        assert mock.greet("hi") == "HI"

    def test_default_outcome_delegates_to_mock(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something")
        result = mock.do_something()
        # DefaultOutcome: delegates to internal Mock(spec=...) child, which is a Mock
        assert isinstance(result, (Mock, MagicMock, NonCallableMagicMock))

    def test_chained_returns_consumed_in_order(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("a").returns("b")
        assert mock.do_something() == "a"
        assert mock.do_something() == "b"

    def test_last_outcome_repeats_beyond_list(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("a").returns("b").at_least(1)
        assert mock.do_something() == "a"
        assert mock.do_something() == "b"
        assert mock.do_something() == "b"


# ---------------------------------------------------------------------------
# Whitelist proxy
# ---------------------------------------------------------------------------


class TestWhitelistProxy:
    def test_call_without_expect_raises(self) -> None:
        mock = DeclarativeMock(MyService)
        with pytest.raises(UnexpectedCallError):
            mock.process_order(1)

    def test_attribute_access_without_expect_raises(self) -> None:
        mock = DeclarativeMock(MyService)
        with pytest.raises(UnexpectedCallError):
            _ = mock.process_order

    def test_nonexistent_attr_raises_attribute_error(self) -> None:
        mock = DeclarativeMock(MyService)
        with pytest.raises(AttributeError):
            _ = mock.nonexistent

    def test_repr_works_without_expect(self) -> None:
        mock = DeclarativeMock(MyService)
        r = repr(mock)
        assert "MyService" in r

    def test_dunder_passthrough_via_getattr(self) -> None:
        mock = DeclarativeMock(MyService)
        # __class__ is on the Mock itself; must not raise UnexpectedCallError
        cls = mock.__class__
        assert cls is not None


# ---------------------------------------------------------------------------
# Order and selection (per-name)
# ---------------------------------------------------------------------------


class TestOrderAndSelection:
    def test_first_matching_non_exhausted_wins(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("one")
        mock.expect("process_order", 2).returns("two")
        assert mock.process_order(2) == "two"
        assert mock.process_order(1) == "one"

    def test_exhausted_expectation_skipped(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("first").once()
        mock.expect("process_order", 1).returns("second").once()
        assert mock.process_order(1) == "first"
        assert mock.process_order(1) == "second"

    def test_order_same_args_registration_order(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("alpha").once()
        mock.expect("do_something").returns("beta").once()
        assert mock.do_something() == "alpha"
        assert mock.do_something() == "beta"

    def test_never_blocks_matching_call(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").never()
        with pytest.raises(UnexpectedCallError):
            mock.do_something()

    def test_never_after_once_guards_extra_calls(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.expect("do_something").never()
        assert mock.do_something() == "ok"
        with pytest.raises(UnexpectedCallError):
            mock.do_something()

    def test_different_methods_independent_order(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("processed")
        mock.expect("do_something").returns("done")
        # do_something registered second but called first — must be fine
        assert mock.do_something() == "done"
        assert mock.process_order(1) == "processed"


# ---------------------------------------------------------------------------
# Unexpected calls (with expectations registered)
# ---------------------------------------------------------------------------


class TestUnexpectedCallsWithExpectations:
    def test_unmatched_args_raises(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 99).returns("x")
        with pytest.raises(UnexpectedCallError):
            mock.process_order(1)

    def test_all_exhausted_raises(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.do_something()
        with pytest.raises(UnexpectedCallError):
            mock.do_something()


# ---------------------------------------------------------------------------
# Quantifier verification via assert_expectations()
# ---------------------------------------------------------------------------


class TestAssertExpectations:
    def test_all_satisfied_passes(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.do_something()
        mock.assert_expectations()  # must not raise

    def test_unsatisfied_once_raises(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        with pytest.raises(UnsatisfiedExpectationError):
            mock.assert_expectations()

    def test_maybe_uncalled_passes(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").maybe()
        mock.assert_expectations()  # must not raise

    def test_never_uncalled_passes(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").never()
        mock.assert_expectations()  # must not raise

    def test_at_least_not_met_raises(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").at_least(2)
        mock.do_something()
        with pytest.raises(UnsatisfiedExpectationError):
            mock.assert_expectations()

    def test_between_satisfied(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").between(1, 3)
        mock.do_something()
        mock.do_something()
        mock.assert_expectations()  # must not raise

    def test_mixed_satisfied_and_unsatisfied_lists_all(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok").once()
        mock.expect("process_order", 1).returns("x").once()
        mock.do_something()
        # process_order not called → unsatisfied
        with pytest.raises(UnsatisfiedExpectationError) as exc_info:
            mock.assert_expectations()
        assert "process_order" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Matchers through dispatch
# ---------------------------------------------------------------------------


class TestMatchersThroughDispatch:
    def test_anything_matcher_dispatches(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", Anything()).returns("matched").at_least(1)
        assert mock.process_order(42) == "matched"
        assert mock.process_order(0) == "matched"

    def test_any_args_any_kwargs_dispatches(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", ANY_ARGS, ANY_KWARGS).returns("wild").at_least(1)
        assert mock.process_order(1) == "wild"
        assert mock.process_order(2) == "wild"

    def test_matched_by_dispatches(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect(
            "process_order", MatchedBy(lambda x: isinstance(x, int) and x > 0)
        ).returns("positive")
        assert mock.process_order(5) == "positive"

    def test_anything_of_type_dispatches(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("greet", AnythingOfType(str)).returns("hello")
        assert mock.greet("world") == "hello"


# ---------------------------------------------------------------------------
# Multiple methods
# ---------------------------------------------------------------------------


class TestMultipleMethods:
    def test_independent_methods_expectations(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("process_order", 1).returns("p")
        mock.expect("do_something").returns("d")
        assert mock.process_order(1) == "p"
        assert mock.do_something() == "d"

    def test_expect_nonexistent_method_raises_attribute_error(self) -> None:
        mock = DeclarativeMock(MyService)
        with pytest.raises(AttributeError):
            mock.expect("nonexistent")


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


class TestRepr:
    def test_repr_contains_spec_name(self) -> None:
        mock = DeclarativeMock(MyService)
        assert "MyService" in repr(mock)


# ---------------------------------------------------------------------------
# Async dispatch
# ---------------------------------------------------------------------------


class TestAsyncDispatch:
    async def test_async_raises_exception(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", 123).raises(ValueError("async-boom"))
        with pytest.raises(ValueError, match="async-boom"):
            await mock.aprocess_order(123)

    async def test_async_runs_sync_callable(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", Anything()).runs(
            lambda x: f"sync-{x}"  # pyright: ignore
        )
        assert await mock.aprocess_order(7) == "sync-7"

    async def test_async_runs_async_callable(self) -> None:
        async def async_fn(x: object) -> str:
            return f"async-{x}"

        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", Anything()).runs(async_fn)
        assert await mock.aprocess_order(9) == "async-9"

    async def test_async_default_outcome(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", 1)
        result = await mock.aprocess_order(1)
        assert isinstance(result, (Mock, MagicMock, NonCallableMagicMock))

    async def test_async_chained_returns(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("aprocess_order", ANY_ARGS).returns("first").returns("second")
        assert await mock.aprocess_order(1) == "first"
        assert await mock.aprocess_order(1) == "second"

    async def test_async_whitelist_blocks_without_expect(self) -> None:
        mock = DeclarativeMock(MyService)
        with pytest.raises(UnexpectedCallError):
            await mock.aprocess_order(1)


# ---------------------------------------------------------------------------
# Property stubs
# ---------------------------------------------------------------------------


class TestPropertySupport:
    def test_basic_property_access_returns_value(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.property("value", 123)
        assert mock.value == 123

    def test_property_with_none_value(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.property("value", None)
        assert mock.value is None

    def test_property_nonspec_name_raises_attribute_error(self) -> None:
        mock = DeclarativeMock(MyService)
        with pytest.raises(AttributeError):
            mock.property("nonexistent", 42)

    def test_property_does_not_require_call(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.property("value", 99)
        val = mock.value
        assert val == 99

    def test_assert_expectations_passes_with_only_properties(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.property("value", 7)
        mock.assert_expectations()  # must not raise

    def test_property_after_expect_same_name_raises_configuration_error(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.expect("do_something").returns("ok")
        with pytest.raises(ConfigurationError):
            mock.property("do_something", "stub")

    def test_expect_after_property_same_name_raises_configuration_error(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.property("value", 1)
        with pytest.raises(ConfigurationError):
            mock.expect("value")

    def test_multiple_properties_on_different_names(self) -> None:
        mock = DeclarativeMock(MyService)
        mock.property("value", 42)
        mock.expect("do_something").returns("done")
        assert mock.value == 42
        assert mock.do_something() == "done"
