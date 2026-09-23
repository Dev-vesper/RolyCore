from roly.diagnostics.errors import RolyError

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
