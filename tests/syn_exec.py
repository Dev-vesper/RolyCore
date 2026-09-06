from pathlib import Path

import pytest

from roly.utils.runner import run_source

SYNTAX_DIR = Path(__file__).resolve().parents[1] / "syntax"

EXPECTED_ENV = {
    "arith_mix.roly": {"a": 23, "b": 9, "c": 10, "d": 5},
    "sum_hundred.roly": {"i": 101, "total": 5050},
    "countdown.roly": {"n": 0},
    "fib_twenty.roly": {"a": 6765, "b": 10946, "count": 20, "next": 10946},
    "parity_scan.roly": {"i": 10, "evens": 5, "odds": 5},
    "power_two.roly": {"base": 2, "exp": 0, "result": 1024},
    "collatz_roam.roly": {"n": 1, "steps": 111},
    "gcd_pair.roly": {"a": 6, "b": 0, "r": 0},
    "digit_fold.roly": {"n": 0, "s": 15},
    "print_showcase.roly": {"x": 42, "i": 0},
    "print.roly": {"strings": "hello world", "i": 11},
}

EXPECTED_PRINTS = {
    "print_showcase.roly": [42, 84, 3, 2, 1],
    "print.roly": ["hello world", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
}


def run_syntax_file(name):
    source = (SYNTAX_DIR / name).read_text(encoding="utf-8")
    printed = []
    env = run_source(source, out=printed.append)
    return env, printed


@pytest.mark.parametrize("name", sorted(EXPECTED_ENV))
def test_program_env(name):
    env, _ = run_syntax_file(name)
    assert env == EXPECTED_ENV[name]


@pytest.mark.parametrize("name", sorted(EXPECTED_PRINTS))
def test_program_prints(name):
    _, printed = run_syntax_file(name)
    assert printed == EXPECTED_PRINTS[name]


def test_every_syntax_file_is_covered():
    files = {path.name for path in SYNTAX_DIR.glob("*.roly")}
    assert files == set(EXPECTED_ENV)


def test_expected_prints_subset_of_env():
    assert set(EXPECTED_PRINTS) <= set(EXPECTED_ENV)


def test_programs_produce_no_stdout_by_default(capsys):
    run_syntax_file("countdown.roly")
    assert capsys.readouterr().out == ""
