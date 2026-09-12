import pytest

import roly.stdlib as stdlib
from roly.errors import RolyError
from roly.utils.runner import run_source


def raises(match, source, **kwargs):
    with pytest.raises(RolyError, match=match):
        run_source(source, **kwargs)


def test_lib_guards_error():
    raises("isqrt: n must be non-negative", "x = isqrt(-1)")
    raises("roman: n must be between 1 and 3999", "x = roman(0)")
    raises("roman: n must be between 1 and 3999", "x = roman(4000)")
    raises("between 2 and 16", "x = to_base(5, 1)")
    raises("between 2 and 16", "x = to_base(5, 17)")
    raises("digit_char: d must be between 0 and 15", "x = digit_char(-1)")
    raises("digit_char: d must be between 0 and 15", "x = digit_char(16)")
    raises("clamp: lo must not exceed hi", "x = clamp(5, 10, 0)")
    raises("division by zero", "x = mod(5, 0)")


def test_lib_argument_types_checked():
    raises("must be int", 'x = abs("-5")')
    raises("must be str", "x = upper(42)")
    raises("must be int", 'x = substr("hi", "0", 1)')
    raises("must be int", 'x = remove_at(list(), "0")')
    raises("must be str", "x = join(list(), 5)")
    raises("must be list", "x = reverse_list(5)")


def test_lib_arity_checked():
    raises("expects 2 arguments", "x = max(1)")
    raises("expects 2 arguments", 'x = starts_with("hi")')
    raises("expects 2 arguments", "x = join(list())")


def test_deleted_names_are_not_lib_functions():
    raises("undefined function 'pow'", "x = pow(2, 10)")
    raises("undefined function 'repeat'", 'x = repeat("a", 2)')
    raises("undefined function 'sign'", "x = sign(-9)")
    raises("undefined function 'factorial'", "x = factorial(5)")


def test_list_lib_guards_error():
    raises("max_list", "x = max_list(list())")
    raises("min_list", "x = min_list(list())")
    raises("remove_at", "x = remove_at(list(), 0)")
    raises("remove_at", "x = remove_at(push(list(), 1), 1)")
    raises("remove_at", "x = remove_at(push(list(), 1), -1)")


def test_list_lib_element_types_checked():
    raises("requires integer operands", 'x = sum_list(list("ab"))')
    raises("requires integer operands", 'x = sort_list(["a"])')
    raises("requires integer operands", "x = max_list([TRUE])")
    raises("requires integer operands", 'x = min_list(["zz"])')
    raises("requires integer operands", "x = sort_list([[1]])")


def test_string_builtin_errors():
    raises("expects a str or a list", "x = len(42)")
    raises("out of range", 'x = char("hi", 2)')
    raises("out of range", 'x = char("hi", -1)')
    raises("expects", "x = char(42, 0)")
    raises("expects 2 arguments", 'x = char("hi")')


def test_conversion_builtin_errors():
    for source in [
        'x = int("")', 'x = int(" 42 ")', 'x = int("1_000")',
        'x = int("0x10")', 'x = int("abc")', 'x = int("-")',
        "x = int(list())",
    ]:
        raises("cannot convert", source)
    raises("cannot convert", "x = bool(list())")


def test_conversion_arity_checked():
    raises("expects 1 argument", "x = int()")
    raises("expects 1 argument", "x = int(1, 2)")


def test_list_builtin_errors():
    raises("expects a str", "x = list(42)")
    raises("no arguments or a str", 'x = list("a", "b")')
    raises("expects a list", "x = push(5, 1)")
    raises("expects 2 arguments", "x = push(list())")
    raises("index 3 out of range for length 3", 'x = get(list("abc"), 3)')
    raises("index -1 out of range", 'x = get(list("abc"), -1)')
    raises("expects a list", 'x = get("abc", 0)')
    raises("expects an int index", 'x = get(list("abc"), "0")')
    raises("expects 2 arguments", "x = get(list())")
    raises(
        "index 2 out of range for length 2",
        "x = set(push(push(list(), 1), 2), 2, 9)",
    )
    raises("expects 3 arguments", "x = set(list(), 0)")


def test_format_errors():
    raises("no argument for placeholder 0", 'x = format("{} and {}")')
    raises("no argument for placeholder 1", 'x = format("{} and {}", 1)')
    raises("no argument for placeholder 2", 'x = format("{2}", 1, 2)')
    raises("single '}'", 'x = format("a}b")')
    raises("unmatched", 'x = format("{")')
    raises("invalid placeholder", 'x = format("{abc}")')
    raises("invalid placeholder", 'x = format("{-1}")')
    raises("cannot mix", 'x = format("{} {0}", 1)')
    raises("cannot mix", 'x = format("{0} {}", 1)')
    raises("expects a str", "x = format(42)")
    raises("expects a format string", "x = format()")


def test_fail_builtin_errors():
    raises("custom message", 'x = fail("custom message")')
    raises("builtin 'fail' expects 1 argument, got 2", 'x = fail("a", "b")')
    raises("builtin 'fail' expects 1 argument, got 0", "x = fail()")
    raises(r"builtin 'fail' expects a str, got 42", "x = fail(42)")


def test_builtin_names_reserved():
    raises("builtin", "push = 5")
    raises("builtin", "fn get () { return 1 }")
    raises("builtin", "fn f (set: int) { return set }")
    raises("builtin", "format = 5")
    raises("builtin", "fn len (a: int) { return a }")
    raises("builtin", "char = 5")


def test_lib_names_reserved():
    raises("reserved by the standard library", "gcd = 5")
    raises("reserved by the standard library", "x = 1 x += 1 lcm = 2")
    raises("reserved by the standard library", "fn gcd (a: int, b: int) { return a }")
    raises(
        "reserved by the standard library",
        "fn f (n: int) { max = 5 return n } x = f(1)",
    )
    raises("reserved by the standard library", "sort_list = 5")
    raises("reserved by the standard library", "upper = 5")
    raises("reserved by the standard library", "fn trim (a: str) { return a }")
    raises(
        "reserved by the standard library",
        "fn reverse_list (l: list) { return l }",
    )


def test_parameter_names_checked():
    raises("parameter 'gcd' of 'f' is reserved", "fn f (gcd: int) { return gcd }")
    raises("parameter 'len' of 'f' is a builtin", "fn f (len: int) { return len }")


def test_missing_lib_dir_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(stdlib, "LIB_DIR", tmp_path / "nowhere")
    stdlib.lib_functions.cache_clear()
    try:
        with pytest.raises(
            RolyError, match="cannot find the standard library directory"
        ):
            stdlib.lib_functions()
    finally:
        stdlib.lib_functions.cache_clear()
