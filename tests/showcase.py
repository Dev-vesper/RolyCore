from pathlib import Path

import pytest

from roly.utils.runner import run_source

ROLYPIP_DIR = Path(__file__).parent / "rolypip"


def run_showcase(path):
    run_source(
        path.read_text(encoding="utf-8"),
        out=lambda value: None,
        base_dir=path.parent,
        entry_path=path,
    )


def test_every_rolypip_program_runs_cleanly():
    programs = sorted(ROLYPIP_DIR.rglob("*.roly"))
    assert programs
    for path in programs:
        try:
            run_showcase(path)
        except Exception as error:
            pytest.fail(f"{path.relative_to(ROLYPIP_DIR)}: {error}")


def test_rolypip_covers_every_feature_folder():
    folders = {path.parent.name for path in ROLYPIP_DIR.rglob("*.roly")}
    assert folders == {
        "arithmetic",
        "booleans",
        "builtins",
        "comparisons",
        "functions",
        "if_else",
        "import",
        "jumps",
        "lib",
        "lists",
        "strings",
        "variables",
        "while",
    }
