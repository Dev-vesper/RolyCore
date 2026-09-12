import pytest

from roly.ast import Import, ModuleCall, ModuleVar, Num, Str, Var
from roly.errors import RolyError
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.utils.runner import run_source


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def write_module(tmp_path, name, source):
    (tmp_path / f"{name}.roly").write_text(source, encoding="utf-8")


def test_parse_import_plain():
    program = parse("import testme")
    assert program.statements[0] == Import("testme", None)


def test_parse_import_with_braces():
    program = parse("import testme {users, setBlock}")
    assert program.statements[0] == Import("testme", ["users", "setBlock"])


def test_parse_import_single_member():
    program = parse("import testme {users}")
    assert program.statements[0] == Import("testme", ["users"])


def test_parse_import_requires_module_name():
    with pytest.raises(ParseError, match="a module name"):
        parse("import")
    with pytest.raises(ParseError, match="a module name"):
        parse("import 5")


def test_parse_import_empty_braces_errors():
    with pytest.raises(ParseError, match="a member name"):
        parse("import testme {}")


def test_parse_import_trailing_comma_errors():
    with pytest.raises(ParseError, match="a member name"):
        parse("import testme {users,}")


def test_import_only_at_top_level():
    with pytest.raises(ParseError, match="only allowed at top level"):
        parse("if (TRUE) { import testme }")
    with pytest.raises(ParseError, match="only allowed at top level"):
        parse("fn f (n: int) { import testme return n }")
    with pytest.raises(ParseError, match="only allowed at top level"):
        parse("while (TRUE) { import testme }")


def test_parse_module_var():
    assert parse("x = testme.users").statements[0].value == ModuleVar("testme", "users")


def test_parse_module_call():
    node = parse("x = testme.setBlock(5)").statements[0].value
    assert node == ModuleCall("testme", "setBlock", [Num(5)])


def test_parse_module_call_no_args():
    node = parse("x = testme.hello()").statements[0].value
    assert node == ModuleCall("testme", "hello", [])


def test_parse_module_call_multiple_args():
    node = parse("x = testme.f(1, 2)").statements[0].value
    assert node.args == [Num(1), Num(2)]


def test_parse_keyword_after_dot_errors():
    with pytest.raises(ParseError, match="a member name"):
        parse("x = testme.print")
    with pytest.raises(ParseError, match="a member name"):
        parse("x = testme.while")
    with pytest.raises(ParseError, match="a member name"):
        parse("x = testme.fn")


def test_parse_assignment_to_member_errors():
    with pytest.raises(ParseError, match="expected '=' or a compound assignment"):
        parse("testme.users = 5")
    with pytest.raises(ParseError, match="expected '=' or a compound assignment"):
        parse("testme.users += 1")


def test_parse_chained_member_errors():
    with pytest.raises(ParseError):
        parse("x = a.b.c")


def test_parse_call_result_dot_errors():
    with pytest.raises(ParseError):
        parse("x = f(1).y")


def test_parse_dot_without_member_errors():
    with pytest.raises(ParseError, match="a member name"):
        parse("x = testme.")


def test_lex_import_keyword():
    from roly.tokens import T

    tokens = Lexer("import").tokenize()
    assert tokens[0].type is T.IMPORT
    tokens = Lexer("importx").tokenize()
    assert tokens[0].value == "importx"
    assert tokens[0].type is T.IDENT
    tokens = Lexer("myimport").tokenize()
    assert tokens[0].type is T.IDENT


def test_lex_dot_token():
    from roly.tokens import T

    tokens = Lexer("a.b").tokenize()
    assert tokens[1].type is T.DOT
    assert tokens[1].value == "."


def test_float_literal_still_rejected():
    with pytest.raises(ParseError):
        parse("x = 1.5")


def test_member_variable_read(tmp_path):
    write_module(tmp_path, "testme", 'greeting = "hi"')
    env = run_source("import testme x = testme.greeting", base_dir=tmp_path)
    assert env["x"] == "hi"


