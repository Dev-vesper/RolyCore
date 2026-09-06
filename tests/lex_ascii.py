import pytest

from roly.lexer import LexError, Lexer
from roly.tokens import T


def tokens_of(source):
    return Lexer(source).tokenize()


def test_superscript_digit_rejected():
    with pytest.raises(LexError):
        tokens_of("x = ²")


def test_arabic_indic_digits_rejected():
    with pytest.raises(LexError):
        tokens_of("١٢")


def test_mixed_unicode_digits_rejected():
    with pytest.raises(LexError):
        tokens_of("1٢3")


def test_unicode_identifier_rejected():
    with pytest.raises(LexError):
        tokens_of("变量 = 5")


def test_unicode_letter_in_identifier_rejected():
    with pytest.raises(LexError):
        tokens_of("café = 1")


def test_nbsp_is_not_whitespace():
    with pytest.raises(LexError):
        tokens_of("x\u00a0= 5")


def test_ascii_identifier_with_underscore_digits():
    token = tokens_of("x_2y")[0]
    assert token.type is T.IDENT
    assert token.value == "x_2y"


def test_ascii_digits_still_work():
    token = tokens_of("123")[0]
    assert token.value == 123


def test_unicode_allowed_inside_string_literals():
    token = tokens_of('"héllo"')[0]
    assert token.value == "héllo"


def test_arabic_digits_inside_string_literals():
    token = tokens_of('"1٢3"')[0]
    assert token.value == "1٢3"
