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


def test_variable_cannot_shadow_function():
    raises(
        "'f' is already a function name",
        "fn f () { return 1 } f = 5",
    )
    raises(
        "'f' is already a function name",
        "f = 5 fn f () { return 1 }",
    )
    raises(
        "'sum_list' is already a function name",
        "!import lists {sum_list} sum_list = 5",
    )


def test_division_by_zero():
    raises("division by zero", "x = 5 / 0")
    raises("division by zero", "z = 0 y = 5 / z")
    raises("division by zero", "x = 4 while (x >= 0) { x = x / 0 }")


def test_operator_type_errors():
    raises("numeric operands", "x = 1 == 1 y = x + 2")
    raises("numeric operands", "x = TRUE + 1")
    raises("numeric operands", 'x = "a" + 1')
    raises("numeric operands", 'x = 1 + "a"')
    raises("numeric operands", 'x = "a" < "b"')
    raises("numeric operands", 'x = "a" * "b"')
    raises("numeric operands", 'x = -TRUE')
    raises("numeric operands", 'x = -"a"')
    raises("numeric operands", "x = list() + list()")
    raises("numeric operands", "x = 1 < TRUE")
    raises("numeric operands", "x = 1.5 + TRUE")
    raises("numeric operands", 'x = 1.5 < "a"')


def test_condition_type_errors():
    raises("condition must be a number", 'x = "a" if (x) { y = 1 }')
    raises("condition must be a number", "if (list()) { x = 1 }")
    raises(
        "condition must be a number",
        'if (FALSE) { y = 1 } else if ("yes") { y = 2 }',
    )


def test_chain_type_error():
    raises("numeric operands", 'x = 1 < 2 < "a"')


def test_float_division_by_zero():
    raises("division by zero", "x = 1 / 0.0")
    raises("division by zero", "x = 1.0 / 0")
    raises("division by zero", "x = 0.0 / 0.0")


def test_float_builtin_errors():
    raises("cannot convert 'abc' to float", 'x = float("abc")')
    raises("cannot convert ' 42' to float", 'x = float(" 42")')
    raises("cannot convert '1_0' to float", 'x = float("1_0")')
    raises("cannot convert 'inf' to float", 'x = float("inf")')
    raises("cannot convert 'nan' to float", 'x = float("nan")')
    raises("cannot convert", "x = float([1])")
    raises("builtin 'float' expects 1 argument", "x = float()")
    raises("builtin 'float' expects 1 argument", "x = float(1, 2)")
    raises("cannot convert inf to int", 'x = int(float("1e999"))')


def test_float_parameter_strictness():
    raises("must be float", "fn h (x: float) { return x } x = h(3)")
    raises("must be float", "fn h (x: float) { return x } x = h(TRUE)")
    raises("must be int", "fn h (x: int) { return x } x = h(1.5)")
    raises("must be int", "fn h (x: int) { return x } x = h(0.0)")


def test_huge_int_meets_float():
    build = "x = 1 i = 0 while (i < 400) { x *= 10 i += 1 } "
    raises("integer too large to convert to float", build + "y = x + 0.5")
    raises("integer too large to convert to float", build + "y = 0.5 - x")
    raises("integer too large to convert to float", build + "y = x * 2.0")
    raises("integer too large to convert to float", build + "y = x / 0.5")
    raises("integer too large to convert to float", build + "x += 0.5")
    raises("integer too large to convert to float", build + "y = float(x)")


def test_step_limit():
    raises("step limit", "while (1) { x = 1 }", max_steps=10)
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
    raises("did not return a value", "fn f () { x = 1 } print(f())")
    raises(
        "did not return a value",
        "fn f () { x = 1 } fn g (n: int) { return n } x = g(f())",
    )


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


def test_ord_errors():
    raises("builtin 'ord' expects a str", "x = ord(1)")
    raises("builtin 'ord' expects a str", "x = ord(TRUE)")
    raises("builtin 'ord' expects a str", "x = ord(1.5)")
    raises("builtin 'ord' expects a str", "x = ord([1])")
    raises("builtin 'ord' expects a single character", 'x = ord("ab")')
    raises("builtin 'ord' expects a single character", 'x = ord("")')
    raises("builtin 'ord' expects 1 argument", "x = ord()")
    raises("builtin 'ord' expects 1 argument", 'x = ord("a", "b")')


def test_insert_errors():
    raises("insert: index 2 out of range for length 1", "x = insert([1], 2, 9)")
    raises("insert: index -1 out of range", "x = insert([1], -1, 9)")
    raises("insert: index 1 out of range for length 0", "x = insert([], 1, 9)")
    raises("builtin 'insert' expects a list", 'x = insert("ab", 0, 9)')
    raises("builtin 'insert' expects a list", "x = insert(5, 0, 9)")
    raises("builtin 'insert' expects an int index", 'x = insert([1], "0", 9)')
    raises("builtin 'insert' expects an int index", "x = insert([1], 0.5, 9)")
    raises("builtin 'insert' expects 3 arguments", "x = insert([1], 0)")
    raises("builtin 'insert' expects 3 arguments", "x = insert([1], 0, 9, 9)")


def test_delete_at_errors():
    raises("delete_at: index 1 out of range for length 1", "x = delete_at([1], 1)")
    raises("delete_at: index -1 out of range", "x = delete_at([1], -1)")
    raises("delete_at: index 0 out of range for length 0", "x = delete_at([], 0)")
    raises("builtin 'delete_at' expects a list", 'x = delete_at("ab", 0)')
    raises("builtin 'delete_at' expects a list", "x = delete_at(5, 0)")
    raises("builtin 'delete_at' expects an int index", 'x = delete_at([1], "0")')
    raises("builtin 'delete_at' expects an int index", "x = delete_at([1], 0.5)")
    raises("builtin 'delete_at' expects 2 arguments", "x = delete_at([1])")
    raises("builtin 'delete_at' expects 2 arguments", "x = delete_at([1], 0, 9)")


def test_concat_errors():
    raises("builtin 'concat' expects a list", "x = concat([1], 2)")
    raises("builtin 'concat' expects a list", "x = concat(1, [2])")
    raises("builtin 'concat' expects a list", 'x = concat("ab", [1])')
    raises("builtin 'concat' expects a list", "x = concat([1], TRUE)")
    raises("builtin 'concat' expects 2 arguments", "x = concat([1])")
    raises("builtin 'concat' expects 2 arguments", "x = concat([1], [2], [3])")


def test_map_equal_errors():
    raises("builtin 'map_equal' expects a list", "x = map_equal(1, [])")
    raises("builtin 'map_equal' expects a list", 'x = map_equal([], "ab")')
    raises("builtin 'map_equal' expects a list", "x = map_equal([1], 2)")
    raises("is not a \\[key, value\\] pair", "x = map_equal([1], [])")
    raises("is not a \\[key, value\\] pair", 'x = map_equal([["a"]], [])')
    raises("is not a \\[key, value\\] pair", 'x = map_equal([], [["a", 1, 2]])')
    raises("is not a \\[key, value\\] pair", 'x = map_equal(["ab"], [])')
    raises("builtin 'map_equal' expects 2 arguments", "x = map_equal([])")
    raises("builtin 'map_equal' expects 2 arguments", "x = map_equal([], [], [])")


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
