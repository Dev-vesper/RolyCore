import pytest

from roly.errors import RolyError
from roly.utils.runner import run_source


def test_string_subscript():
    assert run_source('x = "hello"[0]')["x"] == "h"
    assert run_source('x = "hello"[4]')["x"] == "o"
    assert run_source('s = "ab" i = 1 x = s[i - 1]')["x"] == "a"


def test_string_subscript_with_variable_index():
    env = run_source('s = "roly" i = 2 x = s[i]')
    assert env["x"] == "l"


def test_string_subscript_matches_char_exactly():
    env = run_source('s = "roly" a = s[0] b = char(s, 0) x = a == b')
    assert env["x"] is True


def test_string_subscript_out_of_range_errors():
    with pytest.raises(RolyError, match="char: index 4 out of range for length 4"):
        run_source('x = "roly"[4]')
    with pytest.raises(RolyError, match="index -1 out of range"):
        run_source('x = "roly"[-1]')
    with pytest.raises(RolyError, match="index 0 out of range for length 0"):
        run_source('x = ""[0]')


def test_string_subscript_non_int_index_errors():
    with pytest.raises(RolyError, match="expects \(str, int\)"):
        run_source('x = "ab"["0"]')


def test_list_subscript():
    env = run_source("l = list() l = push(l, 10) l = push(l, 20) x = l[1]")
    assert env["x"] == 20


def test_list_subscript_matches_get_exactly():
    env = run_source("l = push(list(), 7) a = l[0] b = get(l, 0) x = a == b")
    assert env["x"] is True


def test_list_subscript_out_of_range_errors():
    with pytest.raises(RolyError, match="get: index 1 out of range for length 1"):
        run_source("x = push(list(), 5)[1]")
    with pytest.raises(RolyError, match="index -2 out of range"):
        run_source("x = push(list(), 5)[-2]")


def test_list_subscript_non_list_base_errors():
    with pytest.raises(RolyError, match="expects a list"):
        run_source("x = 5[0]")
    with pytest.raises(RolyError, match="expects a list"):
        run_source("x = TRUE[0]")


def test_nested_subscript():
    env = run_source(
        "n = list() n = push(n, list()) n = set(n, 0, push(list(), 42)) x = n[0][0]"
    )
    assert env["x"] == 42


def test_nested_list_of_strings_subscript():
    env = run_source('n = push(list(), list("ab")) x = n[0][1]')
    assert env["x"] == "b"


def test_subscript_on_call_result():
    env = run_source(
        "fn mk () { l = list() l = push(l, 3) l = push(l, 9) return l } x = mk()[1]"
    )
    assert env["x"] == 9


def test_subscript_on_parenthesized_expression():
    assert run_source('x = ("ab")[1]')["x"] == "b"


def test_negative_binds_around_subscript():
    env = run_source("l = push(list(), 4) x = -l[0]")
    assert env["x"] == -4


def test_subscript_in_arithmetic():
    env = run_source(
        "l = list() l = push(l, 10) l = push(l, 32) x = l[0] + l[1] * 2"
    )
    assert env["x"] == 74


def test_subscript_in_condition():
    env = run_source("l = push(list(), 3) if (l[0] > 2) { x = 1 } else { x = 2 }")
    assert env["x"] == 1


def test_subscript_in_while():
    env = run_source(
        "s = 0 l = list(\"123\") i = 0 while (i < len(l)) { s += int(l[i]) i += 1 }"
    )
    assert env["s"] == 6


def test_subscript_inside_function():
    env = run_source(
        "fn sum3 (l: list) { s = 0 i = 0 while (i < len(l)) { s += int(l[i]) i += 1 } return s }"
        " x = sum3(list(\"123\"))"
    )
    assert env["x"] == 6


def test_subscript_base_evaluated_before_index():
    printed = []
    with pytest.raises(RolyError, match="out of range"):
        run_source(
            'fn boom () { print("boom") return list() }'
            " x = boom()[0]",
            out=printed.append,
        )
    assert printed == ["boom"]


def test_chained_subscripts_after_call_chain():
    env = run_source(
        "fn wrap () { l = list() l = push(l, list()) l = set(l, 0, push(list(), 5)) return l }"
        " x = wrap()[0][0]"
    )
    assert env["x"] == 5


def test_subscript_error_messages_name_the_desugared_builtin():
    with pytest.raises(RolyError, match="char"):
        run_source('x = "ab"[9]')
    with pytest.raises(RolyError, match="get"):
        run_source("x = list()[9]")


def test_subscript_composes_with_library():
    env = run_source(
        "n = list() n = push(n, 5) n = push(n, 2) n = push(n, 8)"
        " x = sort_list(n)[0] y = reverse_list(n)[0]"
    )
    assert env["x"] == 2
    assert env["y"] == 8
