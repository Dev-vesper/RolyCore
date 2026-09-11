import sys

from roly.errors import RolyError

sys.set_int_max_str_digits(0)

DIGITS = "0123456789"


def to_int(value):
    if type(value) is int:
        return value
    if type(value) is bool:
        return 1 if value else 0
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
    return str(value)


def to_bool(value):
    if type(value) is bool:
        return value
    if type(value) is int:
        return value != 0
    if type(value) is str:
        return value != ""
    raise RolyError(f"cannot convert {value!r} to bool")


def roly_equal(left, right):
    if type(left) is list and type(right) is list:
        if len(left) != len(right):
            return False
        for a, b in zip(left, right):
            if not roly_equal(a, b):
                return False
        return True
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


def fail(message):
    if type(message) is not str:
        raise RolyError(f"builtin 'fail' expects a str, got {message!r}")
    raise RolyError(message)


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


BUILTINS = {
    "int": to_int,
    "str": to_str,
    "bool": to_bool,
    "list": make_list,
    "len": text_len,
    "char": text_char,
    "format": format_text,
    "fail": fail,
    "push": list_push,
    "get": list_get,
    "set": list_set,
}

BUILTIN_ARITIES = {
    "int": 1,
    "str": 1,
    "bool": 1,
    "len": 1,
    "char": 2,
    "push": 2,
    "get": 2,
    "set": 3,
    "fail": 1,
}
