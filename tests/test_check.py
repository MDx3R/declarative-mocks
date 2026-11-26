"""Tests for dmock._check."""

from __future__ import annotations

from dmock._check import Check, CheckAnd, CheckNot, CheckOr


class TestCheck:
    def test_single_predicate(self) -> None:
        # Arrange
        is_pos = Check[int](lambda x: x > 0)

        # Act & Assert
        assert is_pos(1) is True
        assert is_pos(0) is False

    def test_multiple_predicates_require_all(self) -> None:
        # Arrange
        in_range = Check[int](lambda x: x > 0, lambda x: x < 10)

        # Act & Assert
        assert in_range(5) is True
        assert in_range(0) is False
        assert in_range(10) is False

    def test_invert_negates_check(self) -> None:
        # Arrange
        non_zero = ~Check[int](lambda x: x == 0)

        # Act & Assert
        assert isinstance(non_zero, CheckNot)
        assert non_zero(1) is True
        assert non_zero(0) is False

    def test_and_with_callable_and_check(self) -> None:
        # Arrange
        def less(x: int) -> bool:
            return x < 10

        pos = Check[int](lambda x: x > 0)
        even = Check[int](lambda x: x % 2 == 0)

        # Act
        c1 = pos & less
        c2 = pos & even
        c3 = less & pos

        # Assert
        assert isinstance(c1, CheckAnd)
        assert isinstance(c2, CheckAnd)
        assert isinstance(c3, CheckAnd)
        assert c1(4) is True
        assert c1(12) is False
        assert c2(4) is True
        assert c2(3) is False
        assert c3(4) is True
        assert c3(-1) is False

    def test_or_with_callable_and_check(self) -> None:
        # Arrange
        def equals(x: int) -> bool:
            return x == 0

        neg = Check[int](lambda x: x < 0)
        big = Check[int](lambda x: x > 10)

        # Act
        c1 = neg | equals
        c2 = neg | big
        c3 = equals | neg

        # Assert
        assert isinstance(c1, CheckOr)
        assert isinstance(c2, CheckOr)
        assert isinstance(c3, CheckOr)
        assert c1(-1) is True
        assert c1(0) is True
        assert c1(1) is False
        assert c2(20) is True
        assert c2(5) is False
        assert c3(0) is True
        assert c3(5) is False

    def test_rand_and_ror_with_check_return_not_implemented(self) -> None:
        # Arrange
        a = Check[int](lambda x: x > 0)
        b = Check[int](lambda x: x < 10)

        # Act & Assert
        assert a.__rand__(b) is NotImplemented
        assert a.__ror__(b) is NotImplemented

    def test_repr_formats_class_and_predicates(self) -> None:
        # Arrange
        def p(x: int) -> bool:
            return x > 0

        c = Check(p)
        n = CheckNot(p)
        a = CheckAnd(p)
        o = CheckOr(p)

        # Act & Assert
        assert repr(c).startswith("Check(")
        assert repr(n).startswith("CheckNot(")
        assert repr(a).startswith("CheckAnd(")
        assert repr(o).startswith("CheckOr(")


class TestCheckCombinators:
    def test_check_not_with_multiple_predicates(self) -> None:
        # Arrange
        neither = CheckNot[int](lambda x: x == 1, lambda x: x == 2)

        # Act & Assert
        assert neither(3) is True
        assert neither(1) is False
        assert neither(2) is False

    def test_check_and_with_multiple_predicates(self) -> None:
        # Arrange
        both = CheckAnd[int](lambda x: x > 0, lambda x: x % 2 == 0)

        # Act & Assert
        assert both(2) is True
        assert both(3) is False
        assert both(-2) is False

    def test_check_or_with_multiple_predicates(self) -> None:
        # Arrange
        either = CheckOr[int](lambda x: x < 0, lambda x: x > 10)

        # Act & Assert
        assert either(-1) is True
        assert either(11) is True
        assert either(5) is False
