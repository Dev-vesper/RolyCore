import pytest

from roly.lexer import LexError, Lexer
from roly.tokens import T


def tokens_of(source):
    return Lexer(source).tokenize()


def test_empty_string():
    tokens = tokens_of('""')
    assert tokens[0].type is T.STRING
    assert tokens[0].value == ""


def test_simple_string():
    token = tokens_of('"hello"')[0]
    assert token.type is T.STRING
    assert token.value == "hello"


def test_string_with_spaces():
    assert tokens_of('"hello world"')[0].value == "hello world"


def test_string_can_contain_digits_and_operators():
    assert tokens_of('"x = 5 + 3"')[0].value == "x = 5 + 3"


def test_string_can_contain_single_quotes():
    assert tokens_of('"it\'s"')[0].value == "it's"


def test_escape_newline():
    assert tokens_of('"a\\nb"')[0].value == "a\nb"


def test_escape_tab():
    assert tokens_of('"a\\tb"')[0].value == "a\tb"


def test_escape_backslash():
    assert tokens_of('"a\\\\b"')[0].value == "a\\b"


def test_escape_double_quote():
    assert tokens_of('"say \\"hi\\""')[0].value == 'say "hi"'


def test_unknown_escape_raises():
    with pytest.raises(LexError, match="unknown escape"):
        tokens_of('"a\\qb"')


def test_unterminated_string_raises():
    with pytest.raises(LexError, match="unterminated string"):
        tokens_of('"hello')


def test_string_cannot_span_lines():
    with pytest.raises(LexError, match="unterminated string"):
        tokens_of('"line one\nline two"')


def test_string_with_escaped_quote_is_not_terminated_early():
    token = tokens_of('"a\\"b"')[0]
    assert token.value == 'a"b'
    assert tokens_of('"a\\"b"')[1].type is T.EOF


def test_adjacent_strings_are_separate_tokens():
    tokens = tokens_of('"a""b"')
    assert [t.value for t in tokens[:2]] == ["a", "b"]


def test_string_start_position():
    token = tokens_of('x = "hi"')[2]
    assert (token.line, token.column) == (1, 5)


def test_string_error_position():
    with pytest.raises(LexError) as excinfo:
        tokens_of('x = 5\n"oops')
    assert excinfo.value.line == 2
    assert excinfo.value.column == 1


def test_escape_position_reported_at_string_start():
    with pytest.raises(LexError) as excinfo:
        tokens_of('  "\\q"')
    assert excinfo.value.column == 3
