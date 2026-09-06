from roly.utils.runner import run_source


def test_bool_never_equals_int():
    assert run_source("x = 0 == (1 == 2)")["x"] is False
    assert run_source("x = 1 == (1 == 1)")["x"] is False
    assert run_source("x = (1 == 2) == 0")["x"] is False
    assert run_source("x = (1 == 1) == 1")["x"] is False


def test_bool_int_inequality_mirrors():
    assert run_source("x = 0 != (1 == 2)")["x"] is True
    assert run_source("x = 1 != (1 == 1)")["x"] is True


def test_int_int_equality_unchanged():
    assert run_source("x = 3 == 3")["x"] is True
    assert run_source("x = 3 == 4")["x"] is False
    assert run_source("x = 3 != 4")["x"] is True


def test_bool_bool_equality_unchanged():
    assert run_source("x = (1 == 1) == (2 == 2)")["x"] is True
    assert run_source("x = (1 == 1) == (1 == 2)")["x"] is False
    assert run_source("x = (1 == 1) != (1 == 2)")["x"] is True


def test_string_string_equality_unchanged():
    assert run_source('x = "a" == "a"')["x"] is True
    assert run_source('x = "a" == "b"')["x"] is False
    assert run_source('x = "a" != "b"')["x"] is True


def test_cross_type_string_int_not_equal():
    assert run_source('x = "1" == 1')["x"] is False
    assert run_source('x = "1" != 1')["x"] is True


def test_cross_type_int_string_not_equal():
    assert run_source('x = 1 == "a"')["x"] is False
    assert run_source('x = 1 != "a"')["x"] is True


def test_cross_type_string_bool_not_equal():
    assert run_source('x = "a" == (1 == 1)')["x"] is False
    assert run_source('x = "a" != (1 == 1)')["x"] is True


def test_cross_type_in_condition_takes_else():
    env = run_source('s = "1" if (s == 1) { y = 1 } else { y = 2 }')
    assert env["y"] == 2


def test_equality_still_drives_while():
    env = run_source('s = "ab" n = 0 while (s != "abc") { s += "c" n += 1 }')
    assert env["n"] == 1
