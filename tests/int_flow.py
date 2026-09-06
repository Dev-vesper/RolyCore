from roly.utils.runner import run_source


def test_if_takes_then_branch():
    env = run_source("x = 1 if (x == 1) { y = 10 } else { y = 20 }")
    assert env["y"] == 10


def test_if_takes_else_branch():
    env = run_source("x = 2 if (x == 1) { y = 10 } else { y = 20 }")
    assert env["y"] == 20


def test_if_without_else_skips_body():
    env = run_source("x = 5 if (x > 10) { y = 1 }")
    assert "y" not in env


def test_if_condition_uses_arithmetic():
    env = run_source("a = 3 b = 4 if (a * a + b * b == 25) { hit = 1 }")
    assert env["hit"] == 1


def test_nested_if_inside_else():
    env = run_source(
        "x = 7 if (x < 5) { r = 1 } else { if (x < 10) { r = 2 } else { r = 3 } }"
    )
    assert env["r"] == 2


def test_if_int_condition_zero_is_false():
    env = run_source("x = 0 if (x) { y = 1 } else { y = 2 }")
    assert env["y"] == 2


def test_if_int_condition_nonzero_is_true():
    env = run_source("x = 7 if (x) { y = 1 } else { y = 2 }")
    assert env["y"] == 1


def test_while_counts_down():
    env = run_source("x = 5 while (x > 0) { x -= 1 }")
    assert env["x"] == 0


def test_while_never_runs():
    env = run_source("x = 0 while (x > 100) { x += 1 }")
    assert env["x"] == 0


def test_while_accumulates():
    env = run_source("i = 1 total = 0 while (i <= 10) { total += i i += 1 }")
    assert env["total"] == 55


def test_while_doubles():
    env = run_source("x = 1 n = 0 while (x < 100) { x *= 2 n += 1 }")
    assert env["x"] == 128
    assert env["n"] == 7


def test_nested_while_multiplication_table_cell():
    env = run_source(
        "i = 1 acc = 0 while (i <= 3) { j = 1 while (j <= 3) { acc += i * j j += 1 } i += 1 }"
    )
    assert env["acc"] == (1 + 2 + 3) * (1 + 2 + 3)


def test_if_inside_while():
    env = run_source(
        "i = 0 odd = 0 even = 0 "
        "while (i < 10) { if (i / 2 * 2 == i) { even += 1 } else { odd += 1 } i += 1 }"
    )
    assert env["even"] == 5
    assert env["odd"] == 5


def test_while_halving_with_floor_division():
    env = run_source("x = 100 steps = 0 while (x > 0) { x /= 2 steps += 1 }")
    assert env["x"] == 0
    assert env["steps"] == 7


def test_bare_block_executes_statements():
    env = run_source("x = 1 { x += 1 x *= 10 }")
    assert env["x"] == 20


def test_empty_program_returns_empty_env():
    assert run_source("") == {}


def test_statements_run_in_order():
    env = run_source("x = 1 x = x + 1 x = x * 5")
    assert env["x"] == 10


def test_compound_assign_all_ops():
    assert run_source("x = 10 x += 5")["x"] == 15
    assert run_source("x = 10 x -= 5")["x"] == 5
    assert run_source("x = 10 x *= 5")["x"] == 50
    assert run_source("x = 10 x /= 5")["x"] == 2


def test_compound_assign_uses_current_value():
    assert run_source("x = 3 x += x")["x"] == 6


def test_compound_assign_in_loop_accumulates():
    env = run_source("total = 0 i = 0 while (i < 5) { total += i + 1 i += 1 }")
    assert env["total"] == 15


def test_condition_can_be_comparison_chain():
    env = run_source("a = 3 b = 2 c = 1 if (a > b) { r = 1 }")
    assert env["r"] == 1
