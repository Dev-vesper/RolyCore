from pathlib import Path

import pytest

from roly.utils.runner import run_source

ROOT = Path(__file__).resolve().parents[1]
SYNTAX_DIR = ROOT / "syntax"
ROLYPIP_DIR = Path(__file__).parent / "rolypip"


def run_cleanly(path):
    run_source(
        path.read_text(encoding="utf-8"),
        out=lambda value: None,
        base_dir=path.parent,
        entry_path=path,
    )


def test_every_syntax_program_runs_cleanly():
    programs = sorted(SYNTAX_DIR.glob("*.roly"))
    assert programs
    for path in programs:
        try:
            run_cleanly(path)
        except Exception as error:
            pytest.fail(f"syntax/{path.name}: {error}")


def test_every_rolypip_program_runs_cleanly():
    programs = sorted(ROLYPIP_DIR.rglob("*.roly"))
    assert programs
    for path in programs:
        try:
            run_cleanly(path)
        except Exception as error:
            pytest.fail(f"rolypip/{path.relative_to(ROLYPIP_DIR)}: {error}")
