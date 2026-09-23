import sys
from pathlib import Path

from roly.builtins import to_str
from roly.diagnostics.errors import RolyError


def resolve_lib_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "lib"
    return Path(__file__).resolve().parent / "lib"


LIB_DIR = resolve_lib_dir()


class NativeFn:
    def __init__(self, params, callable):
        self.params = params
        self.callable = callable


def _require_number_element(op, value):
    if type(value) is not int and type(value) is not float:
        raise RolyError(f"operator '{op}' requires numeric operands, got {value!r}")


def native_sort_list(I, items):
    for value in items:
        _require_number_element("+", value)
    return sorted(items)


def native_join(I, items, sep):
    return sep.join(to_str(value) for value in items)


def native_reverse_list(I, items):
    return items[::-1]


NATIVE_LIB = {
    "sort_list": NativeFn([("l", list)], native_sort_list),
    "join": NativeFn([("l", list), ("sep", str)], native_join),
    "reverse_list": NativeFn([("l", list)], native_reverse_list),
}

NATIVE_MODULE_FNS = {
    "lists": NATIVE_LIB,
}
