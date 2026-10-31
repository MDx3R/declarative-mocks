"""Tests for dmock._matchers."""

from __future__ import annotations

import re
from collections import UserDict, UserString
from dataclasses import dataclass, make_dataclass
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, NamedTuple
from uuid import UUID

import pytest

from dmock import (
    ANY_ARGS,
    ANY_KWARGS,
    AWARE_DATETIME,
    EMPTY,
    FALSY,
    IS_DATACLASS,
    IS_UUID,
    NAIVE_DATETIME,
    TRUTHY,
    And,
    AnyOrder,
    Anything,
    AnythingOfType,
    Approx,
    Args,
    Attr,
    CollectionOf,
    Contains,
    Empty,
    EndsWith,
    Equals,
    GreaterEquals,
    GreaterThan,
    HasLen,
    In,
    Includes,
    InstanceOf,
    Is,
    IsDataclass,
    IsNow,
    IsUUID,
    LessEquals,
    LessThan,
    MappingOf,
    MatchedBy,
    Matcher,
    Maybe,
    Never,
    Not,
    Nothing,
    Or,
    PartialMapping,
    Range,
    Regex,
    RegexFullmatch,
    RegexMatch,
    RegexSearch,
    SequenceOf,
    SetOf,
    StartsWith,
)
from dmock._matchers import (
    _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
    _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
)


if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence, Set


class TestAnything:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(42, id="int"),
            pytest.param("hello", id="str"),
            pytest.param(None, id="none"),
            pytest.param([1, 2, 3], id="list"),
        ],
    )
    def test_matches_any_value(self, value: object) -> None:
        assert Anything.matches(value) is True

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

    def test_alias_is_instance_of(self) -> None:
        assert AnythingOfType is InstanceOf

    @pytest.mark.parametrize(
        ("matcher", "value", "matched"),
        [
            pytest.param(AnythingOfType(int), True, True, id="int-accepts-bool"),
            pytest.param(
                AnythingOfType(int, exact=True),
                True,
                False,
                id="exact-int-rejects-bool",
            ),
            pytest.param(
                AnythingOfType(bool, exact=True),
                True,
                True,
                id="exact-bool-accepts-bool",
            ),
            pytest.param(
                AnythingOfType(int, exact=True), 1, True, id="exact-int-accepts-int"
            ),
            pytest.param(InstanceOf(int), True, True, id="alias-accepts-bool"),
            pytest.param(
                InstanceOf(int, exact=True), True, False, id="alias-exact-rejects-bool"
            ),
        ],
    )
    def test_exact_controls_subclass_matching(
        self,
        matcher: Matcher,
        value: object,
        matched: bool,
    ) -> None:
        assert matcher.matches(value) is matched

    def test_exact_rejects_a_subclass(self) -> None:
        class Base:
            pass

        class Child(Base):
            pass

        assert AnythingOfType(Base, exact=True).matches(Child()) is False

    def test_repr(self) -> None:
        assert repr(AnythingOfType(int)) == "AnythingOfType(int, exact=False)"
        assert (
            repr(AnythingOfType(int, exact=True)) == "AnythingOfType(int, exact=True)"
        )

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(AnythingOfType(int), Matcher)
        assert isinstance(AnythingOfType(str), Matcher)


class TestMatchedBy:
    def test_matches_truthy_predicate(self) -> None:
        assert MatchedBy(lambda x: x > 0).matches(5) is True

    def test_rejects_falsy_predicate(self) -> None:
        assert MatchedBy(lambda x: x > 0).matches(-1) is False

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(4, True, id="even"),
            pytest.param(3, False, id="odd"),
        ],
    )
    def test_with_named_function(self, value: int, expected: bool) -> None:
        def is_even(x: object) -> bool:
            return isinstance(x, int) and x % 2 == 0

        assert MatchedBy(is_even).matches(value) is expected

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
        assert isinstance(ANY_ARGS, Matcher) is False

    def test_any_kwargs_not_matcher(self) -> None:
        assert isinstance(ANY_KWARGS, Matcher) is False

    def test_any_args_is_sentinel_type(self) -> None:
        assert isinstance(ANY_ARGS, _AnyArgsSentinel)

    def test_any_kwargs_is_sentinel_type(self) -> None:
        assert isinstance(ANY_KWARGS, _AnyKwargsSentinel)


class TestNever:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(0, id="zero"),
            pytest.param("", id="empty-str"),
            pytest.param(None, id="none"),
            pytest.param(Never, id="never"),
        ],
    )
    def test_matches_nothing(self, value: object) -> None:
        assert Never.matches(value) is False

    def test_nothing_is_same_singleton(self) -> None:
        assert Nothing is Never
        assert Never() is Never
        assert Nothing() is Nothing

    def test_repr(self) -> None:
        assert repr(Never) == "Never"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Never, Matcher)


class TestEquals:
    def test_matches_equal_value(self) -> None:
        assert Equals("a").matches("a") is True

    def test_rejects_unequal_value(self) -> None:
        assert Equals("a").matches("b") is False

    def test_equality_is_symmetric(self) -> None:
        assert Equals("a") == "a"
        assert "a" == Equals("a")  # noqa: SIM300

    def test_repr(self) -> None:
        assert repr(Equals("a")) == "Equals('a')"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Equals("a"), Matcher)


class TestNot:
    def test_matches_different_value(self) -> None:
        assert Not("a").matches("b") is True

    def test_rejects_equal_value(self) -> None:
        assert Not("a").matches("a") is False

    def test_invert_matches_different_value(self) -> None:
        assert (~Equals("a")) == "b"

    def test_invert_rejects_equal_value(self) -> None:
        assert (~Equals("a")) != "a"

    def test_invert_repr(self) -> None:
        assert repr(~Equals("a")) == "Not(Equals('a'))"

    def test_repr(self) -> None:
        assert repr(Not("a")) == "Not('a')"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Not("a"), Matcher)


class TestMaybe:
    def test_matches_none(self) -> None:
        assert Maybe("a").matches(None) is True

    def test_matches_expected_value(self) -> None:
        assert Maybe("a").matches("a") is True

    def test_rejects_other_value(self) -> None:
        assert Maybe("a").matches("b") is False

    def test_repr(self) -> None:
        assert repr(Maybe("a")) == "Maybe('a')"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Maybe("a"), Matcher)


