from roly.utils.runner import run_source


def printed_of(source):
    printed = []
    run_source(source, out=printed.append)
    return printed


def test_print_int_literal():
    assert printed_of("print(5)") == [5]


def test_print_expression():
    assert printed_of("print(2 + 3 * 4)") == [14]


def test_print_variable():
    assert printed_of("x = 7 print(x)") == [7]


def test_print_bool():
    assert printed_of("x = 2 == 2 print(x)") == [True]


def test_print_comparison_directly():
    assert printed_of("print(3 < 5)") == [True]


def test_multiple_prints_preserve_order():
    assert printed_of("print(1) print(2) print(3)") == [1, 2, 3]


def test_print_inside_loop():
    assert printed_of("i = 3 while (i > 0) { print(i) i -= 1 }") == [3, 2, 1]


def test_print_inside_if_branch():
    assert printed_of("if (1) { print(10) } else { print(20) }") == [10]


def test_print_inside_if_else_branch():
    assert printed_of("if (0) { print(10) } else { print(20) }") == [20]


def test_print_skipped_when_condition_false():
    assert printed_of("if (0) { print(99) }") == []


def test_print_after_assignment():
    assert printed_of("x = 2 x += 3 print(x)") == [5]


def test_print_inside_bare_block():
    assert printed_of("{ print(4) }") == [4]


def test_print_does_not_create_variable():
    env = run_source("print(5)", out=None)
    assert env == {}


def test_print_step_is_counted():
    from roly.interpreter import RolyError

    try:
        run_source("while (1) { print(1) }", max_steps=10, out=lambda v: None)
        raised = False
    except RolyError:
        raised = True
    assert raised
