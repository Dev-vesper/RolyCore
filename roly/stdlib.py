import shutil
import sys
from pathlib import Path

from roly.builtins import to_str
from roly.errors import RolyError


def resolve_lib_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "lib"
    return Path(__file__).resolve().parent / "lib"


LIB_DIR = resolve_lib_dir()


class NativeFn:
    def __init__(self, params, callable):
        self.params = params
        self.callable = callable


def _require_int_element(op, value):
    if type(value) is not int:
        raise RolyError(f"operator '{op}' requires integer operands, got {value!r}")


def native_sort_list(I, items):
    for value in items:
        _require_int_element("+", value)
    return sorted(items)


def native_join(I, items, sep):
    return sep.join(to_str(value) for value in items)


def native_reverse_list(I, items):
    return items[::-1]


NATIVE_LIB = {
    "sort_list": NativeFn([("l", list)], native_sort_list),
    "join": NativeFn([("l", list), ("sep", str)], native_join),
    "reverse_list": NativeFn([("l", list)], native_reverse_list),
}


def _io_reason(error):
    if isinstance(error, UnicodeDecodeError):
        return "the file is not valid UTF-8 text"
    text = error.strerror or str(error)
    return text[:1].lower() + text[1:]


def _io_fail(op, action, error):
    raise RolyError(f"{op}: cannot {action}: {_io_reason(error)}")


def _resolve_path(I, path):
    target = Path(path)
    if target.is_absolute():
        return target
    return I.entry_base_dir / target


def native_read(I, path):
    try:
        return _resolve_path(I, path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        _io_fail("read", f"read '{path}'", error)


def native_write(I, path, content):
    try:
        _resolve_path(I, path).write_text(content, encoding="utf-8")
    except OSError as error:
        _io_fail("write", f"write '{path}'", error)
    return True


def native_append(I, path, content):
    try:
        with _resolve_path(I, path).open("a", encoding="utf-8") as handle:
            handle.write(content)
    except OSError as error:
        _io_fail("append", f"append to '{path}'", error)
    return True


def native_delete(I, path):
    try:
        _resolve_path(I, path).unlink()
    except OSError as error:
        _io_fail("delete", f"delete '{path}'", error)
    return True


def native_exists(I, path):
    return _resolve_path(I, path).exists()


def native_size(I, path):
    try:
        return _resolve_path(I, path).stat().st_size
    except OSError as error:
        _io_fail("size", f"get the size of '{path}'", error)


def native_read_lines(I, path):
    try:
        content = _resolve_path(I, path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        _io_fail("read_lines", f"read '{path}'", error)
    if content == "":
        return []
    lines = content.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def native_mkdir(I, path):
    try:
        _resolve_path(I, path).mkdir()
    except OSError as error:
        _io_fail("mkdir", f"make directory '{path}'", error)
    return True


def native_list_dir(I, path):
    try:
        return sorted(entry.name for entry in _resolve_path(I, path).iterdir())
    except OSError as error:
        _io_fail("list_dir", f"list '{path}'", error)


def native_rename(I, src, dst):
    dst_path = _resolve_path(I, dst)
    if dst_path.exists():
        raise RolyError(f"rename: '{dst}' already exists")
    try:
        _resolve_path(I, src).rename(dst_path)
    except OSError as error:
        _io_fail("rename", f"rename '{src}' to '{dst}'", error)
    return True


def native_copy(I, src, dst):
    try:
        shutil.copyfile(_resolve_path(I, src), _resolve_path(I, dst))
    except OSError as error:
        _io_fail("copy", f"copy '{src}' to '{dst}'", error)
    return True


NATIVE_THFILE = {
    "read": NativeFn([("path", str)], native_read),
    "write": NativeFn([("path", str), ("content", str)], native_write),
    "append": NativeFn([("path", str), ("content", str)], native_append),
    "delete": NativeFn([("path", str)], native_delete),
    "exists": NativeFn([("path", str)], native_exists),
    "size": NativeFn([("path", str)], native_size),
    "read_lines": NativeFn([("path", str)], native_read_lines),
    "mkdir": NativeFn([("path", str)], native_mkdir),
    "list_dir": NativeFn([("path", str)], native_list_dir),
    "rename": NativeFn([("src", str), ("dst", str)], native_rename),
    "copy": NativeFn([("src", str), ("dst", str)], native_copy),
}

NATIVE_MODULE_FNS = {
    "lists": NATIVE_LIB,
    "thfile": NATIVE_THFILE,
}
