import pytest

from roly.lexer import Lexer
from roly.parser import MAX_NESTING, ParseError, Parser
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_max_nesting_is_100():
    assert MAX_NESTING == 100


def test_deeply_nested_parens_raise_parse_error():
    with pytest.raises(ParseError, match="nesting"):
        parse("x = " + "(" * 150 + "1" + ")" * 150)


def test_very_deep_parens_raise_quickly():
    with pytest.raises(ParseError):
        parse("x = " + "(" * 5000 + "1")


def test_deeply_nested_blocks_raise_parse_error():
    with pytest.raises(ParseError, match="nesting"):
        parse("{" * 150 + "}" * 150)


def test_very_deep_blocks_raise_quickly():
    with pytest.raises(ParseError):
        parse("{" * 5000 + "}" * 5000)


def test_deep_nesting_error_has_position():
    with pytest.raises(ParseError) as excinfo:
        parse("x = " + "(" * 101 + "1")
    assert excinfo.value.token.line == 1


def test_nested_parens_within_limit_parse():
    source = "x = " + "(" * 90 + "1 + 2" + ")" * 90
    program = parse(source)
    assert program.statements[0].name == "x"


def test_nested_parens_within_limit_evaluate():
    source = "x = " + "(" * 90 + "7" + ")" * 90
    assert run_source(source)["x"] == 7


def test_nested_blocks_within_limit_run():
    source = "x = 0 " + "{ x += 1 " * 90 + "}" * 90
    assert run_source(source)["x"] == 90


def test_nested_if_within_limit_run():
    source = "x = 0 " + "if (1) { " * 60 + "x = 1 " + "} " * 60
    assert run_source(source)["x"] == 1


def test_nested_while_within_limit_run():
    source = "n = 0 " + "while (n < 1) { n += 1 " * 60 + "}" * 60
    assert run_source(source)["n"] == 1


def test_sibling_blocks_do_not_accumulate_depth():
    source = "x = 0 " + "{ x += 1 } " * 500
    assert run_source(source)["x"] == 500


def test_sibling_parens_do_not_accumulate_depth():
    source = "x = " + "(1) + " * 500 + "0"
    assert run_source(source)["x"] == 500


def test_mixed_nesting_within_limit():
    n = 30
    source = "x = 1 " + "if (x) { " * n + "x = " + "(" * n + "x + 1" + ")" * n + "} " * n
    assert run_source(source)["x"] == 2


def test_deep_unary_minus_raises_parse_error():
    with pytest.raises(ParseError, match="nesting"):
        parse("x = " + "-" * 150 + "1")


def test_very_deep_unary_minus_raises_quickly():
    with pytest.raises(ParseError):
        parse("x = " + "-" * 5000 + "1")


def test_unary_minus_within_limit_parses_and_runs():
    assert run_source("x = " + "-" * 90 + "1")["x"] == 1


def test_unary_minus_error_has_position():
    with pytest.raises(ParseError) as excinfo:
        parse("x = " + "-" * 101 + "1")
    assert excinfo.value.token.line == 1


def test_unary_minus_mixed_with_parens_within_limit():
    source = "x = " + "-(" * 45 + "1" + ")" * 45
    assert run_source(source)["x"] == -1


def test_sibling_negations_do_not_accumulate_depth():
    source = "x = " + "-(-(-1)) + " * 100 + "0"
    assert run_source(source)["x"] == -100
