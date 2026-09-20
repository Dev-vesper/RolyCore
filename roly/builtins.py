import shutil
import sys
from pathlib import Path

from roly.errors import RolyError
from roly.runtime import FileHandle

sys.set_int_max_str_digits(0)

DIGITS = "0123456789"

_INF = float("inf")


def _escape_for_list(text):
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def to_int(value):
    if type(value) is int:
        return value
    if type(value) is bool:
        return 1 if value else 0
    if type(value) is float:
        if value != value or value == _INF or value == -_INF:
            raise RolyError(f"cannot convert {value!r} to int")
        return int(value)
    if type(value) is not str:
        raise RolyError(f"cannot convert {value!r} to int")
    text = value
    sign = 1
    if text.startswith("+") or text.startswith("-"):
        if text[0] == "-":
            sign = -1
        text = text[1:]
    if not text or not all(c in DIGITS for c in text):
        raise RolyError(f"cannot convert {value!r} to int")
    return sign * int(text)


def to_str(value):
    if type(value) is str:
        return value
    if type(value) is bool:
        return "True" if value else "False"
    if type(value) is list:
        parts = [
            '"' + _escape_for_list(item) + '"' if type(item) is str
            else to_str(item)
            for item in value
        ]
        return "[" + ", ".join(parts) + "]"
    return str(value)


def to_bool(value):
    if type(value) is bool:
        return value
    if type(value) is int:
        return value != 0
    if type(value) is float:
        return value != 0
    if type(value) is str:
        return value != ""
    raise RolyError(f"cannot convert {value!r} to bool")


def to_float(value):
    if type(value) is float:
        return value
    if type(value) is int:
        try:
            return float(value)
        except OverflowError:
            raise RolyError("integer too large to convert to float")
    if type(value) is bool:
        return 1.0 if value else 0.0
    if type(value) is not str:
        raise RolyError(f"cannot convert {value!r} to float")
    text = value
    i = 0
    if text[:1] in ("+", "-"):
        i = 1
    digits = 0
    while i < len(text) and text[i] in DIGITS:
        i += 1
        digits += 1
    if i < len(text) and text[i] == ".":
        i += 1
        while i < len(text) and text[i] in DIGITS:
            i += 1
            digits += 1
    if digits == 0:
        raise RolyError(f"cannot convert {value!r} to float")
    if i < len(text) and text[i] in "eE":
        i += 1
        if i < len(text) and text[i] in "+-":
            i += 1
        exponent_digits = 0
        while i < len(text) and text[i] in DIGITS:
            i += 1
            exponent_digits += 1
        if exponent_digits == 0:
            raise RolyError(f"cannot convert {value!r} to float")
    if i != len(text):
        raise RolyError(f"cannot convert {value!r} to float")
    return float(text)


def roly_equal(left, right):
    if type(left) is list and type(right) is list:
        if len(left) != len(right):
            return False
        for a, b in zip(left, right):
            if not roly_equal(a, b):
                return False
        return True
    left_is_number = type(left) is int or type(left) is float
    right_is_number = type(right) is int or type(right) is float
    if left_is_number and right_is_number:
        return left == right
    return type(left) is type(right) and left == right


def text_len(value):
    if type(value) is not str and type(value) is not list:
        raise RolyError(f"builtin 'len' expects a str or a list, got {value!r}")
    return len(value)


def text_char(s, i):
    if type(s) is not str or type(i) is not int:
        raise RolyError(f"builtin 'char' expects (str, int), got ({s!r}, {i!r})")
    if i < 0 or i >= len(s):
        raise RolyError(f"char: index {i} out of range for length {len(s)}")
    return s[i]


def text_ord(s):
    if type(s) is not str:
        raise RolyError(f"builtin 'ord' expects a str, got {s!r}")
    if len(s) != 1:
        raise RolyError(f"builtin 'ord' expects a single character, got {s!r}")
    return ord(s)


def text_chr(n):
    if type(n) is not int:
        raise RolyError(f"builtin 'chr' expects an int, got {n!r}")
    if n < 0 or n > 0x10FFFF:
        raise RolyError(f"chr: code point {n} out of range")
    if 0xD800 <= n <= 0xDFFF:
        raise RolyError(f"chr: code point {n} is a surrogate")
    return chr(n)


def fail(message):
    if type(message) is not str:
        raise RolyError(f"builtin 'fail' expects a str, got {message!r}")
    raise RolyError(message)


def read_input(prompt):
    if type(prompt) is not str:
        raise RolyError(f"builtin 'input' expects a str, got {prompt!r}")
    try:
        return input(prompt)
    except EOFError:
        raise RolyError("input: end of input reached")


