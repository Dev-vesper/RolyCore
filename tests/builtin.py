import pytest

from roly.ast import Bool, Call, Neg, Num, Program, Str
from roly.interpreter import RolyError
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_parse_int_builtin_call():
    assert parse("x = int(42)").statements[0].value == Call("int", [Num(42)])


def test_parse_str_builtin_call():
    assert parse('x = str("hi")').statements[0].value == Call("str", [Str("hi")])


def test_parse_bool_builtin_call():
    assert parse("x = bool(TRUE)").statements[0].value == Call("bool", [Bool(True)])


def test_parse_builtin_with_expression_argument():
    node = parse("x = int(a + 1)").statements[0].value
    assert node == Call("int", [Num(1)]) or node.name == "int"


def test_parse_negated_builtin_call():
    node = parse("x = -int(\"5\")").statements[0].value
    assert isinstance(node, Neg)
    assert node.operand.name == "int"


def test_builtin_inside_call_argument():
    node = parse("x = f(int(\"7\"))").statements[0].value
    assert node.args[0].name == "int"


def test_bare_type_name_in_expression_is_error():
    with pytest.raises(ParseError):
        parse("x = int")


def test_bare_str_in_print_is_error():
    with pytest.raises(ParseError):
        parse("print(str)")


def test_int_identity():
    assert run_source("x = int(42)")["x"] == 42
    assert run_source("x = int(-5)")["x"] == -5


def test_int_from_bool():
    assert run_source("x = int(TRUE)")["x"] == 1
    assert run_source("x = int(FALSE)")["x"] == 0


def test_int_from_string():
    assert run_source('x = int("42")')["x"] == 42
    assert run_source('x = int("-7")')["x"] == -7
    assert run_source('x = int("+5")')["x"] == 5
    assert run_source('x = int("0")')["x"] == 0


def test_int_from_string_with_big_digits():
    assert run_source('x = int("123456789012345678901234567890")')["x"] == (
        123456789012345678901234567890
    )


def test_int_from_empty_string_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source('x = int("")')


def test_int_from_whitespace_string_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source('x = int(" 42 ")')


def test_int_from_underscores_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source('x = int("1_000")')


def test_int_from_hex_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source('x = int("0x10")')


def test_int_from_letters_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source('x = int("abc")')


def test_int_from_bare_sign_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source('x = int("-")')


def test_str_identity():
    assert run_source('x = str("hi")')["x"] == "hi"


def test_str_from_int():
    assert run_source("x = str(42)")["x"] == "42"
    assert run_source("x = str(-7)")["x"] == "-7"
    assert run_source("x = str(0)")["x"] == "0"


def test_str_from_bool():
    assert run_source("x = str(TRUE)")["x"] == "True"
    assert run_source("x = str(FALSE)")["x"] == "False"


def test_str_bool_matches_print_output():
    printed = []
    run_source("print(str(TRUE)) print(str(FALSE))", out=printed.append)
    assert printed == ["True", "False"]


def test_bool_identity():
    assert run_source("x = bool(TRUE)")["x"] is True
    assert run_source("x = bool(FALSE)")["x"] is False


def test_bool_from_int():
    assert run_source("x = bool(0)")["x"] is False
    assert run_source("x = bool(3)")["x"] is True
    assert run_source("x = bool(-3)")["x"] is True


def test_bool_from_string():
    assert run_source('x = bool("")')["x"] is False
    assert run_source('x = bool("a")')["x"] is True
    assert run_source('x = bool("0")')["x"] is True


def test_round_trip_int_str():
    assert run_source('x = int(str(42))')["x"] == 42
    assert run_source('x = str(int("12"))')["x"] == "12"


def test_nested_conversions():
    assert run_source('x = int(str(int(str(9))))')["x"] == 9


def test_builtin_in_condition():
    env = run_source('if (bool("")) { a = 1 } else if (bool("x")) { a = 2 }')
    assert env["a"] == 2


def test_builtin_in_while_condition():
    env = run_source("i = 3 while (bool(i)) { i -= 1 }")
    assert env["i"] == 0


def test_builtin_in_string_concatenation():
    assert run_source('x = "n=" + str(7)')["x"] == "n=7"


def test_builtin_result_in_arithmetic():
    assert run_source('x = int("5") * 2 + int(TRUE)')["x"] == 11


def test_builtin_as_function_argument():
    env = run_source(
        'fn dbl (n: int) { return n * 2 } x = dbl(int("21"))'
    )
    assert env["x"] == 42


def test_builtin_result_as_argument_type_checked():
    with pytest.raises(RolyError, match="must be int"):
        run_source('fn f (n: int) { return n } x = f(str(1))')


def test_builtin_zero_args_errors():
    with pytest.raises(RolyError, match="expects 1 argument"):
        run_source("x = int()")


def test_builtin_two_args_errors():
    with pytest.raises(RolyError, match="expects 1 argument"):
        run_source("x = int(1, 2)")


def test_builtin_name_not_a_variable():
    with pytest.raises(ParseError):
        run_source("x = int")


def test_conversion_inside_loop_accumulates():
    env = run_source(
        'i = 0 total = 0 while (i < 3) { total += int("10") i += 1 }'
    )
    assert env["total"] == 30


def test_str_from_counter_and_bench():
    printed = []
    run_source(
        'i = 0 while (i < 3) { print("i=" + str(i)) i += 1 }',
        out=printed.append,
    )
    assert printed == ["i=0", "i=1", "i=2"]