class TestIs:
    def test_matches_same_object(self) -> None:
        value = [1]
        assert Is(value).matches(value) is True

    def test_rejects_equal_copy(self) -> None:
        assert Is([1]).matches([1]) is False

    def test_repr(self) -> None:
        assert repr(Is(None)) == "Is(None)"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Is(None), Matcher)


class TestTruthyAndFalsy:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("a", id="str"),
            pytest.param(1, id="int"),
            pytest.param([0], id="list"),
        ],
    )
    def test_truthy_matches(self, value: object) -> None:
        assert TRUTHY.matches(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("", id="empty-str"),
            pytest.param(0, id="zero"),
            pytest.param(None, id="none"),
            pytest.param([], id="empty-list"),
        ],
    )
    def test_truthy_rejects_falsy(self, value: object) -> None:
        assert TRUTHY.matches(value) is False

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("", id="empty-str"),
            pytest.param(0, id="zero"),
            pytest.param(None, id="none"),
            pytest.param([], id="empty-list"),
        ],
    )
    def test_falsy_matches(self, value: object) -> None:
        assert FALSY.matches(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("a", id="str"),
            pytest.param(1, id="int"),
            pytest.param([0], id="list"),
        ],
    )
    def test_falsy_rejects_truthy(self, value: object) -> None:
        assert FALSY.matches(value) is False

    def test_truthy_repr(self) -> None:
        assert repr(TRUTHY) == "MatchedBy(<class 'bool'>)"


class TestDatetimeMatchers:
    def test_naive_matches_naive_datetime(self) -> None:
        assert NAIVE_DATETIME.matches(datetime(2020, 1, 1)) is True

    def test_naive_rejects_aware_datetime(self) -> None:
        assert NAIVE_DATETIME.matches(datetime(2020, 1, 1, tzinfo=UTC)) is False

    def test_naive_rejects_non_datetime(self) -> None:
        assert NAIVE_DATETIME.matches("2020-01-01") is False

    def test_aware_matches_aware_datetime(self) -> None:
        assert AWARE_DATETIME.matches(datetime(2020, 1, 1, tzinfo=UTC)) is True

    def test_aware_rejects_naive_datetime(self) -> None:
        assert AWARE_DATETIME.matches(datetime(2020, 1, 1)) is False

    def test_aware_rejects_non_datetime(self) -> None:
        assert AWARE_DATETIME.matches(None) is False


class TestEmpty:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("", id="str"),
            pytest.param([], id="list"),
            pytest.param({}, id="dict"),
            pytest.param((), id="tuple"),
        ],
    )
    def test_matches_empty_sized(self, value: object) -> None:
        assert Empty().matches(value) is True

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("a", id="str"),
            pytest.param([1], id="list"),
            pytest.param(None, id="none"),
            pytest.param(0, id="int"),
        ],
    )
    def test_rejects_non_empty_or_unsized(self, value: object) -> None:
        assert Empty().matches(value) is False

    def test_empty_constant_is_an_empty_matcher(self) -> None:
        assert isinstance(EMPTY, Empty)
        assert EMPTY is not Empty()

    def test_repr(self) -> None:
        assert repr(EMPTY) == "Empty()"


class TestHasLen:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param([1, 2, 3], 3, True, id="three-items"),
            pytest.param([1], 3, False, id="too-short"),
            pytest.param([1], GreaterThan(2), False, id="length-below-matcher"),
            pytest.param([1, 2, 3], GreaterThan(2), True, id="length-above-matcher"),
            pytest.param("ab", 2, True, id="str"),
            pytest.param(b"ab", 2, True, id="bytes"),
            pytest.param([], 0, True, id="empty-list"),
            pytest.param({"a": 1}, 1, True, id="dict"),
            pytest.param(None, 0, False, id="none"),
            pytest.param(1, 0, False, id="int"),
        ],
    )
    def test_matches(
        self, value: object, expected: int | Matcher, matched: bool
    ) -> None:
        assert HasLen(expected).matches(value) is matched

    def test_equality_uses_matches(self) -> None:
        assert [1, 2, 3] == HasLen(3)  # noqa: SIM300
        assert HasLen(GreaterThan(2)) == [1, 2, 3]

    def test_repr(self) -> None:
        assert repr(HasLen(3)) == "HasLen(3)"
        assert repr(HasLen(GreaterThan(2))) == "HasLen(GreaterThan(2))"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(HasLen(0), Matcher)


class TestIn:
    def test_matches_member(self) -> None:
        assert In(("a", "b")).matches("a") is True

    def test_rejects_missing_member(self) -> None:
        assert In(("a", "b")).matches("c") is False

    def test_repr(self) -> None:
        assert repr(In(("a", "b"))) == "In(('a', 'b'))"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(In(("a",)), Matcher)


class TestContains:
    def test_matches_list_member(self) -> None:
        assert Contains(1).matches([1, 2]) is True

    def test_matches_substring(self) -> None:
        assert Contains("k").matches("key") is True

    def test_rejects_missing_member(self) -> None:
        assert Contains(1).matches([2]) is False

    def test_rejects_non_container(self) -> None:
        assert Contains(1).matches(1) is False

    def test_repr(self) -> None:
        assert repr(Contains("k")) == "Contains('k')"


class TestIncludes:
    def test_matches_when_every_item_is_present(self) -> None:
        assert Includes("a", "b").matches(["a", "b", "c"]) is True

    def test_rejects_when_an_item_is_missing(self) -> None:
        assert Includes("a", "b").matches(["a"]) is False

    def test_empty_items_match_any_container(self) -> None:
        assert Includes().matches([]) is True

    def test_rejects_non_container(self) -> None:
        assert Includes("a").matches(None) is False

    def test_repr(self) -> None:
        assert repr(Includes("a", "b")) == "Includes('a', 'b')"


