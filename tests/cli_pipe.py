import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLY = ROOT / "roly.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(ROLY), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_exec_simple_assignment_no_output():
    result = run_cli("exec", "x = 5")
    assert result.returncode == 0
    assert result.stdout == ""


def test_exec_assignments_produce_no_env_dump():
    result = run_cli("exec", "b = 2 a = 1")
    assert result.returncode == 0
    assert result.stdout == ""


def test_exec_loop_computes_no_output_without_print():
    result = run_cli("exec", "i = 0 total = 0 while (i < 5) { total += i i += 1 }")
    assert result.returncode == 0
    assert result.stdout == ""


def test_exec_empty_code_prints_nothing():
    result = run_cli("exec", "")
    assert result.returncode == 0
    assert result.stdout == ""


def test_exec_bool_needs_print_to_show():
    result = run_cli("exec", "x = 2 == 2 print(x)")
    assert result.returncode == 0
    assert result.stdout == "True\n"


def test_cli_print_statement_output():
    result = run_cli("exec", "print(5)")
    assert result.returncode == 0
    assert result.stdout == "5\n"


def test_cli_only_print_output_is_shown():
    result = run_cli("exec", "x = 1 print(x)")
    assert result.returncode == 0
    assert result.stdout == "1\n"


def test_cli_string_printed_raw():
    result = run_cli("exec", 'print("hello world")')
    assert result.returncode == 0
    assert result.stdout == "hello world\n"


def test_cli_multiple_prints_in_order():
    result = run_cli("exec", "print(1) print(2) print(3)")
    assert result.returncode == 0
    assert result.stdout == "1\n2\n3\n"


def test_exec_lex_error_exit_code():
    result = run_cli("exec", "x = @")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_exec_parse_error_exit_code():
    result = run_cli("exec", "x = ")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_exec_runtime_error_exit_code():
    result = run_cli("exec", "x = 1 / 0")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_exec_undefined_variable_error():
    result = run_cli("exec", "x = y")
    assert result.returncode == 1
    assert "undefined variable 'y'" in result.stderr


def test_error_goes_to_stderr_not_stdout():
    result = run_cli("exec", "print(1) x = 1 / 0")
    assert result.returncode == 1
    assert result.stdout == "1\n"
    assert "error" in result.stderr


def test_run_file(tmp_path):
    script = tmp_path / "count.roly"
    script.write_text("n = 3 while (n > 0) { n -= 1 } print(n)")
    result = run_cli("run", str(script))
    assert result.returncode == 0
    assert result.stdout == "0\n"


def test_run_syntax_print_file():
    result = run_cli("run", str(ROOT / "syntax" / "print.roly"))
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["hello world", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


def test_run_missing_file():
    result = run_cli("run", "/nonexistent/no_such.roly")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_no_subcommand_exits_with_error():
    result = subprocess.run(
        [sys.executable, str(ROLY)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode != 0
