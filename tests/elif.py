import pytest

from roly.ast import Assign, Block, If, Num, Program, Var
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.interpreter import RolyError
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_parse_single_elif():
    assert parse("if (a) { } else if (b) { x = 1 }") == Program(
        [
            If(
                Var("a"),
                Block([]),
                None,
                [(Var("b"), Block([Assign("x", Num(1))]))],
            )
        ]
    )


def test_parse_two_elifs_and_else():
    assert parse(
        "if (a) { } else if (b) { } else if (c) { } else { }"
    ) == Program(
        [
            If(
                Var("a"),
                Block([]),
                Block([]),
                [(Var("b"), Block([])), (Var("c"), Block([]))],
            )
        ]
    )


def test_parse_elifs_without_else():
    assert parse("if (a) { x = 1 } else if (b) { x = 2 }") == Program(
        [
            If(
                Var("a"),
                Block([Assign("x", Num(1))]),
                None,
                [(Var("b"), Block([Assign("x", Num(2))]))],
            )
        ]
    )


def test_plain_if_has_no_elifs():
    node = parse("if (a) { } else { }").statements[0]
    assert node.elifs is None


def test_parse_elif_condition_is_full_expression():
    node = parse("if (a) { } else if (x + 1 * 2 == 10) { }").statements[0]
    assert node.elifs is not None
    condition, _ = node.elifs[0]
    assert condition == Var("a") or "==" in repr(condition)


def test_parse_nested_if_inside_elif_body():
    node = parse("if (a) { } else if (b) { if (c) { x = 1 } }").statements[0]
    _, elif_block = node.elifs[0]
    assert elif_block.statements[0] == If(Var("c"), Block([Assign("x", Num(1))]), None)


def test_if_after_closed_if_is_new_statement():
    program = parse("if (a) { } if (b) { } else { }")
    assert len(program.statements) == 2


def test_first_true_branch_wins():
    env = run_source(
        "if (TRUE) { y = 1 } else if (TRUE) { y = 2 } else if (TRUE) { y = 3 } else { y = 4 }"
    )
    assert env["y"] == 1


def test_middle_branch_taken():
    env = run_source(
        "if (FALSE) { y = 1 } else if (FALSE) { y = 2 } else if (TRUE) { y = 3 } else { y = 4 }"
    )
    assert env["y"] == 3


def test_else_taken_when_all_false():
    env = run_source(
        "if (FALSE) { y = 1 } else if (FALSE) { y = 2 } else { y = 4 }"
    )
    assert env["y"] == 4


def test_no_branch_and_no_else_runs_nothing():
    env = run_source("if (FALSE) { y = 1 } else if (FALSE) { y = 2 } z = 9")
    assert "y" not in env
    assert env["z"] == 9


def test_last_elif_matches_without_else():
    env = run_source("if (FALSE) { y = 1 } else if (TRUE) { y = 2 }")
    assert env["y"] == 2


def test_later_conditions_not_evaluated():
    printed = []
    run_source(
        "fn pick (n: int) { print(n) return TRUE } "
        "if (pick(1)) { y = 1 } else if (pick(2)) { y = 2 } else if (pick(3)) { y = 3 }",
        out=printed.append,
    )
    assert printed == [1]


def test_evaluation_order_skips_to_else():
    printed = []
    run_source(
        "fn pick (n: int) { print(n) return FALSE } "
        "if (pick(1)) { y = 1 } else if (pick(2)) { y = 2 } else { y = 3 }",
        out=printed.append,
    )
    assert printed == [1, 2]


def test_integer_truthiness_in_elif():
    assert run_source("if (0) { y = 1 } else if (5) { y = 2 }")["y"] == 2
    assert run_source("if (0) { y = 1 } else if (-3) { y = 2 }")["y"] == 2


def test_bool_literals_in_elif():
    env = run_source("if (TRUE == FALSE) { y = 1 } else if (TRUE) { y = 2 }")
    assert env["y"] == 2


def test_string_condition_in_elif_errors():
    with pytest.raises(RolyError):
        run_source('if (FALSE) { y = 1 } else if ("yes") { y = 2 }')


def test_empty_elif_branch_skips_else():
    env = run_source("if (FALSE) { y = 1 } else if (TRUE) { } else { y = 3 }")
    assert "y" not in env


def test_break_inside_elif_branch():
    env = run_source(
        "i = 0 while (TRUE) { i += 1 "
        "if (i / 2 * 2 == i) { continue } else if (i == 5) { break } }"
    )
    assert env["i"] == 5


def test_return_inside_elif_branch():
    env = run_source(
        "fn f (n: int) { if (n == 1) { return 10 } else if (n == 2) { return 20 } return 30 } "
        "a = f(1) b = f(2) c = f(3)"
    )
    assert env["a"] == 10
    assert env["b"] == 20
    assert env["c"] == 30


def test_elif_chain_in_loop_accumulates():
    env = run_source(
        "i = 0 low = 0 high = 0 "
        "while (i < 6) { "
        "if (i < 2) { low += 1 } else if (i < 4) { high += 1 } else { low += 10 } "
        "i += 1 }"
    )
    assert env["low"] == 22
    assert env["high"] == 2


def test_very_long_chain_runs():
    chain = "".join(f" else if (x == {n}) {{ y = {n} }}" for n in range(150))
    env = run_source(f"x = 137 if (FALSE) {{ y = 0 }}{chain}")
    assert env["y"] == 137


def test_elif_without_parens_is_error():
    with pytest.raises(ParseError):
        parse("if (a) { } else if b { }")


def test_elif_without_block_is_error():
    with pytest.raises(ParseError):
        parse("if (a) { } else if (b)")


def test_second_else_is_error():
    with pytest.raises(ParseError):
        parse("if (a) { } else { } else { }")


def test_else_after_elif_chain_else_is_error():
    with pytest.raises(ParseError):
        parse("if (a) { } else if (b) { } else { } else { }")


def test_leading_else_if_is_error():
    with pytest.raises(ParseError):
        parse("else if (b) { }")


def test_elif_after_else_is_error():
    with pytest.raises(ParseError):
        parse("if (a) { } else { } else if (b) { }")


def test_else_if_without_condition_is_error():
    with pytest.raises(ParseError):
        parse("if (a) { } else if () { }")