class TestCollectionOf:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param((1, 2, 3), [1, 2, 3], True, id="tuple-list"),
            pytest.param([1, 2, 3], (1, 2, 3), True, id="list-tuple"),
            pytest.param([1, 2], [1, 2], True, id="same-list"),
            pytest.param([1, 2], [2, 1], False, id="reversed-list"),
            pytest.param((1, 2), [2, 1], False, id="reversed-tuple"),
            pytest.param([1, 2], [1, 2, 3], False, id="shorter-list"),
            pytest.param(range(3), [0, 1, 2], True, id="range"),
            pytest.param((1, 2, 3), {1, 2, 3}, False, id="tuple-vs-set"),
            pytest.param([1, 2], {1, 2}, False, id="list-vs-set"),
            pytest.param({1, 2}, {2, 1}, True, id="same-set"),
            pytest.param({1, 2}, frozenset({2, 1}), True, id="set-frozenset"),
            pytest.param(frozenset({1}), {1}, True, id="frozenset-set"),
            pytest.param({1, 2}, frozenset({1, 3}), False, id="different-set"),
            pytest.param({"b": 1, "a": 2}, {"a": 2, "b": 1}, True, id="dict-order"),
            pytest.param({"a": 1}, {"a": 2}, False, id="dict-value"),
            pytest.param({"a": 1, "b": 2}, {"a": 1}, False, id="dict-extra-key"),
            pytest.param(UserDict({"a": 1}), {"a": 1}, True, id="user-dict"),
            pytest.param(
                MappingProxyType({"b": 1, "a": 2}),
                {"a": 2, "b": 1},
                True,
                id="mapping-proxy",
            ),
            pytest.param({"a": 1}, [("a", 1)], False, id="dict-vs-pairs"),
            pytest.param({1: "a", 2: "b"}.keys(), {1, 2}, True, id="dict-keys"),
            pytest.param({1: "a"}.items(), {(1, "a")}, True, id="dict-items"),
            pytest.param({1: "a"}.values(), ["a"], False, id="dict-values"),
            pytest.param("ab", ["a", "b"], True, id="str-chars"),
            pytest.param(["a", "b"], "ab", True, id="chars-str"),
            pytest.param("ab", ("a", "b"), True, id="str-tuple"),
            pytest.param("ab", "ab", True, id="same-str"),
            pytest.param("ab", ["b", "a"], False, id="reversed-chars"),
            pytest.param("ab", ["a"], False, id="short-str"),
            pytest.param("", [], True, id="empty-str-list"),
            pytest.param([], "", True, id="empty-list-str"),
            pytest.param("", {}, False, id="empty-str-dict"),
            pytest.param("", set[object](), False, id="empty-str-set"),
            pytest.param("ab", {"a", "b"}, False, id="str-vs-set"),
            pytest.param(b"ab", bytearray(b"ab"), True, id="bytes-bytearray"),
            pytest.param(bytearray(b"ab"), b"ab", True, id="bytearray-bytes"),
            pytest.param(b"ab", [97, 98], True, id="bytes-ints"),
            pytest.param([97, 98], b"ab", True, id="ints-bytes"),
            pytest.param(
                bytearray(b"ab"), memoryview(b"ab"), True, id="bytearray-memoryview"
            ),
            pytest.param(memoryview(b"ab"), b"ab", True, id="memoryview-bytes"),
            pytest.param(memoryview(b"ab"), [97, 98], True, id="memoryview-ints"),
            pytest.param(b"ab", memoryview(b"ab"), True, id="bytes-memoryview"),
            pytest.param(b"", [], True, id="empty-bytes"),
            pytest.param(b"ab", ["a", "b"], False, id="bytes-vs-chars"),
            pytest.param("ab", b"ab", False, id="str-vs-bytes"),
            pytest.param(b"ab", "ab", False, id="bytes-vs-str"),
            pytest.param(UserString("ab"), "ab", True, id="userstring-str"),
            pytest.param("ab", UserString("ab"), True, id="str-userstring"),
            pytest.param(UserString("ab"), ["a", "b"], True, id="userstring-chars"),
            pytest.param(["a", "b"], UserString("ab"), True, id="chars-userstring"),
            pytest.param(
                UserString("ab"), UserString("ab"), True, id="same-userstring"
            ),
            pytest.param(1, [1], False, id="int"),
            pytest.param(None, [], False, id="none"),
        ],
    )
    def test_matches(
        self,
        value: object,
        expected: Collection[object],
        matched: bool,
    ) -> None:
        assert CollectionOf(expected).matches(value) is matched

    @pytest.mark.parametrize(
        ("expected", "text"),
        [
            pytest.param([1, 2, 3], "CollectionOf([1, 2, 3])", id="list"),
            pytest.param("ab", "CollectionOf('ab')", id="str"),
            pytest.param(b"ab", "CollectionOf(b'ab')", id="bytes"),
            pytest.param({1, 2}, "CollectionOf({1, 2})", id="set"),
        ],
    )
    def test_repr(self, expected: Collection[object], text: str) -> None:
        assert repr(CollectionOf(expected)) == text

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(CollectionOf([]), Matcher)


class TestSequenceOf:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param((1, 2, 3), [1, 2, 3], True, id="tuple-list"),
            pytest.param([1, 2, 3], (1, 2, 3), True, id="list-tuple"),
            pytest.param([1, 2], [2, 1], False, id="reversed-list"),
            pytest.param([1, 2], [1, 2, 3], False, id="shorter-list"),
            pytest.param(range(3), [0, 1, 2], True, id="range"),
            pytest.param({1, 2, 3}, [1, 2, 3], False, id="set-of-three"),
            pytest.param({1, 2}, [1, 2], False, id="set"),
            pytest.param("ab", ["a", "b"], True, id="str-chars"),
            pytest.param(["a", "b"], "ab", True, id="chars-str"),
            pytest.param("ab", ["b", "a"], False, id="reversed-chars"),
            pytest.param("", [], True, id="empty-str"),
            pytest.param({"a", "b"}, ["a", "b"], False, id="set-of-chars"),
            pytest.param(b"ab", [97, 98], True, id="bytes-ints"),
            pytest.param(bytearray(b"ab"), b"ab", True, id="bytearray-bytes"),
            pytest.param(memoryview(b"ab"), [97, 98], True, id="memoryview-ints"),
            pytest.param("ab", b"ab", False, id="str-vs-bytes"),
            pytest.param(UserString("ab"), "ab", True, id="userstring-str"),
            pytest.param("ab", UserString("ab"), True, id="str-userstring"),
            pytest.param(1, [1], False, id="int"),
            pytest.param(None, [], False, id="none"),
        ],
    )
    def test_matches(
        self,
        value: object,
        expected: Sequence[object],
        matched: bool,
    ) -> None:
        assert SequenceOf(expected).matches(value) is matched

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(SequenceOf([]), Matcher)