def test_member_function_call(tmp_path):
    write_module(tmp_path, "testme", "fn hello () { return 5 }")
    env = run_source("import testme x = testme.hello()", base_dir=tmp_path)
    assert env["x"] == 5


def test_member_function_call_with_args(tmp_path):
    write_module(tmp_path, "testme", "fn add (a: int, b: int) { return a + b }")
    env = run_source("import testme x = testme.add(2, 3)", base_dir=tmp_path)
    assert env["x"] == 5


def test_module_top_level_computes(tmp_path):
    write_module(tmp_path, "testme", "n = 6 * 7")
    env = run_source("import testme x = testme.n", base_dir=tmp_path)
    assert env["x"] == 42


def test_module_load_prints_suppressed(tmp_path):
    write_module(tmp_path, "testme", 'print("loading") n = 1')
    printed = []
    run_source("import testme x = testme.n", base_dir=tmp_path, out=printed.append)
    assert printed == []


def test_module_function_prints_visible_later(tmp_path):
    write_module(tmp_path, "testme", 'fn say () { print("said") return 1 }')
    printed = []
    run_source(
        "import testme x = testme.say()", base_dir=tmp_path, out=printed.append
    )
    assert printed == ["said"]


def test_module_state_live_between_calls(tmp_path):
    write_module(
        tmp_path, "testme", "c = 0 fn bump () { c += 1 return c }"
    )
    env = run_source(
        "import testme a = testme.bump() b = testme.bump() d = testme.c",
        base_dir=tmp_path,
    )
    assert env["a"] == 1
    assert env["b"] == 2
    assert env["d"] == 2


def test_module_fn_reads_own_globals(tmp_path):
    write_module(tmp_path, "testme", "base = 10 fn fetch () { return base }")
    env = run_source("import testme x = testme.fetch()", base_dir=tmp_path)
    assert env["x"] == 10


def test_module_fn_scratch_stays_local(tmp_path):
    write_module(
        tmp_path, "testme", "fn work (n: int) { scratch = n * 2 return scratch }"
    )
    env = run_source("import testme x = testme.work(3)", base_dir=tmp_path)
    assert env["x"] == 6
    with pytest.raises(RolyError, match="no member 'scratch'"):
        run_source("import testme x = testme.scratch", base_dir=tmp_path)


def test_module_fn_write_through_and_user_fn_local_in_one_program(tmp_path):
    write_module(
        tmp_path, "testme", "c = 0 fn bump () { c += 1 return c }"
    )
    env = run_source(
        "import testme"
        " t = 5"
        " fn f () { t = 99 return t }"
        " a = f() b = testme.bump() y = t z = testme.c",
        base_dir=tmp_path,
    )
    assert env["t"] == 5
    assert env["a"] == 99
    assert env["b"] == 1
    assert env["z"] == 1


def test_braces_keep_qualified_access(tmp_path):
    write_module(
        tmp_path, "testme", "users = 1 fn setBlock (n: int) { return n }"
    )
    env = run_source(
        "import testme {users, setBlock}"
        " a = testme.users b = testme.setBlock(4)",
        base_dir=tmp_path,
    )
    assert env["a"] == 1
    assert env["b"] == 4


def test_braces_do_not_restrict_unlisted_member(tmp_path):
    write_module(tmp_path, "testme", "a = 1 b = 2")
    env = run_source(
        "import testme {a} x = testme.a y = testme.b", base_dir=tmp_path
    )
    assert env["x"] == 1
    assert env["y"] == 2


def test_braces_do_not_restrict_unlisted_function(tmp_path):
    write_module(tmp_path, "testme", "fn f () { return 1 } fn g () { return 2 }")
    env = run_source(
        "import testme {f} x = testme.f() y = testme.g()", base_dir=tmp_path
    )
    assert env["x"] == 1
    assert env["y"] == 2


def test_brace_function_called_without_prefix(tmp_path):
    write_module(tmp_path, "testme", "fn add (a: int, b: int) { return a + b }")
    env = run_source("import testme {add} x = add(2, 3)", base_dir=tmp_path)
    assert env["x"] == 5


