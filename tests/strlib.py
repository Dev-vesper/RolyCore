import pytest

from roly.errors import RolyError
from roly.utils.runner import run_source


def test_len_of_string():
    assert run_source('x = len("hello")')["x"] == 5
    assert run_source('x = len("")')["x"] == 0
    assert run_source('x = len("a")')["x"] == 1


def test_len_of_int_errors():
    with pytest.raises(RolyError, match="expects a str"):
        run_source("x = len(42)")


def test_len_of_bool_errors():
    with pytest.raises(RolyError, match="expects a str"):
        run_source("x = len(TRUE)")


def test_char_returns_one_character_string():
    assert run_source('x = char("hello", 0)')["x"] == "h"
    assert run_source('x = char("hello", 4)')["x"] == "o"
    assert run_source('x = char("hello", 1)')["x"] == "e"


def test_char_out_of_range_errors():
    with pytest.raises(RolyError, match="out of range"):
        run_source('x = char("hi", 2)')
    with pytest.raises(RolyError, match="out of range"):
        run_source('x = char("hi", -1)')
    with pytest.raises(RolyError, match="out of range"):
        run_source('x = char("", 0)')


def test_char_wrong_types_error():
    with pytest.raises(RolyError, match="expects"):
        run_source("x = char(42, 0)")
    with pytest.raises(RolyError, match="expects"):
        run_source('x = char("hi", "0")')


def test_char_arity_checked():
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source('x = char("hi")')


def test_char_upper():
    assert run_source('x = char_upper("q")')["x"] == "Q"
    assert run_source('x = char_upper("Q")')["x"] == "Q"
    assert run_source('x = char_upper("9")')["x"] == "9"
    assert run_source('x = char_upper(" ")')["x"] == " "


def test_char_lower():
    assert run_source('x = char_lower("Q")')["x"] == "q"
    assert run_source('x = char_lower("q")')["x"] == "q"
    assert run_source('x = char_lower("!")')["x"] == "!"


def test_upper():
    assert run_source('x = upper("aBc9!")')["x"] == "ABC9!"
    assert run_source('x = upper("")')["x"] == ""
    assert run_source('x = upper("roly")')["x"] == "ROLY"


def test_lower():
    assert run_source('x = lower("AbC9!")')["x"] == "abc9!"
    assert run_source('x = lower("ROLY")')["x"] == "roly"


def test_upper_lower_round_trip():
    assert run_source('x = lower(upper("MiXeD"))')["x"] == "mixed"


def test_trim():
    assert run_source('x = trim("  hi  ")')["x"] == "hi"
    assert run_source('x = trim("")')["x"] == ""
    assert run_source('x = trim("   ")')["x"] == ""
    assert run_source('x = trim("x")')["x"] == "x"
    assert run_source('x = trim(" a b ")')["x"] == "a b"


def test_starts_with():
    assert run_source('x = starts_with("hello", "he")')["x"] is True
    assert run_source('x = starts_with("hello", "heX")')["x"] is False
    assert run_source('x = starts_with("hi", "hello")')["x"] is False
    assert run_source('x = starts_with("hello", "")')["x"] is True


def test_ends_with():
    assert run_source('x = ends_with("hello", "lo")')["x"] is True
    assert run_source('x = ends_with("hello", "Xlo")')["x"] is False
    assert run_source('x = ends_with("lo", "hello")')["x"] is False
    assert run_source('x = ends_with("hello", "")')["x"] is True


def test_index_of():
    assert run_source('x = index_of("hello world", "o w")')["x"] == 4
    assert run_source('x = index_of("hello", "z")')["x"] == -1
    assert run_source('x = index_of("hello", "hello")')["x"] == 0
    assert run_source('x = index_of("aaa", "aa")')["x"] == 0


def test_index_from():
    assert run_source('x = index_from("aaa", "aa", 1)')["x"] == 1
    assert run_source('x = index_from("abc", "a", 1)')["x"] == -1


def test_contains():
    assert run_source('x = contains("hello world", "o w")')["x"] is True
    assert run_source('x = contains("hello", "z")')["x"] is False
    assert run_source('x = contains("anything", "")')["x"] is True


def test_count_sub_non_overlapping():
    assert run_source('x = count_sub("abababa", "aba")')["x"] == 2
    assert run_source('x = count_sub("aaaa", "aa")')["x"] == 2
    assert run_source('x = count_sub("hello", "z")')["x"] == 0
    assert run_source('x = count_sub("x", "")')["x"] == 0


def test_reverse_str():
    assert run_source('x = reverse_str("abc")')["x"] == "cba"
    assert run_source('x = reverse_str("")')["x"] == ""
    assert run_source('x = reverse_str("x")')["x"] == "x"


def test_is_palindrome_str():
    assert run_source('x = is_palindrome_str("racecar")')["x"] is True
    assert run_source('x = is_palindrome_str("hello")')["x"] is False
    assert run_source('x = is_palindrome_str("")')["x"] is True


def test_substr():
    assert run_source('x = substr("hello", 1, 4)')["x"] == "ell"
    assert run_source('x = substr("hello", 0, 5)')["x"] == "hello"
    assert run_source('x = substr("hello", 3, 2)')["x"] == ""
    assert run_source('x = substr("hello", -2, 2)')["x"] == "he"
    assert run_source('x = substr("hello", 2, 99)')["x"] == "llo"
    assert run_source('x = substr("", 0, 5)')["x"] == ""


def test_substr_with_index_of_workflow():
    env = run_source(
        's = substr("name=roly", index_of("name=roly", "=") + 1, len("name=roly"))'
    )
    assert env["s"] == "roly"


def test_string_functions_compose_with_format():
    printed = []
    run_source(
        'print(format("{} {}", upper("abc"), pad(7, 3)))',
        out=printed.append,
    )
    assert printed == ["ABC 007"]


def test_string_functions_arg_types_checked():
    with pytest.raises(RolyError, match="must be str"):
        run_source("x = upper(42)")
    with pytest.raises(RolyError, match="must be int"):
        run_source('x = substr("hi", "0", 1)')


def test_string_functions_arity_checked():
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source('x = starts_with("hi")')


def test_string_lib_names_reserved():
    with pytest.raises(RolyError, match="reserved"):
        run_source("upper = 5")
    with pytest.raises(RolyError, match="reserved"):
        run_source("fn trim (a: str) { return a }")


def test_string_functions_do_not_touch_user_globals():
    env = run_source(
        "i = 1 r = 2 c = 3 a = 4 b = 5 pos = 6 ls = 7 lf = 8 match = 9 "
        'v1 = upper("ab") v2 = trim(" x ") v3 = substr("abcd", 1, 3) '
        'v4 = reverse_str("xy") v5 = count_sub("aa", "a") '
        'v6 = index_of("abc", "b") v7 = contains("abc", "b") '
        'v8 = starts_with("ab", "a") v9 = ends_with("ab", "b") '
        'v10 = is_palindrome_str("aba") v11 = lower("AB") '
        'v12 = index_from("aaa", "a", 2) v13 = char_upper("z") '
        'v14 = char_lower("Z")'
    )
    assert env["i"] == 1
    assert env["r"] == 2
    assert env["c"] == 3
    assert env["a"] == 4
    assert env["b"] == 5
    assert env["pos"] == 6
    assert env["ls"] == 7
    assert env["lf"] == 8
    assert env["match"] == 9
