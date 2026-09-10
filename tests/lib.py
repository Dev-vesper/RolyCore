import pytest

from roly.errors import RolyError
from roly.stdlib import lib_functions
from roly.utils.runner import run_source


def test_lib_provides_functions():
    names = set(lib_functions())
    for name in [
        "abs", "sign", "max", "min", "clamp", "digitsum", "count_digits",
        "reverse", "repeat", "sum_to",
        "pow", "sqrt", "gcd", "lcm", "fact", "fib", "is_prime", "is_even",
        "is_odd",
    ]:
        assert name in names


def test_lib_abs():
    assert run_source("x = abs(-5)")["x"] == 5
    assert run_source("x = abs(5)")["x"] == 5
    assert run_source("x = abs(0)")["x"] == 0


def test_lib_sign():
    assert run_source("x = sign(-9)")["x"] == -1
    assert run_source("x = sign(0)")["x"] == 0
    assert run_source("x = sign(9)")["x"] == 1


def test_lib_max_min():
    assert run_source("x = max(3, 7)")["x"] == 7
    assert run_source("x = max(-3, -7)")["x"] == -3
    assert run_source("x = min(3, 7)")["x"] == 3


def test_lib_clamp():
    assert run_source("x = clamp(150, 0, 100)")["x"] == 100
    assert run_source("x = clamp(-5, 0, 100)")["x"] == 0
    assert run_source("x = clamp(42, 0, 100)")["x"] == 42


def test_lib_digitsum():
    assert run_source("x = digitsum(987654)")["x"] == 39
    assert run_source("x = digitsum(-31)")["x"] == 4
    assert run_source("x = digitsum(0)")["x"] == 0


def test_lib_count_digits():
    assert run_source("x = count_digits(987654)")["x"] == 6
    assert run_source("x = count_digits(-42)")["x"] == 2
    assert run_source("x = count_digits(0)")["x"] == 1


def test_lib_reverse():
    assert run_source("x = reverse(12345)")["x"] == 54321
    assert run_source("x = reverse(-120)")["x"] == -21
    assert run_source("x = reverse(0)")["x"] == 0


def test_lib_repeat():
    assert run_source('x = repeat("ab", 3)')["x"] == "ababab"
    assert run_source('x = repeat("-", 0)')["x"] == ""
    assert run_source('x = repeat("x", 1)')["x"] == "x"


def test_lib_sum_to():
    assert run_source("x = sum_to(100)")["x"] == 5050
    assert run_source("x = sum_to(0)")["x"] == 0
    assert run_source("x = sum_to(-3)")["x"] == 0


def test_lib_pow():
    assert run_source("x = pow(2, 10)")["x"] == 1024
    assert run_source("x = pow(3, 0)")["x"] == 1
    assert run_source("x = pow(-2, 3)")["x"] == -8
    assert run_source("x = pow(2, -1)")["x"] == 1


def test_lib_sqrt():
    assert run_source("x = sqrt(994009)")["x"] == 997
    assert run_source("x = sqrt(0)")["x"] == 0
    assert run_source("x = sqrt(3)")["x"] == 1
    assert run_source("x = sqrt(4)")["x"] == 2


def test_lib_gcd():
    assert run_source("x = gcd(48, 18)")["x"] == 6
    assert run_source("x = gcd(-48, 18)")["x"] == 6
    assert run_source("x = gcd(7, 0)")["x"] == 7


def test_lib_lcm():
    assert run_source("x = lcm(4, 6)")["x"] == 12
    assert run_source("x = lcm(0, 5)")["x"] == 0
    assert run_source("x = lcm(-4, 6)")["x"] == 12


def test_lib_fact():
    assert run_source("x = fact(10)")["x"] == 3628800
    assert run_source("x = fact(0)")["x"] == 1


def test_lib_fib():
    assert run_source("x = fib(15)")["x"] == 610
    assert run_source("x = fib(0)")["x"] == 0
    assert run_source("x = fib(1)")["x"] == 1


def test_lib_is_prime():
    assert run_source("x = is_prime(97)")["x"] is True
    assert run_source("x = is_prime(1)")["x"] is False
    assert run_source("x = is_prime(2)")["x"] is True
    assert run_source("x = is_prime(91)")["x"] is False


