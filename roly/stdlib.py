import gc
import sys
from functools import lru_cache
from pathlib import Path

from roly.ast import FnDef
from roly.errors import RolyError
from roly.lexer import Lexer
from roly.parser import Parser


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


@lru_cache(maxsize=1)
def lib_functions():
    if not LIB_DIR.is_dir():
        raise RolyError(f"cannot find the standard library directory '{LIB_DIR}'")
    functions = {}
    for path in sorted(LIB_DIR.glob("*.roly")):
        source = path.read_text(encoding="utf-8")
        program = Parser(Lexer(source).tokenize()).parse()
        for statement in program.statements:
            if not isinstance(statement, FnDef):
                raise RolyError(
                    f"library file '{path.name}' may only contain "
                    f"function declarations"
                )
            if statement.name in functions or statement.name in NATIVE_LIB:
                raise RolyError(
                    f"library function '{statement.name}' is defined twice"
                )
            functions[statement.name] = statement
    functions.update(NATIVE_LIB)
    gc.collect()
    gc.freeze()
    return functions
