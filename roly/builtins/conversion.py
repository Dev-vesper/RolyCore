from roly.diagnostics.errors import RolyError
from roly.runtime.values import roly_equal, to_str

DIGITS = "0123456789"

_INF = float("inf")


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
