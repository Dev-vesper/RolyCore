import pytest

from roly.lexer import Lexer
from roly.parser import ParseError, Parser


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_bare_statements_error():
    for source in [
        "x", "x + 1", "x 5", "5 = x", "+ x", "}", "5", "1 + 1", "[0] = 1",
    ]:
        with pytest.raises(ParseError):
            parse(source)


def test_only_calls_are_expression_statements():
    for source in ["x = 1 x", "l = [1] l[0]", "fn f () { return [1] } f()[0]"]:
        with pytest.raises(ParseError, match="a call like"):
            parse(source)


def test_missing_expression_after_assign():
    for source in ["x =", "x +="]:
        with pytest.raises(ParseError):
            parse(source)


def test_atom_error_message_lists_every_start():
    with pytest.raises(
        ParseError,
        match="expected a number, a string, a boolean, an identifier, "
        "a list, '-', or '\\(', got '\\)'",
    ):
        parse("x = )")


def test_parenthesis_errors():
    for source in ["x = (1 + 2", "x = ()", "x = 1)"]:
        with pytest.raises(ParseError):
            parse(source)


def test_if_while_structure_errors():
    for source in [
        "if x { }", "if (x)", "if (x) { } else", "if (x) { } else x = 1",
        "if (a) { } else if b { }", "if (a) { } else if (b)",
        "if (a) { } else { } else { }",
        "if (a) { } else if (b) { } else { } else { }",
        "if (a) { } else { } else if (b) { }",
        "if (a) { } else if () { }",
        "else if (b) { }",
        "while x { }", "while (x)", "while (x) { x -= 1",
    ]:
        with pytest.raises(ParseError):
            parse(source)


def test_function_placement_errors():
    for source in [
        "{ fn f () { return 1 } }",
        "if (1) { fn f () { return 1 } }",
        "while (1) { fn f () { return 1 } }",
    ]:
        with pytest.raises(ParseError, match="top level"):
            parse(source)


def test_function_parameter_errors():
    for source in [
        "fn f (a: float) { return a }",
        "fn f (a: print) { return a }",
        "fn f (a) { return a }",
        "fn f (: int) { return 1 }",
        "fn f (a int) { return a }",
        "fn f ()",
        "fn f (a: int,) { return a }",
    ]:
        with pytest.raises(ParseError):
            parse(source)


def test_unknown_type_message():
    with pytest.raises(
        ParseError,
        match=r"unknown type 'float' \(expected int, str, bool, or list\)",
    ):
        parse("fn f (a: float) { return a }")


def test_duplicate_parameter_errors():
    with pytest.raises(ParseError, match="duplicate parameter 'a'"):
        parse("fn f (a: int, a: int) { return a }")


def test_return_outside_function():
    for source in ["return 1", "{ return 1 }", "while (1) { return 1 }"]:
        with pytest.raises(ParseError, match="'return' outside function"):
            parse(source)


def test_jumps_outside_loop():
    for source in [
        "break", "continue", "while (x) { } break", "while (x) { break } continue",
        "fn f () { break }", "fn f () { continue }",
        "while (break) { }", "x = break", "x = continue",
    ]:
        with pytest.raises(ParseError):
            parse(source)


def test_print_structure_errors():
    for source in ["print 5", "print(5", "print()", "print(", "x = print(1)"]:
        with pytest.raises(ParseError):
            parse(source)


def test_float_literals_rejected():
    with pytest.raises(ParseError):
        parse("x = 1.5")


def test_type_names_are_not_values():
    for source in [
        "x = int", "print(str)", "x = list", "fn f (list: int) { return list }",
    ]:
        with pytest.raises(ParseError):
            parse(source)


def test_list_literal_errors():
    for source in ["x = [1, 2,]", "x = [1, 2", "x = [1,]", "x = a[0", "x = a[]"]:
        with pytest.raises(ParseError):
            parse(source)


def test_operator_on_next_line_is_parse_error():
    for source in [
        "x = 5\n-2", "x = 1\n+ 2", "a = 1\n== 2", "x = 10\n* 2", "x = 1 +\n2",
        "l = [1, 2] x = l\n[0]", "x = f\n(1)", "x =\n-2",
    ]:
        with pytest.raises(ParseError, match="cannot continue on the next line"):
            parse(source)


def test_assign_operator_on_next_line_is_parse_error():
    for source in ["x\n= 5", "x = 1\nx\n+= 5"]:
        with pytest.raises(ParseError, match="must follow 'x' on the same line"):
            parse(source)


def test_nesting_limit():
    with pytest.raises(ParseError, match="nesting too deep"):
        parse("x = " + "(" * 150 + "1" + ")" * 150)
    with pytest.raises(ParseError, match="nesting too deep"):
        parse("{" * 150 + "}" * 150)
    with pytest.raises(ParseError, match="nesting too deep"):
        parse("x = " + "-" * 150 + "1")
    with pytest.raises(ParseError):
        parse("x = " + "(" * 5000 + "1")


def test_error_positions():
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\n}")
    assert (excinfo.value.token.line, excinfo.value.token.column) == (2, 1)
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\ny")
    assert (excinfo.value.token.line, excinfo.value.token.column) == (2, 1)
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\n  break")
    assert (excinfo.value.token.line, excinfo.value.token.column) == (2, 3)
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\nreturn 2")
    assert excinfo.value.token.line == 2


def test_error_message_mentions_location():
    with pytest.raises(ParseError, match="line 1"):
        parse("x =")
