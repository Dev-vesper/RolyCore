from roly.utils.runner import run_source


def invariant(source, expected):
    lines = []
    run_source(source, out=lines.append)
    assert lines == expected.splitlines(), f"got {lines!r}"


def test_arithmetic_laws():
    invariant("print(3 + 4 == 4 + 3)", "True")
    invariant("print((1 + 2) + 3 == 1 + (2 + 3))", "True")
    invariant("print(7 + 0 == 7) print(9 * 1 == 9) print(5 - 0 == 5)", "True\nTrue\nTrue")
    invariant("print(10 - 4 + 4 == 10)", "True")
    invariant("print(6 * 7 == 7 * 6)", "True")
    invariant("print(-7 / 2) print(0 / 5) print(7 / 1)", "-4\n0\n7")
    invariant(
        "!import math {mod}\n"
        "a = -7\nb = 2\nprint(a / b * b + mod(a, b) == a)\n"
        "c = 7\nd = 3\nprint(c / d * d + mod(c, d) == c)\n"
        "e = 0\nf = 9\nprint(e / f * f + mod(e, f) == e)",
        "True\nTrue\nTrue",
    )
    invariant("print(1 - 2 + 3) print(10 - 2 + 3)", "2\n11")


def test_float_laws():
    invariant(
        "print(1 + 0.5) print(0.5 + 1) print(2 * 1.5) print(1 - 0.5) print(-1.5)",
        "1.5\n1.5\n3.0\n0.5\n-1.5",
    )
    invariant(
        "print(7 / 2) print(-7 / 2) print(7.0 / 2) print(7 / 2.0) print(7.5 / 0.5)",
        "3\n-4\n3.5\n3.5\n15.0",
    )
    invariant(
        "print(1 == 1.0) print(1.0 == 1) print([1] == [1.0]) print(1.5 != 2)"
        " print(1 < 1.5 < 2) print(2.5 >= 2.5) print(1.0 == TRUE)",
        "True\nTrue\nTrue\nTrue\nTrue\nTrue\nFalse",
    )
    invariant(
        "print(0.1 + 0.2) print(str(0.1 + 0.2)) print(format(\"{}\", 1.5))",
        "0.30000000000000004\n0.30000000000000004\n1.5",
    )
    invariant(
        "print(int(3.9)) print(int(-3.9)) print(int(2.5)) print(float(7))"
        " print(float(\"3.14\")) print(float(\"-2.5e3\")) print(str(1.5))",
        "3\n-3\n2\n7.0\n3.14\n-2500.0\n1.5",
    )
    invariant(
        "fn half (x: float) { return x / 2 }\n"
        "print(half(1.5)) print(half(float(3))) print(half(5.0))",
        "0.75\n1.5\n2.5",
    )
    invariant(
        "x = 1\nx += 0.5\nprint(x)\nx *= 2\nprint(x)\nx -= 0.25\nprint(x)\nx /= 2\nprint(x)",
        "1.5\n3.0\n2.75\n1.375",
    )
    invariant(
        "print(1e2) print(1.5e-2) print(2.5e3) print(bool(0.0)) print(bool(0.5))",
        "100.0\n0.015\n2500.0\nFalse\nTrue",
    )
    invariant(
        "!import lists {sort_list, sum_list, max_list, min_list}\n"
        "print(sort_list([2, 0.5, 1.5, 0])) print(sum_list([1, 0.5, 0.25]))\n"
        "print(max_list([1.5, 2]) + min_list([0.5, 1]))",
        "[0, 0.5, 1.5, 2]\n1.75\n2.5",
    )


def test_string_laws():
    invariant('print(len("ab" + "cd") == len("ab") + len("cd"))', "True")
    invariant('print(("a" + "b") + "c" == "a" + ("b" + "c"))', "True")
    invariant('print("" + "x" == "x")', "True")
    invariant(
        '!import strings {upper, lower, reverse_str, trim, starts_with, substr}\n'
        'print(upper(lower("MiXeD")) == upper("MiXeD"))\n'
        'print(lower(upper("MiXeD")) == lower("MiXeD"))\n'
        'print(reverse_str(reverse_str("ab c")) == "ab c")\n'
        'print(trim("plain") == "plain")\n'
        'print(substr("hello", 0, len("hello")) == "hello")\n'
        'print(starts_with("roly" + "core", "roly"))',
        "True\nTrue\nTrue\nTrue\nTrue\nTrue",
    )


