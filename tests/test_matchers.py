"""Tests for dmock._matchers."""

from __future__ import annotations

from dmock._matchers import (
    ANY_ARGS,
    ANY_KWARGS,
    Anything,
    AnythingOfType,
    MatchedBy,
    Matcher,
    _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
    _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
)


class TestAnything:
    def test_matches_int(self) -> None:
        assert Anything.matches(42) is True

    def test_matches_string(self) -> None:
        assert Anything.matches("hello") is True

    def test_matches_none(self) -> None:
        assert Anything.matches(None) is True

    def test_matches_list(self) -> None:
        assert Anything.matches([1, 2, 3]) is True

    def test_call_returns_same_instance(self) -> None:
        assert Anything() is Anything

    def test_repr(self) -> None:
        assert repr(Anything) == "Anything"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Anything, Matcher)


class TestAnythingOfType:
    def test_matches_exact_type(self) -> None:
        assert AnythingOfType(int).matches(42) is True

    def test_rejects_wrong_type(self) -> None:
        assert AnythingOfType(int).matches("x") is False

    def test_matches_subclass(self) -> None:
        class Base:
            pass

        class Child(Base):
            pass

        assert AnythingOfType(Base).matches(Child()) is True

    def test_matches_none(self) -> None:
        assert AnythingOfType(type(None)).matches(None) is True

    def test_rejects_none_for_int(self) -> None:
        assert AnythingOfType(int).matches(None) is False

    def test_repr(self) -> None:
        assert repr(AnythingOfType(int)) == "AnythingOfType(int)"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(AnythingOfType(int), Matcher)


class TestMatchedBy:
    def test_matches_truthy_predicate(self) -> None:
        assert MatchedBy(lambda x: x > 0).matches(5) is True

    def test_rejects_falsy_predicate(self) -> None:
        assert MatchedBy(lambda x: x > 0).matches(-1) is False

    def test_with_named_function(self) -> None:
        def is_even(x: object) -> bool:
            return isinstance(x, int) and x % 2 == 0

        m = MatchedBy(is_even)
        assert m.matches(4) is True
        assert m.matches(3) is False

    def test_repr_contains_predicate(self) -> None:
        def my_pred(x: object) -> bool:
            return True

        assert "my_pred" in repr(MatchedBy(my_pred))

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(MatchedBy(lambda x: True), Matcher)


class TestSentinels:
    def test_any_args_repr(self) -> None:
        assert repr(ANY_ARGS) == "ANY_ARGS"

    def test_any_kwargs_repr(self) -> None:
        assert repr(ANY_KWARGS) == "ANY_KWARGS"

    def test_any_args_is_sentinel_instance(self) -> None:
        assert type(ANY_ARGS) is _AnyArgsSentinel

    def test_any_args_not_matcher(self) -> None:
        assert not isinstance(ANY_ARGS, Matcher)

    def test_any_kwargs_not_matcher(self) -> None:
        assert not isinstance(ANY_KWARGS, Matcher)

    def test_any_args_is_sentinel_type(self) -> None:
        assert isinstance(ANY_ARGS, _AnyArgsSentinel)

    def test_any_kwargs_is_sentinel_type(self) -> None:
        assert isinstance(ANY_KWARGS, _AnyKwargsSentinel)
