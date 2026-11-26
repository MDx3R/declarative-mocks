"""Integration tests for DeclarativeSpy."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from dmock._check import Check
from dmock._exceptions import (
    BlockedCallError,
    ConfigurationError,
    DeclarativeMockError,
    NoMatchingCallError,
    UnexpectedCallError,
    UnsatisfiedObservationError,
)
from dmock._interaction import in_order
from dmock._matchers import (
    ANY_ARGS,
    ANY_KWARGS,
    Anything,
    AnythingOfType,
    LessThan,
    MatchedBy,
)
from dmock._mock import DeclarativeMock
from dmock._spy import DeclarativeSpy, dspy


# ---------------------------------------------------------------------------
# Object fixture
# ---------------------------------------------------------------------------


class MyService:
    def __init__(self) -> None:
        self.last_processed: int | None = None
        self.failed = False
        self.orders = iter(["ok", "fail", "fail"])

    def process_order(self, order_id: int) -> str:
        self.last_processed = order_id
        return next(self.orders)

    async def aprocess_order(self, order_id: int) -> str:
        self.last_processed = order_id
        return next(self.orders)

    async def ado_something(self) -> str:
        self.failed = True
        raise ValueError("async-boom")

    def do_something(self) -> str:
        self.failed = True
        raise ValueError("boom")

    def greet(self, name: str) -> str:
        return "hello"

    @property
    def value(self) -> int:
        return 999

    def __repr__(self) -> str:
        return "MyService()"


# ---------------------------------------------------------------------------
# dspy()
# ---------------------------------------------------------------------------


class TestDspyFactory:
    def test_returns_a_working_spy_of_the_object(self) -> None:
        # Arrange
        spy = dspy(MyService())
        spy.observe("process_order", 123).returns("ok")

        # Act
        result = spy.process_order(123)

        # Assert
        assert isinstance(spy, DeclarativeSpy)
        assert repr(spy) == "DeclarativeSpy(obj=MyService())"
        assert result == "ok"

    def test_dspy_on_class_raises_configuration_error(self) -> None:
        # Act & Assert
        with pytest.raises(ConfigurationError, match="has to be an instance"):
            dspy(MyService)

    def test_declarative_spy_on_class_raises_configuration_error(self) -> None:
        # Act & Assert
        with pytest.raises(ConfigurationError, match="has to be an instance"):
            DeclarativeSpy(MyService)


# ---------------------------------------------------------------------------
# Basic dispatch
# ---------------------------------------------------------------------------


class TestBasicDispatch:
    def test_returns_checks_configured_value(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe(MyService.process_order, 123).returns("ok")

        # Act
        result = spy.process_order(123)

        # Assert
        assert result == "ok"
        spy.verify()

    def test_returns_mismatch_raises_declarative_mock_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123).returns("wrong")

        # Act & Assert
        with pytest.raises(DeclarativeMockError):
            spy.process_order(123)

    def test_returns_checks_configured_condition(self) -> None:
        # Arrange
        svc = MyService()
        checked = False

        def capture(value: str) -> bool:
            nonlocal checked
            checked = True
            return svc.last_processed is not None and value == "ok"

        spy = DeclarativeSpy(svc)
        spy.observe("process_order", 123).returns("ok", condition=capture)

        # Act
        result = spy.process_order(123)

        # Assert
        assert result == "ok"
        assert checked

    def test_returns_condition_false_raises_declarative_mock_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123).returns("ok", condition=lambda _: False)

        # Act & Assert
        with pytest.raises(DeclarativeMockError):
            spy.process_order(123)

    async def test_async_returns_checks_configured_value(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("aprocess_order", 123).returns("ok")

        # Act
        result = await spy.aprocess_order(123)

        # Assert
        assert result == "ok"

    async def test_async_returns_checks_configured_condition(self) -> None:
        # Arrange
        svc = MyService()
        checked = False

        def capture(value: str) -> bool:
            nonlocal checked
            checked = True
            return svc.last_processed is not None and value == "ok"

        spy = DeclarativeSpy(svc)
        spy.observe("aprocess_order", 123).returns("ok", condition=capture)

        # Act
        result = await spy.aprocess_order(123)

        # Assert
        assert result == "ok"
        assert checked

    def test_raises_checks_exception_instance(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").raises(ValueError("boom"))

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            spy.do_something()

    def test_raises_exception_instance_message_mismatch_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").raises(ValueError("other"))

        # Act & Assert
        with pytest.raises(DeclarativeMockError):
            spy.do_something()

    def test_raises_checks_exception_type(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").raises(ValueError)

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            spy.do_something()

    def test_raises_exception_type_mismatch_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").raises(KeyError)

        # Act & Assert
        with pytest.raises(DeclarativeMockError):
            spy.do_something()

    def test_raises_checks_configured_condition(self) -> None:
        # Arrange
        svc = MyService()
        checked = False

        def capture(exc: BaseException) -> bool:
            nonlocal checked
            checked = True
            return svc.failed and isinstance(exc, ValueError)

        spy = DeclarativeSpy(svc)
        spy.observe("do_something").raises(ValueError, condition=capture)

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            spy.do_something()

        assert checked

    def test_raises_condition_false_raises_declarative_mock_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").raises(ValueError, condition=lambda _: False)

        # Act & Assert
        with pytest.raises(DeclarativeMockError):
            spy.do_something()

    def test_condition_checks_configured_condition(self) -> None:
        # Arrange
        svc = MyService()
        checked = False

        def capture(value: Any) -> bool:
            nonlocal checked
            checked = True
            return svc.last_processed is not None and value == "ok"

        spy = DeclarativeSpy(svc)
        spy.observe("process_order", 123).condition(capture)

        # Act
        result = spy.process_order(123)

        # Assert
        assert result == "ok"
        assert checked

    def test_condition_false_raises_declarative_mock_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123).condition(lambda _: False)

        # Act & Assert
        with pytest.raises(DeclarativeMockError):
            spy.process_order(123)

    def test_condition_accepts_composable_check(self) -> None:
        # Arrange
        def check(value: str) -> bool:
            return value == "ok"

        spy = DeclarativeSpy(MyService())
        is_ok = Check[Any](lambda v: isinstance(v, str)) & check
        spy.observe("process_order", 123).condition(is_ok)

        # Act
        result = spy.process_order(123)

        # Assert
        assert result == "ok"
        spy.verify()

    async def test_async_condition_checks_configured_condition(self) -> None:
        # Arrange
        svc = MyService()
        checked = False

        def capture(value: Any) -> bool:
            nonlocal checked
            checked = True
            return svc.last_processed is not None and value == "ok"

        spy = DeclarativeSpy(svc)
        spy.observe("aprocess_order", 123).condition(capture)

        # Act
        result = await spy.aprocess_order(123)

        # Assert
        assert result == "ok"
        assert checked

    def test_default_outcome_delegates_to_object(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123)

        # Act
        result = spy.process_order(123)

        # Assert
        assert result == "ok"

    def test_chained_returns_consumed_in_order(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123).returns("ok").returns("fail")

        # Act
        first = spy.process_order(123)
        second = spy.process_order(123)

        # Assert
        assert first == "ok"
        assert second == "fail"

    def test_last_outcome_repeats_beyond_list(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123).returns("ok").returns("fail").at_least(1)

        # Act
        first = spy.process_order(123)
        second = spy.process_order(123)
        third = spy.process_order(123)

        # Assert
        assert first == "ok"
        assert second == "fail"
        assert third == "fail"

    def test_condition_skipped_on_failed_returns_observation(self) -> None:
        # Arrange
        checked = False

        def capture(value: Any) -> bool:
            nonlocal checked
            checked = True
            return True

        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").returns("ok", condition=capture)

        # Act
        with pytest.raises(DeclarativeMockError):
            spy.do_something()

        # Assert
        assert checked is False

    def test_condition_skipped_on_failed_raises_observation(self) -> None:
        # Arrange
        checked = False

        def capture(value: Any) -> bool:
            nonlocal checked
            checked = True
            return True

        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123).raises(ValueError, condition=capture)

        # Act
        with pytest.raises(DeclarativeMockError):
            spy.process_order(123)

        # Assert
        assert checked is False

    def test_condition_runs_on_any_condition_observation(self) -> None:
        # Arrange
        checked = False

        def capture(value: Any) -> bool:
            nonlocal checked
            checked = True
            return True

        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").condition(capture)

        # Act
        with pytest.raises(ValueError, match=r"boom"):
            spy.do_something()

        # Assert
        assert checked is True


# ---------------------------------------------------------------------------
# Pass-through proxy
# ---------------------------------------------------------------------------


class TestPassthroughProxy:
    def test_call_without_observe_delegates_to_object(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act
        result = spy.process_order(1)

        # Assert
        assert result == "ok"

    def test_attribute_access_without_observe_delegates_to_object(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act
        val = spy.value

        # Assert
        assert val == 999

    def test_nonexistent_attr_raises_attribute_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act & Assert
        with pytest.raises(AttributeError):
            _ = spy.nonexistent

    def test_repr_works_without_observe(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act
        result = repr(spy)

        # Assert
        assert result == "DeclarativeSpy(obj=MyService())"

    def test_dunder_passthrough_via_getattr(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act
        cls = spy.__class__

        # Assert
        assert cls is DeclarativeSpy


# ---------------------------------------------------------------------------
# Order and selection (per-name)
# ---------------------------------------------------------------------------


class TestOrderAndSelection:
    def test_first_matching_non_exhausted_wins(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 1).returns("fail")
        spy.observe("process_order", 2).returns("ok")

        # Act
        two = spy.process_order(2)
        one = spy.process_order(1)

        # Assert
        assert two == "ok"
        assert one == "fail"

    def test_exhausted_observation_skipped(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 1).returns("ok").once()
        spy.observe("process_order", 1).returns("fail").once()

        # Act
        first = spy.process_order(1)
        second = spy.process_order(1)

        # Assert
        assert first == "ok"
        assert second == "fail"

    def test_order_same_args_registration_order(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").once()
        spy.observe("greet", "ada").returns("hello").once()

        # Act
        first = spy.greet("ada")
        second = spy.greet("ada")

        # Assert
        assert first == "hello"
        assert second == "hello"

    def test_never_blocks_matching_call(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").never()

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy.greet("ada")

    def test_never_after_once_guards_extra_calls(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").once()
        spy.observe("greet", "ada").never()

        # Act
        result = spy.greet("ada")

        # Assert
        assert result == "hello"

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy.greet("ada")

    def test_different_methods_independent_order(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 1).returns("ok")
        spy.observe("greet", "ada").returns("hello")

        # Act
        greeted = spy.greet("ada")
        processed = spy.process_order(1)

        # Assert
        assert greeted == "hello"
        assert processed == "ok"


# ---------------------------------------------------------------------------
# Unexpected calls (with observations registered)
# ---------------------------------------------------------------------------


class TestUnexpectedCallsWithObservations:
    def test_unmatched_args_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 99).returns("ok")

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy.process_order(1)

    def test_all_exhausted_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").once()
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy.greet("ada")


# ---------------------------------------------------------------------------
# Error diagnostics
# ---------------------------------------------------------------------------


class TestErrorDiagnostics:
    def test_args_mismatch_lists_candidate(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 99).returns("ok")

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            spy.process_order(1)

        assert type(exc_info.value) is NoMatchingCallError
        assert str(exc_info.value) == (
            "Unexpected call: 'process_order' called with args=(1,), kwargs={} "
            "- no matching non-exhausted interaction.\n"
            "Candidates:\n"
            "  Observation(process_order(99)) - args mismatch\n"
            "Call history:\n"
            "  1. process_order(1)"
        )

    def test_exhausted_lists_candidate_with_counts(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").once()
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            spy.greet("ada")

        assert type(exc_info.value) is NoMatchingCallError
        assert str(exc_info.value) == (
            "Unexpected call: 'greet' called with args=('ada',), kwargs={} "
            "- no matching non-exhausted interaction.\n"
            "Candidates:\n"
            "  Observation(greet('ada')) - exhausted (1/1 calls)\n"
            "Call history:\n"
            "  1. greet('ada')\n"
            "  2. greet('ada')"
        )

    def test_multiple_candidates_mix_exhausted_and_mismatch(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 1).returns("ok").once()
        spy.observe("process_order", 2).returns("fail")
        spy.process_order(1)

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            spy.process_order(3)

        assert type(exc_info.value) is NoMatchingCallError
        assert str(exc_info.value) == (
            "Unexpected call: 'process_order' called with args=(3,), kwargs={} "
            "- no matching non-exhausted interaction.\n"
            "Candidates:\n"
            "  Observation(process_order(1)) - exhausted (1/1 calls)\n"
            "  Observation(process_order(2)) - args mismatch\n"
            "Call history:\n"
            "  1. process_order(1)\n"
            "  2. process_order(3)"
        )

    def test_blocked_by_prerequisite_uses_shared_format(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        init = spy.observe("greet", "ada").returns("hello").once()
        spy.observe("process_order", 1).returns("ok").not_before(init)

        # Act & Assert
        with pytest.raises(UnexpectedCallError) as exc_info:
            spy.process_order(1)

        assert type(exc_info.value) is BlockedCallError
        assert str(exc_info.value) == (
            "Out-of-order call: 'process_order' called with args=(1,), kwargs={}\n"
            "  Observation(process_order(1)) - blocked by greet "
            "(expected exactly 1 call(s), got 0)\n"
            "Call history:\n"
            "  1. process_order(1)"
        )

    def test_verify_reports_expected_and_got(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").twice()
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnsatisfiedObservationError) as exc_info:
            spy.verify()

        assert str(exc_info.value) == (
            "Unsatisfied observations:\n"
            "  Observation(greet('ada')) - expected exactly 2 call(s), got 1\n"
            "Call history:\n"
            "  1. greet('ada')"
        )

    def test_verify_at_least_uses_quantifier_description(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").at_least(2)
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnsatisfiedObservationError) as exc_info:
            spy.verify()

        assert str(exc_info.value) == (
            "Unsatisfied observations:\n"
            "  Observation(greet('ada')) - expected at least 2 call(s), got 1\n"
            "Call history:\n"
            "  1. greet('ada')"
        )


# ---------------------------------------------------------------------------
# Quantifier verification via verify()
# ---------------------------------------------------------------------------


class TestAssertObservations:
    def test_all_satisfied_passes(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").once()
        spy.greet("ada")

        # Act
        spy.verify()

    def test_unsatisfied_once_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").once()

        # Act & Assert
        with pytest.raises(UnsatisfiedObservationError):
            spy.verify()

    def test_maybe_uncalled_passes(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").maybe()

        # Act
        spy.verify()

    def test_never_uncalled_passes(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").never()

        # Act
        spy.verify()

    def test_at_least_not_met_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").at_least(2)
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnsatisfiedObservationError):
            spy.verify()

    def test_between_satisfied(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").between(1, 3)
        spy.greet("ada")
        spy.greet("ada")

        # Act
        spy.verify()

    def test_mixed_satisfied_and_unsatisfied_lists_all(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello").once()
        spy.observe("process_order", 1).returns("ok").once()
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnsatisfiedObservationError) as exc_info:
            spy.verify()

        assert "process_order" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Matchers through dispatch
# ---------------------------------------------------------------------------


class TestMatchersThroughDispatch:
    @pytest.mark.parametrize("order_id", [42, 0])
    def test_anything_matcher_dispatches(self, order_id: int) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", Anything()).returns("ok").at_least(1)

        # Act
        result = spy.process_order(order_id)

        # Assert
        assert result == "ok"

    @pytest.mark.parametrize("order_id", [1, 2])
    def test_any_args_any_kwargs_dispatches(self, order_id: int) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", ANY_ARGS, ANY_KWARGS).returns("ok").at_least(1)

        # Act
        result = spy.process_order(order_id)

        # Assert
        assert result == "ok"

    @pytest.mark.parametrize("order_id", [1, 2])
    def test_any_args_and_specific_kwargs_dispatches(self, order_id: int) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", ANY_ARGS, order_id=order_id).returns(
            "ok"
        ).at_least(1)

        # Act
        result = spy.process_order(order_id=order_id)

        # Assert
        assert result == "ok"

    @pytest.mark.parametrize("order_id", [1, 2])
    def test_any_kwargs_and_specific_args_dispatches(self, order_id: int) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", order_id, ANY_KWARGS).returns("ok").at_least(1)

        # Act
        result = spy.process_order(order_id)

        # Assert
        assert result == "ok"

    def test_matched_by_dispatches(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe(
            "process_order", MatchedBy(lambda x: isinstance(x, int) and x > 0)
        ).returns("ok")

        # Act
        result = spy.process_order(5)

        # Assert
        assert result == "ok"

    def test_anything_of_type_dispatches(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", AnythingOfType(str)).returns("hello")

        # Act
        result = spy.greet("world")

        # Assert
        assert result == "hello"

    def test_later_matcher_runs_only_after_earlier_observation_is_exhausted(
        self,
    ) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello")
        spy.observe("greet", LessThan(3)).returns("hello")

        # Act
        spy.greet("ada")

        # Assert
        with pytest.raises(TypeError):
            spy.greet("ada")


# ---------------------------------------------------------------------------
# Multiple methods
# ---------------------------------------------------------------------------


class TestMultipleMethods:
    def test_independent_methods_observations(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 1).returns("ok")
        spy.observe("greet", "ada").returns("hello")

        # Act
        processed = spy.process_order(1)
        greeted = spy.greet("ada")

        # Assert
        assert processed == "ok"
        assert greeted == "hello"

    def test_observe_nonexistent_method_raises_attribute_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act & Assert
        with pytest.raises(AttributeError):
            spy.observe("nonexistent")


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


class TestRepr:
    def test_repr_contains_wrapped_object_repr(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act
        result = repr(spy)

        # Assert
        assert result == "DeclarativeSpy(obj=MyService())"


# ---------------------------------------------------------------------------
# Reserved DSL names
# ---------------------------------------------------------------------------


class TestReservedDslNames:
    @pytest.mark.parametrize("name", ["observe", "verify"])
    def test_object_attribute_matching_dsl_raises(self, name: str) -> None:
        # Arrange
        def func(self: Any) -> None:
            return None

        cls = type("CollidingObj", (), {name: func})

        # Act & Assert
        with pytest.raises(ConfigurationError, match=name):
            DeclarativeSpy(cls())

    def test_ordinary_object_still_constructs(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("greet", "ada").returns("hello")

        # Act
        result = spy.greet("ada")

        # Assert
        assert result == "hello"


# ---------------------------------------------------------------------------
# Async dispatch
# ---------------------------------------------------------------------------


class TestAsyncDispatch:
    def test_async_method_is_coroutine_function(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("aprocess_order", 1).returns("ok")

        # Act
        result = inspect.iscoroutinefunction(spy.aprocess_order)

        # Assert
        assert result is True

    async def test_async_raises_exception(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("ado_something").raises(ValueError("async-boom"))

        # Act & Assert
        with pytest.raises(ValueError, match="async-boom"):
            await spy.ado_something()

    async def test_async_default_outcome(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("aprocess_order", 1)

        # Act
        result = await spy.aprocess_order(1)

        # Assert
        assert result == "ok"

    async def test_async_chained_returns(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("aprocess_order", ANY_ARGS).returns("ok").returns("fail")

        # Act
        first = await spy.aprocess_order(1)
        second = await spy.aprocess_order(1)

        # Assert
        assert first == "ok"
        assert second == "fail"

    async def test_async_unmatched_args_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("aprocess_order", 99).returns("ok")

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            await spy.aprocess_order(1)


# ---------------------------------------------------------------------------
# Object attributes passed to observe
# ---------------------------------------------------------------------------


class TestObjectAttributeForms:
    async def test_observe_async_method_returns_configured_value(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe(MyService.aprocess_order, 7).returns("ok")

        # Act
        result = await spy.aprocess_order(7)

        # Assert
        assert result == "ok"

    def test_observe_method_matches_keyword_argument(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe(MyService.greet, name="ada").returns("hello")

        # Act
        result = spy.greet(name="ada")

        # Assert
        assert result == "hello"

    def test_observe_method_without_arguments(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe(MyService.do_something).raises(ValueError("boom")).once()

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            spy.do_something()

        with pytest.raises(UnexpectedCallError):
            spy.do_something()

    def test_observe_without_attribute_name_raises_configuration_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())

        # Act & Assert
        with pytest.raises(ConfigurationError, match="Cannot resolve"):
            spy.observe(object())  # type: ignore[call-overload]

    def test_observe_callable_missing_from_object_raises_attribute_error(self) -> None:
        # Arrange
        def missing(self: MyService) -> str:
            return "nope"

        spy = DeclarativeSpy(MyService())

        # Act & Assert
        with pytest.raises(AttributeError):
            spy.observe(missing)

    async def test_observe_preserves_original_function_identity(self) -> None:
        # Arrange
        svc = MyService()
        spy = DeclarativeSpy(svc)
        spy.observe("greet", Anything())

        # Act
        func = spy.greet
        orig = svc.greet

        # Assert
        attrs = ("__module__", "__name__", "__qualname__", "__doc__", "__annotations__")
        for attr in attrs:
            assert getattr(func, attr) == getattr(orig, attr), f"Mismatch in {attr}"

        assert inspect.signature(func) == inspect.signature(orig), (
            "Mismatch in signature"
        )

    async def test_observe_on_callabale_attribute_no_error(self) -> None:  # noqa: C901
        # Arrange
        class _Callable:
            def __call__(self, *args: Any, **kwds: Any) -> Any:
                return True

        class _AsyncCallable:
            async def __call__(self, *args: Any, **kwds: Any) -> Any:
                return True

        def func() -> bool:
            return True

        async def afunc() -> bool:
            return True

        class _Service:
            class_callable = _Callable()
            aclass_callable = _AsyncCallable()
            class_staticmethod = staticmethod(func)
            aclass_staticmethod = staticmethod(afunc)

            def __init__(self) -> None:
                self.instance_callable = func
                self.ainstance_callable = afunc

            def method(self) -> bool:
                return True

            async def amethod(self) -> bool:
                return True

            @classmethod
            def class_method(cls) -> bool:
                return True

            @classmethod
            async def aclass_method(cls) -> bool:
                return True

            @staticmethod
            def static_method() -> bool:
                return True

            @staticmethod
            async def astatic_method() -> bool:
                return True

        spy = DeclarativeSpy(_Service())

        # Act
        spy.observe("method")
        spy.observe("amethod")
        spy.observe("class_method")
        spy.observe("aclass_method")
        spy.observe("static_method")
        spy.observe("astatic_method")
        spy.observe("class_callable")
        spy.observe("aclass_callable")
        spy.observe("class_staticmethod")
        spy.observe("aclass_staticmethod")
        spy.observe("instance_callable")
        spy.observe("ainstance_callable")

        # Assert
        assert spy.method()
        assert await spy.amethod()
        assert spy.class_method()
        assert await spy.aclass_method()
        assert spy.static_method()
        assert await spy.astatic_method()
        assert spy.class_callable()
        assert await spy.aclass_callable()
        assert spy.class_staticmethod()
        assert await spy.aclass_staticmethod()
        assert spy.instance_callable()
        assert await spy.ainstance_callable()
        spy.verify()

    def test_observe_on_non_callabale_attribute_raises_configuration_error(
        self,
    ) -> None:
        # Arrange
        class _Service:
            class_attr = 0

            def __init__(self) -> None:
                self.instance_attr = 1

            @property
            def value(self) -> int:
                return 999

        spy = DeclarativeSpy(_Service())

        # Act & Assert
        with pytest.raises(
            ConfigurationError,
            match=(
                r"Cannot register observation for non-callable attribute "
                r"'value' of '_Service' \(got int: 999\)"
            ),
        ):
            spy.observe("value")

        with pytest.raises(
            ConfigurationError,
            match=(
                r"Cannot register observation for non-callable attribute "
                r"'class_attr' of '_Service' \(got int: 0\)"
            ),
        ):
            spy.observe("class_attr")

        with pytest.raises(
            ConfigurationError,
            match=(
                r"Cannot register observation for non-callable attribute "
                r"'instance_attr' of '_Service' \(got int: 1\)"
            ),
        ):
            spy.observe("instance_attr")


# ---------------------------------------------------------------------------
# not_before & chained observe
# ---------------------------------------------------------------------------


class TestNotBefore:
    def test_not_before_satisfied_allows_call(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        spy.observe("process_order", 1).returns("ok").not_before(a)

        # Act
        spy.greet("ada")
        result = spy.process_order(1)

        # Assert
        assert result == "ok"

    def test_not_before_unsatisfied_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        spy.observe("process_order", 1).returns("ok").not_before(a)

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="greet"):
            spy.process_order(1)

    def test_not_before_multiple_deps_all_satisfied(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        b = spy.observe("process_order", 1).returns("ok").once()
        spy.observe("process_order", 2).returns("fail").not_before(a, b)

        # Act
        spy.greet("ada")
        spy.process_order(1)
        result = spy.process_order(2)

        # Assert
        assert result == "fail"

    def test_not_before_multiple_deps_one_unsatisfied(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        b = spy.observe("process_order", 1).returns("ok").once()
        spy.observe("process_order", 2).returns("fail").not_before(a, b)
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="process_order"):
            spy.process_order(2)

    def test_not_before_chain_transitive(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("process_order", 1).returns("ok").once()
        b = spy.observe("greet", "ada").returns("hello").once().not_before(a)
        spy.observe("greet", "bob").returns("hello").not_before(b)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy.greet("bob")

        spy.process_order(1)
        with pytest.raises(UnexpectedCallError):
            spy.greet("bob")

        spy.greet("ada")
        result = spy.greet("bob")

        # Assert
        assert result == "hello"

    def test_not_before_cross_spy(self) -> None:
        # Arrange
        spy1 = DeclarativeSpy(MyService())
        spy2 = DeclarativeSpy(MyService())
        a = spy1.observe("process_order", 1).returns("ok").once()
        spy2.observe("greet", "ada").returns("hello").not_before(a)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy2.greet("ada")

        # Act
        spy1.process_order(1)
        result = spy2.greet("ada")

        # Assert
        assert result == "hello"

    def test_not_before_maybe_uncalled_satisfies_dep(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").maybe()
        spy.observe("process_order", 1).returns("ok").not_before(a)

        # Act
        result = spy.process_order(1)

        # Assert
        assert result == "ok"

    def test_not_before_never_uncalled_satisfies_dep(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").never()
        spy.observe("process_order", 1).returns("ok").not_before(a)

        # Act
        result = spy.process_order(1)

        # Assert
        assert result == "ok"

    def test_not_before_never_violated_blocks_dep(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").never()
        spy.observe("process_order", 1).returns("ok").not_before(a)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy.greet("ada")

        with pytest.raises(UnexpectedCallError, match="greet"):
            spy.process_order(1)

    def test_not_before_cycle_raises_config_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello")
        b = spy.observe("process_order", 1).returns("ok")
        a.not_before(b)

        # Act & Assert
        with pytest.raises(ConfigurationError, match=r"[Cc]ycle"):
            b.not_before(a)

    def test_not_before_self_dep_raises_config_error(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello")

        # Act & Assert
        with pytest.raises(ConfigurationError, match=r"[Cc]ycle"):
            a.not_before(a)

    def test_not_before_returns_self_for_chaining(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        b = spy.observe("process_order", 1)

        # Act
        result = b.not_before(a).returns("ok")

        # Assert
        assert result is b

    def test_not_before_does_not_affect_verify(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        spy.observe("process_order", 1).returns("ok").once().not_before(a)

        # Act & Assert
        with pytest.raises(UnsatisfiedObservationError):
            spy.verify()

    def test_chained_observe_forwards_args_and_enforces_order(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        (
            spy.observe("process_order", 1)
            .returns("ok")
            .once()
            .observe("greet", name="ada")
            .returns("hello")
            .once()
        )

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="process_order"):
            spy.greet(name="ada")

        assert spy.process_order(1) == "ok"
        assert spy.greet(name="ada") == "hello"
        spy.verify()


# ---------------------------------------------------------------------------
# in_order
# ---------------------------------------------------------------------------


class TestInOrder:
    def test_in_order_enforces_sequence(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        b = spy.observe("process_order", 1).returns("ok").once()
        c = spy.observe("process_order", 2).returns("fail").once()
        in_order(a, b, c)

        # Act
        spy.greet("ada")
        spy.process_order(1)
        result = spy.process_order(2)

        # Assert
        assert result == "fail"

    def test_in_order_violation_raises(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()
        b = spy.observe("process_order", 1).returns("ok").once()
        c = spy.observe("process_order", 2).returns("fail").once()
        in_order(a, b, c)
        spy.greet("ada")

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="process_order"):
            spy.process_order(2)

    def test_in_order_single_arg_noop(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("greet", "ada").returns("hello").once()

        # Act
        in_order(a)

        # Assert
        assert list(a.requires) == []

    def test_in_order_empty_noop(self) -> None:
        in_order()

    def test_in_order_cross_spy(self) -> None:
        # Arrange
        spy1 = DeclarativeSpy(MyService())
        spy2 = DeclarativeSpy(MyService())
        a = spy1.observe("process_order", 1).returns("ok").once()
        b = spy2.observe("greet", "ada").returns("hello").once()
        in_order(a, b)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy2.greet("ada")

        # Act
        spy1.process_order(1)
        result = spy2.greet("ada")

        # Assert
        assert result == "hello"

    def test_in_order_cross_mock_and_spy(self) -> None:
        # Arrange
        mock = DeclarativeMock(MyService)
        spy = DeclarativeSpy(MyService())
        a = mock.expect("do_something").returns("a").once()
        b = spy.observe("greet", "ada").returns("hello").once()
        in_order(a, b)

        # Act & Assert
        with pytest.raises(UnexpectedCallError):
            spy.greet("ada")

        # Act
        mock.do_something()
        result = spy.greet("ada")

        # Assert
        assert result == "hello"

    def test_in_order_with_quantifiers(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        a = spy.observe("process_order", 1).returns("ok").returns("fail").times(2)
        b = spy.observe("greet", "ada").returns("hello").once()
        in_order(a, b)

        # Act
        spy.process_order(1)

        # Act & Assert
        with pytest.raises(UnexpectedCallError, match="process_order"):
            spy.greet("ada")

        # Act
        spy.process_order(1)
        result = spy.greet("ada")

        # Assert
        assert result == "hello"
