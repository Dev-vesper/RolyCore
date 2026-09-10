import pytest

from roly.ast import BinOp, Chain, Num, Print, Str, Var
from roly.lexer import LexError, Lexer
from roly.parser import ParseError, Parser


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_string_primary():
    assert parse('x = "hi"').statements[0].value == Str("hi")


def test_string_in_expression():
    assert parse('x = "a" + "b"').statements[0].value == BinOp(
        "+", Str("a"), Str("b")
    )


def test_string_concat_binds_after_multiplication_level():
    assert parse('x = "a" + "b"').statements[0].value == BinOp(
        "+", Str("a"), Str("b")
    )


def test_string_with_number_literal():
    assert parse('x = "n" + "5"').statements[0].value == BinOp(
        "+", Str("n"), Str("5")
    )


def test_string_compared_in_condition():
    program = parse('if ("a" == "a") { x = 1 }')
    assert program.statements[0].condition == Chain([Str("a"), Str("a")], ["=="])


def test_string_variable_expression():
    assert parse('x = y + "!"').statements[0].value == BinOp(
        "+", Var("y"), Str("!")
    )


def test_string_in_parentheses():
    assert parse('x = ("hi")').statements[0].value == Str("hi")


def test_empty_string_parses():
    assert parse('x = ""').statements[0].value == Str("")


def test_print_with_string():
    assert parse('print("hello")').statements[0] == Print(Str("hello"))


def test_number_then_string_in_expression():
    program = parse('x = 5 y = "five"')
    assert program.statements[0].value == Num(5)
    assert program.statements[1].value == Str("five")


@pytest.mark.parametrize("source", ['print("hi"'])
def test_string_parse_errors(source):
    with pytest.raises(ParseError):
        parse(source)


@pytest.mark.parametrize("source", ['x = "unclosed', 'x = "bad \\ q"'])
def test_string_lex_errors(source):
    with pytest.raises(LexError):
        parse(source)
