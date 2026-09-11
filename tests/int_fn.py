import pytest

from roly.interpreter import MAX_CALL_DEPTH, RolyError
from roly.utils.runner import run_source


def test_call_returns_value():
    env = run_source("fn one () { return 1 } x = one()")
    assert env["x"] == 1


def test_call_with_args():
    env = run_source("fn add (a: int, b: int) { return a + b } x = add(2, 3)")
    assert env["x"] == 5


def test_call_in_expression():
    env = run_source("fn dbl (n: int) { return n * 2 } x = dbl(3) + dbl(4)")
    assert env["x"] == 14


def test_call_in_condition():
    env = run_source("fn big (n: int) { return n > 10 } y = 0 if (big(20)) { y = 1 }")
    assert env["y"] == 1


def test_call_in_loop_condition():
    env = run_source(
        "fn ongoing (i: int) { return i <= 3 } i = 0 while (ongoing(i)) { i += 1 }"
    )
    assert env["i"] == 4


def test_call_returning_bool_as_condition():
    env = run_source(
        "fn done (i: int) { return i > 3 } i = 0 while (done(i) == (1 == 2)) { i += 1 }"
    )
    assert env["i"] == 4


def test_call_argument_can_be_expression():
    env = run_source("fn dbl (n: int) { return n * 2 } x = dbl(1 + 2 * 3)")
    assert env["x"] == 14


def test_call_argument_can_be_call():
    env = run_source(
        "fn dbl (n: int) { return n * 2 } x = dbl(dbl(dbl(1)))"
    )
    assert env["x"] == 8


def test_call_in_print():
    printed = []
    run_source("fn f () { return 7 } print(f())", out=printed.append)
    assert printed == [7]


def test_recursive_factorial():
    env = run_source(
        "fn myfact (n: int) { if (n <= 1) { return 1 } return n * myfact(n - 1) }"
        " x = myfact(10)"
    )
    assert env["x"] == 3628800


def test_recursive_fibonacci():
    env = run_source(
        "fn myfib (n: int) { if (n < 2) { return n } return myfib(n - 1) + myfib(n - 2) }"
        " x = myfib(15)"
    )
    assert env["x"] == 610


def test_mutual_recursion():
    env = run_source(
        "fn isodd (n: int) { if (n == 0) { return 0 } return iseven(n - 1) } "
        "fn iseven (n: int) { if (n == 0) { return 1 } return isodd(n - 1) } "
        "x = iseven(10)"
    )
    assert env["x"] == 1


def test_call_before_definition_in_source():
    env = run_source("x = f() fn f () { return 5 }")
    assert env["x"] == 5


def test_function_reads_global():
    env = run_source("g = 100 fn f () { return g } x = f()")
    assert env["x"] == 100


def test_param_shadows_global():
    env = run_source("a = 1 fn f (a: int) { return a } x = f(2)")
    assert env["x"] == 2
    assert env["a"] == 1


def test_local_variable_not_visible_outside():
    with pytest.raises(RolyError, match="undefined variable 'loc'"):
        run_source("fn f () { loc = 1 return loc } x = f() y = loc")


def test_local_assignment_shadows_global_for_write():
    env = run_source("a = 1 fn f (a: int) { a = 5 return a } x = f(2)")
    assert env["a"] == 1
    assert env["x"] == 5


def test_writing_new_local_when_global_absent():
    env = run_source("fn f (n: int) { b = n * 2 return b } x = f(3)")
    assert env["x"] == 6
    assert "b" not in env


def test_function_cannot_write_existing_global():
    env = run_source("a = 1 fn bump () { a = a + 1 return a } x = bump() y = a")
    assert env["a"] == 1
    assert env["x"] == 2
    assert env["y"] == 1


def test_function_cannot_write_global_with_compound_assign():
    env = run_source("a = 1 fn bump () { a += 1 return a } x = bump()")
    assert env["a"] == 1
    assert env["x"] == 2


def test_local_write_stable_across_calls():
    env = run_source("fn f () { t = 99 return t } a = f() t = 5 b = f()")
    assert env["t"] == 5
    assert env["a"] == 99
    assert env["b"] == 99


def test_writing_new_local_in_function():
    env = run_source("fn f (n: int) { t = n + 1 return t } x = f(4)")
    assert env["x"] == 5
    assert "t" not in env


def test_local_scopes_reset_between_calls():
    env = run_source(
        "fn f (n: int) { c = n return c } a = f(1) b = f(2)"
    )
    assert env["a"] == 1
    assert env["b"] == 2


def test_nested_calls_get_separate_scopes():
    env = run_source(
        "fn inner (n: int) { v = n * 10 return v } "
        "fn outer (n: int) { v = n + 1 return v + inner(n) } "
        "x = outer(3)"
    )
    assert env["x"] == 34