class TestSetOf:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param({1, 2}, {2, 1}, True, id="same-set"),
            pytest.param(frozenset({1, 2}), {2, 1}, True, id="frozenset-set"),
            pytest.param({1}, frozenset({1}), True, id="set-frozenset"),
            pytest.param({1, 2}, frozenset({1, 3}), False, id="different-set"),
            pytest.param([1, 2], {1, 2}, False, id="list"),
            pytest.param((1, 2), {1, 2}, False, id="tuple"),
            pytest.param({"a": 1}, {1}, False, id="dict"),
            pytest.param({1: "a", 2: "b"}.keys(), {1, 2}, True, id="dict-keys"),
            pytest.param(1, {1}, False, id="int"),
        ],
    )
    def test_matches(
        self,
        value: object,
        expected: Set[object],
        matched: bool,
    ) -> None:
        assert SetOf(expected).matches(value) is matched

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(SetOf({1}), Matcher)


class TestMappingOf:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param({"b": 1, "a": 2}, {"a": 2, "b": 1}, True, id="same-pairs"),
            pytest.param({"a": 1}, {"a": 2}, False, id="different-value"),
            pytest.param({"a": 1, "b": 2}, {"a": 1}, False, id="extra-key"),
            pytest.param({"a": 1}, {"a": 1, "b": 2}, False, id="missing-key"),
            pytest.param(UserDict({"a": 1}), {"a": 1}, True, id="user-dict"),
            pytest.param(
                MappingProxyType({"b": 1, "a": 2}),
                {"a": 2, "b": 1},
                True,
                id="mapping-proxy",
            ),
            pytest.param([("a", 1)], {"a": 1}, False, id="list"),
            pytest.param((("a", 1),), {"a": 1}, False, id="tuple"),
            pytest.param(1, {"a": 1}, False, id="int"),
        ],
    )
    def test_matches(
        self,
        value: object,
        expected: Mapping[object, object],
        matched: bool,
    ) -> None:
        assert MappingOf(expected).matches(value) is matched

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(MappingOf({"a": 1}), Matcher)


