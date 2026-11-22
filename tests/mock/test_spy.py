"""Integration tests for DeclarativeSpy."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from dmock._exceptions import ConfigurationError, DeclarativeMockError
from dmock._matchers import Anything
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


class TestDmockFactory:
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


# ---------------------------------------------------------------------------
# Basic dispatch
# ---------------------------------------------------------------------------


class TestBasicDispatch:
    def test_returns_checks_configured_value(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("process_order", 123).returns("ok")

        # Act
        result = spy.process_order(123)

        # Assert
        assert result == "ok"
        spy.verify()

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
        mock = DeclarativeSpy(MyService())
        mock.observe("do_something").raises(ValueError("boom"))

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            mock.do_something()

    def test_raises_checks_exception_type(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("do_something").raises(ValueError)

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            spy.do_something()

    def test_raises_checks_configured_condition(self) -> None:
        # Arrange
        svc = MyService()

        checked = False

        def capture(exc: BaseException) -> bool:
            nonlocal checked
            checked = True
            return svc.failed and isinstance(exc, ValueError)

        mock = DeclarativeSpy(svc)
        mock.observe("do_something").raises(ValueError, condition=capture)

        # Act & Assert
        with pytest.raises(ValueError, match="boom"):
            mock.do_something()

        assert checked

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

    def test_default_outcome_delegates_to_mock(self) -> None:
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

    async def test_different_returns_consumed_in_any_order(self) -> None:
        # Arrange
        spy = DeclarativeSpy(MyService())
        spy.observe("aprocess_order", 123).returns("fail")
        spy.observe("process_order", 123).returns("ok")

        # Act
        first = spy.process_order(123)
        second = await spy.aprocess_order(123)

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

    async def test_condition_skipped_on_failed_returns_observation(self) -> None:
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

    async def test_condition_skipped_on_failed_raises_observation(self) -> None:
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

    async def test_condition_runs_on_any_condition_observation(self) -> None:
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
# Object attributes passed to observe
# ---------------------------------------------------------------------------


class TestObjectAttributeForms:
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
        # TODO: verify
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
