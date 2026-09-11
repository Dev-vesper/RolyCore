import pytest

from roly.ast import Block, FnDef, Num, Return, Var
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.tokens import T


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_fn_lexes_as_keyword():
    assert Lexer("fn").tokenize()[0].type is T.FN


def test_return_lexes_as_keyword():
    assert Lexer("return").tokenize()[0].type is T.RETURN


def test_type_names_lex_as_keywords():
    assert Lexer("int").tokenize()[0].type is T.INT_TYPE
    assert Lexer("str").tokenize()[0].type is T.STR_TYPE
    assert Lexer("bool").tokenize()[0].type is T.BOOL_TYPE


def test_colon_and_comma_tokens():
    tokens = Lexer(":,").tokenize()
    assert tokens[0].type is T.COLON
    assert tokens[1].type is T.COMMA


def test_keyword_prefixed_idents_stay_ident():
    tokens = Lexer("fnx returns ints strs bools").tokenize()
    assert all(t.type is T.IDENT for t in tokens[:5])


def test_parse_function_no_params():
    program = parse("fn f () { return 1 }")
    assert program.statements[0] == FnDef("f", [], Block([Return(Num(1))]))


def test_parse_function_typed_params():
    program = parse("fn f (a: int, b: str, c: bool) { return a }")
    assert program.statements[0] == FnDef(
        "f",
        [("a", int), ("b", str), ("c", bool)],
        Block([Return(Var("a"))]),
    )


def test_parse_function_with_statements_before_return():
    program = parse("fn f (n: int) { x = n + 1 return x }")
    body = program.statements[0].body.statements
    assert len(body) == 2
    assert isinstance(body[1], Return)


def test_functions_and_statements_interleave():
    program = parse("x = 1 fn f () { return x } y = f()")
    assert program.statements[0].name == "x"
    assert isinstance(program.statements[1], FnDef)
    assert program.statements[2].name == "y"


def test_function_inside_block_is_error():
    with pytest.raises(ParseError, match="top level"):
        parse("{ fn f () { return 1 } }")


def test_function_inside_if_is_error():
    with pytest.raises(ParseError, match="top level"):
        parse("if (1) { fn f () { return 1 } }")


def test_function_inside_while_is_error():
    with pytest.raises(ParseError, match="top level"):
        parse("while (1) { fn f () { return 1 } }")


def test_float_type_rejected():
    with pytest.raises(ParseError, match="unknown type"):
        parse("fn f (a: float) { return a }")


def test_unknown_type_message_single_quoted_and_lists():
    with pytest.raises(
        ParseError,
        match=r"unknown type 'float' \(expected int, str, bool, or list\)",
    ):
        parse("fn f (a: float) { return a }")


def test_unknown_type_on_keyword_token():
    with pytest.raises(ParseError, match=r"unknown type 'print'"):
        parse("fn f (a: print) { return a }")


def test_untyped_param_rejected():
    with pytest.raises(ParseError):
        parse("fn f (a) { return a }")


def test_missing_param_name_rejected():
    with pytest.raises(ParseError):
        parse("fn f (: int) { return 1 }")


def test_missing_colon_rejected():
    with pytest.raises(ParseError):
        parse("fn f (a int) { return a }")


def test_missing_body_rejected():
    with pytest.raises(ParseError):
        parse("fn f ()")


def test_trailing_comma_in_params_rejected():
    with pytest.raises(ParseError):
        parse("fn f (a: int,) { return a }")


def test_return_outside_function():
    with pytest.raises(ParseError, match="'return' outside function"):
        parse("return 1")


def test_return_inside_block_outside_function():
    with pytest.raises(ParseError, match="'return' outside function"):
        parse("{ return 1 }")


def test_return_inside_loop_outside_function():
    with pytest.raises(ParseError, match="'return' outside function"):
        parse("while (1) { return 1 }")


def test_return_error_position():
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\nreturn 2")
    assert excinfo.value.token.line == 2


def test_break_inside_fn_body_outside_loop_errors():
    with pytest.raises(ParseError, match="'break' outside loop"):
        parse("fn f () { break }")


def test_continue_inside_fn_body_outside_loop_errors():
    with pytest.raises(ParseError, match="'continue' outside loop"):
        parse("fn f () { continue }")


def test_while_inside_fn_body_allows_break():
    program = parse("fn f () { while (1) { break } return 1 }")
    body = program.statements[0].body.statements
    while_loop = body[0]
    assert while_loop.body.statements[0].__class__.__name__ == "Break"
    assert body[1] == Return(Num(1))


def test_duplicate_parameter_errors():
    with pytest.raises(ParseError, match="duplicate parameter 'a'"):
        parse("fn f (a: int, a: int) { return a }")
    with pytest.raises(ParseError, match="duplicate parameter 'b'"):
        parse("fn f (a: int, b: str, b: bool) { return a }")