class TestAnyOrder:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param([1, 2, 3], [3, 1, 2], True, id="permuted"),
            pytest.param([1, 2, 3], [1, 2, 3], True, id="same-order"),
            pytest.param((1, 2, 3), [3, 2, 1], True, id="tuple"),
            pytest.param([2, 0, 1], range(3), True, id="range"),
            pytest.param([1], [1], True, id="single"),
            pytest.param([], [], True, id="empty-lists"),
            pytest.param((), [], True, id="empty-tuple"),
            pytest.param([1, 2], [1, 2, 3], False, id="shorter-value"),
            pytest.param([1, 2, 3], [1, 2], False, id="shorter-expected"),
            pytest.param([1, 2, 3], [1, 2, 4], False, id="different-item"),
            pytest.param([1, 2], [1, 1], False, id="duplicate-expected"),
            pytest.param([1.0, 2.0], [2, 1], True, id="floats"),
            pytest.param([[2], [1]], [[1], [2]], True, id="nested-lists"),
            pytest.param([{2}, {1}], [{1}, {2}], True, id="nested-sets"),
            pytest.param([1], [True], True, id="bool-equals-int"),
            pytest.param([1, 2], [True, 2], True, id="bool-with-int"),
            pytest.param([1, 2], [1, True], False, id="bool-takes-the-only-one"),
            pytest.param([float("nan")], [float("nan")], False, id="nan"),
        ],
    )
    def test_matches_same_items_in_any_order(
        self,
        value: object,
        expected: Collection[object],
        matched: bool,
    ) -> None:
        assert AnyOrder(expected).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param([1, 1], [1, 1], True, id="two-ones"),
            pytest.param([1, 1, 1], [1, 1, 1], True, id="three-ones"),
            pytest.param([2, 1, 2], [1, 2, 2], True, id="two-twos"),
            pytest.param([1, 2], [1, 1], False, id="one-extra-one"),
            pytest.param([1, 1], [1, 2], False, id="missing-two"),
            pytest.param([1, 1, 2], [1, 1, 1], False, id="three-vs-two"),
            pytest.param("aa", ["a", "a"], True, id="repeated-char"),
            pytest.param("ab", ["a", "a"], False, id="different-chars"),
            pytest.param(b"aa", [97, 97], True, id="repeated-byte"),
            pytest.param(b"ab", [97, 97], False, id="different-bytes"),
            pytest.param({1, 2}, [1, 1], False, id="set-collapses-duplicate"),
        ],
    )
    def test_pairs_each_item_with_a_distinct_element(
        self,
        value: object,
        expected: Collection[object],
        matched: bool,
    ) -> None:
        assert AnyOrder(expected).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param(
                [11, -1], [GreaterThan(10), LessThan(0)], True, id="greater-and-less"
            ),
            pytest.param(
                [-1, 11],
                [GreaterThan(10), LessThan(0)],
                True,
                id="swapped-greater-and-less",
            ),
            pytest.param(
                [11, 12], [GreaterThan(10), LessThan(0)], False, id="both-greater"
            ),
            pytest.param(
                [1, 2], [GreaterThan(0), GreaterThan(0)], True, id="two-positive"
            ),
            pytest.param(
                [15, 5],
                [GreaterThan(0), GreaterThan(10)],
                True,
                id="backtrack-large-first",
            ),
            pytest.param(
                [5, 15],
                [GreaterThan(10), GreaterThan(0)],
                True,
                id="backtrack-large-second",
            ),
            pytest.param(
                [5, 6], [GreaterThan(0), GreaterThan(10)], False, id="no-large-enough"
            ),
            pytest.param(
                [15, 5],
                [GreaterThan(10), GreaterThan(10)],
                False,
                id="both-need-the-large-one",
            ),
            pytest.param(
                [15, -1, 5],
                [GreaterThan(0), GreaterThan(10), LessThan(0)],
                True,
                id="three-with-greater",
            ),
            pytest.param(
                [15, -1, 5],
                [GreaterThan(0), LessThan(10), LessThan(0)],
                True,
                id="three-with-less",
            ),
            pytest.param([2, 1], [Equals(1), Equals(2)], True, id="equals-swapped"),
            pytest.param([1, 1], [Equals(1), Equals(1)], True, id="equals-duplicates"),
            pytest.param(
                [1, 2], [Equals(1), Equals(1)], False, id="equals-missing-duplicate"
            ),
            pytest.param([1, "x"], [Anything(), Anything()], True, id="two-anything"),
            pytest.param([1], [Anything(), Anything()], False, id="anything-too-short"),
            pytest.param(
                ["x", 1], [Anything(), Equals(1)], True, id="anything-then-equals"
            ),
            pytest.param(
                ["x", 2],
                [Anything(), Equals(1)],
                False,
                id="anything-then-wrong-equals",
            ),
        ],
    )
    def test_applies_matcher_items(
        self,
        value: object,
        expected: Collection[object],
        matched: bool,
    ) -> None:
        assert AnyOrder(expected).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param("ba", ["a", "b"], True, id="str-chars"),
            pytest.param(["a", "b"], "ba", True, id="chars-str"),
            pytest.param("ab", ["b", "a"], True, id="reversed-chars"),
            pytest.param("ab", "ba", True, id="str-str"),
            pytest.param("ab", ["a"], False, id="short-expected"),
            pytest.param("ab", ["a", "b", "c"], False, id="long-expected"),
            pytest.param("", [], True, id="empty-str"),
            pytest.param([], "", True, id="empty-list"),
            pytest.param(UserString("ba"), ["a", "b"], True, id="userstring-chars"),
            pytest.param(["a", "b"], UserString("ba"), True, id="chars-userstring"),
            pytest.param(b"ba", [98, 97], True, id="bytes-ints"),
            pytest.param([97, 98], b"ab", True, id="ints-bytes"),
            pytest.param(bytearray(b"ba"), [98, 97], True, id="bytearray-ints"),
            pytest.param(memoryview(b"ba"), [98, 97], True, id="memoryview-ints"),
            pytest.param([97, 98], bytearray(b"ba"), True, id="ints-bytearray"),
            pytest.param("ab", b"ab", False, id="str-vs-bytes"),
            pytest.param(b"ab", ["a", "b"], False, id="bytes-vs-chars"),
        ],
    )
    def test_compares_string_like_values_by_elements(
        self,
        value: object,
        expected: Collection[object],
        matched: bool,
    ) -> None:
        assert AnyOrder(expected).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param({1, 2}, [2, 1], True, id="set-list"),
            pytest.param([1, 2], {2, 1}, True, id="list-set"),
            pytest.param(frozenset({1, 2}), [2, 1], True, id="frozenset"),
            pytest.param({1, 2}, [1, 3], False, id="different-set"),
            pytest.param("ba", {"a", "b"}, True, id="str-set"),
            pytest.param({"b": 1, "a": 2}, ["a", "b"], True, id="dict-keys-as-list"),
            pytest.param(["a", "b"], {"b": 1, "a": 2}, True, id="list-dict-keys"),
            pytest.param({"a": 1, "b": 2}.keys(), ["b", "a"], True, id="keys-view"),
            pytest.param({"a": 1, "b": 2}.values(), [2, 1], True, id="values-view"),
            pytest.param(
                {"a": 1, "b": 2}.items(), [("b", 2), ("a", 1)], True, id="items-view"
            ),
            pytest.param(set[object](), [], True, id="empty-set"),
            pytest.param({}, [], True, id="empty-dict"),
            pytest.param([], {}, True, id="empty-list-dict"),
            pytest.param({"a": 1}, ["a", "b"], False, id="missing-key"),
        ],
    )
    def test_matches_non_sequence_collections_by_iteration(
        self,
        value: object,
        expected: Collection[object],
        matched: bool,
    ) -> None:
        assert AnyOrder(expected).matches(value) is matched

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(1, id="int"),
            pytest.param(None, id="none"),
            pytest.param(True, id="bool"),
        ],
    )
    def test_rejects_a_non_collection(self, value: object) -> None:
        assert AnyOrder([1]).matches(value) is False

    def test_equality_uses_matches(self) -> None:
        assert [2, 1] == AnyOrder([1, 2])  # noqa: SIM300
        assert AnyOrder([1, 2]) == [2, 1]
        assert [1, 2] != AnyOrder([1, 1])  # noqa: SIM300

    def test_repr_lists_the_items(self) -> None:
        assert repr(AnyOrder([3, 1, 2])) == "AnyOrder([3, 1, 2])"
        assert repr(AnyOrder((2, 1))) == "AnyOrder([2, 1])"
        assert repr(AnyOrder("ba")) == "AnyOrder(['b', 'a'])"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(AnyOrder([]), Matcher)


class TestPartialMapping:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        [
            pytest.param({"a": 1, "b": 2}, {"a": 1}, True, id="extra-key"),
            pytest.param(
                {"status": "ok", "id": 1}, {"status": "ok"}, True, id="status-with-id"
            ),
            pytest.param({"a": 1}, {"a": 1, "b": 2}, False, id="missing-key"),
            pytest.param({"a": 1}, {"b": 1}, False, id="wrong-key"),
            pytest.param({"a": 1}, {}, True, id="empty-expected"),
            pytest.param({}, {}, True, id="empty-mapping"),
            pytest.param(UserDict({"a": 1, "b": 2}), {"b": 2}, True, id="user-dict"),
            pytest.param(
                MappingProxyType({"a": 1, "extra": 9}),
                {"a": 1},
                True,
                id="mapping-proxy",
            ),
            pytest.param([("a", 1)], {"a": 1}, False, id="list"),
            pytest.param(None, {"a": 1}, False, id="none"),
            pytest.param(1, {}, False, id="int"),
        ],
    )
    def test_matches(
        self,
        value: object,
        expected: Mapping[object, object],
        matched: bool,
    ) -> None:
        assert PartialMapping(expected).matches(value) is matched

    def test_applies_a_matcher_value(self) -> None:
        assert PartialMapping({"a": GreaterThan(0)}).matches({"a": 1, "b": 2}) is True
        assert PartialMapping({"a": GreaterThan(0)}).matches({"a": 0}) is False

    def test_nested_partial_mapping(self) -> None:
        value = {"user": {"name": "a", "age": 1}}
        assert (
            PartialMapping({"user": PartialMapping({"name": "a"})}).matches(value)
            is True
        )

    def test_equality_uses_matches(self) -> None:
        assert {"a": 1, "b": 2} == PartialMapping({"a": 1})  # noqa: SIM300
        assert PartialMapping({"b": 1}) != {"a": 1}

    def test_repr(self) -> None:
        assert (
            repr(PartialMapping({"status": "ok"})) == "PartialMapping({'status': 'ok'})"
        )

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(PartialMapping({}), Matcher)


