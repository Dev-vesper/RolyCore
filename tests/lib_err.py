import pytest

import roly.stdlib as stdlib
from roly.errors import RolyError
from roly.utils.runner import run_source


def raises(match, source, **kwargs):
    with pytest.raises(RolyError, match=match):
        run_source(source, **kwargs)


def test_lib_guards_error():
    raises("isqrt: n must be non-negative", "!import math {isqrt} x = isqrt(-1)")
    raises("roman: n must be between 1 and 3999", "!import fmt {roman} x = roman(0)")
    raises("roman: n must be between 1 and 3999", "!import fmt {roman} x = roman(4000)")
    raises("between 2 and 16", "!import fmt {to_base} x = to_base(5, 1)")
    raises("between 2 and 16", "!import fmt {to_base} x = to_base(5, 17)")
    raises("digit_char: d must be between 0 and 15", "!import fmt {digit_char} x = digit_char(-1)")
    raises("digit_char: d must be between 0 and 15", "!import fmt {digit_char} x = digit_char(16)")
    raises("clamp: lo must not exceed hi", "!import math {clamp} x = clamp(5, 10, 0)")
    raises("division by zero", "!import math {mod} x = mod(5, 0)")


def test_lib_argument_types_checked():
    raises("must be int", '!import math {abs} x = abs("-5")')
    raises("must be str", "!import strings {upper} x = upper(42)")
    raises("must be int", '!import strings {substr} x = substr("hi", "0", 1)')
    raises("must be int", '!import lists {remove_at} x = remove_at(list(), "0")')
    raises("must be str", "!import lists {join} x = join(list(), 5)")
    raises("must be list", "!import lists {reverse_list} x = reverse_list(5)")


def test_lib_arity_checked():
    raises("expects 2 arguments", "!import math {max} x = max(1)")
    raises("expects 2 arguments", '!import strings {starts_with} x = starts_with("hi")')
    raises("expects 2 arguments", "!import lists {join} x = join(list())")


def test_deleted_names_are_not_lib_functions():
    raises("undefined function 'pow'", "x = pow(2, 10)")
    raises("undefined function 'repeat'", 'x = repeat("a", 2)')
    raises("undefined function 'sign'", "x = sign(-9)")
    raises("undefined function 'factorial'", "x = factorial(5)")


def test_list_lib_guards_error():
    raises("max_list", "!import lists {max_list} x = max_list(list())")
    raises("min_list", "!import lists {min_list} x = min_list(list())")
    raises("remove_at", "!import lists {remove_at} x = remove_at(list(), 0)")
    raises("remove_at", "!import lists {remove_at} x = remove_at(push(list(), 1), 1)")
    raises("remove_at", "!import lists {remove_at} x = remove_at(push(list(), 1), -1)")


def test_list_lib_element_types_checked():
    raises("requires numeric operands", '!import lists {sum_list} x = sum_list(list("ab"))')
    raises("requires numeric operands", '!import lists {sort_list} x = sort_list(["a"])')
    raises("requires numeric operands", "!import lists {max_list} x = max_list([TRUE])")
    raises("requires numeric operands", '!import lists {min_list} x = min_list(["zz"])')
    raises("requires numeric operands", "!import lists {sort_list} x = sort_list([[1]])")
    raises("requires numeric operands", "!import lists {sort_list} x = sort_list([TRUE])")


def test_string_builtin_errors():
    raises("expects a str or a list", "x = len(42)")
    raises("out of range", 'x = char("hi", 2)')
    raises("out of range", 'x = char("hi", -1)')
    raises("expects", "x = char(42, 0)")
    raises("expects 2 arguments", 'x = char("hi")')


def test_conversion_builtin_errors():
    for source in [
        'x = int("")', 'x = int(" 42 ")', 'x = int("1_000")',
        'x = int("0x10")', 'x = int("abc")', 'x = int("-")',
        "x = int(list())",
    ]:
        raises("cannot convert", source)
    raises("cannot convert", "x = bool(list())")


def test_conversion_arity_checked():
    raises("expects 1 argument", "x = int()")
    raises("expects 1 argument", "x = int(1, 2)")


def test_list_builtin_errors():
    raises("expects a str", "x = list(42)")
    raises("no arguments or a str", 'x = list("a", "b")')
    raises("expects a list", "x = push(5, 1)")
    raises("expects 2 arguments", "x = push(list())")
    raises("index 3 out of range for length 3", 'x = get(list("abc"), 3)')
    raises("index -1 out of range", 'x = get(list("abc"), -1)')
    raises("expects a list", 'x = get("abc", 0)')
    raises("expects an int index", 'x = get(list("abc"), "0")')
    raises("expects 2 arguments", "x = get(list())")
    raises(
        "index 2 out of range for length 2",
        "x = set(push(push(list(), 1), 2), 2, 9)",
    )
    raises("expects 3 arguments", "x = set(list(), 0)")


def test_format_errors():
    raises("no argument for placeholder 0", 'x = format("{} and {}")')
    raises("no argument for placeholder 1", 'x = format("{} and {}", 1)')
    raises("no argument for placeholder 2", 'x = format("{2}", 1, 2)')
    raises("single '}'", 'x = format("a}b")')
    raises("unmatched", 'x = format("{")')
    raises("invalid placeholder", 'x = format("{abc}")')
    raises("invalid placeholder", 'x = format("{-1}")')
    raises("cannot mix", 'x = format("{} {0}", 1)')
    raises("cannot mix", 'x = format("{0} {}", 1)')
    raises("expects a str", "x = format(42)")
    raises("expects a format string", "x = format()")


