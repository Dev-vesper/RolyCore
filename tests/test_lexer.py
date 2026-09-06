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


def test_identifier():
    tokens = Lexer("counter").tokenize()
    assert tokens[0].type is T.IDENT
    assert tokens[0].value == "counter"


def test_keywords():
    assert types("if") == [T.IF, T.EOF]
    assert types("else") == [T.ELSE, T.EOF]
    assert types("while") == [T.WHILE, T.EOF]


def test_keyword_prefixed_identifier():
    tokens = Lexer("ifx while_loop").tokenize()
    assert tokens[0].type is T.IDENT and tokens[0].value == "ifx"
    assert tokens[1].type is T.IDENT and tokens[1].value == "while_loop"


@pytest.mark.parametrize(
    "source, token_type, value",
    [
        ("=", T.ASSIGN, "="),
        ("+=", T.PLUS_ASSIGN, "+="),
        ("-=", T.MINUS_ASSIGN, "-="),
        ("*=", T.STAR_ASSIGN, "*="),
        ("/=", T.SLASH_ASSIGN, "/="),
        ("+", T.PLUS, "+"),
        ("-", T.MINUS, "-"),
        ("*", T.STAR, "*"),
        ("/", T.SLASH, "/"),
        ("==", T.EQ, "=="),
        ("!=", T.NE, "!="),
        ("<", T.LT, "<"),
        (">", T.GT, ">"),
        ("<=", T.LE, "<="),
        (">=", T.GE, ">="),
        ("(", T.LPAREN, "("),
        (")", T.RPAREN, ")"),
        ("{", T.LBRACE, "{"),
        ("}", T.RBRACE, "}"),
    ],
)
def test_operators(source, token_type, value):
    tokens = Lexer(source).tokenize()
    assert tokens[0].type is token_type
    assert tokens[0].value == value


def test_position_tracking():
    tokens = Lexer("x = 5\n  y").tokenize()
    assert (tokens[0].line, tokens[0].column) == (1, 1)
    assert (tokens[1].line, tokens[1].column) == (1, 3)
    y_token = tokens[3]
    assert (y_token.line, y_token.column) == (2, 3)


def test_adjacent_int_and_ident():
    tokens = Lexer("5x").tokenize()
    assert tokens[0].type is T.INT
    assert tokens[1].type is T.IDENT


def test_full_program():
    source = "x = 5 while (x > 0) { x -= 1 }"
    tokens = Lexer(source).tokenize()
    assert tokens[-1].type is T.EOF
    assert types(source) == [
        T.IDENT, T.ASSIGN, T.INT,
        T.WHILE, T.LPAREN, T.IDENT, T.GT, T.INT, T.RPAREN,
        T.LBRACE, T.IDENT, T.MINUS_ASSIGN, T.INT, T.RBRACE,
        T.EOF,
    ]


@pytest.mark.parametrize("source", ["@", "!", "$", "5 # 3"])
def test_invalid_character_raises(source):
    with pytest.raises(LexError):
        Lexer(source).tokenize()


def test_lex_error_position():
    with pytest.raises(LexError) as excinfo:
        Lexer("x = 5\n@").tokenize()
    assert excinfo.value.line == 2
    assert excinfo.value.column == 1
