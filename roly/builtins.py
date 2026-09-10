from roly.errors import RolyError

DIGITS = "0123456789"


def to_int(value):
    if type(value) is int:
        return value
    if type(value) is bool:
        return 1 if value else 0
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
    return value != ""


def text_len(value):
    if type(value) is not str:
        raise RolyError(f"builtin 'len' expects a str, got {value!r}")
    return len(value)


def text_char(s, i):
    if type(s) is not str or type(i) is not int:
        raise RolyError(f"builtin 'char' expects (str, int), got ({s!r}, {i!r})")
    if i < 0 or i >= len(s):
        raise RolyError(f"char: index {i} out of range for length {len(s)}")
    return s[i]


def fail(message):
    raise RolyError(message)


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
    "len": text_len,
    "char": text_char,
    "format": format_text,
    "fail": fail,
}

BUILTIN_ARITIES = {
    "int": 1,
    "str": 1,
    "bool": 1,
    "len": 1,
    "char": 2,
}
