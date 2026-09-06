import pytest

from roly.lexer import LexError, Lexer
from roly.tokens import T


def tokens_of(source):
    return Lexer(source).tokenize()


def test_first_token_position():
    token = tokens_of("x")[0]
    assert (token.line, token.column) == (1, 1)


def test_position_advances_on_same_line():
    tokens = tokens_of("x = 5")
    assert (tokens[1].line, tokens[1].column) == (1, 3)
    assert (tokens[2].line, tokens[2].column) == (1, 5)


def test_position_resets_after_newline():
    tokens = tokens_of("x = 5\n  y")
    y_token = tokens[3]
    assert (y_token.line, y_token.column) == (2, 3)


def test_position_across_multiple_lines():
    tokens = tokens_of("a\n\n\n  b")
    b_token = tokens[1]
    assert (b_token.line, b_token.column) == (4, 3)


def test_newline_inside_expression():
    tokens = tokens_of("x =\n5")
    assert (tokens[2].line, tokens[2].column) == (2, 1)


def test_eof_position():
    tokens = tokens_of("x = 5\n")
    eof = tokens[-1]
    assert eof.type is T.EOF
    assert (eof.line, eof.column) == (2, 1)


def test_multi_char_token_start_position():
    tokens = tokens_of("a <= 3")
    assert (tokens[1].line, tokens[1].column) == (1, 3)


def test_lex_error_position():
    with pytest.raises(LexError) as excinfo:
        tokens_of("x = 5\n@")
    assert excinfo.value.line == 2
    assert excinfo.value.column == 1


def test_lex_error_position_mid_line():
    with pytest.raises(LexError) as excinfo:
        tokens_of("ab @")
    assert excinfo.value.line == 1
    assert excinfo.value.column == 4


def test_lex_error_message_mentions_location():
    with pytest.raises(LexError, match="line 2"):
        tokens_of("\n$")
