from roly.diagnostics.errors import RolyError
from roly.runtime.handles import FileHandle


def _escape_for_list(text):
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


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


def list_get(items, index):
    require_list("get", items)
    require_index("get", index, len(items))
    return items[index]


def text_char(s, i):
    if type(s) is not str or type(i) is not int:
        raise RolyError(f"builtin 'char' expects (str, int), got ({s!r}, {i!r})")
    if i < 0 or i >= len(s):
        raise RolyError(f"char: index {i} out of range for length {len(s)}")
    return s[i]


def _argument_count(count):
    if count == 0:
        return "no arguments"
    if count == 1:
        return "1 argument"
    return f"{count} arguments"


def _method_impl(methods, value, name):
    if type(value) is not FileHandle:
        raise RolyError(f"method '{name}' expects a file handle, got {value!r}")
    function = methods.get(name)
    if function is None:
        raise RolyError(f"file has no method '{name}'")
    return function


def checked_method(methods, arities, value, name, count):
    function = _method_impl(methods, value, name)
    arity = arities[name]
    if arity != count:
        raise RolyError(
            f"method '{name}' expects {_argument_count(arity)}, got {count}"
        )
    return function


def member_value(methods, value, name, owner):
    _method_impl(methods, value, name)
    raise RolyError(f"'{name}' is a method, call it as {owner}.{name}()")
