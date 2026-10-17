"""Tests for dmock._matchers."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from dmock import (
    ANY_ARGS,
    ANY_KWARGS,
    AWARE_DATETIME,
    EMPTY,
    FALSY,
    NAIVE_DATETIME,
    TRUTHY,
    And,
    Anything,
    AnythingOfType,
    Approx,
    Args,
    Attr,
    Contains,
    Empty,
    EndsWith,
    Equals,
    GreaterEquals,
    GreaterThan,
    In,
    Includes,
    Is,
    LessEquals,
    LessThan,
    MatchedBy,
    Matcher,
    Maybe,
    Never,
    Not,
    Nothing,
    Or,
    Range,
    Regex,
    RegexFullmatch,
    RegexMatch,
    RegexSearch,
    StartsWith,
)
from dmock._matchers import (
    _AnyArgsSentinel,  # pyright: ignore[reportPrivateUsage]
    _AnyKwargsSentinel,  # pyright: ignore[reportPrivateUsage]
)


class TestAnything:
    @pytest.mark.parametrize("value", [42, "hello", None, [1, 2, 3]])
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

    def test_repr(self) -> None:
        assert repr(AnythingOfType(int)) == "AnythingOfType(int)"

    def test_satisfies_matcher_protocol(self) -> None:
        assert isinstance(AnythingOfType(int), Matcher)


class TestMatchedBy:
    def test_matches_truthy_predicate(self) -> None:
        assert MatchedBy(lambda x: x > 0).matches(5) is True

    def test_rejects_falsy_predicate(self) -> None:
        assert MatchedBy(lambda x: x > 0).matches(-1) is False

    @pytest.mark.parametrize(("value", "expected"), [(4, True), (3, False)])
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
    @pytest.mark.parametrize("value", [0, "", None, Never])
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
    @pytest.mark.parametrize("value", ["a", 1, [0]])
    def test_truthy_matches(self, value: object) -> None:
        assert TRUTHY.matches(value) is True

    @pytest.mark.parametrize("value", ["", 0, None, []])
    def test_truthy_rejects_falsy(self, value: object) -> None:
        assert TRUTHY.matches(value) is False

    @pytest.mark.parametrize("value", ["", 0, None, []])
    def test_falsy_matches(self, value: object) -> None:
        assert FALSY.matches(value) is True

    @pytest.mark.parametrize("value", ["a", 1, [0]])
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
    @pytest.mark.parametrize("value", ["", [], {}, ()])
    def test_matches_empty_sized(self, value: object) -> None:
        assert Empty().matches(value) is True

    @pytest.mark.parametrize("value", ["a", [1], None, 0])
    def test_rejects_non_empty_or_unsized(self, value: object) -> None:
        assert Empty().matches(value) is False

    def test_empty_constant_is_an_empty_matcher(self) -> None:
        assert isinstance(EMPTY, Empty)
        assert EMPTY is not Empty()

    def test_repr(self) -> None:
        assert repr(EMPTY) == "Empty()"


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
    )
    def test_repr(self, matcher: Matcher, text: str) -> None:
        assert repr(matcher) == text


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
