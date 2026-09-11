import pytest

from roly.errors import RolyError
from roly.stdlib import lib_functions
from roly.utils.runner import run_source


def test_lib_provides_functions():
    names = set(lib_functions())
    for name in [
        "abs", "sign", "min", "max", "clamp", "mod", "gcd", "lcm",
        "isqrt",
        "digit_char", "to_base", "binary", "hex", "pad", "group",
        "roman",
        "digit_count", "digit_sum", "digital_root", "reverse_digits",
        "is_palindrome",
        "is_even", "is_odd", "popcount", "bitlen",
        "is_prime", "next_prime", "factorial", "fibonacci", "divisor_count",
        "collatz_steps",
    ]:
        assert name in names, name
    assert "pow" not in names
    assert "repeat" not in names


def test_lib_abs():
    assert run_source("x = abs(-5)")["x"] == 5
    assert run_source("x = abs(5)")["x"] == 5
    assert run_source("x = abs(0)")["x"] == 0


def test_lib_sign():
    assert run_source("x = sign(-9)")["x"] == -1
    assert run_source("x = sign(0)")["x"] == 0
    assert run_source("x = sign(9)")["x"] == 1


def test_lib_min_max():
    assert run_source("x = min(3, 7)")["x"] == 3
    assert run_source("x = min(-3, -7)")["x"] == -7
    assert run_source("x = max(3, 7)")["x"] == 7
    assert run_source("x = max(-3, -7)")["x"] == -3


def test_lib_clamp():
    assert run_source("x = clamp(150, 0, 100)")["x"] == 100
    assert run_source("x = clamp(-5, 0, 100)")["x"] == 0
    assert run_source("x = clamp(42, 0, 100)")["x"] == 42


def test_lib_clamp_contradictory_bounds_error():
    with pytest.raises(RolyError, match="clamp: lo must not exceed hi"):
        run_source("x = clamp(5, 10, 0)")


def test_lib_mod_positive():
    assert run_source("x = mod(7, 3)")["x"] == 1
    assert run_source("x = mod(6, 3)")["x"] == 0


def test_lib_mod_is_floored():
    assert run_source("x = mod(-7, 3)")["x"] == 2
    assert run_source("x = mod(7, -3)")["x"] == -2
    assert run_source("x = mod(-7, -3)")["x"] == -1


def test_lib_mod_invariant():
    env = run_source(
        "a = -17 d = 5 q = a / d r = mod(a, d) ok = a == q * d + r"
    )
    assert env["ok"] is True


def test_lib_mod_zero_divisor_errors():
    with pytest.raises(RolyError):
        run_source("x = mod(5, 0)")


def test_lib_pow_big():
    env = run_source("fn pow (b: int, e: int) { r = 1 i = 0 while (i < e) { r *= b i += 1 } return r } x = pow(2, 100)")
    assert env["x"] == 2**100


def test_pow_and_repeat_are_not_lib_functions():
    with pytest.raises(RolyError, match="undefined function 'pow'"):
        run_source("x = pow(2, 10)")
    with pytest.raises(RolyError, match="undefined function 'repeat'"):
        run_source('x = repeat("a", 2)')


def test_pow_and_repeat_names_are_free():
    env = run_source(
        'fn repeat (s: str, n: int) { r = "" i = 0 while (i < n) { r = r + s i += 1 } return r }'
        ' x = repeat("ab", 3)'
    )
    assert env["x"] == "ababab"
    env = run_source("pow = 5 repeat = 6 x = pow + repeat")
    assert env["x"] == 11


def test_lib_gcd():
    assert run_source("x = gcd(48, 18)")["x"] == 6
    assert run_source("x = gcd(-48, 18)")["x"] == 6
    assert run_source("x = gcd(7, 0)")["x"] == 7
    assert run_source("x = gcd(0, 0)")["x"] == 0


def test_lib_lcm():
    assert run_source("x = lcm(4, 6)")["x"] == 12
    assert run_source("x = lcm(0, 5)")["x"] == 0
    assert run_source("x = lcm(-4, 6)")["x"] == 12


def test_lib_isqrt():
    assert run_source("x = isqrt(994009)")["x"] == 997
    assert run_source("x = isqrt(0)")["x"] == 0
    assert run_source("x = isqrt(3)")["x"] == 1
    assert run_source("x = isqrt(4)")["x"] == 2
    with pytest.raises(RolyError, match="non-negative"):
        run_source("x = isqrt(-4)")


def test_lib_digit_char():
    assert run_source('x = digit_char(0)')["x"] == "0"
    assert run_source('x = digit_char(9)')["x"] == "9"
    assert run_source('x = digit_char(10)')["x"] == "a"
    assert run_source('x = digit_char(15)')["x"] == "f"


def test_lib_digit_char_out_of_range_errors():
    with pytest.raises(RolyError, match="digit_char: d must be between 0 and 15"):
        run_source("x = digit_char(-1)")
    with pytest.raises(RolyError, match="digit_char: d must be between 0 and 15"):
        run_source("x = digit_char(16)")


