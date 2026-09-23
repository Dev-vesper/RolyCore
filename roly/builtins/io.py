from roly.diagnostics.errors import RolyError, _io_reason
from roly.runtime.handles import FileHandle


def read_input(I, prompt):
    if type(prompt) is not str:
        raise RolyError(f"builtin 'input' expects a str, got {prompt!r}")
    try:
        return I.read_input(prompt)
    except EOFError:
        raise RolyError("input: end of input reached")


def _io_fail(op, action, error):
    raise RolyError(f"{op}: cannot {action}: {_io_reason(error)}")


def _resolve_path(I, path):
    if I.fs.is_absolute(path):
        return I.fs.absolute(path)
    return I.fs.join(I.entry_base_dir, path)


def _method_path(I, handle, path):
    if I.fs.is_absolute(path):
        return I.fs.absolute(path)
    return I.fs.join(handle.base, path)


OPEN_MODES = {"r": "rb+", "w": "wb+", "a": "ab+"}


def open_file(I, path, mode):
    if type(path) is not str:
        raise RolyError(f"builtin 'open' expects a str path, got {path!r}")
    if type(mode) is not str:
        raise RolyError(f"builtin 'open' expects a str mode, got {mode!r}")
    binary = OPEN_MODES.get(mode)
    if binary is None:
        raise RolyError(f'open: mode must be "r", "w" or "a", got {mode!r}')
    target = _resolve_path(I, path)
    try:
        stream = I.fs.open(target, binary)
    except OSError as error:
        _io_fail("open", f"open '{path}'", error)
    return FileHandle(target, path, I.entry_base_dir, stream)


def make_dir(I, path):
    if type(path) is not str:
        raise RolyError(f"builtin 'mkdir' expects a str path, got {path!r}")
    try:
        I.fs.mkdir(_resolve_path(I, path))
    except OSError as error:
        _io_fail("mkdir", f"make directory '{path}'", error)
    return True


def list_dir_native(I, path):
    if type(path) is not str:
        raise RolyError(f"builtin 'list_dir' expects a str path, got {path!r}")
    try:
        return I.fs.listdir(_resolve_path(I, path))
    except OSError as error:
        _io_fail("list_dir", f"list '{path}'", error)


def _require_stream(handle):
    if handle.stream is None:
        raise RolyError("file is closed")


def _close_stream(handle):
    if handle.stream is not None:
        handle.stream.close()
        handle.stream = None


def _read_text(I, handle, op):
    _require_stream(handle)
    try:
        data = handle.stream.read()
    except OSError as error:
        _io_fail(op, f"read '{handle.name}'", error)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        _io_fail(op, f"read '{handle.name}'", error)


def file_read(I, handle):
    return _read_text(I, handle, "read")


def file_read_lines(I, handle):
    content = _read_text(I, handle, "read_lines")
    if content == "":
        return []
    lines = content.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def file_write(I, handle, content):
    _require_stream(handle)
    if type(content) is not str:
        raise RolyError(f"method 'write' expects a str, got {content!r}")
    try:
        handle.stream.write(content.encode("utf-8"))
        handle.stream.flush()
    except OSError as error:
        _io_fail("write", f"write '{handle.name}'", error)
    return True


def file_seek(I, handle, offset):
    _require_stream(handle)
    if type(offset) is not int:
        raise RolyError(f"method 'seek' expects an int offset, got {offset!r}")
    if offset < 0:
        raise RolyError(f"seek: offset {offset} out of range")
    try:
        handle.stream.seek(offset)
    except OSError as error:
        _io_fail("seek", f"seek in '{handle.name}'", error)
    return True


def file_tell(I, handle):
    _require_stream(handle)
    return handle.stream.tell()


def file_close(I, handle):
    _close_stream(handle)
    return True


def file_exists(I, handle):
    return I.fs.exists(handle.path)


def file_size(I, handle):
    try:
        return I.fs.stat_size(handle.path)
    except OSError as error:
        _io_fail("size", f"get the size of '{handle.name}'", error)


def file_rename(I, handle, path):
    if type(path) is not str:
        raise RolyError(f"method 'rename' expects a str path, got {path!r}")
    target = _method_path(I, handle, path)
    if I.fs.exists(target):
        raise RolyError(f"rename: '{path}' already exists")
    _close_stream(handle)
    try:
        I.fs.rename(handle.path, target)
    except OSError as error:
        _io_fail("rename", f"rename '{handle.name}' to '{path}'", error)
    handle.path = target
    handle.name = path
    return True


def file_copy(I, handle, path):
    if type(path) is not str:
        raise RolyError(f"method 'copy' expects a str path, got {path!r}")
    try:
        I.fs.copy(handle.path, _method_path(I, handle, path))
    except OSError as error:
        _io_fail("copy", f"copy '{handle.name}' to '{path}'", error)
    return True


def file_delete(I, handle):
    _close_stream(handle)
    try:
        I.fs.unlink(handle.path)
    except OSError as error:
        _io_fail("delete", f"delete '{handle.name}'", error)
    return True


FILE_METHODS = {
    "read": file_read,
    "read_lines": file_read_lines,
    "write": file_write,
    "seek": file_seek,
    "tell": file_tell,
    "close": file_close,
    "exists": file_exists,
    "size": file_size,
    "rename": file_rename,
    "copy": file_copy,
    "delete": file_delete,
}

FILE_METHOD_ARITIES = {
    "read": 0,
    "read_lines": 0,
    "write": 1,
    "seek": 1,
    "tell": 0,
    "close": 0,
    "exists": 0,
    "size": 0,
    "rename": 1,
    "copy": 1,
    "delete": 0,
}
