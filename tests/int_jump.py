import pytest

from roly.interpreter import RolyError
from roly.utils.runner import run_source


def test_break_stops_loop():
    env = run_source("i = 0 while (i < 100) { i += 1 if (i == 5) { break } }")
    assert env["i"] == 5


def test_break_in_first_iteration():
    env = run_source("i = 0 while (i < 100) { break }")
    assert env["i"] == 0


def test_break_unconditional_runs_body_before_it():
    env = run_source("x = 0 while (1) { x += 7 break }")
    assert env["x"] == 7


def test_continue_skips_rest_of_body():
    env = run_source(
        "i = 0 total = 0 while (i < 10) { i += 1 if (i / 2 * 2 == i) { continue } total += i }"
    )
    assert env["i"] == 10
    assert env["total"] == 25


def test_continue_re_evaluates_condition():
    env = run_source("i = 0 while (i < 5) { i += 1 continue }")
    assert env["i"] == 5


def test_continue_alone_still_terminates():
    env = run_source("i = 0 while (i < 3) { i += 1 continue }")
    assert env["i"] == 3


def test_break_affects_innermost_loop_only():
    env = run_source(
        "i = 0 outer = 0 inner = 0 "
        "while (i < 3) { i += 1 outer += 1 j = 0 "
        "while (j < 100) { j += 1 inner += 1 if (j == 2) { break } } }"
    )
    assert env["outer"] == 3
    assert env["inner"] == 6


def test_continue_affects_innermost_loop_only():
    env = run_source(
        "i = 0 hits = 0 "
        "while (i < 3) { i += 1 j = 0 "
        "while (j < 3) { j += 1 if (j == 1) { continue } hits += 1 } }"
    )
    assert env["hits"] == 6


def test_break_propagates_out_of_nested_if():
    env = run_source(
        "i = 0 while (i < 100) { i += 1 if (i > 3) { if (i == 4) { break } } }"
    )
    assert env["i"] == 4


def test_continue_propagates_out_of_nested_if():
    env = run_source(
        "i = 0 done = 0 while (i < 5) { i += 1 if (i < 5) { continue } done = 1 }"
    )
    assert env["i"] == 5
    assert env["done"] == 1


def test_break_propagates_out_of_bare_block():
    env = run_source("i = 0 while (i < 100) { i += 1 { { break } } }")
    assert env["i"] == 1


def test_continue_propagates_out_of_bare_block():
    env = run_source("i = 0 hit = 0 while (i < 3) { i += 1 { { continue } } hit = 1 }")
    assert env["hit"] == 0


def test_statements_after_break_not_executed():
    env = run_source("x = 0 while (1) { x = 1 break x = 2 }")
    assert env["x"] == 1


def test_statements_after_continue_not_executed():
    env = run_source("x = 0 i = 0 while (i < 2) { i += 1 continue x = 1 }")
    assert env["x"] == 0


def test_break_in_else_branch():
    env = run_source("i = 0 while (i < 10) { i += 1 if (i < 5) { } else { break } }")
    assert env["i"] == 5


def test_break_infinite_loop_with_step_limit():
    with pytest.raises(RolyError, match="step limit"):
        run_source("while (1) { continue }", max_steps=50)


def test_break_prevents_step_limit_hit():
    env = run_source("while (1) { break }", max_steps=50)
    assert env == {}


def test_break_inside_loop_after_work():
    env = run_source(
        "total = 0 i = 1 while (1) { total += i if (total > 10) { break } i += 1 }"
    )
    assert env["total"] == 15
    assert env["i"] == 5


def test_print_still_works_in_loop_with_jumps():
    printed = []
    run_source(
        "i = 0 while (i < 6) { i += 1 if (i / 2 * 2 == i) { continue } print(i) }",
        out=printed.append,
    )
    assert printed == [1, 3, 5]


def test_nested_break_then_outer_continues():
    env = run_source(
        "i = 0 done = 0 "
        "while (i < 3) { i += 1 j = 0 while (j < 10) { j += 1 if (j == 1) { break } } "
        "done += j }"
    )
    assert env["done"] == 3


def test_search_with_break():
    env = run_source(
        "n = 2 while (n < 100) { "
        "if (n / 7 * 7 == n) { break } n += 1 }"
    )
    assert env["n"] == 7


def test_no_signal_leak_to_cli_shape():
    env = run_source("while (1) { break } x = 1")
    assert env == {"x": 1}
