import pytest

from roly.interpreter import RolyError
from roly.utils.runner import run_source


def test_flat_addition_chain():
    assert run_source("x = 1" + " + 1" * 4999)["x"] == 5000


def test_flat_subtraction_chain():
    assert run_source("x = 10000" + " - 1" * 10000)["x"] == 0


def test_flat_multiplication_chain():
    assert run_source("x = 2" + " * 2" * 20)["x"] == 2**21


def test_flat_mixed_chain():
    assert run_source("x = 0" + " + 2 * 3" * 1000)["x"] == 6000


def test_flat_division_chain():
    assert run_source("x = 1024" + " / 2" * 10)["x"] == 1


def test_long_concatenation_chain():
    n = 3000
    source = "x = " + '"ab" + ' * n + '"ab"'
    assert run_source(source)["x"] == "ab" * (n + 1)


def test_leftmost_undefined_reported_first():
    with pytest.raises(RolyError, match="undefined variable 'a'"):
        run_source("x = a + b")


def test_leftmost_error_wins_in_subtraction():
    with pytest.raises(RolyError, match="undefined variable 'a'"):
        run_source("x = a - b")


def test_division_by_zero_before_right_operand():
    with pytest.raises(RolyError, match="division by zero"):
        run_source("x = 1 / 0 + b")


def test_right_operand_error_after_left():
    with pytest.raises(RolyError, match="undefined variable 'b'"):
        run_source("x = 5 + b")


def test_nested_parens_value():
    source = "x = " + "(" * 90 + "7" + ")" * 90
    assert run_source(source)["x"] == 7


def test_left_deep_chain_inside_loop():
    source = "n = 0 while (n < 10) { n += 1 i = " + "1 + " * 200 + "0 }"
    assert run_source(source)["i"] == 200