def test_brace_variable_read_without_prefix(tmp_path):
    write_module(tmp_path, "testme", 'greeting = "hi"')
    env = run_source("import testme {greeting} x = greeting", base_dir=tmp_path)
    assert env["x"] == "hi"


def test_brace_variable_read_is_live(tmp_path):
    write_module(
        tmp_path, "testme", "users = 0 fn store (n: int) { users = n return users }"
    )
    env = run_source(
        "import testme {users, store}"
        " a = users b = store(7) c = users d = testme.users",
        base_dir=tmp_path,
    )
    assert env["a"] == 0
    assert env["b"] == 7
    assert env["c"] == 7
    assert env["d"] == 7


def test_assignment_to_brace_variable_rebinds_locally(tmp_path):
    write_module(tmp_path, "testme", "users = 0")
    env = run_source(
        "import testme {users} users = 5 a = users b = testme.users",
        base_dir=tmp_path,
    )
    assert env["a"] == 5
    assert env["b"] == 0


def test_brace_call_prints_visible(tmp_path):
    write_module(tmp_path, "testme", 'fn say () { print("said") return 1 }')
    printed = []
    run_source(
        "import testme {say} x = say()", base_dir=tmp_path, out=printed.append
    )
    assert printed == ["said"]


def test_brace_call_cannot_see_caller_locals(tmp_path):
    write_module(tmp_path, "testme", "fn leak () { return secret }")
    with pytest.raises(RolyError, match="undefined variable 'secret'"):
        run_source(
            "import testme {leak}"
            " fn wrap () { secret = 99 return leak() }"
            " x = wrap()",
            base_dir=tmp_path,
        )


def test_brace_function_arity_checked(tmp_path):
    write_module(tmp_path, "testme", "fn f (a: int, b: int) { return a }")
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source("import testme {f} x = f(1)", base_dir=tmp_path)


def test_brace_function_arg_types_checked(tmp_path):
    write_module(tmp_path, "testme", "fn f (a: int) { return a }")
    with pytest.raises(RolyError, match="must be int"):
        run_source('import testme {f} x = f("1")', base_dir=tmp_path)


def test_brace_function_name_read_as_variable_errors(tmp_path):
    write_module(tmp_path, "testme", "fn f () { return 1 }")
    with pytest.raises(RolyError, match="'f' is a function, call it as"):
        run_source("import testme {f} x = f", base_dir=tmp_path)


def test_brace_function_collides_with_user_fn(tmp_path):
    write_module(tmp_path, "testme", "fn f () { return 1 }")
    with pytest.raises(RolyError, match="already defined"):
        run_source("fn f () { return 2 } import testme {f}", base_dir=tmp_path)


def test_brace_variable_overwrites_existing_global(tmp_path):
    write_module(tmp_path, "testme", "x = 9")
    env = run_source("x = 1 import testme {x} a = x", base_dir=tmp_path)
    assert env["a"] == 9


def test_braces_nonexistent_member_errors_at_import(tmp_path):
    write_module(tmp_path, "testme", "a = 1")
    with pytest.raises(RolyError, match="has no member 'nope'"):
        run_source("import testme {nope}", base_dir=tmp_path)


def test_reimport_applies_more_aliases(tmp_path):
    write_module(tmp_path, "testme", "a = 1 b = 2")
    env = run_source(
        "import testme {a} import testme {b} x = a y = b",
        base_dir=tmp_path,
    )
    assert env["x"] == 1
    assert env["y"] == 2


def test_plain_reimport_keeps_aliases(tmp_path):
    write_module(tmp_path, "testme", "a = 1 b = 2")
    env = run_source(
        "import testme {a} import testme x = a y = testme.b", base_dir=tmp_path
    )
    assert env["x"] == 1
    assert env["y"] == 2


