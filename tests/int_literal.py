import pytest

from roly.ast import BinOp, Bool, Neg, Num, Var
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.tokens import T
from roly.interpreter import RolyError
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_true_lexes_as_keyword():
    assert Lexer("TRUE").tokenize()[0].type is T.TRUE


def test_false_lexes_as_keyword():
    assert Lexer("FALSE").tokenize()[0].type is T.FALSE


def test_lowercase_true_is_ident():
    assert Lexer("true").tokenize()[0].type is T.IDENT


def test_lowercase_false_is_ident():
    assert Lexer("false").tokenize()[0].type is T.IDENT


def test_true_prefixed_ident_stays_ident():
    assert Lexer("TRUEX").tokenize()[0].type is T.IDENT


def test_parse_true_literal():
    assert parse("x = TRUE").statements[0].value == Bool(True)


def test_parse_false_literal():
    assert parse("x = FALSE").statements[0].value == Bool(False)


def test_bool_literals_in_condition():
    program = parse("if (TRUE) { x = 1 }")
    assert program.statements[0].condition == Bool(True)


def test_negative_number_parses():
    assert parse("x = -5").statements[0].value == Neg(Num(5))


def test_double_negative_parses():
    assert parse("x = --5").statements[0].value == Neg(Neg(Num(5)))


def test_negative_in_expression():
    assert parse("x = -5 + 3").statements[0].value == BinOp(
        "+", Neg(Num(5)), Num(3)
    )


def test_negative_applies_to_identifier():
    assert parse("x = -y").statements[0].value == Neg(Var("y"))


def test_negative_applies_to_call():
    program = parse("x = -f(1)")
    assert isinstance(program.statements[0].value, Neg)


def test_minus_still_binary_between_terms():
    assert parse("x = 5 - 3").statements[0].value == BinOp("-", Num(5), Num(3))


def test_evaluate_negative_literal():
    assert run_source("x = -5")["x"] == -5


def test_evaluate_double_negative():
    assert run_source("x = --5")["x"] == 5


def test_negative_in_arithmetic():
    assert run_source("x = -5 + 3")["x"] == -2


def test_negative_multiplication():
    assert run_source("x = -3 * -4")["x"] == 12


def test_negative_division():
    assert run_source("x = -7 / 2")["x"] == -4


def test_negative_from_variable():
    assert run_source("y = 3 x = -y")["x"] == -3


def test_negative_in_comparison():
    assert run_source("x = -5 < 0")["x"] is True


def test_true_and_false_values():
    env = run_source("B = TRUE Bv2 = FALSE")
    assert env["B"] is True
    assert env["Bv2"] is False


def test_bool_literals_compare():
    assert run_source("x = TRUE == TRUE")["x"] is True
    assert run_source("x = TRUE == FALSE")["x"] is False
    assert run_source("x = TRUE != FALSE")["x"] is True


def test_bool_literal_does_not_equal_int():
    assert run_source("x = TRUE == 1")["x"] is False
    assert run_source("x = FALSE == 0")["x"] is False


def test_bool_literal_as_condition():
    env = run_source("if (TRUE) { a = 1 } if (FALSE) { b = 1 }")
    assert env["a"] == 1
    assert "b" not in env


def test_bool_literal_in_while():
    env = run_source("i = 0 while (TRUE) { i += 1 if (i == 3) { break } }")
    assert env["i"] == 3


def test_bool_literal_arithmetic_still_errors():
    with pytest.raises(RolyError, match="integer operands"):
        run_source("x = TRUE + 1")


def test_negate_bool_errors():
    with pytest.raises(RolyError, match="integer operands"):
        run_source("x = -TRUE")


def test_negate_string_errors():
    with pytest.raises(RolyError, match="integer operands"):
        run_source('x = -"a"')


def test_bool_literal_as_function_arg():
    env = run_source(
        "fn f (b: bool) { return b } x = f(TRUE) y = f(FALSE)"
    )
    assert env["x"] is True
    assert env["y"] is False


def test_negative_arg_to_int_param():
    env = run_source("fn dbl (n: int) { return n * 2 } x = dbl(-4)")
    assert env["x"] == -8


def test_var_roly_style_program():
    printed = []
    run_source(
        'S = "STRINGS, abcdefghijklmnopqx" I = 1234567890 Iv2 = -123456789 '
        "B = TRUE Bv2 = FALSE "
        "print(S) print(I) print(Iv2) print(B) print(Bv2)",
        out=printed.append,
    )
    assert printed == [
        "STRINGS, abcdefghijklmnopqx",
        1234567890,
        -123456789,
        True,
        False,
    ]
