import sys

from builder.engine import pyinstaller_command
from builder.libs import sync_lib
from builder.platform import exe_name, is_windows


def test_exe_name_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert exe_name() == "roly.exe"


def test_exe_name_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert exe_name() == "roly"


def test_exe_name_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert exe_name() == "roly"


def test_is_windows_matches_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert is_windows()
    monkeypatch.setattr(sys, "platform", "linux")
    assert not is_windows()


def test_command_uses_native_name_and_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    dist = tmp_path / "dist"
    command = pyinstaller_command(tmp_path, dist)
    assert command[command.index("--name") + 1] == "roly"
    assert command[command.index("--distpath") + 1] == str(dist)
    assert command[command.index("--workpath") + 1] == str(tmp_path / "build")
    assert str(tmp_path / "roly.py") in command
    assert "--onefile" in command
    assert "--noconfirm" in command


def test_command_keeps_exe_suffix_on_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    command = pyinstaller_command(tmp_path, tmp_path / "dist")
    assert command[command.index("--name") + 1] == "roly.exe"


def test_sync_lib_copies_roly_files(tmp_path):
    source = tmp_path / "lib"
    source.mkdir()
    (source / "math.roly").write_text("fn f(a: int) { return a }", encoding="utf-8")
    target = sync_lib(source, tmp_path / "out")
    assert (target / "math.roly").read_text(encoding="utf-8") == "fn f(a: int) { return a }"


def test_sync_lib_replaces_stale_target(tmp_path):
    source = tmp_path / "lib"
    source.mkdir()
    (source / "a.roly").write_text("x", encoding="utf-8")
    target = tmp_path / "out"
    target.mkdir()
    (target / "stale.roly").write_text("y", encoding="utf-8")
    sync_lib(source, target)
    assert [p.name for p in sorted(target.iterdir())] == ["a.roly"]


def test_sync_lib_returns_target(tmp_path):
    source = tmp_path / "lib"
    source.mkdir()
    target = tmp_path / "out"
    assert sync_lib(source, target) == target
    assert target.is_dir()