def test_module_brace_import_reachable_from_importer(tmp_path):
    write_module(tmp_path, "inner", "fn dbl (n: int) { return n * 2 }")
    write_module(
        tmp_path, "outer", "import inner {dbl} fn go (n: int) { return dbl(n) }"
    )
    env = run_source(
        "import outer {go} x = go(6) y = outer.go(5)", base_dir=tmp_path
    )
    assert env["x"] == 12
    assert env["y"] == 10


def test_brace_name_dual_variable_and_function(tmp_path):
    write_module(tmp_path, "testme", "x = 5 fn x () { return 9 }")
    env = run_source("import testme {x} a = x b = x()", base_dir=tmp_path)
    assert env["a"] == 5
    assert env["b"] == 9


def test_reimport_does_not_reexecute(tmp_path):
    write_module(tmp_path, "testme", "c = 0 fn bump () { c += 1 return c }")
    env = run_source(
        "import testme a = testme.bump() import testme b = testme.c",
        base_dir=tmp_path,
    )
    assert env["b"] == 1


def test_module_shared_across_importers(tmp_path):
    write_module(tmp_path, "shared", "c = 0 fn bump () { c += 1 return c }")
    write_module(tmp_path, "first", "import shared x = shared.bump()")
    env = run_source(
        "import first import shared v = shared.c", base_dir=tmp_path
    )
    assert env["v"] == 1


def test_module_cannot_see_main_globals(tmp_path):
    write_module(tmp_path, "testme", "fn fetch () { return mainonly }")
    with pytest.raises(RolyError, match="undefined variable 'mainonly'"):
        run_source(
            "mainonly = 7 import testme x = testme.fetch()", base_dir=tmp_path
        )


def test_module_fn_cannot_see_caller_locals(tmp_path):
    write_module(tmp_path, "testme", "fn leak () { return secret }")
    with pytest.raises(RolyError, match="undefined variable 'secret'"):
        run_source(
            "import testme"
            " fn wrap () { secret = 99 return testme.leak() }"
            " x = wrap()",
            base_dir=tmp_path,
        )


def test_main_globals_untouched_by_module_load(tmp_path):
    write_module(tmp_path, "testme", "x = 99 y = 1")
    env = run_source(
        "x = 1 y = 2 import testme a = testme.x", base_dir=tmp_path
    )
    assert env["x"] == 1
    assert env["y"] == 2
    assert env["a"] == 99


def test_module_fn_can_call_module_fn(tmp_path):
    write_module(
        tmp_path,
        "testme",
        "fn sq (n: int) { return n * n } fn sum_sq (a: int, b: int) {"
        " return sq(a) + sq(b) }",
    )
    env = run_source("import testme x = testme.sum_sq(3, 4)", base_dir=tmp_path)
    assert env["x"] == 25


def test_module_recursion(tmp_path):
    write_module(
        tmp_path,
        "testme",
        "fn fact (n: int) { if (n <= 1) { return 1 } return n * fact(n - 1) }",
    )
    env = run_source("import testme x = testme.fact(5)", base_dir=tmp_path)
    assert env["x"] == 120


def test_module_uses_lib_functions(tmp_path):
    write_module(
        tmp_path, "testme", "fn h (a: int, b: int) { return gcd(a, b) }"
    )
    env = run_source("import testme x = testme.h(48, 18)", base_dir=tmp_path)
    assert env["x"] == 6


def test_module_uses_builtins(tmp_path):
    write_module(
        tmp_path,
        "testme",
        'fn label (n: int) { return format("n={}", n) }',
    )
    env = run_source("import testme x = testme.label(7)", base_dir=tmp_path)
    assert env["x"] == "n=7"


def test_module_fn_arity_checked(tmp_path):
    write_module(tmp_path, "testme", "fn f (a: int, b: int) { return a }")
    with pytest.raises(RolyError, match="expects 2 arguments"):
        run_source("import testme x = testme.f(1)", base_dir=tmp_path)


def test_module_fn_arg_types_checked(tmp_path):
    write_module(tmp_path, "testme", "fn f (a: int) { return a }")
    with pytest.raises(RolyError, match="must be int"):
        run_source('import testme x = testme.f("1")', base_dir=tmp_path)