class TestAttr:
    def test_matches_existing_attribute(self) -> None:
        class Item:
            name = "n"

        assert Attr("name").matches(Item()) is True

    def test_rejects_missing_attribute(self) -> None:
        assert Attr("name").matches(object()) is False

    def test_repr(self) -> None:
        assert repr(Attr("name")) == "Attr('name')"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Attr("name"), Matcher)


class TestOrdering:
    @pytest.mark.parametrize(
        ("matcher", "value", "expected"),
        [
            pytest.param(LessThan(3), 2, True, id="less-than"),
            pytest.param(LessThan(3), 3, False, id="less-than-equal"),
            pytest.param(GreaterThan(3), 4, True, id="greater-than"),
            pytest.param(GreaterThan(3), 3, False, id="greater-than-equal"),
            pytest.param(LessEquals(3), 3, True, id="less-equals"),
            pytest.param(LessEquals(3), 4, False, id="less-equals-above"),
            pytest.param(GreaterEquals(3), 3, True, id="greater-equals"),
            pytest.param(GreaterEquals(3), 2, False, id="greater-equals-below"),
            pytest.param(Range(0, 10), 5, True, id="inside-range"),
            pytest.param(Range(0, 10), 0, False, id="range-left-edge"),
            pytest.param(Range(0, 10), 10, False, id="range-right-edge"),
        ],
    )
    def test_matches(self, matcher: Matcher, value: int, expected: bool) -> None:
        assert matcher.matches(value) is expected

    @pytest.mark.parametrize(
        ("matcher", "text"),
        [
            pytest.param(LessThan(3), "LessThan(3)", id="less-than"),
            pytest.param(GreaterThan(3), "GreaterThan(3)", id="greater-than"),
            pytest.param(LessEquals(3), "LessEquals(3)", id="less-equals"),
            pytest.param(GreaterEquals(3), "GreaterEquals(3)", id="greater-equals"),
            pytest.param(Range(0, 10), "Range(left=0, right=10)", id="range"),
        ],
    )
    def test_repr(self, matcher: Matcher, text: str) -> None:
        assert repr(matcher) == text

    def test_incomparable_value_raises(self) -> None:
        with pytest.raises(TypeError):
            LessThan(3).matches("a")


class TestApprox:
    def test_matches_exact_value(self) -> None:
        assert Approx(1.0).matches(1.0) is True

    def test_matches_int(self) -> None:
        assert Approx(1.0).matches(1) is True

    def test_matches_within_relative_tolerance(self) -> None:
        assert Approx(1.0).matches(1.0 + 1e-12) is True

    def test_rejects_outside_relative_tolerance(self) -> None:
        assert Approx(1.0).matches(1.0 + 1e-6) is False

    def test_absolute_tolerance(self) -> None:
        assert Approx(1.0, rel_tol=0, abs_tol=0.1).matches(1.05) is True

    def test_rejects_outside_absolute_tolerance(self) -> None:
        assert Approx(1.0, rel_tol=0, abs_tol=0.1).matches(1.2) is False

    def test_rejects_non_float(self) -> None:
        assert Approx(1.0).matches("1") is False

    def test_repr(self) -> None:
        assert repr(Approx(1.0)) == "Approx(1.0, rel_tol=1e-09, abs_tol=0)"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(Approx(1.0), Matcher)


class TestStartsWith:
    def test_matches_prefix(self) -> None:
        assert StartsWith("k").matches("key") is True

    def test_rejects_other_prefix(self) -> None:
        assert StartsWith("k").matches("eye") is False

    def test_rejects_non_string(self) -> None:
        assert StartsWith("k").matches(None) is False

    def test_repr(self) -> None:
        assert repr(StartsWith("k")) == "StartsWith('k')"


class TestEndsWith:
    def test_matches_suffix(self) -> None:
        assert EndsWith("ey").matches("key") is True

    def test_rejects_other_suffix(self) -> None:
        assert EndsWith("ey").matches("kid") is False

    def test_rejects_non_string(self) -> None:
        assert EndsWith("ey").matches(1) is False

    def test_repr(self) -> None:
        assert repr(EndsWith("ey")) == "EndsWith('ey')"


class TestRegex:
    def test_regex_alias(self) -> None:
        assert Regex is RegexMatch

    def test_match_from_start(self) -> None:
        assert RegexMatch(r"k.*").matches("key") is True

    def test_match_rejects_pattern_past_the_start(self) -> None:
        assert RegexMatch(r"ey").matches("key") is False

    def test_search_anywhere(self) -> None:
        assert RegexSearch("ey").matches("key") is True

    def test_fullmatch_whole_string(self) -> None:
        assert RegexFullmatch(r"k.y").matches("key") is True

    def test_fullmatch_rejects_extra_characters(self) -> None:
        assert RegexFullmatch(r"k.y").matches("key!") is False

    @pytest.mark.parametrize(
        ("matcher", "value"),
        [
            pytest.param(RegexMatch("a"), 1, id="match-int"),
            pytest.param(RegexSearch("a"), None, id="search-none"),
            pytest.param(RegexFullmatch("a"), b"a", id="fullmatch-bytes"),
        ],
    )
    def test_rejects_non_string(self, matcher: Matcher, value: object) -> None:
        assert matcher.matches(value) is False

    def test_ignore_case_flag(self) -> None:
        assert RegexMatch("a", re.IGNORECASE).matches("A") is True

    def test_match_is_case_sensitive(self) -> None:
        assert RegexMatch("a").matches("A") is False

    def test_compiled_pattern(self) -> None:
        assert RegexSearch(re.compile(r"ey")).matches("key") is True

    def test_compiled_pattern_with_flags_raises(self) -> None:
        matcher = RegexMatch(re.compile("a"), re.IGNORECASE)
        with pytest.raises(ValueError, match="flags"):
            matcher.matches("A")

    @pytest.mark.parametrize(
        ("matcher", "text"),
        [
            pytest.param(
                RegexMatch(r"k.*"),
                "RegexMatch(expected='k.*', flags=re.NOFLAG)",
                id="match",
            ),
            pytest.param(
                RegexSearch("ey"),
                "RegexSearch(expected='ey', flags=re.NOFLAG)",
                id="search",
            ),
            pytest.param(
                RegexFullmatch(r"k.y"),
                "RegexFullmatch(expected='k.y', flags=re.NOFLAG)",
                id="fullmatch",
            ),
        ],
    )
    def test_repr(self, matcher: Matcher, text: str) -> None:
        assert repr(matcher) == text


