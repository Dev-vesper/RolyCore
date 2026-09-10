import pytest

from roly.ast import Call, Num, Str
from roly.errors import RolyError
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_parse_format_call():
    assert parse('x = format("{}")').statements[0].value == Call(
        "format", [Str("{}")]
    )


def test_parse_format_multiple_args():
    node = parse('x = format("{} {}", 1, 2)').statements[0].value
    assert node.name == "format"
    assert node.args == [Str("{} {}"), Num(1), Num(2)]


def test_format_single_placeholder():
    assert run_source('x = format("{}", 42)')["x"] == "42"


def test_format_sequential_placeholders():
    assert run_source('x = format("{} + {} = {}", 1, 2, 3)')["x"] == "1 + 2 = 3"


def test_format_converts_each_argument():
    env = run_source(
        'x = format("{} {} {}", TRUE, FALSE, -7)'
    )
    assert env["x"] == "True False -7"


def test_format_positional_reuse():
    assert run_source('x = format("{0}-{1}-{0}", "a", "b")')["x"] == "a-b-a"


def test_format_skips_index():
    assert run_source('x = format("{1} then {0}", "a", "b")')["x"] == "b then a"


def test_format_brace_escapes():
    assert run_source('x = format("{{}}")')["x"] == "{}"
    assert run_source('x = format("}}")')["x"] == "}"
    assert run_source('x = format("{{{{}}}}")')["x"] == "{{}}"


def test_format_plain_string():
    assert run_source('x = format("plain")')["x"] == "plain"
    assert run_source('x = format("")')["x"] == ""


def test_format_extra_arguments_ignored():
    assert run_source('x = format("{} end", 1, 2, 3)')["x"] == "1 end"


def test_format_works_with_expressions():
    assert run_source('x = format("n={}", 6 * 7)')["x"] == "n=42"


def test_format_with_lib_and_builtin_values():
    assert run_source('x = format("{}-{}", gcd(12, 8), int("7"))')["x"] == "4-7"


def test_format_in_print():
    printed = []
    run_source('print(format("x={} y={}", 1, "a"))', out=printed.append)
    assert printed == ["x=1 y=a"]


def test_format_in_condition_via_comparison():
    env = run_source('ok = format("{}", 1) == "1"')
    assert env["ok"] is True


def test_format_missing_argument_errors():
    with pytest.raises(RolyError, match="no argument for placeholder 0"):
        run_source('x = format("{} and {}")')


def test_format_missing_later_argument_errors():
    with pytest.raises(RolyError, match="no argument for placeholder 1"):
        run_source('x = format("{} and {}", 1)')


def test_format_index_out_of_range_errors():
    with pytest.raises(RolyError, match="no argument for placeholder 2"):
        run_source('x = format("{2}", 1, 2)')


def test_format_single_closing_brace_errors():
    with pytest.raises(RolyError, match="single '}'"):
        run_source('x = format("a}b")')


def test_format_unmatched_opening_brace_errors():
    with pytest.raises(RolyError, match="unmatched"):
        run_source('x = format("{")')


def test_format_invalid_placeholder_errors():
    with pytest.raises(RolyError, match="invalid placeholder"):
        run_source('x = format("{abc}")')


def test_format_negative_index_placeholder_errors():
    with pytest.raises(RolyError, match="invalid placeholder"):
        run_source('x = format("{-1}")')


def test_format_mixing_auto_and_manual_errors():
    with pytest.raises(RolyError, match="cannot mix"):
        run_source('x = format("{} {0}", 1)')


def test_format_mixing_manual_and_auto_errors():
    with pytest.raises(RolyError, match="cannot mix"):
        run_source('x = format("{0} {}", 1)')


def test_format_non_string_format_errors():
    with pytest.raises(RolyError, match="expects a str"):
        run_source("x = format(42)")


def test_format_zero_arguments_errors():
    with pytest.raises(RolyError, match="expects a format string"):
        run_source("x = format()")


def test_format_name_reserved_as_variable():
    with pytest.raises(RolyError, match="builtin"):
        run_source("format = 5")


def test_format_name_reserved_as_function():
    with pytest.raises(RolyError, match="builtin"):
        run_source("fn format (a: int) { return a }")


def test_len_and_char_names_reserved():
    with pytest.raises(RolyError, match="builtin"):
        run_source("len = 5")
    with pytest.raises(RolyError, match="builtin"):
        run_source("char = 5")
    with pytest.raises(RolyError, match="builtin"):
        run_source("fn len (a: int) { return a }")
    with pytest.raises(RolyError, match="builtin"):
        run_source("fn char (a: int) { return a }")
