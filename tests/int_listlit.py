from roly.errors import RolyError
from roly.utils.runner import run_source


def test_empty_literal():
    env = run_source("l = []")
    assert env["l"] == []


def test_int_literal():
    env = run_source("l = [1, 2, 3]")
    assert env["l"] == [1, 2, 3]


def test_mixed_type_literal():
    env = run_source('l = [1, "a", TRUE]')
    assert env["l"] == [1, "a", True]


def test_nested_literal():
    env = run_source("l = [[1, 2], [3]]")
    assert env["l"] == [[1, 2], [3]]


def test_nested_literal_subscript():
    env = run_source("l = [[1, 2], [3]] x = l[0][1]")
    assert env["x"] == 2


def test_items_are_expressions():
    env = run_source("a = 10 l = [a + 1, a * 2]")
    assert env["l"] == [11, 20]


def test_literal_in_subscript_base():
    env = run_source("x = [5, 6, 7][2]")
    assert env["x"] == 7


def test_literal_function_argument():
    printed = []
    run_source('print(join(["a", "b"], "-"))', out=printed.append)
    assert printed == ["a-b"]


def test_literal_equality_structural():
    env = run_source("a = [1, 2] b = [1, 2] c = [2, 1] e = a == b d = a == c")
    assert env["e"] is True
    assert env["d"] is False


def test_literal_equality_strict_types():
    env = run_source("a = [TRUE] b = [1] e = a == b")
    assert env["e"] is False


def test_literal_equality_length():
    env = run_source("e = [1] == [1, 1]")
    assert env["e"] is False


def test_literal_with_lib_functions():
    env = run_source("s = sum_list([1, 2, 3]) r = reverse_list([1, 2, 3])")
    assert env["s"] == 6
    assert env["r"] == [3, 2, 1]


def test_literal_push_and_set():
    env = run_source("l = push([1], 2) m = set([1, 2], 0, 9)")
    assert env["l"] == [1, 2]
    assert env["m"] == [9, 2]


def test_literal_len():
    env = run_source("n = len([]) m = len([1, 2, 3])")
    assert env["n"] == 0
    assert env["m"] == 3


def test_literal_str_and_format():
    printed = []
    run_source('print(format("{}", [1, "a"]))', out=printed.append)
    assert printed == ["[1, 'a']"]


def test_literal_print_passes_value_to_out():
    printed = []
    run_source('print([1, "a", TRUE, [2]])', out=printed.append)
    assert printed == [[1, "a", True, [2]]]


def test_items_evaluate_left_to_right():
    printed = []

    source = (
        "fn probe(n: int) { print(n) return n } "
        "l = [probe(1), probe(2), probe(3)]"
    )
    run_source(source, out=printed.append)
    assert printed == [1, 2, 3]


def test_literal_bool_conversion_rejected():
    try:
        run_source("b = bool([])")
        raise AssertionError("expected RolyError")
    except RolyError as error:
        assert "cannot convert [] to bool" in str(error)


def test_literal_condition_rejected():
    try:
        run_source("if ([1]) { x = 1 }")
        raise AssertionError("expected RolyError")
    except RolyError as error:
        assert "condition must be a number" in str(error)


def test_literal_index_error_message():
    try:
        run_source("x = [1, 2][5]")
        raise AssertionError("expected RolyError")
    except RolyError as error:
        assert "get: index 5 out of range for length 2" in str(error)


def test_literal_assign_through_subscript_is_parse_error():
    from roly.parser import ParseError

    try:
        run_source("l = [1] l[0] = 2")
        raise AssertionError("expected ParseError")
    except ParseError:
        pass


def test_literal_while_accumulate():
    env = run_source(
        "total = 0 i = 0 "
        "while (i < len([10, 20, 30])) {"
        " total += [10, 20, 30][i]"
        " i += 1"
        "}"
    )
    assert env["total"] == 60


def test_empty_literal_is_not_aliasing():
    env = run_source("a = [] b = push(a, 1)")
    assert env["a"] == []
    assert env["b"] == [1]
