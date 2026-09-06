import pytest

from roly.interpreter import DEFAULT_MAX_STEPS, Interpreter, RolyError
from roly.lexer import Lexer
from roly.parser import Parser
from roly.utils.runner import run_source


def interpret(source, max_steps=DEFAULT_MAX_STEPS):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return Interpreter(max_steps=max_steps).run(program)


def test_step_limit_infinite_while():
    with pytest.raises(RolyError, match="step limit"):
        interpret("while (1) { }", max_steps=10)


def test_step_limit_infinite_compound():
    with pytest.raises(RolyError, match="step limit"):
        interpret("x = 1 while (x > 0) { x += 1 }", max_steps=25)


def test_step_limit_allows_finite_program():
    env = interpret("i = 0 while (i < 5) { i += 1 }", max_steps=100)
    assert env["i"] == 5


def test_default_step_is_large():
    assert DEFAULT_MAX_STEPS >= 1_000_000


def test_division_by_zero_message():
    with pytest.raises(RolyError, match="division by zero"):
        interpret("x = 1 / 0")


def test_division_by_zero_from_variable():
    with pytest.raises(RolyError):
        interpret("z = 0 y = 5 / z")


def test_undefined_variable_message():
    with pytest.raises(RolyError, match="undefined variable 'nope'"):
        interpret("x = nope")


def test_undefined_variable_in_condition():
    with pytest.raises(RolyError, match="undefined variable 'n'"):
        interpret("while (n < 3) { n += 1 }")


def test_type_error_adding_bool():
    with pytest.raises(RolyError, match="integer operands"):
        interpret("x = 1 == 1 y = x + 2")


def test_type_error_ordering_bool():
    with pytest.raises(RolyError, match="integer operands"):
        interpret("x = 1 == 1 y = x < 2")


def test_type_error_multiplying_bool():
    with pytest.raises(RolyError, match="integer operands"):
        interpret("x = 1 != 1 y = 3 * x")


def test_equality_works_on_bools():
    env = interpret("x = 1 == 1 y = x == x")
    assert env["y"] is True


def test_interpreter_env_isolated_between_runs():
    interpret("x = 1")
    env = interpret("y = 2")
    assert "x" not in env


def test_unknown_operator_raises():
    with pytest.raises(RolyError):
        Interpreter().apply_op("%", 1, 2)


def test_fresh_interpreter_empty_env():
    assert Interpreter().env == {}
