import sys
from pathlib import Path

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


def native_sort_list(items):
    for value in items:
        _require_int_element("+", value)
    return sorted(items)


def native_join(items, sep):
    return sep.join(str(value) for value in items)


def native_reverse_list(items):
    return items[::-1]


NATIVE_LIB = {
    "sort_list": NativeFn([("l", list)], native_sort_list),
    "join": NativeFn([("l", list), ("sep", str)], native_join),
    "reverse_list": NativeFn([("l", list)], native_reverse_list),
}

NATIVE_MODULE_FNS = {
    "lists": NATIVE_LIB,
}