def test_fail_builtin_errors():
    raises("custom message", 'x = fail("custom message")')
    raises("builtin 'fail' expects 1 argument, got 2", 'x = fail("a", "b")')
    raises("builtin 'fail' expects 1 argument, got 0", "x = fail()")
    raises(r"builtin 'fail' expects a str, got 42", "x = fail(42)")


def test_input_builtin_errors():
    raises("builtin 'input' expects 1 argument, got 0", "x = input()")
    raises("builtin 'input' expects 1 argument, got 2", 'x = input("a", "b")')
    raises(r"builtin 'input' expects a str, got 42", "x = input(42)")
    raises("builtin", "input = 5")


def test_builtin_names_reserved():
    raises("builtin", "push = 5")
    raises("builtin", "fn get () { return 1 }")
    raises("builtin", "fn f (set: int) { return set }")
    raises("builtin", "format = 5")
    raises("builtin", "fn len (a: int) { return a }")
    raises("builtin", "char = 5")


def test_unimported_lib_functions_error():
    raises("undefined function 'gcd'", "x = gcd(4, 6)")
    raises("undefined variable 'gcd'", "x = gcd")
    raises("undefined function 'upper'", 'print(upper("hi"))')


def test_lib_import_errors():
    raises("library 'nope' not found", "!import nope")
    raises("has no member 'nope'", "!import math {nope}")
    raises(
        "already defined",
        "fn gcd (a: int, b: int) { return a } !import math {gcd}",
    )


def test_brace_fn_over_variable_errors(tmp_path):
    (tmp_path / "mfn.roly").write_text(
        "fn x (n: int) { return n * 2 }\n", encoding="utf-8"
    )
    (tmp_path / "mvar.roly").write_text("x = 7\n", encoding="utf-8")
    raises(
        "'x' is already a variable name",
        "x = 5\nimport mfn {x}",
        base_dir=tmp_path,
    )
    raises(
        "'x' is already a variable name",
        "import mvar {x}\nimport mfn {x}",
        base_dir=tmp_path,
    )


def test_non_utf8_module_errors(tmp_path):
    (tmp_path / "badmod.roly").write_bytes(b'x = "\xff"\n')
    raises("not valid UTF-8", "import badmod", base_dir=tmp_path)


def test_parameter_names_checked():
    raises("parameter 'len' of 'f' is a builtin", "fn f (len: int) { return len }")


def test_missing_lib_dir_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(stdlib, "LIB_DIR", tmp_path / "nowhere")
    raises("cannot find the standard library directory", "!import math")


def test_thfile_errors(tmp_path):
    raises("cannot read", '!import thfile {read} x = read("nope.txt")', base_dir=tmp_path)
    raises("cannot delete", '!import thfile {delete} delete("nope.txt")', base_dir=tmp_path)
    raises("cannot get the size", '!import thfile {size} x = size("nope.txt")', base_dir=tmp_path)
    raises("read_lines", '!import thfile {read_lines} x = read_lines("nope.txt")', base_dir=tmp_path)
    raises("cannot make directory", '!import thfile {mkdir} mkdir("no/deep")', base_dir=tmp_path)
    raises("cannot list", '!import thfile {list_dir} x = list_dir("nope")', base_dir=tmp_path)
    raises("cannot rename", '!import thfile {rename} rename("a.txt", "b.txt")', base_dir=tmp_path)
    raises("cannot copy", '!import thfile {copy} copy("a.txt", "b.txt")', base_dir=tmp_path)
    raises("has no member 'nope'", "!import thfile {nope}")
    raises("has no member 'nope'", "!import thfile thfile.nope()")
    raises("module 'thfile' not found", "import thfile")


def test_thfile_types_and_guards(tmp_path):
    raises("must be str", '!import thfile {read} x = read(42)', base_dir=tmp_path)
    raises("expects 2 arguments", '!import thfile {copy} x = copy("a")', base_dir=tmp_path)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    raises("already exists", '!import thfile {rename} rename("a.txt", "b.txt")', base_dir=tmp_path)


def test_native_module_reimport_from_second_importer(tmp_path):
    (tmp_path / "helper.roly").write_text(
        "!import lists {join}\nfn shout (l: list) {\n    return join(l, \"!\")\n}\n",
        encoding="utf-8",
    )
    run_source(
        "!import lists {sort_list}\n"
        "import helper {shout}\n"
        "print(shout([1, 2, 3]))\n"
        "print(sort_list([3, 1]))",
        base_dir=tmp_path,
    )
    (tmp_path / "filehelper.roly").write_text(
        "!import thfile {exists}\nfn probe (p: str) {\n    return exists(p)\n}\n",
        encoding="utf-8",
    )
    run_source(
        "!import thfile {write, delete}\n"
        "import filehelper {probe}\n"
        "write(\"t.txt\", \"x\")\n"
        "print(probe(\"t.txt\"))\n"
        "delete(\"t.txt\")",
        base_dir=tmp_path,
    )


def test_thfile_binary_read_errors(tmp_path):
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00abc")
    raises(
        "not valid UTF-8 text",
        '!import thfile {read} x = read("blob.bin")',
        base_dir=tmp_path,
    )
    raises(
        "not valid UTF-8 text",
        '!import thfile {read_lines} x = read_lines("blob.bin")',
        base_dir=tmp_path,
    )
