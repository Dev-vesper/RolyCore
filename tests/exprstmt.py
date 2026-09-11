import pytest

from roly.ast import Call, ExprStmt, ModuleCall, Num, Program
from roly.errors import RolyError
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_call_alone_is_expression_statement():
    assert parse("f(1)") == Program([ExprStmt(Call("f", [Num(1)]))])


def test_call_without_arguments_is_expression_statement():
    node = parse("tick()").statements[0]
    assert isinstance(node, ExprStmt)
    assert node.value.name == "tick"
    assert node.value.args == []


def test_module_call_alone_is_expression_statement():
    node = parse("mod.tick()").statements[0]
    assert isinstance(node, ExprStmt)
    assert isinstance(node.value, ModuleCall)
    assert node.value.module == "mod"
    assert node.value.name == "tick"


def test_expression_statement_after_assignment():
    program = parse("x = 5 f(x)")
    assert isinstance(program.statements[1], ExprStmt)


def test_bare_number_is_parse_error():
    with pytest.raises(ParseError, match="expected a statement"):
        parse("1")


def test_bare_arithmetic_is_parse_error():
    with pytest.raises(ParseError, match="expected a statement"):
        parse("1 + 1")


def test_bare_variable_is_parse_error():
    with pytest.raises(ParseError, match="a call like"):
        parse("x = 1 x")


def test_bare_subscript_is_parse_error():
    with pytest.raises(ParseError, match="a call like"):
        parse("l = [1] l[0]")


def test_subscript_on_call_result_is_parse_error():
    with pytest.raises(ParseError, match="a call like"):
        parse("fn f () { return [1] } f()[0]")


def test_bare_builtin_call_is_expression_statement():
    node = parse("l = [1, 2] len(l)").statements[1]
    assert isinstance(node, ExprStmt)
    assert node.value.name == "len"


def test_call_runs_for_side_effects_and_discards_value():
    printed = []
    run_source('fn shout (m: str) { print(m) return 99 } shout("hi")', out=printed.append)
    assert printed == ["hi"]


def test_module_call_mutates_state_via_bare_call(tmp_path):
    (tmp_path / "counter.roly").write_text(
        "total = 0\nfn bump (n: int) {\n    total += n\n    return total\n}\n",
        encoding="utf-8",
    )
    printed = []
    env = run_source(
        "import counter\nx = counter.bump(5)\ncounter.bump(10)\nprint(counter.total)\n",
        out=printed.append,
        base_dir=tmp_path,
        entry_path=tmp_path / "main.roly",
    )
    assert printed == [15]
    assert env["x"] == 5


def test_expression_statement_counts_steps():
    src = "fn one () { return 1 } " + "one() " * 200
    run_source(src)
    with pytest.raises(RolyError, match="step"):
        run_source("fn one () { return 1 } " + "one() " * 200, max_steps=100)


def test_bare_call_to_function_without_return_errors():
    with pytest.raises(RolyError):
        run_source("fn noend () { one = 1 } noend()")