class TestIsNow:
    def test_matches_naive_now(self) -> None:
        assert IsNow().matches(datetime.now()) is True

    def test_matches_aware_now(self) -> None:
        assert IsNow().matches(datetime.now(UTC)) is True

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(datetime(2020, 1, 1), id="naive"),
            pytest.param(datetime(2020, 1, 1, tzinfo=UTC), id="aware"),
            pytest.param("now", id="str"),
            pytest.param(None, id="none"),
        ],
    )
    def test_rejects_distant_or_non_datetime(self, value: object) -> None:
        assert IsNow().matches(value) is False

    def test_timedelta_tolerance(self) -> None:
        moment = datetime.now() - timedelta(seconds=30)
        assert IsNow(tolerance=timedelta(seconds=120)).matches(moment) is True
        assert IsNow(tolerance=timedelta(seconds=1)).matches(moment) is False

    def test_negative_tolerance_matches_nothing(self) -> None:
        assert IsNow(tolerance=-1).matches(datetime.now()) is False
        assert IsNow(tolerance=timedelta(seconds=-1)).matches(datetime.now()) is False

    def test_equality_uses_matches(self) -> None:
        assert datetime.now(UTC) == IsNow()
        assert IsNow() != datetime(2020, 1, 1)

    def test_repr(self) -> None:
        assert repr(IsNow()) == "IsNow(tolerance=5.0)"
        assert repr(IsNow(tolerance=timedelta(seconds=10))) == "IsNow(tolerance=10.0)"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(IsNow(), Matcher)


class TestIsUUID:
    UUID4 = UUID("12345678-1234-4234-8234-123456789abc")
    UUID1 = UUID("12345678-1234-1234-8234-123456789abc")
    UUID5 = UUID("12345678-1234-5234-8234-123456789abc")

    @pytest.mark.parametrize(
        ("value", "version", "matched"),
        [
            pytest.param(UUID4, 4, True, id="uuid4-version-4"),
            pytest.param(UUID4, 1, False, id="uuid4-version-1"),
            pytest.param(UUID4, 5, False, id="uuid4-version-5"),
            pytest.param(UUID1, 1, True, id="uuid1-version-1"),
            pytest.param(UUID1, 4, False, id="uuid1-version-4"),
            pytest.param(UUID5, 5, True, id="uuid5-version-5"),
            pytest.param(UUID5, 4, False, id="uuid5-version-4"),
            pytest.param(UUID(int=0), 4, False, id="nil-version-4"),
            pytest.param(str(UUID4), 4, True, id="uuid4-string-version-4"),
            pytest.param(str(UUID4), 1, False, id="uuid4-string-version-1"),
            pytest.param(str(UUID1), 4, False, id="uuid1-string-version-4"),
            pytest.param(str(UUID4).upper(), 4, True, id="uppercase-version-4"),
            pytest.param("urn:uuid:" + str(UUID1), 4, False, id="urn-version-4"),
            pytest.param(UUID4.hex, 4, True, id="hex-version-4"),
            pytest.param(str(UUID(int=0)), 4, False, id="nil-string-version-4"),
            pytest.param("123", 4, False, id="invalid-string"),
            pytest.param(None, 4, False, id="none"),
            pytest.param(1, 4, False, id="int"),
            pytest.param(UUID4.bytes, 4, False, id="bytes"),
        ],
    )
    def test_matches_requested_version(
        self, value: object, version: int, matched: bool
    ) -> None:
        assert IsUUID(version=version).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "matched"),
        [
            pytest.param(UUID4, True, id="uuid4"),
            pytest.param(UUID1, True, id="uuid1"),
            pytest.param(UUID5, True, id="uuid5"),
            pytest.param(UUID(int=0), True, id="nil"),
            pytest.param(str(UUID5), True, id="string"),
            pytest.param("{" + str(UUID4) + "}", True, id="braces"),
            pytest.param("not-a-uuid", False, id="invalid-string"),
            pytest.param("", False, id="empty-string"),
            pytest.param(" " + str(UUID4), False, id="leading-space"),
            pytest.param(None, False, id="none"),
            pytest.param(UUID4.bytes, False, id="bytes"),
        ],
    )
    def test_matches_any_version(self, value: object, matched: bool) -> None:
        assert IsUUID().matches(value) is matched

    def test_default_accepts_any_version(self) -> None:
        assert IsUUID().matches(self.UUID1) is True
        assert IsUUID().matches(str(self.UUID4)) is True

    def test_constant_accepts_any_version(self) -> None:
        assert isinstance(IS_UUID, IsUUID)
        assert IS_UUID is not IsUUID()
        assert IS_UUID.matches(self.UUID1) is True
        assert IS_UUID.matches(str(self.UUID4)) is True
        assert IS_UUID.matches("not-a-uuid") is False
        assert repr(IS_UUID) == "IsUUID(version=None)"

    def test_equality_uses_matches(self) -> None:
        assert self.UUID4 == IsUUID(version=4)  # noqa: SIM300
        assert IsUUID(version=4) == self.UUID4
        assert self.UUID1 != IsUUID(version=4)  # noqa: SIM300
        assert str(self.UUID1) != IsUUID(version=4)

    def test_repr_includes_version(self) -> None:
        assert repr(IsUUID()) == "IsUUID(version=None)"
        assert repr(IsUUID(version=4)) == "IsUUID(version=4)"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(IsUUID(), Matcher)