def test_lib_is_even_is_odd():
    assert run_source("x = is_even(10)")["x"] is True
    assert run_source("x = is_even(7)")["x"] is False
    assert run_source("x = is_odd(7)")["x"] is True
    assert run_source("x = is_odd(-4)")["x"] is False


def test_lib_functions_call_each_other():
    assert run_source("x = lcm(12, 18)")["x"] == 36


def test_lib_function_in_user_expression():
    assert run_source("x = gcd(48, 18) + pow(2, 5)")["x"] == 38
    assert run_source('x = "[" + repeat("=", 4) + "]"')["x"] == "[====]"


def test_lib_function_in_condition():
    env = run_source("if (is_prime(7)) { a = 1 } else { a = 2 }")
    assert env["a"] == 1


def test_lib_function_as_user_fn_argument():
    env = run_source(
        "fn dbl (n: int) { return n * 2 } x = dbl(sqrt(81))"
    )
    assert env["x"] == 18


def test_user_fn_can_call_lib():
    env = run_source(
        "fn hyp_sq (a: int, b: int) { return pow(a, 2) + pow(b, 2) }"
        " x = hyp_sq(3, 4)"
    )
    assert env["x"] == 25


def test_user_fn_redefining_lib_name_errors():
    with pytest.raises(RolyError, match="reserved by the standard library"):
        run_source("fn gcd (a: int, b: int) { return a }")


def test_variable_with_lib_name_errors():
    with pytest.raises(RolyError, match="reserved by the standard library"):
        run_source("fact = 5")


def test_compound_assign_with_lib_name_errors():
    with pytest.raises(RolyError, match="reserved by the standard library"):
        run_source("x = 1 x += 1 fib = 2")


def test_local_variable_with_lib_name_errors():
    with pytest.raises(RolyError, match="reserved by the standard library"):
        run_source("fn f (n: int) { max = 5 return n } x = f(1)")


def test_lib_arg_types_checked():
    with pytest.raises(RolyError, match="must be int"):
        run_source('x = abs("-5")')


def test_lib_arity_checked():
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source("x = max(1)")


def test_lib_builtin_and_lib_together():
    env = run_source('x = int(repeat("1", 3)) + fact(3)')
    assert env["x"] == 117


def test_lib_does_not_touch_user_globals():
    source = (
        "r = 1 i = 2 s = 3 t = 4 a = 5 b = 6 g = 7 c = 8 d = 9 m = 10 "
        "x = 11 y = 12 n = 13 e = 14 lo = 15 hi = 16 "
        "v1 = pow(2, 5) v2 = sqrt(17) v3 = gcd(12, 8) v4 = lcm(3, 4) "
        "v5 = fact(5) v6 = fib(9) v7 = is_prime(11) v8 = abs(-9) "
        "v9 = sign(-2) v10 = max(1, 2) v11 = min(1, 2) v12 = clamp(5, 0, 3) "
        "v13 = digitsum(99) v14 = count_digits(500) v15 = reverse(321) "
        "v16 = sum_to(10) v17 = is_even(4) v18 = is_odd(4)"
    )
    env = run_source(source)
    for name in [
        "r", "i", "s", "t", "a", "b", "g", "c", "d", "m",
        "x", "y", "n", "e", "lo", "hi",
    ]:
        assert name in env, name
    assert env["r"] == 1
    assert env["i"] == 2
    assert env["s"] == 3
    assert env["t"] == 4
    assert env["a"] == 5
    assert env["b"] == 6
    assert env["g"] == 7
    assert env["c"] == 8
    assert env["d"] == 9
    assert env["m"] == 10
    assert env["x"] == 11
    assert env["y"] == 12
    assert env["n"] == 13
    assert env["e"] == 14
    assert env["lo"] == 15
    assert env["hi"] == 16


def test_lib_does_not_touch_user_locals():
    env = run_source(
        "fn f (p: int) { g = 100 r = 100 s = 100 a = 100 "
        "v = lcm(4, 6) w = gcd(10, 4) u = digitsum(77) "
        "return g + r + s + a } out = f(1)"
    )
    assert env["out"] == 400


def test_lib_result_can_assign_to_user_variable():
    env = run_source("s = repeat(\"=\", 3) print(digitsum(99))")
    assert env["s"] == "==="
