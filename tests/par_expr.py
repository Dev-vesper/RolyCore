from roly.ast import Assign, BinOp, Chain, Num, Var
from roly.lexer import Lexer
from roly.parser import Parser


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


def test_multiline_expression():
    assert expr_of("1 +\n2") == BinOp("+", Num(1), Num(2))


def test_assignment_node_shape():
    program = parse("x = 5")
    assert program.statements[0] == Assign("x", Num(5))


def test_comparison_single_stays_binop_chain_of_one():
    node = expr_of("a < b")
    assert isinstance(node, Chain)
    assert node.ops == ["<"]


def test_comparison_not_chainable_from_additive_only():
    assert expr_of("a + b") == BinOp("+", Var("a"), Var("b"))
