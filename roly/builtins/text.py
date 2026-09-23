from roly.builtins.conversion import DIGITS, to_str
from roly.diagnostics.errors import RolyError
from roly.runtime.values import text_char


def text_len(value):
    if type(value) is not str and type(value) is not list:
        raise RolyError(f"builtin 'len' expects a str or a list, got {value!r}")
    return len(value)


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
