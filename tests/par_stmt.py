from roly.ast import (
    Assign,
    BinOp,
    Block,
    CompoundAssign,
    If,
    Num,
    Program,
    Var,
    While,
)
from roly.lexer import Lexer
from roly.parser import Parser


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_empty_program():
    assert parse("") == Program([])


def test_whitespace_only_program():
    assert parse("  \n\t\n") == Program([])


def test_single_assignment():
    assert parse("x = 5") == Program([Assign("x", Num(5))])


def test_two_assignments_without_separator():
    assert parse("x = 1 y = 2") == Program(
        [Assign("x", Num(1)), Assign("y", Num(2))]
    )


def test_assignments_across_lines():
    assert parse("x = 1\ny = 2\n") == Program(
        [Assign("x", Num(1)), Assign("y", Num(2))]
    )


def test_assignment_with_complex_expression():
    assert parse("total = a + b * 2") == Program(
        [Assign("total", BinOp("+", Var("a"), BinOp("*", Var("b"), Num(2))))]
    )


def test_compound_assignment_plus():
    assert parse("x += 1") == Program([CompoundAssign("x", "+", Num(1))])


def test_compound_assignment_minus():
    assert parse("x -= 1") == Program([CompoundAssign("x", "-", Num(1))])


def test_compound_assignment_star():
    assert parse("x *= 2") == Program([CompoundAssign("x", "*", Num(2))])


def test_compound_assignment_slash():
    assert parse("x /= 2") == Program([CompoundAssign("x", "/", Num(2))])


def test_compound_assignment_with_expression():
    assert parse("x += a + 1") == Program(
        [CompoundAssign("x", "+", BinOp("+", Var("a"), Num(1)))]
    )


def test_if_without_else():
    assert parse("if (x) { y = 1 }") == Program(
        [
            If(
                Var("x"),
                Block([Assign("y", Num(1))]),
                None,
            )
        ]
    )


def test_if_with_else():
    assert parse("if (x > 0) { y = 1 } else { y = 2 }") == Program(
        [
            If(
                BinOp(">", Var("x"), Num(0)),
                Block([Assign("y", Num(1))]),
                Block([Assign("y", Num(2))]),
            )
        ]
    )


def test_if_condition_is_full_expression():
    assert parse("if (a + b * 2 == 10) { }") == Program(
        [
            If(
                BinOp("==", BinOp("+", Var("a"), BinOp("*", Var("b"), Num(2))), Num(10)),
                Block([]),
                None,
            )
        ]
    )


def test_nested_if_inside_else():
    assert parse("if (a) { } else { if (b) { x = 1 } }") == Program(
        [
            If(
                Var("a"),
                Block([]),
                Block([If(Var("b"), Block([Assign("x", Num(1))]), None)]),
            )
        ]
    )


def test_empty_block_statement():
    assert parse("{ }") == Program([Block([])])


def test_bare_block_statement():
    assert parse("{ x = 1 y = 2 }") == Program(
        [Block([Assign("x", Num(1)), Assign("y", Num(2))])]
    )


def test_nested_bare_blocks():
    assert parse("{ { x = 1 } }") == Program([Block([Block([Assign("x", Num(1))])])])


def test_while_simple():
    assert parse("while (x) { x -= 1 }") == Program(
        [While(Var("x"), Block([CompoundAssign("x", "-", Num(1))]))]
    )


def test_while_empty_body():
    assert parse("while (x < 10) { }") == Program(
        [While(BinOp("<", Var("x"), Num(10)), Block([]))]
    )


def test_while_with_multiple_statements():
    assert parse("while (a < b) { a += 1 b -= 1 }") == Program(
        [
            While(
                BinOp("<", Var("a"), Var("b")),
                Block([CompoundAssign("a", "+", Num(1)), CompoundAssign("b", "-", Num(1))]),
            )
        ]
    )


def test_while_nested_inside_if():
    assert parse("if (x) { while (y) { y -= 1 } }") == Program(
        [
            If(
                Var("x"),
                Block([While(Var("y"), Block([CompoundAssign("y", "-", Num(1))]))]),
                None,
            )
        ]
    )


def test_full_program_mixing_everything():
    source = (
        "x = 10\n"
        "while (x > 0) {\n"
        "  if (x / 2 == 5) { x -= 3 } else { x -= 1 }\n"
        "}\n"
        "y = x * 2\n"
    )
    assert parse(source) == Program(
        [
            Assign("x", Num(10)),
            While(
                BinOp(">", Var("x"), Num(0)),
                Block(
                    [
                        If(
                            BinOp("==", BinOp("/", Var("x"), Num(2)), Num(5)),
                            Block([CompoundAssign("x", "-", Num(3))]),
                            Block([CompoundAssign("x", "-", Num(1))]),
                        )
                    ]
                ),
            ),
            Assign("y", BinOp("*", Var("x"), Num(2))),
        ]
    )


def test_statement_order_is_preserved():
    program = parse("a = 1 b = 2 c = 3")
    assert [stmt.name for stmt in program.statements] == ["a", "b", "c"]