def test_module_fn_in_condition(tmp_path):
    write_module(tmp_path, "testme", "fn odd (n: int) { return mod(n, 2) != 0 }")
    env = run_source(
        "import testme if (testme.odd(3)) { a = 1 } else { a = 2 }",
        base_dir=tmp_path,
    )
    assert env["a"] == 1


def test_module_fn_in_expression(tmp_path):
    write_module(tmp_path, "testme", "fn dbl (n: int) { return n * 2 }")
    env = run_source(
        "import testme x = testme.dbl(5) + 1", base_dir=tmp_path
    )
    assert env["x"] == 11


def test_module_fn_called_from_user_fn(tmp_path):
    write_module(tmp_path, "testme", "fn dbl (n: int) { return n * 2 }")
    env = run_source(
        "import testme"
        " fn quad (n: int) { return testme.dbl(testme.dbl(n)) }"
        " x = quad(3)",
        base_dir=tmp_path,
    )
    assert env["x"] == 12


def test_use_before_import_errors(tmp_path):
    write_module(tmp_path, "testme", "a = 1")
    with pytest.raises(RolyError, match="is not imported"):
        run_source("x = testme.a import testme", base_dir=tmp_path)


def test_missing_module_errors(tmp_path):
    with pytest.raises(RolyError, match="not found"):
        run_source("import nope", base_dir=tmp_path)


def test_module_syntax_error_wrapped(tmp_path):
    write_module(tmp_path, "testme", "x = ")
    with pytest.raises(RolyError, match=r"error in module 'testme'"):
        run_source("import testme", base_dir=tmp_path)


def test_module_runtime_error_wrapped(tmp_path):
    write_module(tmp_path, "testme", "x = 1 / 0")
    with pytest.raises(RolyError, match="error in module 'testme'"):
        run_source("import testme", base_dir=tmp_path)


def test_module_reserved_name_error_wrapped(tmp_path):
    write_module(tmp_path, "testme", "fn gcd (a: int, b: int) { return a }")
    with pytest.raises(RolyError, match="error in module 'testme'"):
        run_source("import testme", base_dir=tmp_path)


def test_circular_self_import(tmp_path):
    write_module(tmp_path, "looped", "import looped x = 1")
    with pytest.raises(RolyError, match="circular import: looped -> looped"):
        run_source("import looped", base_dir=tmp_path)


def test_circular_mutual_import(tmp_path):
    write_module(tmp_path, "a", "import b x = 1")
    write_module(tmp_path, "b", "import a y = 2")
    with pytest.raises(RolyError, match="circular import: a -> b -> a"):
        run_source("import a", base_dir=tmp_path)


def test_importing_entry_file_errors(tmp_path):
    write_module(tmp_path, "bad", "import prog y = 2")
    with pytest.raises(RolyError, match="circular import: prog -> bad -> prog"):
        run_source(
            "import bad",
            base_dir=tmp_path,
            entry_path=tmp_path / "prog.roly",
        )


def test_module_var_on_function_errors(tmp_path):
    write_module(tmp_path, "testme", "fn hello () { return 1 }")
    with pytest.raises(RolyError, match="is a function in module 'testme'"):
        run_source("import testme x = testme.hello", base_dir=tmp_path)


def test_module_call_on_variable_errors(tmp_path):
    write_module(tmp_path, "testme", "a = 1")
    with pytest.raises(RolyError, match="is not a function in module 'testme'"):
        run_source("import testme x = testme.a()", base_dir=tmp_path)


def test_module_name_coexists_with_variable(tmp_path):
    write_module(tmp_path, "testme", "a = 5")
    env = run_source(
        "testme = 2 import testme x = testme.a y = testme",
        base_dir=tmp_path,
    )
    assert env["x"] == 5
    assert env["y"] == 2


