import pytest

from roly.lexer import Lexer
from roly.parser import ParseError, Parser


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_bare_identifier_not_a_statement():
    with pytest.raises(ParseError):
        parse("x")


def test_identifier_without_assignment_operator():
    with pytest.raises(ParseError):
        parse("x + 1")


def test_identifier_followed_by_number():
    with pytest.raises(ParseError):
        parse("x 5")


def test_missing_expression_after_assign():
    with pytest.raises(ParseError):
        parse("x =")


def test_missing_expression_after_compound_assign():
    with pytest.raises(ParseError):
        parse("x +=")


def test_unary_minus_not_supported():
    with pytest.raises(ParseError):
        parse("x = -5")


def test_unclosed_parenthesis():
    with pytest.raises(ParseError):
        parse("x = (1 + 2")


def test_empty_parentheses():
    with pytest.raises(ParseError):
        parse("x = ()")


def test_stray_closing_parenthesis():
    with pytest.raises(ParseError):
        parse("x = 1)")


def test_if_without_condition_parens():
    with pytest.raises(ParseError):
        parse("if x { }")


def test_if_without_block():
    with pytest.raises(ParseError):
        parse("if (x)")


def test_else_without_block():
    with pytest.raises(ParseError):
        parse("if (x) { } else")


def test_else_followed_by_statement():
    with pytest.raises(ParseError):
        parse("if (x) { } else x = 1")


def test_while_without_condition_parens():
    with pytest.raises(ParseError):
        parse("while x { }")


def test_while_without_block():
    with pytest.raises(ParseError):
        parse("while (x)")


def test_unclosed_block():
    with pytest.raises(ParseError):
        parse("while (x) { x -= 1")


def test_stray_closing_brace_at_top_level():
    with pytest.raises(ParseError):
        parse("}")


def test_statement_starting_with_number():
    with pytest.raises(ParseError):
        parse("5 = x")


def test_statement_starting_with_operator():
    with pytest.raises(ParseError):
        parse("+ x")


def test_error_carries_token_position():
    with pytest.raises(ParseError) as excinfo:
        parse("x = 5\n@")
    assert excinfo.value.token.line == 2
    assert excinfo.value.token.column == 1


def test_error_position_after_newline():
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\ny")
    assert excinfo.value.token.line == 2
    assert excinfo.value.token.column == 1


def test_error_message_mentions_location():
    with pytest.raises(ParseError, match="line 1"):
        parse("x =")
