import pytest

from roly.errors import RolyError
from roly.utils.runner import run_source


def nums():
    return "n = list() n = push(n, 5) n = push(n, 2) n = push(n, 8) n = push(n, 3)"


def test_reverse_list():
    assert run_source(f"x = reverse_list(list(\"\"))")["x"] == []
    env = run_source(f"{nums()} x = reverse_list(n)")
    assert env["x"] == [3, 8, 2, 5]


def test_join():
    assert run_source('x = join(list(), ",")')["x"] == ""
    env = run_source(f"{nums()} x = join(n, \"-\")")
    assert env["x"] == "5-2-8-3"


def test_join_renders_elements_python_style():
    printed = []
    run_source(
        'b = list() b = push(b, 1) b = push(b, TRUE) print(join(b, ","))',
        out=printed.append,
    )
    assert printed == ["1,True"]


def test_sum_list():
    assert run_source("x = sum_list(list())")["x"] == 0
    env = run_source(f"{nums()} x = sum_list(n)")
    assert env["x"] == 18


def test_sum_list_non_int_elements_error():
    with pytest.raises(RolyError, match="requires integer operands"):
        run_source('x = sum_list(list("ab"))')


def test_max_list():
    env = run_source(f"{nums()} x = max_list(n)")
    assert env["x"] == 8


def test_min_list():
    env = run_source(f"{nums()} x = min_list(n)")
    assert env["x"] == 2


def test_max_min_empty_list_errors():
    with pytest.raises(RolyError, match="max_list"):
        run_source("x = max_list(list())")
    with pytest.raises(RolyError, match="min_list"):
        run_source("x = min_list(list())")


def test_sublist_clamps_like_substr():
    env = run_source(f"{nums()} x = sublist(n, 1, 4)")
    assert env["x"] == [2, 8, 3]
    assert run_source("x = sublist(push(list(), 7), -2, 2)")["x"] == [7]
    assert run_source("x = sublist(list(), 0, 5)")["x"] == []
    assert run_source("x = sublist(push(list(), 7), 3, 2)")["x"] == []


def test_remove_at():
    env = run_source(f"{nums()} x = remove_at(n, 1)")
    assert env["x"] == [5, 8, 3]
    assert env["n"] == [5, 2, 8, 3]


def test_remove_at_out_of_range_errors():
    with pytest.raises(RolyError, match="remove_at"):
        run_source("x = remove_at(list(), 0)")
    with pytest.raises(RolyError, match="remove_at"):
        run_source("x = remove_at(push(list(), 1), 1)")
    with pytest.raises(RolyError, match="remove_at"):
        run_source("x = remove_at(push(list(), 1), -1)")


def test_sort_list():
    assert run_source("x = sort_list(list())")["x"] == []
    assert run_source("x = sort_list(push(list(), 7))")["x"] == [7]
    env = run_source(f"{nums()} x = sort_list(n)")
    assert env["x"] == [2, 3, 5, 8]
    assert env["n"] == [5, 2, 8, 3]


def test_sort_list_with_duplicates_and_negatives():
    env = run_source(
        "n = list() n = push(n, 3) n = push(n, 1) n = push(n, 3) "
        "n = push(n, -4) x = sort_list(n)"
    )
    assert env["x"] == [-4, 1, 3, 3]


def test_sort_list_is_stable():
    env = run_source(
        "n = list() n = push(n, 1) n = push(n, 1) x = remove_at(sort_list(n), 0)"
    )
    assert env["x"] == [1]


def test_list_functions_arg_types_checked():
    with pytest.raises(RolyError, match="must be list"):
        run_source("x = reverse_list(5)")
    with pytest.raises(RolyError, match="must be int"):
        run_source("x = remove_at(list(), \"0\")")
    with pytest.raises(RolyError, match="must be str"):
        run_source("x = join(list(), 5)")


def test_list_functions_arity_checked():
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source("x = join(list())")


def test_list_lib_names_reserved():
    with pytest.raises(RolyError, match="reserved"):
        run_source("sort_list = 5")
    with pytest.raises(RolyError, match="reserved"):
        run_source("fn reverse_list (l: list) { return l }")


def test_list_functions_do_not_touch_user_globals():
    env = run_source(
        "r = 1 i = 2 s = 3 m = 4 a = 5 b = 6 x = 7 pos = 8 j = 9 "
        "n = list() n = push(n, 4) n = push(n, 1) "
        "v1 = reverse_list(n) v2 = join(n, \"-\") v3 = sum_list(n) "
        "v4 = max_list(n) v5 = min_list(n) v6 = sublist(n, 0, 1) "
        "v7 = remove_at(n, 0) v8 = sort_list(n)"
    )
    assert env["r"] == 1
    assert env["i"] == 2
    assert env["s"] == 3
    assert env["m"] == 4
    assert env["a"] == 5
    assert env["b"] == 6
    assert env["x"] == 7
    assert env["pos"] == 8
    assert env["j"] == 9