def make_list(*values):
    if len(values) > 1:
        raise RolyError("builtin 'list' expects no arguments or a str")
    if not values:
        return []
    value = values[0]
    if type(value) is not str:
        raise RolyError(f"builtin 'list' expects a str, got {value!r}")
    return list(value)


def require_list(name, value):
    if type(value) is not list:
        raise RolyError(f"builtin '{name}' expects a list, got {value!r}")


def require_index(name, index, length):
    if type(index) is not int:
        raise RolyError(f"builtin '{name}' expects an int index, got {index!r}")
    if index < 0 or index >= length:
        raise RolyError(
            f"{name}: index {index} out of range for length {length}"
        )


def list_push(items, value):
    require_list("push", items)
    return items + [value]


def list_insert(items, index, value):
    require_list("insert", items)
    if type(index) is not int:
        raise RolyError(f"builtin 'insert' expects an int index, got {index!r}")
    if index < 0 or index > len(items):
        raise RolyError(
            f"insert: index {index} out of range for length {len(items)}"
        )
    return items[:index] + [value] + items[index:]


def list_delete_at(items, index):
    require_list("delete_at", items)
    if type(index) is not int:
        raise RolyError(f"builtin 'delete_at' expects an int index, got {index!r}")
    if index < 0 or index >= len(items):
        raise RolyError(
            f"delete_at: index {index} out of range for length {len(items)}"
        )
    return items[:index] + items[index + 1 :]


def list_concat(left, right):
    require_list("concat", left)
    if type(right) is not list:
        raise RolyError(f"builtin 'concat' expects a list, got {right!r}")
    return left + right


def map_equal(a, b):
    require_list("map_equal", a)
    if type(b) is not list:
        raise RolyError(f"builtin 'map_equal' expects a list, got {b!r}")
    for pairs in (a, b):
        for pair in pairs:
            if type(pair) is not list or len(pair) != 2:
                raise RolyError("map_equal: element is not a [key, value] pair")
    if len(a) != len(b):
        return False
    remaining = list(b)
    for key, value in a:
        found = -1
        for i, (other_key, other_value) in enumerate(remaining):
            if roly_equal(key, other_key) and roly_equal(value, other_value):
                found = i
                break
        if found == -1:
            return False
        del remaining[found]
    return True


def list_get(items, index):
    require_list("get", items)
    require_index("get", index, len(items))
    return items[index]


def list_set(items, index, value):
    require_list("set", items)
    require_index("set", index, len(items))
    return items[:index] + [value] + items[index + 1 :]


def format_text(*values):
    if not values:
        raise RolyError("builtin 'format' expects a format string")
    fmt = values[0]
    if type(fmt) is not str:
        raise RolyError(f"format expects a str, got {fmt!r}")
    args = [to_str(v) for v in values[1:]]
    out = []
    i = 0
    n = len(fmt)
    auto = False
    manual = False
    next_auto = 0
    while i < n:
        c = fmt[i]
        if c == "{":
            if i + 1 < n and fmt[i + 1] == "{":
                out.append("{")
                i += 2
                continue
            end = fmt.find("}", i + 1)
            if end == -1:
                raise RolyError("format: unmatched '{' in format string")
            field = fmt[i + 1:end]
            if field == "":
                if manual:
                    raise RolyError(
                        "format: cannot mix '{}' and '{n}' placeholders"
                    )
                auto = True
                index = next_auto
                next_auto += 1
            elif all(ch in DIGITS for ch in field):
                if auto:
                    raise RolyError(
                        "format: cannot mix '{}' and '{n}' placeholders"
                    )
                manual = True
                index = int(field)
            else:
                raise RolyError(f"format: invalid placeholder '{{{field}}}'")
            if index >= len(args):
                raise RolyError(
                    f"format: no argument for placeholder {index}"
                )
            out.append(args[index])
            i = end + 1
        elif c == "}":
            if i + 1 < n and fmt[i + 1] == "}":
                out.append("}")
                i += 2
                continue
            raise RolyError("format: single '}' in format string")
        else:
            out.append(c)
            i += 1
    return "".join(out)


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


def _method_path(handle, path):
    target = Path(path)
    if target.is_absolute():
        return target
    return handle.base / target


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
        stream = target.open(binary)
    except OSError as error:
        _io_fail("open", f"open '{path}'", error)
    return FileHandle(target, path, I.entry_base_dir, stream)


def make_dir(I, path):
    if type(path) is not str:
        raise RolyError(f"builtin 'mkdir' expects a str path, got {path!r}")
    try:
        _resolve_path(I, path).mkdir()
    except OSError as error:
        _io_fail("mkdir", f"make directory '{path}'", error)
    return True