def test_lib_to_base():
    assert run_source('x = to_base(255, 16)')["x"] == "ff"
    assert run_source('x = to_base(10, 2)')["x"] == "1010"
    assert run_source('x = to_base(255, 2)')["x"] == "11111111"
    assert run_source('x = to_base(255, 8)')["x"] == "377"
    assert run_source('x = to_base(5, 10)')["x"] == "5"


def test_lib_to_base_edge_cases():
    assert run_source('x = to_base(0, 2)')["x"] == "0"
    assert run_source('x = to_base(-10, 2)')["x"] == "-1010"
    assert run_source('x = to_base(1, 2)')["x"] == "1"


def test_lib_to_base_invalid_base():
    with pytest.raises(RolyError, match="between 2 and 16"):
        run_source("x = to_base(5, 1)")
    with pytest.raises(RolyError, match="between 2 and 16"):
        run_source("x = to_base(5, 17)")


def test_lib_binary_hex():
    assert run_source('x = binary(2026)')["x"] == "11111101010"
    assert run_source('x = hex(255)')["x"] == "ff"
    assert run_source('x = hex(4096)')["x"] == "1000"
    assert run_source('x = binary(0)')["x"] == "0"


def test_lib_pad():
    assert run_source('x = pad(42, 5)')["x"] == "00042"
    assert run_source('x = pad(-42, 5)')["x"] == "-0042"
    assert run_source('x = pad(12345, 3)')["x"] == "12345"
    assert run_source('x = pad(7, 1)')["x"] == "7"


def test_lib_group():
    assert run_source('x = group(1234567)')["x"] == "1,234,567"
    assert run_source('x = group(-9876543)')["x"] == "-9,876,543"
    assert run_source('x = group(0)')["x"] == "0"
    assert run_source('x = group(999)')["x"] == "999"
    assert run_source('x = group(1000)')["x"] == "1,000"
    assert run_source('x = group(1000001)')["x"] == "1,000,001"


def test_lib_roman():
    assert run_source('x = roman(1994)')["x"] == "MCMXCIV"
    assert run_source('x = roman(2026)')["x"] == "MMXXVI"
    assert run_source('x = roman(3999)')["x"] == "MMMCMXCIX"
    assert run_source('x = roman(58)')["x"] == "LVIII"
    assert run_source('x = roman(4)')["x"] == "IV"
    assert run_source('x = roman(9)')["x"] == "IX"
    with pytest.raises(RolyError, match="between 1 and 3999"):
        run_source("x = roman(0)")
    with pytest.raises(RolyError, match="between 1 and 3999"):
        run_source("x = roman(4000)")


def test_lib_digit_count():
    assert run_source("x = digit_count(987654)")["x"] == 6
    assert run_source("x = digit_count(-42)")["x"] == 2
    assert run_source("x = digit_count(0)")["x"] == 1


def test_lib_digit_sum():
    assert run_source("x = digit_sum(987654)")["x"] == 39
    assert run_source("x = digit_sum(-31)")["x"] == 4
    assert run_source("x = digit_sum(0)")["x"] == 0


def test_lib_digital_root():
    assert run_source("x = digital_root(987654)")["x"] == 3
    assert run_source("x = digital_root(0)")["x"] == 0
    assert run_source("x = digital_root(7)")["x"] == 7


def test_lib_reverse_digits():
    assert run_source("x = reverse_digits(12345)")["x"] == 54321
    assert run_source("x = reverse_digits(-120)")["x"] == -21
    assert run_source("x = reverse_digits(0)")["x"] == 0


def test_lib_is_palindrome():
    assert run_source("x = is_palindrome(12321)")["x"] is True
    assert run_source("x = is_palindrome(12322)")["x"] is False
    assert run_source("x = is_palindrome(-121)")["x"] is False
    assert run_source("x = is_palindrome(7)")["x"] is True


def test_lib_is_even_is_odd():
    assert run_source("x = is_even(10)")["x"] is True
    assert run_source("x = is_even(7)")["x"] is False
    assert run_source("x = is_odd(7)")["x"] is True
    assert run_source("x = is_odd(-4)")["x"] is False


def test_lib_popcount():
    assert run_source("x = popcount(255)")["x"] == 8
    assert run_source("x = popcount(0)")["x"] == 0
    assert run_source("x = popcount(1)")["x"] == 1
    assert run_source("x = popcount(-7)")["x"] == 3


def test_lib_bitlen():
    assert run_source("x = bitlen(255)")["x"] == 8
    assert run_source("x = bitlen(0)")["x"] == 0
    assert run_source("x = bitlen(256)")["x"] == 9


def test_lib_is_prime():
    assert run_source("x = is_prime(97)")["x"] is True
    assert run_source("x = is_prime(1)")["x"] is False
    assert run_source("x = is_prime(2)")["x"] is True
    assert run_source("x = is_prime(91)")["x"] is False


def test_lib_next_prime():
    assert run_source("x = next_prime(97)")["x"] == 101
    assert run_source("x = next_prime(1)")["x"] == 2
    assert run_source("x = next_prime(0)")["x"] == 2


def test_lib_factorial():
    assert run_source("x = factorial(10)")["x"] == 3628800
    assert run_source("x = factorial(0)")["x"] == 1


