import pytest

from roly.interpreter import RolyError
from roly.utils.runner import run_source


def test_run_source_returns_env_dict():
    assert run_source("a = 1 b = 2") == {"a": 1, "b": 2}


def test_variable_read_before_assignment_raises():
    with pytest.raises(RolyError, match="undefined variable 'y'"):
        run_source("x = y")


def test_assignment_can_use_earlier_variable():
    assert run_source("a = 2 b = a + 3")["b"] == 5


def test_blocks_share_global_scope():
    env = run_source("x = 1 while (x < 3) { y = x x += 1 }")
    assert env["y"] == 2


def test_variable_inside_if_visible_outside():
    env = run_source("if (1) { inner = 42 }")
    assert env["inner"] == 42


def test_reassignment_overwrites():
    env = run_source("x = 1 x = 2 x = 3")
    assert env["x"] == 3


def test_compound_assign_undefined_raises():
    with pytest.raises(RolyError, match="undefined variable 'x'"):
        run_source("x += 1")


def test_compound_assign_reads_before_writes():
    with pytest.raises(RolyError, match="undefined variable 'b'"):
        run_source("a = 1 a += b")


def test_assign_bool_value():
    env = run_source("flag = 2 == 2")
    assert env["flag"] is True


def test_loop_variable_persists_after_loop():
    env = run_source("i = 0 while (i < 5) { i += 1 }")
    assert env["i"] == 5


def test_env_is_plain_dict():
    env = run_source("x = 1")
    assert isinstance(env, dict)


def test_many_variables():
    env = run_source("a = 1 b = a + 1 c = b + 1 d = c + 1")
    assert env == {"a": 1, "b": 2, "c": 3, "d": 4}