def list_dir_native(I, path):
    if type(path) is not str:
        raise RolyError(f"builtin 'list_dir' expects a str path, got {path!r}")
    try:
        return sorted(entry.name for entry in _resolve_path(I, path).iterdir())
    except OSError as error:
        _io_fail("list_dir", f"list '{path}'", error)


def _require_stream(handle):
    if handle.stream is None:
        raise RolyError("file is closed")


def _close_stream(handle):
    if handle.stream is not None:
        handle.stream.close()
        handle.stream = None


def _read_text(handle, op):
    _require_stream(handle)
    try:
        data = handle.stream.read()
    except OSError as error:
        _io_fail(op, f"read '{handle.name}'", error)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        _io_fail(op, f"read '{handle.name}'", error)


def file_read(handle):
    return _read_text(handle, "read")


def file_read_lines(handle):
    content = _read_text(handle, "read_lines")
    if content == "":
        return []
    lines = content.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def file_write(handle, content):
    _require_stream(handle)
    if type(content) is not str:
        raise RolyError(f"method 'write' expects a str, got {content!r}")
    try:
        handle.stream.write(content.encode("utf-8"))
        handle.stream.flush()
    except OSError as error:
        _io_fail("write", f"write '{handle.name}'", error)
    return True


def file_seek(handle, offset):
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


def file_tell(handle):
    _require_stream(handle)
    return handle.stream.tell()


def file_close(handle):
    _close_stream(handle)
    return True


def file_exists(handle):
    return handle.path.exists()


def file_size(handle):
    try:
        return handle.path.stat().st_size
    except OSError as error:
        _io_fail("size", f"get the size of '{handle.name}'", error)


def file_rename(handle, path):
    if type(path) is not str:
        raise RolyError(f"method 'rename' expects a str path, got {path!r}")
    target = _method_path(handle, path)
    if target.exists():
        raise RolyError(f"rename: '{path}' already exists")
    _close_stream(handle)
    try:
        handle.path.rename(target)
    except OSError as error:
        _io_fail("rename", f"rename '{handle.name}' to '{path}'", error)
    handle.path = target
    handle.name = path
    return True


def file_copy(handle, path):
    if type(path) is not str:
        raise RolyError(f"method 'copy' expects a str path, got {path!r}")
    try:
        shutil.copyfile(handle.path, _method_path(handle, path))
    except OSError as error:
        _io_fail("copy", f"copy '{handle.name}' to '{path}'", error)
    return True


def file_delete(handle):
    _close_stream(handle)
    try:
        handle.path.unlink()
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


def _argument_count(count):
    if count == 0:
        return "no arguments"
    if count == 1:
        return "1 argument"
    return f"{count} arguments"


def _method_impl(value, name):
    if type(value) is not FileHandle:
        raise RolyError(f"method '{name}' expects a file handle, got {value!r}")
    function = FILE_METHODS.get(name)
    if function is None:
        raise RolyError(f"file has no method '{name}'")
    return function


def checked_method(value, name, count):
    function = _method_impl(value, name)
    arity = FILE_METHOD_ARITIES[name]
    if arity != count:
        raise RolyError(
            f"method '{name}' expects {_argument_count(arity)}, got {count}"
        )
    return function


def member_value(value, name, owner):
    _method_impl(value, name)
    raise RolyError(f"'{name}' is a method, call it as {owner}.{name}()")


BUILTINS = {
    "int": to_int,
    "str": to_str,
    "bool": to_bool,
    "float": to_float,
    "list": make_list,
    "len": text_len,
    "char": text_char,
    "ord": text_ord,
    "chr": text_chr,
    "format": format_text,
    "fail": fail,
    "input": read_input,
    "push": list_push,
    "insert": list_insert,
    "delete_at": list_delete_at,
    "concat": list_concat,
    "map_equal": map_equal,
    "get": list_get,
    "set": list_set,
    "open": open_file,
    "mkdir": make_dir,
    "list_dir": list_dir_native,
}

BUILTINS_WITH_INTERP = {"open", "mkdir", "list_dir"}

BUILTIN_ARITIES = {
    "int": 1,
    "str": 1,
    "bool": 1,
    "float": 1,
    "len": 1,
    "char": 2,
    "ord": 1,
    "chr": 1,
    "push": 2,
    "insert": 3,
    "delete_at": 2,
    "concat": 2,
    "map_equal": 2,
    "get": 2,
    "set": 3,
    "fail": 1,
    "input": 1,
    "open": 2,
    "mkdir": 1,
    "list_dir": 1,
}