def test_function_can_call_in_loop():
    printed = []
    run_source(
        "fn dbl (n: int) { return n * 2 } i = 0 "
        "while (i < 3) { i += 1 print(dbl(i)) }",
        out=printed.append,
    )
    assert printed == [2, 4, 6]


def test_return_inside_loop_terminates_call():
    env = run_source(
        "fn firstbig (limit: int) { i = 0 while (1) { i += 1 if (i >= limit) { return i } } }"
        " x = firstbig(5)"
    )
    assert env["x"] == 5


def test_return_from_loop_after_iterations():
    env = run_source(
        "fn sum (n: int) { t = 0 i = 1 while (i <= n) { t += i i += 1 } return t }"
        " x = sum(100)"
    )
    assert env["x"] == 5050


def test_return_overrides_continue():
    env = run_source(
        "fn f () { i = 0 while (i < 10) { i += 1 if (i == 3) { return i } continue } }"
        " x = f()"
    )
    assert env["x"] == 3


def test_multiple_returns_in_branches():
    env = run_source(
        "fn mysign (n: int) { if (n > 0) { return 1 } if (n < 0) { return 0 - 1 } return 0 }"
        " a = mysign(5) b = mysign(0 - 3) c = mysign(0)"
    )
    assert env["a"] == 1
    assert env["b"] == -1
    assert env["c"] == 0


def test_string_param_and_return():
    env = run_source('fn greet (name: str) { return "hello " + name } x = greet("roly")')
    assert env["x"] == "hello roly"


def test_bool_param_and_return():
    env = run_source("fn notv (b: bool) { return b == (1 < 1) } x = notv(2 < 1)")
    assert env["x"] is True


def test_arity_mismatch_error():
    with pytest.raises(RolyError, match="expects 2 arguments, got 1"):
        run_source("fn add (a: int, b: int) { return a + b } x = add(1)")


def test_arity_too_many_error():
    with pytest.raises(RolyError, match="got 3"):
        run_source("fn add (a: int, b: int) { return a + b } x = add(1, 2, 3)")


def test_type_mismatch_int_param():
    with pytest.raises(RolyError, match="argument 'a'.*must be int"):
        run_source('fn f (a: int) { return a } x = f("s")')


def test_type_mismatch_str_param():
    with pytest.raises(RolyError, match="argument 'a'.*must be str"):
        run_source("fn f (a: str) { return a } x = f(1)")


def test_type_mismatch_bool_param():
    with pytest.raises(RolyError, match="argument 'a'.*must be bool"):
        run_source("fn f (a: bool) { return a } x = f(1)")


def test_bool_literal_not_accepted_for_int():
    with pytest.raises(RolyError, match="must be int"):
        run_source("fn f (a: int) { return a } x = f(1 == 1)")


def test_undefined_function_error():
    with pytest.raises(RolyError, match="undefined function 'g'"):
        run_source("x = g(1)")


def test_redefinition_error():
    with pytest.raises(RolyError, match="already defined"):
        run_source("fn f () { return 1 } fn f () { return 2 }")


def test_missing_return_error():
    with pytest.raises(RolyError, match="did not return a value"):
        run_source("fn f () { x = 1 } y = f()")


def test_runaway_recursion_hits_depth_limit():
    with pytest.raises(RolyError, match="call depth"):
        run_source("fn loop (n: int) { return loop(n + 1) } x = loop(0)")


def test_max_call_depth_value():
    assert MAX_CALL_DEPTH == 200


def test_deep_but_valid_recursion():
    env = run_source(
        "fn sum (n: int) { if (n == 0) { return 0 } return n + sum(n - 1) }"
        " x = sum(150)"
    )
    assert env["x"] == 11325


def test_function_not_a_value():
    with pytest.raises(RolyError, match="'f' is a function, call it as"):
        run_source("fn f () { return 1 } x = f")


def test_call_counted_in_step_limit():
    with pytest.raises(RolyError, match="step limit"):
        run_source("fn f () { return f() } x = f()", max_steps=30)


def test_callee_cannot_read_caller_local():
    with pytest.raises(RolyError, match="undefined variable 'v'"):
        run_source(
            "fn inner () { return v } fn outer (n: int) { v = n + 1 return inner() }"
            " x = outer(3)"
        )


def test_callee_cannot_write_caller_local():
    env = run_source(
        "fn g () { t = 5 return t }"
        " fn f (n: int) { t = n + 1 x = g() return t }"
        " x = f(10)"
    )
    assert env["x"] == 11


def test_sibling_calls_have_separate_locals():
    env = run_source(
        "fn a () { t = 1 return t } fn b () { t = 2 return t } x = a() y = b()"
    )
    assert env["x"] == 1
    assert env["y"] == 2


def test_reserved_parameter_name_errors():
    with pytest.raises(RolyError, match="parameter 'gcd' of 'f' is reserved"):
        run_source("fn f (gcd: int) { return gcd }")
    with pytest.raises(RolyError, match="parameter 'len' of 'f' is a builtin"):
        run_source("fn f (len: int) { return len }")
