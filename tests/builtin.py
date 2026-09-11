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


def test_str_of_huge_int_beyond_python_default_cap():
    env = run_source("x = str(pow(2, 20000)) y = len(x)")
    assert env["y"] == 6021


def test_print_of_huge_int():
    printed = []
    run_source("print(pow(2, 20000))", out=printed.append)
    assert printed == [2 ** 20000]


def test_format_with_huge_int():
    env = run_source('x = format("{}", pow(2, 5000))')
    assert len(env["x"]) == 1506


def test_fail_two_args_errors():
    with pytest.raises(RolyError, match="builtin 'fail' expects 1 argument, got 2"):
        run_source('x = fail("a", "b")')


def test_fail_zero_args_errors():
    with pytest.raises(RolyError, match="builtin 'fail' expects 1 argument, got 0"):
        run_source("x = fail()")


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


def test_parse_list_builtin_call():
    node = parse("x = list()").statements[0].value
    assert node.name == "list"


def test_lex_list_keyword():
    from roly.tokens import T

    tokens = Lexer("list").tokenize()
    assert tokens[0].type is T.LIST_TYPE
    tokens = Lexer("listing").tokenize()
    assert tokens[0].type is T.IDENT
    tokens = Lexer("List").tokenize()
    assert tokens[0].type is T.IDENT


def test_bare_list_in_expression_is_error():
    with pytest.raises(ParseError):
        parse("x = list")


def test_list_parameter_type_parses():
    assert parse("fn f (l: list) { return l }").statements[0].name == "f"


def test_list_parameter_name_is_error():
    with pytest.raises(ParseError):
        parse("fn f (list: int) { return list }")


def test_empty_list():
    assert run_source("x = list()")["x"] == []


def test_list_from_string():
    assert run_source('x = list("abc")')["x"] == ["a", "b", "c"]
    assert run_source('x = list("")')["x"] == []


def test_list_from_non_string_errors():
    with pytest.raises(RolyError, match="expects a str"):
        run_source("x = list(42)")


def test_list_two_args_errors():
    with pytest.raises(RolyError, match="no arguments or a str"):
        run_source('x = list("a", "b")')


def test_push_appends_and_returns_new_list():
    env = run_source("a = list() b = push(a, 5) c = push(b, 9)")
    assert env["a"] == []
    assert env["b"] == [5]
    assert env["c"] == [5, 9]


def test_push_is_immutable():
    env = run_source("a = push(list(), 1) b = push(a, 2)")
    assert env["a"] == [1]
    assert env["b"] == [1, 2]


def test_push_accepts_any_value_type():
    env = run_source('b = list() b = push(b, 1) b = push(b, "x") b = push(b, TRUE)')
    assert env["b"] == [1, "x", True]


def test_push_non_list_errors():
    with pytest.raises(RolyError, match="expects a list"):
        run_source("x = push(5, 1)")


def test_push_arity_checked():
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source("x = push(list())")


def test_get_returns_element():
    assert run_source('x = get(list("abc"), 1)')["x"] == "b"


def test_get_out_of_range_errors():
    with pytest.raises(RolyError, match="index 3 out of range for length 3"):
        run_source('x = get(list("abc"), 3)')
    with pytest.raises(RolyError, match="index -1 out of range"):
        run_source('x = get(list("abc"), -1)')
    with pytest.raises(RolyError, match="index 0 out of range for length 0"):
        run_source("x = get(list(), 0)")


def test_get_wrong_types_error():
    with pytest.raises(RolyError, match="expects a list"):
        run_source('x = get("abc", 0)')
    with pytest.raises(RolyError, match="expects an int index"):
        run_source('x = get(list("abc"), "0")')


def test_get_arity_checked():
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source("x = get(list())")


def test_set_replaces_and_returns_new_list():
    env = run_source("a = list() a = push(a, 1) a = push(a, 2) b = set(a, 0, 50)")
    assert env["a"] == [1, 2]
    assert env["b"] == [50, 2]


def test_set_out_of_range_errors():
    with pytest.raises(RolyError, match="index 2 out of range for length 2"):
        run_source("x = set(push(push(list(), 1), 2), 2, 9)")
    with pytest.raises(RolyError, match="index -1 out of range"):
        run_source("x = set(list(), -1, 9)")


def test_set_arity_checked():
    with pytest.raises(RolyError, match="expects 3 arguments"):
        run_source("x = set(list(), 0)")


def test_len_of_list():
    assert run_source("x = len(list())")["x"] == 0
    assert run_source('x = len(list("abc"))')["x"] == 3
    assert run_source("x = len(push(list(), 1))")["x"] == 1


def test_len_of_int_still_errors():
    with pytest.raises(RolyError, match="expects a str or a list"):
        run_source("x = len(42)")


def test_list_names_are_reserved():
    with pytest.raises(RolyError, match="builtin"):
        run_source("push = 5")
    with pytest.raises(RolyError, match="builtin"):
        run_source("fn get () { return 1 }")
    with pytest.raises(RolyError, match="builtin"):
        run_source("fn f (set: int) { return set }")


def test_int_from_list_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source("x = int(list())")


def test_bool_from_list_errors():
    with pytest.raises(RolyError, match="cannot convert"):
        run_source("x = bool(list())")


def test_str_of_list_renders_python_style():
    assert run_source("x = str(push(list(), 42))")["x"] == "[42]"
    assert run_source('x = str(list("ab"))')["x"] == "['a', 'b']"


def test_list_as_function_argument():
    env = run_source(
        "fn head (l: list) { return get(l, 0) } x = head(list(\"ab\"))"
    )
    assert env["x"] == "a"


def test_list_argument_type_checked():
    with pytest.raises(RolyError, match="must be list"):
        run_source("fn f (l: list) { return l } x = f(5)")


def test_list_not_truthy_in_condition():
    with pytest.raises(RolyError, match="condition must be a number"):
        run_source("if (list()) { x = 1 }")


def test_list_in_format():
    printed = []
    run_source('print(format("l={}", push(list(), 7)))', out=printed.append)
    assert printed == ["l=[7]"]


def test_list_plus_list_errors():
    with pytest.raises(RolyError, match="requires integer operands"):
        run_source("x = list() + list()")
