import pytest

from roly.errors import RolyError
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def write_module(tmp_path, name, source):
    (tmp_path / f"{name}.roly").write_text(source, encoding="utf-8")


def raises(match, source, base_dir, **kwargs):
    with pytest.raises(RolyError, match=match):
        run_source(source, base_dir=base_dir, **kwargs)


def test_import_parse_errors():
    for source in [
        "import", "import 5",
        "import testme {}", "import testme {users,}",
        "if (TRUE) { import testme }",
        "fn f (n: int) { import testme return n }",
        "while (TRUE) { import testme }",
        "x = testme.print", "x = testme.while", "x = testme.fn",
        "testme.users = 5", "testme.users += 1",
        "x = a.b.c", "x = f(1).y", "x = testme.",
        "!import", "!import 5",
        "!import testme {}", "!import testme {users,}",
        "if (TRUE) { !import testme }",
        "fn f (n: int) { !import testme return n }",
        "while (TRUE) { !import testme }",
        "x = !TRUE", "! x = 5", "!\nimport testme",
    ]:
        with pytest.raises(ParseError):
            parse(source)


def test_import_and_lib_import_name_clash(tmp_path):
    write_module(tmp_path, "math", "fn double (n: int) { return n * 2 }")
    raises("'math' is already imported", "import math !import math", tmp_path)
    raises("'math' is already imported", "!import math import math", tmp_path)


def test_missing_module_errors(tmp_path):
    raises("not found", "import nope", tmp_path)


def test_module_load_errors_wrapped(tmp_path):
    write_module(tmp_path, "testme", "x = ")
    raises("error in module 'testme'", "import testme", tmp_path)
    write_module(tmp_path, "testme", "x = 1 / 0")
    raises("error in module 'testme'", "import testme", tmp_path)
    write_module(tmp_path, "testme", "fn len (a: int) { return a }")
    raises("error in module 'testme'", "import testme", tmp_path)


def test_circular_imports(tmp_path):
    write_module(tmp_path, "looped", "import looped x = 1")
    raises("circular import: looped -> looped", "import looped", tmp_path)
    write_module(tmp_path, "a", "import b x = 1")
    write_module(tmp_path, "b", "import a y = 2")
    raises("circular import: a -> b -> a", "import a", tmp_path)


def test_importing_entry_file_errors(tmp_path):
    write_module(tmp_path, "bad", "import prog y = 2")
    with pytest.raises(RolyError, match="circular import: prog -> bad -> prog"):
        run_source("import bad", base_dir=tmp_path, entry_path=tmp_path / "prog.roly")


def test_use_before_import_errors(tmp_path):
    write_module(tmp_path, "testme", "a = 1")
    raises("is not imported", "x = testme.a import testme", tmp_path)


def test_missing_member_errors(tmp_path):
    write_module(tmp_path, "testme", "a = 1 fn hello () { return 1 }")
    raises("no member 'scratch'", "import testme x = testme.scratch", tmp_path)
    raises("has no member 'nope'", "import testme {nope}", tmp_path)
    raises("is a function in module 'testme'", "import testme x = testme.hello", tmp_path)
    raises("is not a function in module 'testme'", "import testme x = testme.a()", tmp_path)


def test_module_isolation_errors(tmp_path):
    write_module(tmp_path, "testme", "fn fetch () { return mainonly }")
    raises(
        "undefined variable 'mainonly'",
        "mainonly = 7 import testme x = testme.fetch()",
        tmp_path,
    )
    write_module(tmp_path, "testme", "fn leak () { return secret }")
    raises(
        "undefined variable 'secret'",
        "import testme fn wrap () { secret = 99 return testme.leak() } x = wrap()",
        tmp_path,
    )
    write_module(tmp_path, "testme", "fn go () { return helper() }")
    raises(
        "undefined function 'helper'",
        "import testme fn helper () { return 1 } x = testme.go()",
        tmp_path,
    )


def test_module_function_checks(tmp_path):
    write_module(tmp_path, "testme", "fn f (a: int, b: int) { return a }")
    raises("expects 2 arguments", "import testme x = testme.f(1)", tmp_path)
    raises("expects 2 arguments", "import testme {f} x = f(1)", tmp_path)
    write_module(tmp_path, "testme", "fn f (a: int) { return a }")
    raises("must be int", 'import testme x = testme.f("1")', tmp_path)
    write_module(tmp_path, "testme", "fn f () { a = 1 }")
    raises("did not return", "import testme x = testme.f()", tmp_path)


def test_module_arity_checked_before_argument_effects(tmp_path):
    write_module(tmp_path, "testme", "fn f (a: int) { return a }")
    printed = []
    with pytest.raises(RolyError, match="expects 1 argument"):
        run_source(
            'import testme fn g () { print(42) return 1 } x = testme.f(g(), 2)',
            base_dir=tmp_path,
            out=printed.append,
        )
    assert printed == []


def test_brace_collision_errors(tmp_path):
    write_module(tmp_path, "testme", "fn f () { return 1 }")
    raises("already defined", "fn f () { return 2 } import testme {f}", tmp_path)
    write_module(tmp_path, "testme", "x = 9")
    raises("'x' is already a function name", "fn x () { return 1 } import testme {x}", tmp_path)


def test_module_step_limit(tmp_path):
    write_module(tmp_path, "testme", "while (TRUE) { }")
    raises("step limit", "import testme", tmp_path, max_steps=100)
    write_module(tmp_path, "testme", "fn f () { return 1 }")
    raises(
        "step limit",
        "import testme i = 0 while (i < 100) { i = testme.f() }",
        tmp_path,
        max_steps=250,
    )
