"""Tests for dmock._matchers."""

from __future__ import annotations

import re
from collections import UserDict, UserString
from collections.abc import Collection, Mapping, Sequence, Set
from dataclasses import dataclass, make_dataclass
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import NamedTuple
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


class TestAnything:
    @pytest.mark.parametrize(
        "value",
        [42, "hello", None, [1, 2, 3]],
        ids=["int", "str", "none", "list"],
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
            (AnythingOfType(int), True, True),
            (AnythingOfType(int, exact=True), True, False),
            (AnythingOfType(bool, exact=True), True, True),
            (AnythingOfType(int, exact=True), 1, True),
            (InstanceOf(int), True, True),
            (InstanceOf(int, exact=True), True, False),
        ],
        ids=[
            "int-accepts-bool",
            "exact-int-rejects-bool",
            "exact-bool-accepts-bool",
            "exact-int-accepts-int",
            "alias-accepts-bool",
            "alias-exact-rejects-bool",
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
        [(4, True), (3, False)],
        ids=["even", "odd"],
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
        "value", [0, "", None, Never], ids=["zero", "empty-str", "none", "never"]
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
    @pytest.mark.parametrize("value", ["a", 1, [0]], ids=["str", "int", "list"])
    def test_truthy_matches(self, value: object) -> None:
        assert TRUTHY.matches(value) is True

    @pytest.mark.parametrize(
        "value", ["", 0, None, []], ids=["empty-str", "zero", "none", "empty-list"]
    )
    def test_truthy_rejects_falsy(self, value: object) -> None:
        assert TRUTHY.matches(value) is False

    @pytest.mark.parametrize(
        "value", ["", 0, None, []], ids=["empty-str", "zero", "none", "empty-list"]
    )
    def test_falsy_matches(self, value: object) -> None:
        assert FALSY.matches(value) is True

    @pytest.mark.parametrize("value", ["a", 1, [0]], ids=["str", "int", "list"])
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
        "value", ["", [], {}, ()], ids=["str", "list", "dict", "tuple"]
    )
    def test_matches_empty_sized(self, value: object) -> None:
        assert Empty().matches(value) is True

    @pytest.mark.parametrize(
        "value", ["a", [1], None, 0], ids=["str", "list", "none", "int"]
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
        list[tuple[object, int | Matcher, bool]](
            [
                ([1, 2, 3], 3, True),
                ([1], 3, False),
                ([1], GreaterThan(2), False),
                ([1, 2, 3], GreaterThan(2), True),
                ("ab", 2, True),
                (b"ab", 2, True),
                ([], 0, True),
                ({"a": 1}, 1, True),
                (None, 0, False),
                (1, 0, False),
            ]
        ),
        ids=[
            "three-items",
            "too-short",
            "length-below-matcher",
            "length-above-matcher",
            "str",
            "bytes",
            "empty-list",
            "dict",
            "none",
            "int",
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
        list[tuple[object, Collection[object], bool]](
            [
                ((1, 2, 3), [1, 2, 3], True),
                ([1, 2, 3], (1, 2, 3), True),
                ([1, 2], [1, 2], True),
                ([1, 2], [2, 1], False),
                ((1, 2), [2, 1], False),
                ([1, 2], [1, 2, 3], False),
                (range(3), [0, 1, 2], True),
                ((1, 2, 3), {1, 2, 3}, False),
                ([1, 2], {1, 2}, False),
                ({1, 2}, {2, 1}, True),
                ({1, 2}, frozenset({2, 1}), True),
                (frozenset({1}), {1}, True),
                ({1, 2}, frozenset({1, 3}), False),
                ({"b": 1, "a": 2}, {"a": 2, "b": 1}, True),
                ({"a": 1}, {"a": 2}, False),
                ({"a": 1, "b": 2}, {"a": 1}, False),
                (UserDict({"a": 1}), {"a": 1}, True),
                (MappingProxyType({"b": 1, "a": 2}), {"a": 2, "b": 1}, True),
                ({"a": 1}, [("a", 1)], False),
                ({1: "a", 2: "b"}.keys(), {1, 2}, True),
                ({1: "a"}.items(), {(1, "a")}, True),
                ({1: "a"}.values(), ["a"], False),
                ("ab", ["a", "b"], True),
                (["a", "b"], "ab", True),
                ("ab", ("a", "b"), True),
                ("ab", "ab", True),
                ("ab", ["b", "a"], False),
                ("ab", ["a"], False),
                ("", [], True),
                ([], "", True),
                ("", {}, False),
                ("", set(), False),
                ("ab", {"a", "b"}, False),
                (b"ab", bytearray(b"ab"), True),
                (bytearray(b"ab"), b"ab", True),
                (b"ab", [97, 98], True),
                ([97, 98], b"ab", True),
                (bytearray(b"ab"), memoryview(b"ab"), True),
                (memoryview(b"ab"), b"ab", True),
                (memoryview(b"ab"), [97, 98], True),
                (b"ab", memoryview(b"ab"), True),
                (b"", [], True),
                (b"ab", ["a", "b"], False),
                ("ab", b"ab", False),
                (b"ab", "ab", False),
                (UserString("ab"), "ab", True),
                ("ab", UserString("ab"), True),
                (UserString("ab"), ["a", "b"], True),
                (["a", "b"], UserString("ab"), True),
                (UserString("ab"), UserString("ab"), True),
                (1, [1], False),
                (None, [], False),
            ]
        ),
        ids=[
            "tuple-list",
            "list-tuple",
            "same-list",
            "reversed-list",
            "reversed-tuple",
            "shorter-list",
            "range",
            "tuple-vs-set",
            "list-vs-set",
            "same-set",
            "set-frozenset",
            "frozenset-set",
            "different-set",
            "dict-order",
            "dict-value",
            "dict-extra-key",
            "user-dict",
            "mapping-proxy",
            "dict-vs-pairs",
            "dict-keys",
            "dict-items",
            "dict-values",
            "str-chars",
            "chars-str",
            "str-tuple",
            "same-str",
            "reversed-chars",
            "short-str",
            "empty-str-list",
            "empty-list-str",
            "empty-str-dict",
            "empty-str-set",
            "str-vs-set",
            "bytes-bytearray",
            "bytearray-bytes",
            "bytes-ints",
            "ints-bytes",
            "bytearray-memoryview",
            "memoryview-bytes",
            "memoryview-ints",
            "bytes-memoryview",
            "empty-bytes",
            "bytes-vs-chars",
            "str-vs-bytes",
            "bytes-vs-str",
            "userstring-str",
            "str-userstring",
            "userstring-chars",
            "chars-userstring",
            "same-userstring",
            "int",
            "none",
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
            ([1, 2, 3], "CollectionOf([1, 2, 3])"),
            ("ab", "CollectionOf('ab')"),
            (b"ab", "CollectionOf(b'ab')"),
            ({1, 2}, "CollectionOf({1, 2})"),
        ],
        ids=["list", "str", "bytes", "set"],
    )
    def test_repr(self, expected: Collection[object], text: str) -> None:
        assert repr(CollectionOf(expected)) == text

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(CollectionOf([]), Matcher)


class TestSequenceOf:
    @pytest.mark.parametrize(
        ("value", "expected", "matched"),
        list[tuple[object, Sequence[object], bool]](
            [
                ((1, 2, 3), [1, 2, 3], True),
                ([1, 2, 3], (1, 2, 3), True),
                ([1, 2], [2, 1], False),
                ([1, 2], [1, 2, 3], False),
                (range(3), [0, 1, 2], True),
                ({1, 2, 3}, [1, 2, 3], False),
                ({1, 2}, [1, 2], False),
                ("ab", ["a", "b"], True),
                (["a", "b"], "ab", True),
                ("ab", ["b", "a"], False),
                ("", [], True),
                ({"a", "b"}, ["a", "b"], False),
                (b"ab", [97, 98], True),
                (bytearray(b"ab"), b"ab", True),
                (memoryview(b"ab"), [97, 98], True),
                ("ab", b"ab", False),
                (UserString("ab"), "ab", True),
                ("ab", UserString("ab"), True),
                (1, [1], False),
                (None, [], False),
            ]
        ),
        ids=[
            "tuple-list",
            "list-tuple",
            "reversed-list",
            "shorter-list",
            "range",
            "set-of-three",
            "set",
            "str-chars",
            "chars-str",
            "reversed-chars",
            "empty-str",
            "set-of-chars",
            "bytes-ints",
            "bytearray-bytes",
            "memoryview-ints",
            "str-vs-bytes",
            "userstring-str",
            "str-userstring",
            "int",
            "none",
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
        list[tuple[object, Set[object], bool]](
            [
                ({1, 2}, {2, 1}, True),
                (frozenset({1, 2}), {2, 1}, True),
                ({1}, frozenset({1}), True),
                ({1, 2}, frozenset({1, 3}), False),
                ([1, 2], {1, 2}, False),
                ((1, 2), {1, 2}, False),
                ({"a": 1}, {1}, False),
                ({1: "a", 2: "b"}.keys(), {1, 2}, True),
                (1, {1}, False),
            ]
        ),
        ids=[
            "same-set",
            "frozenset-set",
            "set-frozenset",
            "different-set",
            "list",
            "tuple",
            "dict",
            "dict-keys",
            "int",
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
        list[tuple[object, Mapping[object, object], bool]](
            [
                ({"b": 1, "a": 2}, {"a": 2, "b": 1}, True),
                ({"a": 1}, {"a": 2}, False),
                ({"a": 1, "b": 2}, {"a": 1}, False),
                ({"a": 1}, {"a": 1, "b": 2}, False),
                (UserDict({"a": 1}), {"a": 1}, True),
                (MappingProxyType({"b": 1, "a": 2}), {"a": 2, "b": 1}, True),
                ([("a", 1)], {"a": 1}, False),
                ((("a", 1),), {"a": 1}, False),
                (1, {"a": 1}, False),
            ]
        ),
        ids=[
            "same-pairs",
            "different-value",
            "extra-key",
            "missing-key",
            "user-dict",
            "mapping-proxy",
            "list",
            "tuple",
            "int",
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
        list[tuple[object, Collection[object], bool]](
            [
                ([1, 2, 3], [3, 1, 2], True),
                ([1, 2, 3], [1, 2, 3], True),
                ((1, 2, 3), [3, 2, 1], True),
                ([2, 0, 1], range(3), True),
                ([1], [1], True),
                ([], [], True),
                ((), [], True),
                ([1, 2], [1, 2, 3], False),
                ([1, 2, 3], [1, 2], False),
                ([1, 2, 3], [1, 2, 4], False),
                ([1, 2], [1, 1], False),
                ([1.0, 2.0], [2, 1], True),
                ([[2], [1]], [[1], [2]], True),
                ([{2}, {1}], [{1}, {2}], True),
                ([1], [True], True),
                ([1, 2], [True, 2], True),
                ([1, 2], [1, True], False),
                ([float("nan")], [float("nan")], False),
            ]
        ),
        ids=[
            "permuted",
            "same-order",
            "tuple",
            "range",
            "single",
            "empty-lists",
            "empty-tuple",
            "shorter-value",
            "shorter-expected",
            "different-item",
            "duplicate-expected",
            "floats",
            "nested-lists",
            "nested-sets",
            "bool-equals-int",
            "bool-with-int",
            "bool-takes-the-only-one",
            "nan",
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
        list[tuple[object, Collection[object], bool]](
            [
                ([1, 1], [1, 1], True),
                ([1, 1, 1], [1, 1, 1], True),
                ([2, 1, 2], [1, 2, 2], True),
                ([1, 2], [1, 1], False),
                ([1, 1], [1, 2], False),
                ([1, 1, 2], [1, 1, 1], False),
                ("aa", ["a", "a"], True),
                ("ab", ["a", "a"], False),
                (b"aa", [97, 97], True),
                (b"ab", [97, 97], False),
                ({1, 2}, [1, 1], False),
            ]
        ),
        ids=[
            "two-ones",
            "three-ones",
            "two-twos",
            "one-extra-one",
            "missing-two",
            "three-vs-two",
            "repeated-char",
            "different-chars",
            "repeated-byte",
            "different-bytes",
            "set-collapses-duplicate",
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
        list[tuple[object, Collection[object], bool]](
            [
                ([11, -1], [GreaterThan(10), LessThan(0)], True),
                ([-1, 11], [GreaterThan(10), LessThan(0)], True),
                ([11, 12], [GreaterThan(10), LessThan(0)], False),
                ([1, 2], [GreaterThan(0), GreaterThan(0)], True),
                ([15, 5], [GreaterThan(0), GreaterThan(10)], True),
                ([5, 15], [GreaterThan(10), GreaterThan(0)], True),
                ([5, 6], [GreaterThan(0), GreaterThan(10)], False),
                ([15, 5], [GreaterThan(10), GreaterThan(10)], False),
                ([15, -1, 5], [GreaterThan(0), GreaterThan(10), LessThan(0)], True),
                ([15, -1, 5], [GreaterThan(0), LessThan(10), LessThan(0)], True),
                ([2, 1], [Equals(1), Equals(2)], True),
                ([1, 1], [Equals(1), Equals(1)], True),
                ([1, 2], [Equals(1), Equals(1)], False),
                ([1, "x"], [Anything(), Anything()], True),
                ([1], [Anything(), Anything()], False),
                (["x", 1], [Anything(), Equals(1)], True),
                (["x", 2], [Anything(), Equals(1)], False),
            ]
        ),
        ids=[
            "greater-and-less",
            "swapped-greater-and-less",
            "both-greater",
            "two-positive",
            "backtrack-large-first",
            "backtrack-large-second",
            "no-large-enough",
            "both-need-the-large-one",
            "three-with-greater",
            "three-with-less",
            "equals-swapped",
            "equals-duplicates",
            "equals-missing-duplicate",
            "two-anything",
            "anything-too-short",
            "anything-then-equals",
            "anything-then-wrong-equals",
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
        list[tuple[object, Collection[object], bool]](
            [
                ("ba", ["a", "b"], True),
                (["a", "b"], "ba", True),
                ("ab", ["b", "a"], True),
                ("ab", "ba", True),
                ("ab", ["a"], False),
                ("ab", ["a", "b", "c"], False),
                ("", [], True),
                ([], "", True),
                (UserString("ba"), ["a", "b"], True),
                (["a", "b"], UserString("ba"), True),
                (b"ba", [98, 97], True),
                ([97, 98], b"ab", True),
                (bytearray(b"ba"), [98, 97], True),
                (memoryview(b"ba"), [98, 97], True),
                ([97, 98], bytearray(b"ba"), True),
                ("ab", b"ab", False),
                (b"ab", ["a", "b"], False),
            ]
        ),
        ids=[
            "str-chars",
            "chars-str",
            "reversed-chars",
            "str-str",
            "short-expected",
            "long-expected",
            "empty-str",
            "empty-list",
            "userstring-chars",
            "chars-userstring",
            "bytes-ints",
            "ints-bytes",
            "bytearray-ints",
            "memoryview-ints",
            "ints-bytearray",
            "str-vs-bytes",
            "bytes-vs-chars",
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
        list[tuple[object, Collection[object], bool]](
            [
                ({1, 2}, [2, 1], True),
                ([1, 2], {2, 1}, True),
                (frozenset({1, 2}), [2, 1], True),
                ({1, 2}, [1, 3], False),
                ("ba", {"a", "b"}, True),
                ({"b": 1, "a": 2}, ["a", "b"], True),
                (["a", "b"], {"b": 1, "a": 2}, True),
                ({"a": 1, "b": 2}.keys(), ["b", "a"], True),
                ({"a": 1, "b": 2}.values(), [2, 1], True),
                ({"a": 1, "b": 2}.items(), [("b", 2), ("a", 1)], True),
                (set[object](), [], True),
                ({}, [], True),
                ([], {}, True),
                ({"a": 1}, ["a", "b"], False),
            ]
        ),
        ids=[
            "set-list",
            "list-set",
            "frozenset",
            "different-set",
            "str-set",
            "dict-keys-as-list",
            "list-dict-keys",
            "keys-view",
            "values-view",
            "items-view",
            "empty-set",
            "empty-dict",
            "empty-list-dict",
            "missing-key",
        ],
    )
    def test_matches_non_sequence_collections_by_iteration(
        self,
        value: object,
        expected: Collection[object],
        matched: bool,
    ) -> None:
        assert AnyOrder(expected).matches(value) is matched

    @pytest.mark.parametrize("value", [1, None, True], ids=["int", "none", "bool"])
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
        list[tuple[object, Mapping[object, object], bool]](
            [
                ({"a": 1, "b": 2}, {"a": 1}, True),
                ({"status": "ok", "id": 1}, {"status": "ok"}, True),
                ({"a": 1}, {"a": 1, "b": 2}, False),
                ({"a": 1}, {"b": 1}, False),
                ({"a": 1}, {}, True),
                ({}, {}, True),
                (UserDict({"a": 1, "b": 2}), {"b": 2}, True),
                (MappingProxyType({"a": 1, "extra": 9}), {"a": 1}, True),
                ([("a", 1)], {"a": 1}, False),
                (None, {"a": 1}, False),
                (1, {}, False),
            ]
        ),
        ids=[
            "extra-key",
            "status-with-id",
            "missing-key",
            "wrong-key",
            "empty-expected",
            "empty-mapping",
            "user-dict",
            "mapping-proxy",
            "list",
            "none",
            "int",
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
            (LessThan(3), 2, True),
            (LessThan(3), 3, False),
            (GreaterThan(3), 4, True),
            (GreaterThan(3), 3, False),
            (LessEquals(3), 3, True),
            (LessEquals(3), 4, False),
            (GreaterEquals(3), 3, True),
            (GreaterEquals(3), 2, False),
            (Range(0, 10), 5, True),
            (Range(0, 10), 0, False),
            (Range(0, 10), 10, False),
        ],
        ids=[
            "less-than",
            "less-than-equal",
            "greater-than",
            "greater-than-equal",
            "less-equals",
            "less-equals-above",
            "greater-equals",
            "greater-equals-below",
            "inside-range",
            "range-left-edge",
            "range-right-edge",
        ],
    )
    def test_matches(self, matcher: Matcher, value: int, expected: bool) -> None:
        assert matcher.matches(value) is expected

    @pytest.mark.parametrize(
        ("matcher", "text"),
        [
            (LessThan(3), "LessThan(3)"),
            (GreaterThan(3), "GreaterThan(3)"),
            (LessEquals(3), "LessEquals(3)"),
            (GreaterEquals(3), "GreaterEquals(3)"),
            (Range(0, 10), "Range(left=0, right=10)"),
        ],
        ids=["less-than", "greater-than", "less-equals", "greater-equals", "range"],
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
            (RegexMatch("a"), 1),
            (RegexSearch("a"), None),
            (RegexFullmatch("a"), b"a"),
        ],
        ids=["match-int", "search-none", "fullmatch-bytes"],
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
            (RegexMatch(r"k.*"), "RegexMatch(expected='k.*', flags=re.NOFLAG)"),
            (RegexSearch("ey"), "RegexSearch(expected='ey', flags=re.NOFLAG)"),
            (
                RegexFullmatch(r"k.y"),
                "RegexFullmatch(expected='k.y', flags=re.NOFLAG)",
            ),
        ],
        ids=["match", "search", "fullmatch"],
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
        [datetime(2020, 1, 1), datetime(2020, 1, 1, tzinfo=UTC), "now", None],
        ids=["naive", "aware", "str", "none"],
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
        list[tuple[object, int, bool]](
            [
                (UUID4, 4, True),
                (UUID4, 1, False),
                (UUID4, 5, False),
                (UUID1, 1, True),
                (UUID1, 4, False),
                (UUID5, 5, True),
                (UUID5, 4, False),
                (UUID(int=0), 4, False),
                (str(UUID4), 4, True),
                (str(UUID4), 1, False),
                (str(UUID1), 4, False),
                (str(UUID4).upper(), 4, True),
                ("urn:uuid:" + str(UUID1), 4, False),
                (UUID4.hex, 4, True),
                (str(UUID(int=0)), 4, False),
                ("123", 4, False),
                (None, 4, False),
                (1, 4, False),
                (UUID4.bytes, 4, False),
            ]
        ),
        ids=[
            "uuid4-version-4",
            "uuid4-version-1",
            "uuid4-version-5",
            "uuid1-version-1",
            "uuid1-version-4",
            "uuid5-version-5",
            "uuid5-version-4",
            "nil-version-4",
            "uuid4-string-version-4",
            "uuid4-string-version-1",
            "uuid1-string-version-4",
            "uppercase-version-4",
            "urn-version-4",
            "hex-version-4",
            "nil-string-version-4",
            "invalid-string",
            "none",
            "int",
            "bytes",
        ],
    )
    def test_matches_requested_version(
        self, value: object, version: int, matched: bool
    ) -> None:
        assert IsUUID(version=version).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "matched"),
        list[tuple[object, bool]](
            [
                (UUID4, True),
                (UUID1, True),
                (UUID5, True),
                (UUID(int=0), True),
                (str(UUID5), True),
                ("{" + str(UUID4) + "}", True),
                ("not-a-uuid", False),
                ("", False),
                (" " + str(UUID4), False),
                (None, False),
                (UUID4.bytes, False),
            ]
        ),
        ids=[
            "uuid4",
            "uuid1",
            "uuid5",
            "nil",
            "string",
            "braces",
            "invalid-string",
            "empty-string",
            "leading-space",
            "none",
            "bytes",
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
        list[tuple[object, bool]](
            [
                (Item("n"), True),
                (FrozenItem("n"), True),
                (SlotsItem("n"), True),
                (ItemChild("n"), True),
                (Made("n"), True),
                (Item, False),
                (FrozenItem, False),
                (SlotsItem, False),
                (ItemChild, False),
                (Made, False),
                (Plain(), False),
                (Plain, False),
                (Point("n"), False),
                (object(), False),
                (None, False),
                ("n", False),
            ]
        ),
        ids=[
            "instance",
            "frozen-instance",
            "slots-instance",
            "subclass-instance",
            "made-instance",
            "class",
            "frozen-class",
            "slots-class",
            "subclass",
            "made-class",
            "plain-instance",
            "plain-class",
            "namedtuple",
            "object",
            "none",
            "str",
        ],
    )
    def test_matches_an_instance(self, value: object, matched: bool) -> None:
        assert IsDataclass(instance=True).matches(value) is matched

    @pytest.mark.parametrize(
        ("value", "matched"),
        list[tuple[object, bool]](
            [
                (Item("n"), True),
                (Item, True),
                (FrozenItem("n"), True),
                (FrozenItem, True),
                (SlotsItem("n"), True),
                (SlotsItem, True),
                (ItemChild("n"), True),
                (ItemChild, True),
                (Made("n"), True),
                (Made, True),
                (Plain(), False),
                (Plain, False),
                (Point, False),
                (1, False),
            ]
        ),
        ids=[
            "instance",
            "class",
            "frozen-instance",
            "frozen-class",
            "slots-instance",
            "slots-class",
            "subclass-instance",
            "subclass",
            "made-instance",
            "made-class",
            "plain-instance",
            "plain-class",
            "namedtuple",
            "int",
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
