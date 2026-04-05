"""Tests for dmock._expectation."""

from __future__ import annotations

import pytest

from dmock._exceptions import ConfigurationError, UnexpectedCallError
from dmock._expectation import Expectation
from dmock._matchers import ANY_ARGS, ANY_KWARGS, Anything, AnythingOfType, MatchedBy
from dmock._types import (
    AtLeast,
    Between,
    DefaultOutcome,
    ExactlyN,
    Never,
    RaiseOutcome,
    ReturnOutcome,
    RunOutcome,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make(name: str = "method", *args: object, **kwargs: object) -> Expectation:
    return Expectation(name, args, kwargs)


# ---------------------------------------------------------------------------
# Quantifier types -- construction and validation
# ---------------------------------------------------------------------------


class TestQuantifierTypes:
    def test_exactly_n_valid(self) -> None:
        q = ExactlyN(3)
        assert q.n == 3
        assert q.max_calls == 3

    def test_exactly_n_zero_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            ExactlyN(0)

    def test_exactly_n_negative_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            ExactlyN(-1)

    def test_at_least_valid(self) -> None:
        q = AtLeast(2)
        assert q.n == 2
        assert q.max_calls is None

    def test_at_least_zero_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            AtLeast(0)

    def test_at_least_negative_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            AtLeast(-1)

    def test_between_valid(self) -> None:
        q = Between(1, 3)
        assert q.lo == 1
        assert q.hi == 3
        assert q.max_calls == 3

    def test_between_lo_equals_hi_valid(self) -> None:
        q = Between(2, 2)
        assert q.max_calls == 2

    def test_between_lo_zero_valid(self) -> None:
        q = Between(0, 5)
        assert q.lo == 0

    def test_between_lo_greater_than_hi_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            Between(3, 1)

    def test_between_negative_lo_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            Between(-1, 2)

    def test_never_max_calls_zero(self) -> None:
        assert Never().max_calls == 0

    def test_never_equality(self) -> None:
        assert Never() == Never()

    def test_exactly_n_equality(self) -> None:
        assert ExactlyN(3) == ExactlyN(3)
        assert ExactlyN(3) != ExactlyN(4)

    def test_quantifier_is_satisfied_and_exhausted(self) -> None:
        assert ExactlyN(2).is_satisfied(2) is True
        assert ExactlyN(2).is_satisfied(1) is False
        assert ExactlyN(2).is_exhausted(2) is True
        assert ExactlyN(2).is_exhausted(1) is False

        assert AtLeast(2).is_satisfied(2) is True
        assert AtLeast(2).is_satisfied(1) is False
        assert AtLeast(2).is_exhausted(100) is False

        assert Between(1, 3).is_satisfied(1) is True
        assert Between(1, 3).is_satisfied(0) is False
        assert Between(1, 3).is_exhausted(3) is True
        assert Between(1, 3).is_exhausted(2) is False

        assert Between(0, 2).is_satisfied(0) is True  # at_most semantics
        assert Between(0, 2).is_exhausted(2) is True

        assert Never().is_satisfied(0) is True
        assert Never().is_satisfied(1) is False
        assert Never().is_exhausted(0) is False  # stays active for dispatch


# ---------------------------------------------------------------------------
# Matching -- positional args
# ---------------------------------------------------------------------------


class TestMatchingPositional:
    def test_no_args_matches_empty_call(self) -> None:
        exp = make("f")
        assert exp.matches((), {}) is True

    def test_no_args_rejects_positional(self) -> None:
        exp = make("f")
        assert exp.matches((1,), {}) is False

    def test_exact_positional_match(self) -> None:
        exp = make("f", 1, 2)
        assert exp.matches((1, 2), {}) is True

    def test_exact_positional_mismatch_value(self) -> None:
        exp = make("f", 1, 2)
        assert exp.matches((1, 3), {}) is False

    def test_exact_positional_mismatch_length(self) -> None:
        exp = make("f", 1, 2)
        assert exp.matches((1,), {}) is False

    def test_anything_matcher_in_positional(self) -> None:
        exp = make("f", Anything)
        assert exp.matches((42,), {}) is True
        assert exp.matches(("x",), {}) is True

    def test_anything_callable_in_positional(self) -> None:
        exp = make("f", Anything())
        assert exp.matches((99,), {}) is True

    def test_anything_of_type_in_positional(self) -> None:
        exp = make("f", AnythingOfType(int))
        assert exp.matches((5,), {}) is True
        assert exp.matches(("s",), {}) is False

    def test_matched_by_in_positional(self) -> None:
        exp = make("f", MatchedBy(lambda x: isinstance(x, int) and x > 0))
        assert exp.matches((3,), {}) is True
        assert exp.matches((-1,), {}) is False


# ---------------------------------------------------------------------------
# Matching -- keyword args
# ---------------------------------------------------------------------------


class TestMatchingKeyword:
    def test_exact_kwargs_match(self) -> None:
        exp = Expectation("f", (), {"x": 1, "y": 2})
        assert exp.matches((), {"x": 1, "y": 2}) is True

    def test_kwargs_mismatch_value(self) -> None:
        exp = Expectation("f", (), {"x": 1})
        assert exp.matches((), {"x": 99}) is False

    def test_kwargs_mismatch_key(self) -> None:
        exp = Expectation("f", (), {"x": 1})
        assert exp.matches((), {"y": 1}) is False

    def test_kwargs_extra_key_rejected(self) -> None:
        exp = Expectation("f", (), {"x": 1})
        assert exp.matches((), {"x": 1, "y": 2}) is False

    def test_matcher_in_kwargs(self) -> None:
        exp = Expectation("f", (), {"x": AnythingOfType(str)})
        assert exp.matches((), {"x": "hello"}) is True
        assert exp.matches((), {"x": 42}) is False


# ---------------------------------------------------------------------------
# Matching -- mixed args + kwargs
# ---------------------------------------------------------------------------


class TestMatchingMixed:
    def test_positional_and_kwargs(self) -> None:
        exp = Expectation("f", (1,), {"key": "val"})
        assert exp.matches((1,), {"key": "val"}) is True

    def test_positional_mismatch_but_kwargs_ok(self) -> None:
        exp = Expectation("f", (1,), {"key": "val"})
        assert exp.matches((2,), {"key": "val"}) is False


# ---------------------------------------------------------------------------
# Matching -- sentinels
# ---------------------------------------------------------------------------


class TestMatchingSentinels:
    def test_any_args_accepts_any_positional(self) -> None:
        exp = Expectation("f", (ANY_ARGS,), {})
        assert exp.matches((1, 2, 3), {}) is True
        assert exp.matches((), {}) is True

    def test_any_kwargs_accepts_any_kwargs(self) -> None:
        exp = Expectation("f", (ANY_KWARGS,), {})
        assert exp.matches((), {"a": 1, "b": 2}) is True
        assert exp.matches((), {}) is True

    def test_both_sentinels_accepts_anything(self) -> None:
        exp = Expectation("f", (ANY_ARGS, ANY_KWARGS), {})
        assert exp.matches((1, 2), {"x": "y"}) is True
        assert exp.matches((), {}) is True

    def test_any_args_with_expected_kwargs(self) -> None:
        exp = Expectation("f", (ANY_ARGS,), {"key": "val"})
        assert exp.matches((1, 2), {"key": "val"}) is True
        assert exp.matches((1, 2), {"key": "wrong"}) is False

    def test_any_kwargs_with_expected_args(self) -> None:
        exp = Expectation("f", (1, 2, ANY_KWARGS), {})
        assert exp.matches((1, 2), {}) is True
        assert exp.matches((), {}) is False


# ---------------------------------------------------------------------------
# Outcome sequencing
# ---------------------------------------------------------------------------


class TestOutcomeSequencing:
    def test_single_returns(self) -> None:
        exp = make("f").returns("ok").once()
        assert exp.consume() == ReturnOutcome("ok")

    def test_single_raises(self) -> None:
        exp = make("f").raises(ValueError).at_least(1)
        assert exp.consume() == RaiseOutcome(ValueError)

    def test_single_runs(self) -> None:
        fn = lambda: None  # noqa: E731
        exp = make("f").runs(fn).at_least(1)
        assert exp.consume() == RunOutcome(fn)

    def test_chained_returns_sequence(self) -> None:
        exp = make("f").returns("a").returns("b")
        assert exp.consume() == ReturnOutcome("a")
        assert exp.consume() == ReturnOutcome("b")

    def test_last_outcome_repeats_after_list_end(self) -> None:
        exp = make("f").returns("a").returns("b").at_least(1)
        exp.consume()  # "a"
        exp.consume()  # "b"
        assert exp.consume() == ReturnOutcome("b")  # repeats last

    def test_no_outcomes_returns_default(self) -> None:
        exp = make("f").at_least(1)
        assert exp.consume() == DefaultOutcome()


# ---------------------------------------------------------------------------
# Quantifiers -- satisfied / exhausted via Expectation
# ---------------------------------------------------------------------------


class TestQuantifierOnce:
    def setup_method(self) -> None:
        self.exp = make("f").returns("x").once()

    def test_not_satisfied_before_call(self) -> None:
        assert self.exp.is_satisfied() is False

    def test_satisfied_after_one_call(self) -> None:
        self.exp.consume()
        assert self.exp.is_satisfied() is True

    def test_exhausted_after_one_call(self) -> None:
        self.exp.consume()
        assert self.exp.is_exhausted() is True

    def test_not_exhausted_before_call(self) -> None:
        assert self.exp.is_exhausted() is False


class TestQuantifierTwice:
    def setup_method(self) -> None:
        self.exp = make("f").returns("x").twice()

    def test_not_satisfied_after_one(self) -> None:
        self.exp.consume()
        assert self.exp.is_satisfied() is False

    def test_satisfied_after_two(self) -> None:
        self.exp.consume()
        self.exp.consume()
        assert self.exp.is_satisfied() is True

    def test_exhausted_after_two(self) -> None:
        self.exp.consume()
        self.exp.consume()
        assert self.exp.is_exhausted() is True


class TestQuantifierTimesN:
    def test_satisfied_exactly_at_n(self) -> None:
        exp = make("f").returns("x").times(3)
        for _ in range(3):
            exp.consume()
        assert exp.is_satisfied() is True
        assert exp.is_exhausted() is True

    def test_not_satisfied_before_n(self) -> None:
        exp = make("f").returns("x").times(3)
        exp.consume()
        exp.consume()
        assert exp.is_satisfied() is False


class TestQuantifierAtLeast:
    def test_not_satisfied_before_min(self) -> None:
        exp = make("f").returns("x").at_least(2)
        exp.consume()
        assert exp.is_satisfied() is False

    def test_satisfied_at_min(self) -> None:
        exp = make("f").returns("x").at_least(2)
        exp.consume()
        exp.consume()
        assert exp.is_satisfied() is True

    def test_never_exhausted(self) -> None:
        exp = make("f").returns("x").at_least(1)
        for _ in range(100):
            exp.consume()
        assert exp.is_exhausted() is False


class TestQuantifierAtMost:
    def test_satisfied_at_zero_calls(self) -> None:
        exp = make("f").returns("x").at_most(2)
        assert exp.is_satisfied() is True

    def test_exhausted_at_max(self) -> None:
        exp = make("f").returns("x").at_most(2)
        exp.consume()
        exp.consume()
        assert exp.is_exhausted() is True

    def test_not_exhausted_before_max(self) -> None:
        exp = make("f").returns("x").at_most(2)
        exp.consume()
        assert exp.is_exhausted() is False


class TestQuantifierBetween:
    def test_not_satisfied_before_lo(self) -> None:
        exp = make("f").returns("x").between(2, 4)
        exp.consume()
        assert exp.is_satisfied() is False

    def test_satisfied_at_lo(self) -> None:
        exp = make("f").returns("x").between(2, 4)
        exp.consume()
        exp.consume()
        assert exp.is_satisfied() is True

    def test_exhausted_at_hi(self) -> None:
        exp = make("f").returns("x").between(2, 4)
        for _ in range(4):
            exp.consume()
        assert exp.is_exhausted() is True


class TestQuantifierMaybe:
    def test_always_satisfied_at_zero_calls(self) -> None:
        exp = make("f").returns("x").maybe()
        assert exp.is_satisfied() is True

    def test_once_maybe_satisfied_before_call(self) -> None:
        exp = make("f").returns("x").once().maybe()
        assert exp.is_satisfied() is True

    def test_once_maybe_satisfied_after_call(self) -> None:
        exp = make("f").returns("x").once().maybe()
        exp.consume()
        assert exp.is_satisfied() is True

    def test_maybe_then_count_satisfied_before_call(self) -> None:
        exp = make("f").returns("x").maybe().once()
        assert exp.is_satisfied() is True

    def test_optional_flag_set(self) -> None:
        exp = make("f").returns("x").maybe()
        assert exp.is_optional() is True

    def test_maybe_does_not_lock_quantifier(self) -> None:
        exp = make("f").maybe()
        assert exp.is_quantifier_locked is False


class TestQuantifierNever:
    def test_satisfied_when_uncalled(self) -> None:
        exp = make("f").never()
        assert exp.is_satisfied() is True

    def test_consume_raises_unexpected_call(self) -> None:
        exp = make("f").never()
        with pytest.raises(UnexpectedCallError):
            exp.consume()

    def test_is_not_exhausted_for_dispatch_safety(self) -> None:
        exp = make("f").never()
        assert exp.is_exhausted() is False


# ---------------------------------------------------------------------------
# consume() raises on over-call (exhaustion guard)
# ---------------------------------------------------------------------------


class TestConsumeExhaustionGuard:
    def test_once_raises_on_second_call(self) -> None:
        exp = make("f").returns("x").once()
        exp.consume()
        with pytest.raises(UnexpectedCallError):
            exp.consume()

    def test_twice_raises_on_third_call(self) -> None:
        exp = make("f").returns("x").twice()
        exp.consume()
        exp.consume()
        with pytest.raises(UnexpectedCallError):
            exp.consume()

    def test_between_raises_after_hi(self) -> None:
        exp = make("f").returns("x").between(1, 2)
        exp.consume()
        exp.consume()
        with pytest.raises(UnexpectedCallError):
            exp.consume()

    def test_at_least_never_raises(self) -> None:
        exp = make("f").returns("x").at_least(1)
        for _ in range(50):
            exp.consume()


# ---------------------------------------------------------------------------
# Auto-adjusted quantifier (no explicit quantifier set)
# ---------------------------------------------------------------------------


class TestAutoQuantifier:
    def test_one_outcome_means_exactly_once(self) -> None:
        exp = make("f").returns("a")
        assert exp.quantifier == ExactlyN(1)

    def test_two_outcomes_means_exactly_twice(self) -> None:
        exp = make("f").returns("a").returns("b")
        assert exp.quantifier == ExactlyN(2)

    def test_no_outcomes_means_exactly_once(self) -> None:
        exp = make("f")
        assert exp.quantifier == ExactlyN(1)

    def test_explicit_times_overrides_outcome_count(self) -> None:
        exp = make("f").returns("a").times(5)
        assert exp.quantifier == ExactlyN(5)

    def test_at_least_quantifier(self) -> None:
        exp = make("f").returns("a").at_least(2)
        assert exp.quantifier == AtLeast(2)

    def test_between_quantifier(self) -> None:
        exp = make("f").returns("a").between(1, 4)
        assert exp.quantifier == Between(1, 4)

    def test_at_most_maps_to_between(self) -> None:
        exp = make("f").returns("a").at_most(3)
        assert exp.quantifier == Between(0, 3)

    def test_never_quantifier(self) -> None:
        exp = make("f").never()
        assert exp.quantifier == Never()


# ---------------------------------------------------------------------------
# is_quantifier_locked
# ---------------------------------------------------------------------------


class TestIsQuantifierLocked:
    def test_not_locked_by_default(self) -> None:
        exp = make("f")
        assert exp.is_quantifier_locked is False

    def test_locked_after_once(self) -> None:
        exp = make("f").once()
        assert exp.is_quantifier_locked is True

    def test_not_locked_after_maybe_only(self) -> None:
        exp = make("f").maybe()
        assert exp.is_quantifier_locked is False

    def test_locked_after_maybe_then_once(self) -> None:
        exp = make("f").maybe().once()
        assert exp.is_quantifier_locked is True


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class TestConfigurationErrors:
    def test_once_then_twice_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            make("f").returns("x").once().twice()

    def test_times_then_at_least_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            make("f").returns("x").times(3).at_least(1)

    def test_once_then_maybe_ok(self) -> None:
        exp = make("f").returns("x").once().maybe()
        assert exp.is_optional() is True

    def test_maybe_then_once_ok(self) -> None:
        exp = make("f").returns("x").maybe().once()
        assert exp.is_quantifier_locked is True

    def test_times_zero_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            make("f").times(0)

    def test_at_least_zero_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            make("f").at_least(0)

    def test_between_inverted_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            make("f").between(5, 2)


# ---------------------------------------------------------------------------
# call_count property
# ---------------------------------------------------------------------------


class TestCallCount:
    def test_zero_initially(self) -> None:
        exp = make("f").at_least(1)
        assert exp.call_count == 0

    def test_increments_per_consume(self) -> None:
        exp = make("f").returns("x").at_least(1)
        exp.consume()
        assert exp.call_count == 1
        exp.consume()
        assert exp.call_count == 2


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


class TestRepr:
    def test_contains_method_name(self) -> None:
        exp = make("my_method")
        assert "my_method" in repr(exp)

    def test_contains_positional_args(self) -> None:
        exp = make("f", 1, "hello")
        r = repr(exp)
        assert "1" in r
        assert "'hello'" in r

    def test_contains_kwargs(self) -> None:
        exp = Expectation("f", (), {"key": 42})
        assert "key=42" in repr(exp)

    def test_contains_any_args_sentinel(self) -> None:
        exp = Expectation("f", (ANY_ARGS,), {})
        assert "ANY_ARGS" in repr(exp)

    def test_contains_any_kwargs_sentinel(self) -> None:
        exp = Expectation("f", (ANY_KWARGS,), {})
        assert "ANY_KWARGS" in repr(exp)
