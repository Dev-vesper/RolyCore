import shlex
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


def test_lex_error_exit_code():
    result = run_cli("exec", "x = @")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_parse_error_exit_code():
    result = run_cli("exec", "x = ")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_runtime_error_exit_code():
    result = run_cli("exec", "x = 1 / 0")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_error_goes_to_stderr_not_stdout():
    result = run_cli("exec", "print(1) x = 1 / 0")
    assert result.returncode == 1
    assert result.stdout == "1\n"
    assert "error" in result.stderr


def test_missing_run_file():
    result = run_cli("run", "/nonexistent/no_such.roly")
    assert result.returncode == 1
    assert "error" in result.stderr


def test_no_subcommand_exits_with_error():
    result = run_cli()
    assert result.returncode != 0


def test_run_file_error_exit_code(tmp_path):
    script = tmp_path / "broken.roly"
    script.write_text("x = y", encoding="utf-8")
    result = run_cli("run", str(script))
    assert result.returncode == 1
    assert "undefined variable 'y'" in result.stderr


def test_run_missing_imported_module_errors(tmp_path):
    script = tmp_path / "main.roly"
    script.write_text("import nope print(1)", encoding="utf-8")
    result = run_cli("run", str(script))
    assert result.returncode == 1
    assert "not found" in result.stderr


def test_broken_pipe_handled_cleanly(tmp_path):
    code = "i = 0 while (i < 100000) { print(i) i += 1 }"
    err_file = tmp_path / "stderr.txt"
    cmd = (
        f"{sys.executable} {shlex.quote(str(ROLY))} exec {shlex.quote(code)} "
        f"2>{shlex.quote(str(err_file))} | head -1; exit ${{PIPESTATUS[0]}}"
    )
    result = subprocess.run(
        ["bash", "-c", cmd], capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 1
    assert result.stdout.splitlines()[0] == "0"
    stderr = err_file.read_text()
    assert "Traceback" not in stderr
    assert "BrokenPipeError" not in stderr
