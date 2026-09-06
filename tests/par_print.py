from roly.ast import Assign, BinOp, Block, If, Num, Print, Program, Var, While
import pytest

from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.tokens import T


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_print_lexes_as_keyword():
    tokens = Lexer("print").tokenize()
    assert tokens[0].type is T.PRINT


def test_print_prefixed_identifier_stays_ident():
    tokens = Lexer("printer printed").tokenize()
    assert all(t.type is T.IDENT for t in tokens[:2])


def test_parse_simple_print():
    assert parse("print(5)") == Program([Print(Num(5))])


def test_parse_print_identifier():
    assert parse("print(x)") == Program([Print(Var("x"))])


def test_parse_print_full_expression():
    assert parse("print(1 + 2 * 3)") == Program(
        [Print(BinOp("+", Num(1), BinOp("*", Num(2), Num(3))))]
    )


def test_print_inside_block():
    assert parse("{ print(1) }") == Program([Block([Print(Num(1))])])


def test_print_inside_while():
    assert parse("while (x) { print(x) }") == Program(
        [While(Var("x"), Block([Print(Var("x"))]))]
    )


def test_print_inside_if():
    assert parse("if (x) { print(1) } else { print(2) }") == Program(
        [
            If(
                Var("x"),
                Block([Print(Num(1))]),
                Block([Print(Num(2))]),
            )
        ]
    )


def test_print_as_last_statement():
    assert parse("x = 1 print(x)") == Program(
        [Assign("x", Num(1)), Print(Var("x"))]
    )


def test_print_missing_parens():
    with pytest.raises(ParseError):
        parse("print 5")


def test_print_missing_closing_paren():
    with pytest.raises(ParseError):
        parse("print(5")


def test_print_empty_parens():
    with pytest.raises(ParseError):
        parse("print()")


def test_print_missing_expression():
    with pytest.raises(ParseError):
        parse("print(")


def test_print_cannot_appear_in_expression():
    with pytest.raises(ParseError):
        parse("x = print(1)")


def test_print_error_position():
    with pytest.raises(ParseError) as excinfo:
        parse("print 5")
    assert excinfo.value.token.line == 1
