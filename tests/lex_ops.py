import pytest

from roly.lexer import Lexer
from roly.tokens import T


def first(source):
    return Lexer(source).tokenize()[0]


@pytest.mark.parametrize(
    "source, token_type",
    [
        ("=", T.ASSIGN),
        ("+=", T.PLUS_ASSIGN),
        ("-=", T.MINUS_ASSIGN),
        ("*=", T.STAR_ASSIGN),
        ("/=", T.SLASH_ASSIGN),
        ("+", T.PLUS),
        ("-", T.MINUS),
        ("*", T.STAR),
        ("/", T.SLASH),
        ("==", T.EQ),
        ("!=", T.NE),
        ("<", T.LT),
        (">", T.GT),
        ("<=", T.LE),
        (">=", T.GE),
        ("(", T.LPAREN),
        (")", T.RPAREN),
        ("{", T.LBRACE),
        ("}", T.RBRACE),
    ],
)
def test_single_operator(source, token_type):
    token = first(source)
    assert token.type is token_type
    assert token.value == source


@pytest.mark.parametrize(
    "source, first_type, second_type",
    [
        ("== =", T.EQ, T.ASSIGN),
        ("= =", T.ASSIGN, T.ASSIGN),
        ("<=", T.LE, T.EOF),
        ("< =", T.LT, T.ASSIGN),
        (">=>", T.GE, T.GT),
        ("<==", T.LE, T.ASSIGN),
        ("<!=<", T.LT, T.NE),
        ("+ +=", T.PLUS, T.PLUS_ASSIGN),
        ("-=-", T.MINUS_ASSIGN, T.MINUS),
        ("*=", T.STAR_ASSIGN, T.EOF),
        ("/ /", T.SLASH, T.SLASH),
    ],
)
def test_two_char_ops_win_over_one_char(source, first_type, second_type):
    tokens = Lexer(source).tokenize()
    assert tokens[0].type is first_type
    assert tokens[1].type is second_type


def test_all_compound_ops_in_one_stream():
    tokens = Lexer("a += b -= c *= d /= e").tokenize()
    ops = [t.type for t in tokens if t.type in {T.PLUS_ASSIGN, T.MINUS_ASSIGN, T.STAR_ASSIGN, T.SLASH_ASSIGN}]
    assert ops == [T.PLUS_ASSIGN, T.MINUS_ASSIGN, T.STAR_ASSIGN, T.SLASH_ASSIGN]


def test_all_comparison_ops_in_one_stream():
    tokens = Lexer("a == b != c < d > e <= f >= g").tokenize()
    ops = [t.type for t in tokens if t.type in {T.EQ, T.NE, T.LT, T.GT, T.LE, T.GE}]
    assert ops == [T.EQ, T.NE, T.LT, T.GT, T.LE, T.GE]


def test_operator_values_preserved():
    tokens = Lexer("+ - * / == != < > <= >=").tokenize()
    assert [t.value for t in tokens[:-1]] == ["+", "-", "*", "/", "==", "!=", "<", ">", "<=", ">="]
