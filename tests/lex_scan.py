import pytest

from roly.lexer import LexError, Lexer
from roly.tokens import T


def types(source):
    return [token.type for token in Lexer(source).tokenize()]


def test_int_literal():
    tokens = Lexer("42").tokenize()
    assert tokens[0].type is T.INT
    assert tokens[0].value == 42
    assert tokens[-1].type is T.EOF


def test_zero_literal():
    tokens = Lexer("0").tokenize()
    assert tokens[0].value == 0


def test_long_int_literal():
    tokens = Lexer("1234567").tokenize()
    assert tokens[0].value == 1234567


def test_identifier():
    tokens = Lexer("counter").tokenize()
    assert tokens[0].type is T.IDENT
    assert tokens[0].value == "counter"


def test_identifier_with_underscore_and_digits():
    tokens = Lexer("x_2_y").tokenize()
    assert tokens[0].type is T.IDENT
    assert tokens[0].value == "x_2_y"


def test_identifier_leading_underscore():
    tokens = Lexer("_hidden").tokenize()
    assert tokens[0].type is T.IDENT
    assert tokens[0].value == "_hidden"


def test_keywords():
    assert types("if") == [T.IF, T.EOF]
    assert types("else") == [T.ELSE, T.EOF]
    assert types("while") == [T.WHILE, T.EOF]


def test_keyword_prefixed_identifier():
    tokens = Lexer("ifx while_loop else1").tokenize()
    assert [t.value for t in tokens[:3]] == ["ifx", "while_loop", "else1"]
    assert all(t.type is T.IDENT for t in tokens[:3])


def test_whitespace_between_tokens():
    assert types("  x   =   5  ") == [T.IDENT, T.ASSIGN, T.INT, T.EOF]


def test_newlines_are_whitespace():
    assert types("x = 5\ny = 3\n") == [
        T.IDENT, T.ASSIGN, T.INT,
        T.IDENT, T.ASSIGN, T.INT,
        T.EOF,
    ]


def test_tabs_and_carriage_returns():
    assert types("x\t=\r5") == [T.IDENT, T.ASSIGN, T.INT, T.EOF]


def test_empty_source():
    assert types("") == [T.EOF]


def test_only_whitespace_source():
    assert types("  \n\t  \n") == [T.EOF]


def test_adjacent_int_and_ident():
    tokens = Lexer("5x").tokenize()
    assert tokens[0].type is T.INT
    assert tokens[1].type is T.IDENT


def test_full_program():
    source = "x = 5 while (x > 0) { x -= 1 }"
    assert types(source) == [
        T.IDENT, T.ASSIGN, T.INT,
        T.WHILE, T.LPAREN, T.IDENT, T.GT, T.INT, T.RPAREN,
        T.LBRACE, T.IDENT, T.MINUS_ASSIGN, T.INT, T.RBRACE,
        T.EOF,
    ]


def test_if_else_program():
    source = "if (x == 1) { y = 2 } else { y = 3 }"
    assert types(source) == [
        T.IF, T.LPAREN, T.IDENT, T.EQ, T.INT, T.RPAREN,
        T.LBRACE, T.IDENT, T.ASSIGN, T.INT, T.RBRACE,
        T.ELSE,
        T.LBRACE, T.IDENT, T.ASSIGN, T.INT, T.RBRACE,
        T.EOF,
    ]


@pytest.mark.parametrize("source", ["@", "!", "$", "%", "&", "5 # 3", "x = 5;"])
def test_invalid_character_raises(source):
    with pytest.raises(LexError):
        Lexer(source).tokenize()


def test_line_comment_skipped():
    assert types("x = 1 // trailing") == types("x = 1")


def test_line_comment_alone():
    assert types("// whole line\nx = 1") == types("x = 1")


def test_line_comment_at_eof_without_newline():
    assert types("x = 1 // end") == types("x = 1")


def test_only_comment_yields_eof():
    assert types("// nothing") == [T.EOF]


def test_comment_after_compound_slash_assign():
    assert types("x /= 2 // halve") == types("x /= 2")


def test_double_slash_in_string_is_content():
    tokens = Lexer('x = "http://roly"').tokenize()
    assert tokens[2].type is T.STRING
    assert tokens[2].value == "http://roly"
