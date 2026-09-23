import pytest

from roly.frontend.lexer import Lexer
from roly.frontend.parser import ParseError, Parser


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


def test_empty_block_errors():
    for source in [
        "fn f () { }", "fn f () { return 1 } fn g () { }",
        "if (TRUE) { }", "if (TRUE) { x = 1 } else { }",
        "while (TRUE) { }", "{ }",
    ]:
        with pytest.raises(ParseError, match="a block cannot be empty"):
            parse(source)


def test_semicolon_errors():
    for source in [
        "x = 1;", "x = 1;; y = 2", "x = 1; ; y = 2",
        "if (TRUE) { x = 1; }",
        "while (x > 0) { x -= 1; }",
        "fn f () { return 1; }",
        "x = f(1; 2)", "l = [1; 2]",
    ]:
        with pytest.raises(ParseError):
            parse(source)


def test_ellipsis_errors():
    for source in [
        "...", "x = ...", "print(...)",
        "if (TRUE) { ... x = 1 }",
        "fn f () { ... return 1 }",
        "x = 1 ...",
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
        "fn f (a: print) { return a }",
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
        match=r"unknown type 'double' \(expected int, str, bool, list, float, or file\)",
    ):
        parse("fn f (a: double) { return a }")


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


def test_malformed_float_literals_rejected():
    for source in ["x = 1.", "x = 1.2.3", "x = .5", "x = 1e", "x = 1e+", "x = 1.5e"]:
        with pytest.raises(ParseError):
            parse(source)


def test_type_names_are_not_values():
    for source in [
        "x = int", "print(str)", "x = list", "fn f (list: int) { return list }",
        "x = float", "x = file", "print(file)", "fn f (file: int) { return file }",
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
        "if\n(TRUE) { ... }", "while\n(TRUE) { break }", "print\n(1)",
        "fn f\n(a: int) { return a }",
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


def test_member_name_must_follow_dot_on_same_line():
    for source in ["x = testme.\nvalue", "x = testme.\nbump()"]:
        with pytest.raises(ParseError, match="cannot continue on the next line"):
            parse(source)


def test_fn_name_must_follow_fn_on_same_line():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("fn\nf () { return 1 }")


def test_else_if_is_not_supported():
    with pytest.raises(ParseError, match="expected '\\{', got 'if'"):
        parse("if (TRUE) { x = 1 } else if (TRUE) { x = 2 }")


def test_block_brace_follows_introducer_on_same_line():
    for source in [
        "if (TRUE)\n{ x = 1 }",
        "if (TRUE) { x = 1 } else\n{ x = 2 }",
        "while (TRUE)\n{ break }",
        "fn f ()\n{ return 1 }",
        "if (TRUE)\n{\nx = 1\n}",
    ]:
        with pytest.raises(ParseError, match="cannot continue on the next line"):
            parse(source)


def test_import_keyword_and_name_same_line():
    for source in ["import\nmath", "!import\nmath", "import math\n{gcd}"]:
        with pytest.raises(ParseError, match="cannot continue on the next line"):
            parse(source)


def test_import_brace_list_stays_on_one_line():
    for source in [
        "!import math {\ngcd}",
        "!import math {gcd,\nlcm}",
        "!import math {gcd\n}",
        "import math {gcd\n, lcm}",
    ]:
        with pytest.raises(ParseError, match="cannot continue on the next line"):
            parse(source)


def test_annotation_must_be_same_line():
    for source in [
        "fn f (a:\nint) { return a }",
        "fn f (a\n: int) { return a }",
    ]:
        with pytest.raises(ParseError, match="cannot continue on the next line"):
            parse(source)


def test_bare_identifier_error_message():
    with pytest.raises(ParseError, match="expected '=' or a compound assignment"):
        parse("x\ny = 5")
