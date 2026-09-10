import sys
from pathlib import Path

import pytest

import roly.stdlib as stdlib
from roly.errors import RolyError
from roly.stdlib import lib_functions, resolve_lib_dir


def test_resolve_lib_dir_source_mode(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    expected = Path(stdlib.__file__).resolve().parent / "lib"
    assert resolve_lib_dir() == expected


def test_resolve_lib_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/opt/roly/bin/roly.exe")
    assert resolve_lib_dir() == Path("/opt/roly/bin/lib")


def test_lib_dir_exists_in_project():
    assert resolve_lib_dir().is_dir()


def test_missing_lib_dir_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(stdlib, "LIB_DIR", tmp_path / "nowhere")
    lib_functions.cache_clear()
    try:
        with pytest.raises(RolyError, match="cannot find the standard library directory"):
            lib_functions()
    finally:
        lib_functions.cache_clear()