def test_module_step_limit(tmp_path):
    write_module(tmp_path, "testme", "while (TRUE) { }")
    with pytest.raises(RolyError, match="step limit"):
        run_source("import testme", base_dir=tmp_path, max_steps=100)


def test_nested_import_private_to_module(tmp_path):
    write_module(tmp_path, "inner", "v = 9")
    write_module(tmp_path, "outer", "import inner x = inner.v")
    env = run_source("import outer a = outer.x", base_dir=tmp_path)
    assert env["a"] == 9
    with pytest.raises(RolyError, match="is not imported"):
        run_source("import outer a = inner.v", base_dir=tmp_path)


def test_module_fn_uses_its_own_import(tmp_path):
    write_module(tmp_path, "inner", "fn dbl (n: int) { return n * 2 }")
    write_module(tmp_path, "outer", "import inner fn go (n: int) { return inner.dbl(n) }")
    env = run_source("import outer x = outer.go(6)", base_dir=tmp_path)
    assert env["x"] == 12


def test_import_executes_in_order(tmp_path):
    write_module(tmp_path, "testme", "n = 3")
    env = run_source(
        "a = 10 import testme b = a + testme.n", base_dir=tmp_path
    )
    assert env["b"] == 13


def test_module_fn_as_user_fn_argument(tmp_path):
    write_module(tmp_path, "testme", "fn dbl (n: int) { return n * 2 }")
    env = run_source(
        "import testme"
        " fn apply (n: int) { return n + 1 }"
        " x = apply(testme.dbl(10))",
        base_dir=tmp_path,
    )
    assert env["x"] == 21


def test_module_without_return_errors(tmp_path):
    write_module(tmp_path, "testme", "fn f () { a = 1 }")
    with pytest.raises(RolyError, match="did not return"):
        run_source("import testme x = testme.f()", base_dir=tmp_path)


def test_module_fn_calling_main_fn_errors(tmp_path):
    write_module(tmp_path, "testme", "fn go () { return helper() }")
    with pytest.raises(RolyError, match="undefined function 'helper'"):
        run_source(
            "import testme"
            " fn helper () { return 1 }"
            " x = testme.go()",
            base_dir=tmp_path,
        )


def test_module_global_updated_during_load_visible(tmp_path):
    write_module(
        tmp_path,
        "testme",
        "total = 0"
        " fn add (n: int) { total += n return total }"
        " start = add(5)",
    )
    env = run_source(
        "import testme a = testme.total b = testme.add(2)", base_dir=tmp_path
    )
    assert env["a"] == 5
    assert env["b"] == 7


def test_module_can_reference_itself_qualified(tmp_path):
    write_module(
        tmp_path,
        "testme",
        "c = 0 fn bump () { c += 1 return c }"
        " fn go () { return testme.bump() + testme.bump() }",
    )
    env = run_source(
        "import testme a = testme.go() b = testme.c", base_dir=tmp_path
    )
    assert env["a"] == 3
    assert env["b"] == 2


def test_module_self_reference_at_top_level(tmp_path):
    write_module(
        tmp_path, "testme", "fn five () { return 5 } top = testme.five()"
    )
    env = run_source("import testme a = testme.top", base_dir=tmp_path)
    assert env["a"] == 5


def test_import_self_inside_module_still_circular(tmp_path):
    write_module(tmp_path, "looped", "import looped x = 1")
    with pytest.raises(RolyError, match="circular import"):
        run_source("import looped", base_dir=tmp_path)


def test_qualified_call_counts_steps(tmp_path):
    write_module(tmp_path, "testme", "fn f () { return 1 }")
    with pytest.raises(RolyError, match="step limit"):
        run_source(
            "import testme i = 0 while (i < 100) { i = testme.f() }",
            base_dir=tmp_path,
            max_steps=250,
        )


def test_brace_variable_colliding_with_user_fn_errors(tmp_path):
    write_module(tmp_path, "testme", "x = 9")
    with pytest.raises(RolyError, match="'x' is already a function name"):
        run_source("fn x () { return 1 } import testme {x}", base_dir=tmp_path)


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
