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
            if statement.name in functions:
                raise RolyError(
                    f"library function '{statement.name}' is defined twice"
                )
            functions[statement.name] = statement
    return functions
