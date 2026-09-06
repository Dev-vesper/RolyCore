import pytest

from roly.interpreter import RolyError
from roly.utils.runner import run_source


def env_of(source):
    return run_source(f"x = {source}")["x"]


def test_int_addition():
    assert env_of("2 + 3") == 5


def test_int_subtraction():
    assert env_of("10 - 4") == 6


def test_int_subtraction_negative_result():
    assert env_of("3 - 10") == -7


def test_int_multiplication():
    assert env_of("6 * 7") == 42


def test_multiplication_by_zero():
    assert env_of("5 * 0") == 0


def test_floor_division_exact():
    assert env_of("8 / 2") == 4


def test_floor_division_positive_rounds_down():
    assert env_of("7 / 2") == 3


def test_floor_division_negative_floor():
    assert run_source("x = 0 - 7 y = x / 2")["y"] == -4
    assert run_source("x = 0 - 1 y = x / 2")["y"] == -1


def test_floor_division_by_one():
    assert env_of("9 / 1") == 9


def test_division_by_zero_raises():
    with pytest.raises(RolyError, match="division by zero"):
        env_of("5 / 0")


def test_division_by_zero_in_loop():
    with pytest.raises(RolyError, match="division by zero"):
        run_source("x = 4 while (x >= 0) { x = x / 0 }")


def test_precedence_add_mul():
    assert env_of("1 + 2 * 3") == 7


def test_precedence_parentheses():
    assert env_of("(1 + 2) * 3") == 9


def test_left_associative_subtraction():
    assert env_of("10 - 3 - 2") == 5


def test_left_associative_division():
    assert env_of("100 / 5 / 2") == 10


def test_mixed_arith_chain():
    assert env_of("2 * 3 + 4 * 5 - 6 / 2") == 23


def test_arithmetic_with_variables():
    assert run_source("a = 3 b = 4 x = a * a + b * b")["x"] == 25


def test_comparison_returns_bool():
    assert env_of("3 < 5") is True
    assert env_of("5 < 3") is False


def test_equality_returns_bool():
    assert env_of("3 == 3") is True
    assert env_of("3 != 3") is False


def test_all_comparisons():
    assert env_of("1 < 2") is True
    assert env_of("2 < 1") is False
    assert env_of("1 > 2") is False
    assert env_of("2 > 1") is True
    assert env_of("2 <= 2") is True
    assert env_of("3 <= 2") is False
    assert env_of("2 >= 3") is False
    assert env_of("3 >= 3") is True
    assert env_of("3 == 3") is True
    assert env_of("3 == 4") is False
    assert env_of("3 != 4") is True
    assert env_of("3 != 3") is False


def test_comparison_of_arithmetic_results():
    assert env_of("2 + 2 == 4") is True


def test_arithmetic_on_bool_raises():
    with pytest.raises(RolyError, match="integer operands"):
        run_source("x = 1 < 2 y = x + 1")


def test_bool_comparison_of_bool_raises():
    with pytest.raises(RolyError, match="integer operands"):
        run_source("x = 1 < 2 y = x < 2")