class TestIsDataclass:
    @dataclass
    class Item:
        name: str

    @dataclass(frozen=True)
    class FrozenItem:
        name: str

    @dataclass(slots=True)
    class SlotsItem:
        name: str

    class ItemChild(Item):
        pass

    class Plain:
        pass

    class Point(NamedTuple):
        name: str

    Made = make_dataclass("Made", [("name", str)])

    @pytest.mark.parametrize(
        ("value", "matched"),
        [
            pytest.param(Item("n"), True, id="instance"),
            pytest.param(FrozenItem("n"), True, id="frozen-instance"),
            pytest.param(SlotsItem("n"), True, id="slots-instance"),
            pytest.param(ItemChild("n"), True, id="subclass-instance"),
            pytest.param(Made("n"), True, id="made-instance"),
            pytest.param(Item, False, id="class"),
            pytest.param(FrozenItem, False, id="frozen-class"),
            pytest.param(SlotsItem, False, id="slots-class"),
            pytest.param(ItemChild, False, id="subclass"),
            pytest.param(Made, False, id="made-class"),
            pytest.param(Plain(), False, id="plain-instance"),
            pytest.param(Plain, False, id="plain-class"),
            pytest.param(Point("n"), False, id="namedtuple"),
            pytest.param(object(), False, id="object"),
            pytest.param(None, False, id="none"),
            pytest.param("n", False, id="str"),
        ],
    )
    def test_matches_an_instance(self, value: object, matched: bool) -> None:
        assert IsDataclass(instance=True).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "matched"),
        [
            pytest.param(Item("n"), True, id="instance"),
            pytest.param(Item, True, id="class"),
            pytest.param(FrozenItem("n"), True, id="frozen-instance"),
            pytest.param(FrozenItem, True, id="frozen-class"),
            pytest.param(SlotsItem("n"), True, id="slots-instance"),
            pytest.param(SlotsItem, True, id="slots-class"),
            pytest.param(ItemChild("n"), True, id="subclass-instance"),
            pytest.param(ItemChild, True, id="subclass"),
            pytest.param(Made("n"), True, id="made-instance"),
            pytest.param(Made, True, id="made-class"),
            pytest.param(Plain(), False, id="plain-instance"),
            pytest.param(Plain, False, id="plain-class"),
            pytest.param(Point, False, id="namedtuple"),
            pytest.param(1, False, id="int"),
        ],
    )
    def test_matches_a_class_or_instance(self, value: object, matched: bool) -> None:
        assert IsDataclass(instance=False).matches(value) is matched

    def test_default_matches_an_instance(self) -> None:
        assert IsDataclass().matches(self.Item("n")) is True
        assert IsDataclass().matches(self.Item) is False

    def test_constant_matches_an_instance(self) -> None:
        assert isinstance(IS_DATACLASS, IsDataclass)
        assert IS_DATACLASS is not IsDataclass()
        assert IS_DATACLASS.matches(self.Item("n")) is True
        assert IS_DATACLASS.matches(self.Item) is False
        assert repr(IS_DATACLASS) == "IsDataclass(instance=True)"

    def test_equality_uses_matches(self) -> None:
        assert self.Item("n") == IsDataclass()
        assert IsDataclass() == self.Item("n")
        assert self.Item != IsDataclass()

    def test_repr_includes_instance(self) -> None:
        assert repr(IsDataclass()) == "IsDataclass(instance=True)"
        assert repr(IsDataclass(instance=False)) == "IsDataclass(instance=False)"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(IsDataclass(), Matcher)


class TestAnd:
    def test_matches_when_every_argument_matches(self) -> None:
        assert And(GreaterThan(0), LessThan(10)).matches(5) is True

    def test_rejects_when_an_argument_does_not_match(self) -> None:
        assert And(GreaterThan(0), LessThan(10)).matches(0) is False

    def test_equality_is_reflected(self) -> None:
        assert And(1, 1) == 1
        assert 1 == And(1, 1)  # noqa: SIM300
        assert And(1, 2) != 1

    def test_operator_combines_matchers(self) -> None:
        combined = GreaterThan(0) & LessThan(10)
        assert repr(combined) == "And(GreaterThan(0), LessThan(10))"
        assert combined == 5

    def test_operator_wraps_plain_value_on_the_right(self) -> None:
        combined = Equals(1) & 1
        assert repr(combined) == "And(Equals(1), Equals(1))"
        assert combined == 1

    def test_operator_wraps_plain_value_on_the_left(self) -> None:
        combined = 1 & Equals(1)
        assert repr(combined) == "And(Equals(1), Equals(1))"
        assert combined == 1

    def test_reflected_operator_defers_to_matcher_on_the_left(self) -> None:
        assert Equals(1).__rand__(Equals(2)) is NotImplemented

    def test_empty_matches_any_value(self) -> None:
        assert And().matches(1) is True

    def test_repr(self) -> None:
        assert repr(And(1, "a")) == "And(1, 'a')"


class TestOr:
    def test_matches_when_any_argument_matches(self) -> None:
        assert Or("a", "b").matches("b") is True

    def test_rejects_when_no_argument_matches(self) -> None:
        assert Or("a", "b").matches("c") is False

    def test_equality_is_reflected(self) -> None:
        assert Or(1, 2) == 1
        assert 1 == Or(1, 2)  # noqa: SIM300
        assert Or(1, 2) != 3

    def test_operator_combines_matchers(self) -> None:
        combined = Equals(1) | Equals(2)
        assert repr(combined) == "Or(Equals(1), Equals(2))"
        assert combined == 2

    def test_operator_wraps_plain_value_on_the_right(self) -> None:
        combined = Equals(1) | 2
        assert repr(combined) == "Or(Equals(1), Equals(2))"
        assert combined == 2

    def test_operator_wraps_plain_value_on_the_left(self) -> None:
        combined = 1 | Equals(2)
        assert repr(combined) == "Or(Equals(1), Equals(2))"
        assert combined == 1

    def test_reflected_operator_defers_to_matcher_on_the_left(self) -> None:
        assert Equals(1).__ror__(Equals(2)) is NotImplemented

    def test_empty_matches_nothing(self) -> None:
        assert Or().matches(1) is False

    def test_repr(self) -> None:
        assert repr(Or(1, 2)) == "Or(1, 2)"


class TestArgs:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            Args(Anything)  # pyright: ignore[reportAbstractUsage]


class TestMatcher:
    def test_hash_is_constant(self) -> None:
        assert hash(Equals(1)) == 0
        assert hash(Anything) == 0
