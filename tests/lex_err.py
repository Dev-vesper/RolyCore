import pytest

from roly.lexer import LexError, Lexer


@pytest.mark.parametrize(
    "source",
    [
        "@", "$", "%", "&", "5 # 3", "x = 5;",
        "x = ²", "١٢", "1٢3", "变量 = 5", "café = 1", "x\u00a0= 5",
    ],
)
def test_invalid_source_raises(source):
    with pytest.raises(LexError):
        Lexer(source).tokenize()


def test_unknown_escape_raises():
    with pytest.raises(LexError, match="unknown escape"):
        Lexer('"a\\qb"').tokenize()


def test_unterminated_string_raises():
    with pytest.raises(LexError, match="unterminated string"):
        Lexer('"hello').tokenize()


def test_string_cannot_span_lines():
    with pytest.raises(LexError, match="unterminated string"):
        Lexer('"line one\nline two"').tokenize()


def test_error_position_on_second_line():
    with pytest.raises(LexError) as excinfo:
        Lexer("x = 5\n@").tokenize()
    assert (excinfo.value.line, excinfo.value.column) == (2, 1)


def test_error_position_mid_line():
    with pytest.raises(LexError) as excinfo:
        Lexer("ab @").tokenize()
    assert (excinfo.value.line, excinfo.value.column) == (1, 4)


def test_string_error_reported_at_string_start():
    with pytest.raises(LexError) as excinfo:
        Lexer('x = 5\n"oops').tokenize()
    assert (excinfo.value.line, excinfo.value.column) == (2, 1)
    with pytest.raises(LexError) as excinfo:
        Lexer('  "\\q"').tokenize()
    assert excinfo.value.column == 3


def test_error_message_mentions_location():
    with pytest.raises(LexError, match="line 2"):
        Lexer("\n$").tokenize()
