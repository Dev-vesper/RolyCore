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


BUILTINS = {
    "int": to_int,
    "str": to_str,
    "bool": to_bool,
}
