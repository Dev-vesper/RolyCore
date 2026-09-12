import pytest

from roly.ast import BinOp, Num
from roly.compiler import compile_expression
from roly.errors import RolyError
from roly.utils.runner import run_source


def raises(match, source, **kwargs):
    with pytest.raises(RolyError, match=match):
        run_source(source, **kwargs)


def test_undefined_variable():
    raises("undefined variable 'y'", "x = y")
    raises("undefined variable 'n'", "while (n < 3) { n += 1 }")
    raises("undefined variable 's'", 'x = s + "!"')
    raises("undefined variable 'x'", "x += 1")
    raises("undefined variable 'b'", "a = 1 a += b")
    raises(
        "undefined variable 'loc'",
        "fn f () { loc = 1 return loc } x = f() y = loc",
    )


def test_leftmost_operand_error_reported_first():
    raises("undefined variable 'a'", "x = a + b")
    raises("division by zero", "x = 1 / 0 + b")


def test_undefined_function():
    raises("undefined function 'g'", "x = g(1)")


def test_division_by_zero():
    raises("division by zero", "x = 5 / 0")
    raises("division by zero", "z = 0 y = 5 / z")
    raises("division by zero", "x = 4 while (x >= 0) { x = x / 0 }")


def test_operator_type_errors():
    raises("integer operands", "x = 1 == 1 y = x + 2")
    raises("integer operands", "x = TRUE + 1")
    raises("integer operands", 'x = "a" + 1')
    raises("integer operands", 'x = 1 + "a"')
    raises("integer operands", 'x = "a" < "b"')
    raises("integer operands", 'x = "a" * "b"')
    raises("integer operands", 'x = -TRUE')
    raises("integer operands", 'x = -"a"')
    raises("integer operands", "x = list() + list()")


def test_condition_type_errors():
    raises("condition must be a number", 'x = "a" if (x) { y = 1 }')
    raises("condition must be a number", "if (list()) { x = 1 }")
    raises(
        "condition must be a number",
        'if (FALSE) { y = 1 } else if ("yes") { y = 2 }',
    )


def test_chain_type_error():
    raises("integer operands", 'x = 1 < 2 < "a"')


def test_step_limit():
    raises("step limit", "while (1) { }", max_steps=10)
    raises("step limit", "x = 1 while (x > 0) { x += 1 }", max_steps=25)
    raises("step limit", "while (1) { continue }", max_steps=50)
    raises("step limit", "fn f () { return f() } x = f()", max_steps=30)
    raises(
        "step limit",
        "fn one () { return 1 } " + "one() " * 200,
        max_steps=100,
    )


def test_call_depth_limit():
    raises("call depth", "fn loop (n: int) { return loop(n + 1) } x = loop(0)")


def test_deep_recursion_becomes_clean_message():
    body = "return r(n - 1)"
    for _ in range(30):
        body = "if (TRUE) { " + body + " }"
    raises(
        "call depth of 200",
        "fn r (n: int) { if (n <= 0) { return 0 } " + body + " } x = r(1000)",
    )


def test_function_arity_errors():
    fn = "fn add (a: int, b: int) { return a + b }"
    raises("expects 2 arguments, got 1", fn + " x = add(1)")
    raises("got 3", fn + " x = add(1, 2, 3)")
    raises("expects 1 argument, got 0", "fn f (a: int) { return a } x = f()")


def test_arity_checked_before_argument_effects():
    printed = []
    with pytest.raises(RolyError, match="expects 1 argument"):
        run_source(
            'fn f (a: int) { return a } fn g () { print(42) return 1 }'
            " x = f(g(), 2)",
            out=printed.append,
        )
    assert printed == []


def test_function_argument_type_errors():
    raises("argument 'a'.*must be int", 'fn f (a: int) { return a } x = f("s")')
    raises("argument 'a'.*must be str", "fn f (a: str) { return a } x = f(1)")
    raises("argument 'a'.*must be bool", "fn f (a: bool) { return a } x = f(1)")
    raises("argument 'a'.*must be int", "fn f (a: int) { return a } x = f(1 == 1)")
    raises("argument 'l'.*must be list", "fn f (l: list) { return l } x = f(5)")


def test_function_must_return():
    raises("did not return a value", "fn f () { x = 1 } y = f()")
    raises("did not return a value", "fn noend () { one = 1 } noend()")


def test_function_redefinition():
    raises("already defined", "fn f () { return 1 } fn f () { return 2 }")


def test_function_not_a_value():
    raises("'f' is a function, call it as", "fn f () { return 1 } x = f")


def test_callee_cannot_see_caller_locals():
    raises(
        "undefined variable 'v'",
        "fn inner () { return v } fn outer (n: int) { v = n + 1 return inner() }"
        " x = outer(3)",
    )


def test_builtin_used_as_value():
    raises("'len' is a builtin, not a value", "x = len")
    raises("'format' is a builtin, not a value", "x = format")


def test_subscript_errors():
    raises("char: index 4 out of range for length 4", 'x = "roly"[4]')
    raises("index -1 out of range", 'x = "roly"[-1]')
    raises("index 0 out of range for length 0", 'x = ""[0]')
    raises(r"expects \(str, int\)", 'x = "ab"["0"]')
    raises("get: index 1 out of range for length 1", "x = push(list(), 5)[1]")
    raises("expects a list", "x = 5[0]")
    raises("expects a list", "x = TRUE[0]")


def test_unknown_operator_fails_to_compile():
    with pytest.raises(RolyError, match="unknown operator"):
        compile_expression(BinOp("%", Num(1), Num(2)))