def test_list_laws():
    invariant(
        "!import lists {sort_list, join, sum_list, sublist, reverse_list}\n"
        "l = [3, 1, 2]\n"
        "print(len(push(l, 9)) == len(l) + 1)\n"
        "print(reverse_list(reverse_list(l)) == l)\n"
        "print(sort_list(sort_list(l)) == sort_list(l))\n"
        "print(sort_list(l))\n"
        "print(sum_list([5]) == 5)\n"
        "print(sublist(l, 0, len(l)) == l)\n"
        "print(delete_at(push(l, 9), 3) == l)\n"
        "print(join(l, \"-\"))",
        "True\nTrue\nTrue\n[1, 2, 3]\nTrue\nTrue\nTrue\n3-1-2",
    )
    invariant(
        "!import lists {join}\n"
        'print(join([[1, "a"]], "-"))\n'
        'print(join([TRUE, "b"], ","))',
        '[1, "a"]\nTrue,b',
    )
    invariant("print([] == []) print(len([]) == 0)", "True\nTrue")
    invariant(
        'm1 = [["a", [1]], ["b", [2]]]\n'
        'm2 = [["b", [2]], ["a", [1]]]\n'
        "print(m1 == m2) print(map_equal(m1, m2))\n"
        "print(map_equal(m1, m1))\n"
        'print(map_equal([["x", [1]]], [["x", [1]], ["z", [3]]]))\n'
        'print(map_equal([["x", [1]], ["y", [2]]], [["x", [1]], ["y", [99]]]))\n'
        'print(map_equal([], []))\n'
        'print(map_equal([["n", 1]], [["n", 1.0]]))\n'
        'print(map_equal([[1, 2]], [["1", 2]]))\n'
        'print(map_equal([["x", [1]], ["x", [2]]], [["x", [1]], ["x", [2]]]))',
        "False\nTrue\nTrue\nFalse\nFalse\nTrue\nTrue\nFalse\nTrue",
    )


def test_boolean_laws():
    invariant(
        "a = TRUE\nb = FALSE\n"
        "print((a != b) != (a == b)) print((b != a) != (b == a))\n"
        "print((a == b) == FALSE) print((a != b) == TRUE)\n"
        "print(1 == 1 != 2) print(3 != 3 == 3)",
        "True\nTrue\nTrue\nTrue\nTrue\nFalse",
    )
    invariant(
        "fn land (x: bool, y: bool) { if (x) { return y } return FALSE }\n"
        "fn lor (x: bool, y: bool) { if (x) { return TRUE } return y }\n"
        "fn lnot (x: bool) { if (x) { return FALSE } return TRUE }\n"
        "a = TRUE\nb = FALSE\n"
        "print(land(a, b) == FALSE) print(land(a, a) == TRUE)\n"
        "print(lor(a, b) == TRUE) print(lor(b, b) == FALSE)\n"
        "print(lnot(lnot(a)) == a) print(lnot(lnot(b)) == b)",
        "True\nTrue\nTrue\nTrue\nTrue\nTrue",
    )


def test_control_flow():
    invariant(
        "n = 5\ns = 0\ni = 1\nwhile (i <= n) { s += i i += 1 }\n"
        "print(s == n * (n + 1) / 2)",
        "True",
    )
    invariant(
        "x = 2\nif (x < 1) { print(\"low\") } else if (x < 5) { print(\"mid\") } "
        "else { print(\"high\") }",
        "mid",
    )
    invariant(
        "i = 0\nc = 0\nwhile (i < 10) { i += 1 if (i / 2 * 2 == i) { continue } c += 1 "
        "if (c == 3) { break } }\nprint(c)",
        "3",
    )


def test_function_laws():
    invariant(
        "fn fact (n: int) { if (n <= 1) { return 1 } return n * fact(n - 1) }\n"
        "p = 1\ni = 1\nwhile (i <= 5) { p = p * i i += 1 }\n"
        "print(fact(5) == p)",
        "True",
    )
    invariant(
        "fn is_even (n: int) { if (n == 0) { return TRUE } return is_odd(n - 1) }\n"
        "fn is_odd (n: int) { if (n == 0) { return FALSE } return is_even(n - 1) }\n"
        "print(is_even(10)) print(is_odd(7))",
        "True\nTrue",
    )
    invariant(
        "fn triple (n: int) { return n * 3 }\nprint(triple(4))",
        "12",
    )
    invariant(
        "fn quiet (n: int) { x = n * 2 }\nquiet(5)\nprint(\"ok\")",
        "ok",
    )


def test_metamorphic_transformations():
    base = "x = 5\ny = x * 2\nprint(x + y)\n"
    invariant(base, "15")
    dead = (
        "fn unused (n: int) { return n / 0 }\n"
        "if (FALSE) { print(\"dead\") } else { ... }\n"
        "while (FALSE) { print(\"dead\") }\n"
    ) + base
    invariant(dead, "15")
    invariant(base.replace("x", "aa").replace("y", "bb"), "15")
    invariant("y = 5 * 2\nx = 5\nprint(x + y)\n", "15")
    invariant("x = 5; y = x * 2; print(x + y)", "15")
    invariant("\n\n" + base + "\n\n", "15")