def test_lib_fibonacci():
    assert run_source("x = fibonacci(15)")["x"] == 610
    assert run_source("x = fibonacci(0)")["x"] == 0
    assert run_source("x = fibonacci(1)")["x"] == 1


def test_lib_divisor_count():
    assert run_source("x = divisor_count(28)")["x"] == 6
    assert run_source("x = divisor_count(36)")["x"] == 9
    assert run_source("x = divisor_count(1)")["x"] == 1
    with pytest.raises(RolyError, match="positive integer"):
        run_source("x = divisor_count(0)")


def test_lib_collatz_steps():
    assert run_source("x = collatz_steps(27)")["x"] == 111
    assert run_source("x = collatz_steps(1)")["x"] == 0
    assert run_source("x = collatz_steps(6)")["x"] == 8


def test_lib_functions_call_each_other():
    assert run_source("x = lcm(12, 18)")["x"] == 36
    assert run_source('x = group(1000001)')["x"] == "1,000,001"


def test_lib_function_in_user_expression():
    assert run_source("x = gcd(48, 18) + isqrt(25)")["x"] == 11
    assert run_source('x = "[" + binary(3) + "]"')["x"] == "[11]"


def test_lib_function_in_condition():
    env = run_source("if (is_prime(7)) { a = 1 } else { a = 2 }")
    assert env["a"] == 1


def test_lib_function_as_user_fn_argument():
    env = run_source(
        "fn dbl (n: int) { return n * 2 } x = dbl(isqrt(81))"
    )
    assert env["x"] == 18


def test_user_fn_can_call_lib():
    env = run_source(
        "fn hyp_sq (a: int, b: int) { return isqrt(a * a + b * b) }"
        " x = hyp_sq(3, 4)"
    )
    assert env["x"] == 5


def test_user_fn_redefining_lib_name_errors():
    with pytest.raises(RolyError, match="reserved by the standard library"):
        run_source("fn gcd (a: int, b: int) { return a }")


def test_variable_with_lib_name_errors():
    with pytest.raises(RolyError, match="reserved by the standard library"):
        run_source("factorial = 5")


def test_compound_assign_with_lib_name_errors():
    with pytest.raises(RolyError, match="reserved by the standard library"):
        run_source("x = 1 x += 1 fibonacci = 2")


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
    env = run_source('x = int(binary(7)) + factorial(3)')
    assert env["x"] == 117


def test_lib_does_not_touch_user_globals():
    source = (
        "r = 1 i = 2 s = 3 t = 4 a = 5 b = 6 g = 7 c = 8 d = 9 m = 10 "
        "x = 11 y = 12 n = 13 e = 14 lo = 15 hi = 16 w = 17 first = 18 "
        "chunk = 19 target = 20 base = 21 "
        "v1 = binary(5) v2 = isqrt(17) v3 = gcd(12, 8) v4 = lcm(3, 4) "
        "v5 = factorial(5) v6 = fibonacci(9) v7 = is_prime(11) v8 = abs(-9) "
        "v9 = sign(-2) v10 = max(1, 2) v11 = min(1, 2) v12 = clamp(5, 0, 3) "
        "v13 = digit_sum(99) v14 = digit_count(500) "
        "v15 = reverse_digits(321) v16 = digital_root(99) "
        "v17 = is_even(4) v18 = is_odd(4) v19 = popcount(7) v20 = bitlen(7) "
        "v21 = mod(7, 3) v22 = next_prime(10) v23 = divisor_count(12) "
        "v24 = collatz_steps(6) v25 = to_base(10, 2) v26 = pad(1, 3) "
        "v27 = group(1000) v28 = roman(9) v29 = is_palindrome(9)"
    )
    env = run_source(source)
    for name, value in [
        ("r", 1), ("i", 2), ("s", 3), ("t", 4), ("a", 5), ("b", 6),
        ("g", 7), ("c", 8), ("d", 9), ("m", 10), ("x", 11), ("y", 12),
        ("n", 13), ("e", 14), ("lo", 15), ("hi", 16), ("w", 17),
        ("first", 18), ("chunk", 19), ("target", 20), ("base", 21),
    ]:
        assert env[name] == value, name


def test_lib_does_not_touch_user_locals():
    env = run_source(
        "fn f (p: int) { g = 100 r = 100 s = 100 a = 100 m = 100 "
        "v = lcm(4, 6) w = gcd(10, 4) u = digit_sum(77) t = to_base(9, 2) "
        "return g + r + s + a + m } out = f(1)"
    )
    assert env["out"] == 500


def test_lib_result_can_assign_to_user_variable():
    env = run_source('s = binary(5) print(digit_sum(99))')
    assert env["s"] == "101"


def test_lib_fail_builtin_raises():
    with pytest.raises(RolyError, match="custom message"):
        run_source('x = fail("custom message")')


def test_lib_negative_inputs_error():
    with pytest.raises(RolyError, match="fibonacci: n must be non-negative"):
        run_source("x = fibonacci(-1)")
    with pytest.raises(RolyError, match="collatz_steps: n must be a positive"):
        run_source("x = collatz_steps(0)")
