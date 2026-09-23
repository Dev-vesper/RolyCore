from roly.builtins import default_registry
from roly.diagnostics.errors import RolyError
from roly.frontend.lexer import LexError, Lexer
from roly.frontend.parser import ParseError, Parser
from roly.runtime.interpreter import Interpreter
from roly.runtime.limits import DEFAULT_MAX_STEPS


def run_source(source, max_steps=DEFAULT_MAX_STEPS, out=None, base_dir=None, entry_path=None):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    try:
        return Interpreter(
            max_steps=max_steps,
            out=out,
            base_dir=base_dir,
            entry_path=entry_path,
            registry=default_registry(),
        ).run(program)
    except RecursionError:
        raise RolyError(
            "call depth of 200 exceeded (possible runaway recursion)"
        ) from None