def test_determinism():
    source = "i = 1\nwhile (i <= 5) { print(i * i) i += 1 }\n"
    first = []
    second = []
    run_source(source, out=first.append)
    run_source(source, out=second.append)
    assert first == second


def test_library_invariants():
    invariant(
        "!import math {gcd, abs, is_prime}\n"
        "g = gcd(48, 18)\n"
        "print(48 / g * g == 48) print(18 / g * g == 18)\n"
        "print(gcd(7, 7) == abs(7))\n"
        "print(is_prime(2)) print(is_prime(9)) print(is_prime(97))",
        "True\nTrue\nTrue\nTrue\nFalse\nTrue",
    )
    invariant(
        "!import fmt {to_base, binary, hex, pad}\n"
        "print(to_base(255, 16)) print(binary(5)) print(hex(255)) print(pad(7, 3))",
        "ff\n101\nff\n007",
    )
    invariant(
        "!import math !import math {gcd}\nprint(gcd(12, 8))",
        "4",
    )


def test_subscript_invariants():
    invariant(
        'l = [10, 20, 30]\ns = "hello"\n'
        "print(l[0] + l[2])\n"
        'print(s[1] == char(s, 1))\n'
        "print(l[1] == get(l, 1))\n"
        "print(set(l, 0, 99)[0] == 99)\n"
        "print(set(l, 1, get(l, 1)) == l)\n"
        "print(push(l, 40)[3] == 40)\n"
        "print([[1, 2], [3]][0][1])",
        "40\nTrue\nTrue\nTrue\nTrue\nTrue\n2",
    )
    invariant(
        '!import strings {reverse_str}\n'
        'print(reverse_str("hello")[0] == "o")\nprint("hello"[4] == "o")',
        "True\nTrue",
    )
    invariant(
        "!import lists {sublist}\n"
        "l = [10, 20, 30]\n"
        "print(sublist(l, 1, 3) == [20, 30])\n"
        "print(delete_at(l, 0) == [20, 30])\n"
        "print(delete_at(l, 1) == [10, 30])",
        "True\nTrue\nTrue",
    )


def test_format_invariants():
    invariant(
        'print(format("{1} {0}", "a", "b"))\nprint(format("{{}}"))\n'
        'print(format("a{}b{}c", 1, 2))',
        "b a\n{}\na1b2c",
    )


def test_module_invariants(tmp_path):
    (tmp_path / "box.roly").write_text(
        "counter = 0\nfn bump () { counter += 1 return counter }\n",
        encoding="utf-8",
    )
    source = (
        "import box\n"
        "x = box.bump()\n"
        "y = box.bump()\n"
        "print(x == 1) print(y == 2) print(box.counter == 2)\n"
        "import box\n"
        "print(box.counter == 2)\n"
    )
    lines = []
    run_source(
        source, out=lines.append, base_dir=tmp_path,
        entry_path=tmp_path / "main.roly",
    )
    assert lines == ["True", "True", "True", "True"]


def test_rendering_invariants():
    invariant('print([1, "a", [2, "b"], TRUE])', '[1, "a", [2, "b"], True]')
    invariant('print([[]]) print([["x"]])', '[[]]\n[["x"]]')
    invariant('print(str(5)) print(str(TRUE)) print(-3)', "5\nTrue\n-3")
    invariant('print(format("{}", 42)) print(format("{} {}", 1, "x"))', "42\n1 x")
    invariant('print(format("{}", [1, "a"]))', '[1, "a"]')


def test_conversion_round_trips():
    invariant(
        "print(int(str(0)) == 0) print(int(str(-42)) == -42)\n"
        "print(int(str(987654321)) == 987654321)\n"
        "print(bool(0) == FALSE) print(bool(1) == TRUE)\n"
        "print(len(str(12345)) == 5) print(int(TRUE) == 1)",
        "True\nTrue\nTrue\nTrue\nTrue\nTrue\nTrue",
    )
    invariant('print(list("ab")) print(len(list("")) == 0)', '["a", "b"]\nTrue')


def test_evaluation_order():
    invariant(
        'fn tag (s: str) { print("t:" + s) return 1 }\n'
        'fn box (n: int) { print("b:" + str(n)) return 2 }\n'
        'x = tag("a") + tag("b") + box(3)\nprint(x)',
        "t:a\nt:b\nb:3\n4",
    )
    invariant(
        'fn mark (n: int) { print("m" + str(n)) return n }\n'
        'print(mark(1) < mark(2))',
        "m1\nm2\nTrue",
    )
