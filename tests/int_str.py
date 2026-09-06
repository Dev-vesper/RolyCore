import pytest

from roly.interpreter import RolyError
from roly.utils.runner import run_source


def printed_of(source):
    printed = []
    run_source(source, out=printed.append)
    return printed


def test_assign_string_variable():
    assert run_source('x = "hello"')["x"] == "hello"


def test_print_string_literal():
    assert printed_of('print("hello world")') == ["hello world"]


def test_print_empty_string():
    assert printed_of('print("")') == [""]


def test_string_concatenation():
    assert run_source('x = "foo" + "bar"')["x"] == "foobar"


def test_string_concat_with_variable():
    assert run_source('name = "roly" x = "hello " + name')["x"] == "hello roly"


def test_concat_empty_strings():
    assert run_source('x = "" + ""')["x"] == ""


def test_concat_chain():
    assert run_source('x = "a" + "b" + "c"')["x"] == "abc"


def test_string_equality_true():
    assert run_source('x = "a" == "a"')["x"] is True


def test_string_equality_false():
    assert run_source('x = "a" == "b"')["x"] is False


def test_string_inequality():
    assert run_source('x = "a" != "b"')["x"] is True


def test_empty_vs_nonempty_equality():
    assert run_source('x = "" == ""')["x"] is True
    assert run_source('x = "" == "a"')["x"] is False


def test_string_equality_with_variable():
    assert run_source('a = "x" b = "x" eq = a == b')["eq"] is True


def test_string_condition_in_if():
    env = run_source('x = "go" if (x == "go") { y = 1 } else { y = 2 }')
    assert env["y"] == 1


def test_string_condition_in_while():
    env = run_source('s = "ab" n = 0 while (s != "abc") { s += "c" n += 1 }')
    assert env["n"] == 1
    assert env["s"] == "abc"


def test_string_in_loop_print():
    assert printed_of(
        's = "a" while (s != "aaa") { print(s) s += "a" }'
    ) == ["a", "aa"]


def test_adding_string_and_number_raises():
    with pytest.raises(RolyError, match="integer operands"):
        run_source('x = "a" + 1')


def test_adding_number_and_string_raises():
    with pytest.raises(RolyError, match="integer operands"):
        run_source('x = 1 + "a"')


def test_ordering_strings_raises():
    with pytest.raises(RolyError, match="integer operands"):
        run_source('x = "a" < "b"')


def test_multiplying_strings_raises():
    with pytest.raises(RolyError, match="integer operands"):
        run_source('x = "a" * "b"')


def test_dividing_strings_raises():
    with pytest.raises(RolyError, match="integer operands"):
        run_source('x = "a" / "b"')


def test_string_is_falsy_in_condition():
    with pytest.raises(RolyError, match="condition must be"):
        run_source('x = "a" if (x) { y = 1 }')


def test_string_undefined_variable_still_raises():
    with pytest.raises(RolyError, match="undefined variable 's'"):
        run_source('x = s + "!"')


def test_hello_world_program():
    env, printed = {}, printed_of('greeting = "hello world" print(greeting)')
    assert printed == ["hello world"]
