import pytest

from roly.ast import Assign, BinOp, Chain, ListLit, Num, Program, Subscript, Var
from roly.lexer import Lexer
from roly.parser import ParseError, Parser


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def expr_of(source):
    program = parse(f"x = {source}")
    return program.statements[0].value


def test_operator_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("x = 5\n-2")


def test_operator_on_next_line_error_carries_position():
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\n+ 2")
    assert excinfo.value.token.line == 2


def test_comparison_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("a = 1\n== 2")


def test_multiplicative_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("x = 10\n* 2")


def test_right_operand_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("x = 1 +\n2")


def test_subscript_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("l = [1, 2] x = l\n[0]")


def test_dot_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("import mod\nx = mod\n.value")


def test_minus_operand_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("x =\n-2")


def test_call_paren_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        parse("x = f\n(1)")


def test_parentheses_allow_continuation():
    assert expr_of("(1 +\n2)") == BinOp("+", Num(1), Num(2))


def test_nested_parentheses_allow_blank_lines():
    assert expr_of("(1 +\n\n(2 *\n3))") == BinOp("+", Num(1), BinOp("*", Num(2), Num(3)))


def test_list_literal_allows_continuation():
    assert expr_of("[1,\n2,\n3]") == ListLit([Num(1), Num(2), Num(3)])


def test_call_arguments_allow_continuation():
    program = parse("fn add (a: int, b: int) { return a + b } x = add(1,\n2)")
    assert program.statements[1].value.args == [Num(1), Num(2)]


def test_if_condition_allows_continuation():
    program = parse('n = 5 if (\nn > 1\n) { print("big") }')
    assert program.statements[1].condition == Chain([Var("n"), Num(1)], [">"])


def test_index_expression_allows_continuation():
    program = parse("l = [10, 20] x = l[0 +\n0]")
    assert program.statements[1] == Assign(
        "x", Subscript(Var("l"), BinOp("+", Num(0), Num(0)))
    )


def test_statements_still_split_on_lines():
    assert parse("x = 1\ny = 2") == Program(
        [Assign("x", Num(1)), Assign("y", Num(2))]
    )


def test_closing_bracket_can_land_on_next_line():
    assert expr_of("(1 +\n2\n)") == BinOp("+", Num(1), Num(2))


def test_assign_operator_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="must follow 'x' on the same line"):
        parse("x\n= 5")


def test_compound_assign_operator_on_next_line_is_parse_error():
    with pytest.raises(ParseError, match="must follow 'x' on the same line"):
        parse("x = 1\nx\n+= 5")


def test_assignment_on_its_own_lines_still_works():
    assert parse("x = 5\ny = x") == Program(
        [Assign("x", Num(5)), Assign("y", Var("x"))]
    )
