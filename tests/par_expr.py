import pytest

from roly.ast import Assign, BinOp, Call, Chain, ListLit, Neg, Num, Var
from roly.lexer import Lexer
from roly.parser import ParseError, Parser


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def expr_of(source):
    program = parse(f"x = {source}")
    return program.statements[0].value


def test_single_number():
    assert expr_of("5") == Num(5)


def test_single_identifier():
    assert expr_of("y") == Var("y")


def test_simple_addition():
    assert expr_of("1 + 2") == BinOp("+", Num(1), Num(2))


def test_simple_subtraction():
    assert expr_of("10 - 4") == BinOp("-", Num(10), Num(4))


def test_multiplication_binds_tighter_than_addition():
    assert expr_of("1 + 2 * 3") == BinOp("+", Num(1), BinOp("*", Num(2), Num(3)))


def test_multiplication_binds_tighter_than_subtraction():
    assert expr_of("2 * 3 - 1") == BinOp("-", BinOp("*", Num(2), Num(3)), Num(1))


def test_division_binds_tighter_than_addition():
    assert expr_of("8 + 4 / 2") == BinOp("+", Num(8), BinOp("/", Num(4), Num(2)))


def test_mixed_mul_and_div_left_assoc():
    assert expr_of("8 / 4 * 2") == BinOp("*", BinOp("/", Num(8), Num(4)), Num(2))


def test_additive_left_associativity():
    assert expr_of("1 - 2 - 3") == BinOp("-", BinOp("-", Num(1), Num(2)), Num(3))


def test_additive_chain_of_three():
    assert expr_of("1 + 2 + 3") == BinOp("+", BinOp("+", Num(1), Num(2)), Num(3))


def test_parentheses_override_precedence():
    assert expr_of("(1 + 2) * 3") == BinOp("*", BinOp("+", Num(1), Num(2)), Num(3))


def test_nested_parentheses():
    assert expr_of("((5))") == Num(5)


def test_parenthesized_whole_expression():
    assert expr_of("(x + 1) * (y - 2)") == BinOp(
        "*",
        BinOp("+", Var("x"), Num(1)),
        BinOp("-", Var("y"), Num(2)),
    )


def test_comparison_over_additive():
    assert expr_of("a + 1 < b * 2") == Chain(
        [BinOp("+", Var("a"), Num(1)), BinOp("*", Var("b"), Num(2))],
        ["<"],
    )


def test_comparison_chain():
    assert expr_of("a < b < c") == Chain(
        [Var("a"), Var("b"), Var("c")],
        ["<", "<"],
    )


def test_comparison_chain_mixed():
    assert expr_of("a <= b == c >= d") == Chain(
        [Var("a"), Var("b"), Var("c"), Var("d")],
        ["<=", "==", ">="],
    )


def test_assignment_value_can_be_comparison():
    program = parse("flag = a == b")
    assert program.statements[0].value == Chain([Var("a"), Var("b")], ["=="])


def test_deep_expression():
    assert expr_of("x + y * z - w / v + 0") == BinOp(
        "+",
        BinOp(
            "-",
            BinOp("+", Var("x"), BinOp("*", Var("y"), Var("z"))),
            BinOp("/", Var("w"), Var("v")),
        ),
        Num(0),
    )


def test_whitespace_free_expression():
    assert expr_of("1+2*3") == BinOp("+", Num(1), BinOp("*", Num(2), Num(3)))


def test_multiline_expression_is_parse_error():
    with pytest.raises(ParseError, match="cannot continue on the next line"):
        expr_of("1 +\n2")


def test_assignment_node_shape():
    program = parse("x = 5")
    assert program.statements[0] == Assign("x", Num(5))


def test_comparison_single_stays_binop_chain_of_one():
    node = expr_of("a < b")
    assert isinstance(node, Chain)
    assert node.ops == ["<"]


def test_comparison_not_chainable_from_additive_only():
    assert expr_of("a + b") == BinOp("+", Var("a"), Var("b"))


def test_parse_subscript():
    node = parse("x = a[0]").statements[0].value
    assert node.base.name == "a"
    assert node.index.value == 0


def test_parse_subscript_with_expression_index():
    node = parse("x = a[i + 1]").statements[0].value
    assert node.index.op == "+"


def test_parse_nested_subscript():
    node = parse("x = a[0][1]").statements[0].value
    assert node.base.base.name == "a"
    assert node.base.index.value == 0
    assert node.index.value == 1


def test_parse_subscript_on_call_result():
    node = parse("x = f()[0]").statements[0].value
    assert node.base.name == "f"


def test_parse_subscript_on_parenthesized():
    node = parse("x = (a)[0]").statements[0].value
    assert node.base.name == "a"


def test_parse_negative_binds_around_subscript():
    from roly.ast import Neg

    node = parse("x = -a[0]").statements[0].value
    assert isinstance(node, Neg)
    assert node.operand.base.name == "a"


def test_parse_subscript_missing_close_errors():
    with pytest.raises(ParseError, match="expected ']'"):
        parse("x = a[0")


def test_parse_subscript_missing_index_errors():
    with pytest.raises(ParseError):
        parse("x = a[]")


def test_parse_list_literal():
    node = parse("x = [1, 2]").statements[0].value
    assert node == ListLit([Num(1), Num(2)])


def test_parse_empty_list_literal():
    node = parse("x = []").statements[0].value
    assert node == ListLit([])


def test_parse_single_item_list_literal():
    node = parse("x = [1]").statements[0].value
    assert node == ListLit([Num(1)])


def test_parse_list_literal_items_are_expressions():
    node = parse("x = [1 + 2, f(), -3]").statements[0].value
    assert node.items[0] == BinOp("+", Num(1), Num(2))
    assert node.items[1] == Call("f", [])
    assert isinstance(node.items[2], Neg)


def test_parse_nested_list_literal():
    node = parse("x = [[1], [2, 3]]").statements[0].value
    assert node == ListLit([ListLit([Num(1)]), ListLit([Num(2), Num(3)])])


def test_parse_list_literal_trailing_comma_rejected():
    with pytest.raises(ParseError, match="expected a number"):
        parse("x = [1, 2,]")


def test_parse_list_literal_missing_close_rejected():
    with pytest.raises(ParseError, match="expected ']'"):
        parse("x = [1, 2")


def test_parse_list_literal_missing_item_rejected():
    with pytest.raises(ParseError):
        parse("x = [1,]")


def test_parse_subscript_on_list_literal():
    node = parse("x = [1, 2][1]").statements[0].value
    assert node.base == ListLit([Num(1), Num(2)])
    assert node.index == Num(1)


def test_parse_statement_cannot_start_with_bracket():
    with pytest.raises(ParseError):
        parse("[0] = 1")
