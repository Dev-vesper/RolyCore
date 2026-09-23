import gc
import sys

from roly import stdlib
from roly.adapters import terminal
from roly.adapters.filesystem import FileSystem
from roly.builtins import default_registry
from roly.diagnostics.errors import RolyError
from roly.frontend.lexer import LexError, Lexer
from roly.frontend.parser import ParseError, Parser
from roly.runtime.interpreter import Interpreter
from roly.runtime.limits import DEFAULT_MAX_STEPS


def run_source(
    source,
    max_steps=DEFAULT_MAX_STEPS,
    out=None,
    base_dir=None,
    entry_path=None,
    fs=None,
    read_input=None,
    registry=None,
    lib_dir=None,
    native_fns=None,
):
    if fs is None:
        fs = FileSystem()
    if out is None:
        out = terminal.write
    if read_input is None:
        read_input = terminal.read
    if registry is None:
        registry = default_registry()
    if lib_dir is None:
        lib_dir = lambda: stdlib.LIB_DIR
    if native_fns is None:
        native_fns = lambda name: stdlib.NATIVE_MODULE_FNS.get(name, {})

    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    sys.setrecursionlimit(10_000)
    gc_enabled = gc.isenabled()
    gc.disable()
    try:
        try:
            return Interpreter(
                max_steps=max_steps,
                out=out,
                base_dir=base_dir,
                entry_path=entry_path,
                registry=registry,
                fs=fs,
                read_input=read_input,
                lib_dir=lib_dir,
                native_fns=native_fns,
            ).run(program)
        except RecursionError:
            raise RolyError(
                "call depth of 200 exceeded (possible runaway recursion)"
            ) from None
    finally:
        if gc_enabled:
            gc.enable()
