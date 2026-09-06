from roly.interpreter import DEFAULT_MAX_STEPS, Interpreter, RolyError
from roly.lexer import LexError, Lexer
from roly.parser import ParseError, Parser


def run_source(source, max_steps=DEFAULT_MAX_STEPS):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return Interpreter(max_steps=max_steps).run(program)
