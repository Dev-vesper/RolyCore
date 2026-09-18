# Roly — Language Internals

This document is the maintainer's map of Roly: how every piece works, why it
works that way, where the sharp edges are, and what has to be updated when
something changes. It is not a tutorial — `guide/index.html` is the user-facing
reference. The source code carries no comments or docstrings (project
convention), so the "why" lives here — the file is public and tracked in the
repository.

Facts below were verified against the source on 2026-09-18. When this document
and the code disagree, the code wins — then fix this document.

---

## 1. Project Layout & Module Responsibilities

| Path | Responsibility |
|---|---|
| `roly.py` | CLI entry point. `run file.roly` / `exec "code"`. Prints only program `print()` output; errors go to stderr as `error: {msg}` with exit code 1. Handles `BrokenPipeError` by redirecting stdout to devnull. |
| `roly/tokens.py` | `T` token enum, `Token` frozen dataclass (type/value/line/column), `KEYWORDS` map (16 entries), `TYPE_TOKENS` (int/str/bool/list/float). |
| `roly/lexer.py` | Hand-written scanner. Two-char/one-char operator tables, string escapes, `//` line comments, `sys.intern` on identifiers, ASCII-only identifier rule, line/column tracking. |
| `roly/parser.py` | Recursive-descent parser producing the AST. Owns the nesting limit, loop-depth and fn-depth tracking, the one-line rule, and all parse-time semantic checks. |
| `roly/ast.py` | 13 expression + 12 statement node types, all `@dataclass(slots=True)`. `If` is a two-branch node: `then_block` plus an optional `else_block`. |
| `roly/errors.py` | `LexError`, `ParseError`, `RolyError` — the only exception types the pipeline raises. |
| `roly/builtins.py` | The 18 builtin implementations, `BUILTINS` dispatch dict, `BUILTIN_ARITIES`, `roly_equal`, `format_text`, list primitives. |
| `roly/stdlib.py` | Standard-library support: `resolve_lib_dir()` (frozen builds resolve next to the exe), the `NativeFn` class, the native implementations (3 for `lists`, 11 for `thfile`), and `NATIVE_MODULE_FNS` mapping module names to their natives. Lib loading itself goes through the normal module machinery. |
| `roly/compiler.py` | Compiles the AST to nested Python closures. All evaluation logic lives here since the performance pass. |
| `roly/runtime.py` | Control-flow signals (`BreakSignal`/`ContinueSignal`/`ReturnSignal`) and module wrappers (`ModuleEntry`/`ModuleAlias`/`ModuleFunctionRef`). Splits out to break the interpreter↔compiler import cycle. |
| `roly/interpreter.py` | `Interpreter`: program execution, function invocation, scoping, module machinery (load/import/context swap), step accounting, limits. |
| `roly/utils/runner.py` | `run_source()` — the single entry the CLI, tests and smoke all use. Wraps `RecursionError` into a clean depth message. |
| `roly/lib/*.roly` | The standard library itself: 6 modules — 49 pure-Roly functions in math/fmt/strings/lists/map plus the thfile anchor (all-native, no Roly code) — imported explicitly with `!import`. |
| `builder/` + `build.py` | Standalone-exe build: `platform.py` (exe name), `engine.py` (PyInstaller command + runner), `libs.py` (lib folder sync). `build.py` is a thin argparse shell. |
| `grammar` | The EBNF grammar. Authoritative for syntax shape — read it before touching the parser. |
| `guide/index.html` | Single-page user guide. Documents every feature, including desugarings (`l[i]` ≡ `get(l, i)`). |
| `syntax/*.roly` | Example programs, one per feature area; run by the smoke test. |
| `tests/` | Error-only test suite (7 files) + `tests/rolypip/` per-feature showcase programs (also smoke-covered). |
| `internals.md` | This file. |

## 2. Pipeline

```
source ──lexer──▶ tokens ──parser──▶ AST ──compiler──▶ Python closures ──interpreter──▶ run
```

- **Lexer** raises `LexError` (carries line/column). Newlines are ordinary
  whitespace to the lexer — line discipline is entirely a parser concern.
- **Parser** raises `ParseError`. It is recursive descent with a nesting
  counter, but builds *iterative* spines for left-associative operators
  (see §12 — this shape is load-bearing).
- **Compiler** (`roly/compiler.py`) turns each statement/expression node into
  a closure `I -> value` (or `I -> None` for statements) exactly once.
  Top-level statements are compiled eagerly; fn bodies lazily on first call.
  Unknown operators fail at compile time, not run time.
- **Interpreter** drives the closures, owns all mutable state (globals,
  function table, modules, step counter) and all runtime errors (`RolyError`).

The old tree-walking evaluator (`eval`/`exec_statement` with an explicit
stack) was deleted in the 2026-09-12 performance pass. Do not resurrect it.

## 3. Grammar & Precedence

`grammar` is authoritative. Shape summary:

```
program     : (import | fn-decl | statement)*
statement   : assignment | compound-assign | if | while | print
            | break | continue | return | block
            | expression-statement        (call or module-call ONLY)
expression  : comparison (flat chain of >1 comparison op allowed)
comparison  : additive ((== != < <= > >=) additive)*
additive    : multiplicative ((+|-) multiplicative)*     ← iterative spine
multiplicative: unary ((*|/) unary)*                     ← iterative spine
unary       : '-' unary | primary
primary     : atom ('[' expression ']')*                 ← iterative postfix
atom        : INT | FLOAT | STRING | TRUE | FALSE | list-literal
            | IDENT call? | IDENT '.' IDENT call? | builtin-call
            | '-' atom | '(' expression ')'
```

Precedence, loosest to tightest:

| Level | Forms | Notes |
|---|---|---|
| 1 | comparisons `== != < <= > >=` | flat chains, see §7 |
| 2 | `+ -` | numeric operands (int/float) or str+str for `+` |
| 3 | `* /` | `/` floors two ints, true division when either side is a float |
| 4 | unary `-` | `-a[0]` is `Neg(Subscript)` — postfix beats unary |
| 5 | postfix `()` `[]` `.` | call, subscript, module access; chains freely: `f()[0].x[1]` |

Assignment is a *statement*, never an expression. There are no `and`/`or`/`not`.

**The one-line rule.** An operator (binary or compound-assign `=`) and its
left-hand side must share a line. The parser tracks `prev_line` (line of the
last consumed token) and calls `require_same_line()` before every operator,
right operand, `[`, `(` and `.` — and at every other binding site: the member
name after `.`, the type after a parameter `:`, the module name after
`import`/`!import` and its brace list, and the `if` after `else` must all
stay on their line. After every statement keyword, the `(` that opens
`if`/`while`/`print` and a function's parameter list must follow its keyword
on the same line. That check is a no-op while `bracket_depth >
0` — inside open `(` or `[` groups (call args, subscripts, parenthesized
expressions, list literals, and the parens of `if`/`while`/`print`) newlines
are free. The lexer itself skips all whitespace including newlines, so the
whole rule lives in `Parser.new_line()`. Violations get one of two messages:
`'=' must follow 'x' on the same line` — assignments, and only when an
`=`/compound operator really sits on the next line — or `an expression
cannot continue on the next line` for everything else; a lone identifier
statement falls through to the rewind path's own `expected '=' or a
compound assignment after 'x', or a call like x(...)` error.

**Expression statements.** `parse_assignment` peeks a leading identifier; if
no `=`/compound operator follows on the same line, it rewinds
(`self.pos -= 1`) and re-parses as an expression. Only `Call` and
`ModuleCall` nodes survive as statements — `f()` and `mod.f()` are legal
lines, `1 + 2` alone is a parse error. This is also why the rewind exists:
statement-level parsing must not consume the identifier before deciding.

**Blocks are never empty.** `parse_block` rejects `{ }` immediately after
the `{` with one message for every block kind (fn body, if/else,
while, bare block). The grammar's `block` rule is `statement+`. The one
exception: `{ ... }` — an ELLIPSIS token as the entire body marks the
block as intentionally empty and compiles to `Block([])`.

**`;` is a statement separator.** `parse_statements` consumes one SEMI
after any statement, then requires another statement before the
terminator (`a statement must follow ';'` on trailing). `;;` errors via
`parse_statement`'s "expected a statement" — SEMI is not a statement and
never appears inside an expression. Statements remain freely juxtaposed
without `;`; it is pure sugar for one-liners and `exec`.

## 4. Values & Type System

Five value types, period: `int`, `str`, `bool`, `list`, `float`.

- **int** is Python `int` (unbounded; `sys.set_int_max_str_digits(0)` lifts
  the print limit). `/` floors two ints, true division when either side is
  a float; division by zero is a runtime error either way. `mod(n, d)` is
  implemented in the lib as `n - n/d*d` purely so it inherits the flooring
  for free.
- **float** is Python `float` (64-bit IEEE-754 double), including Python's
  `inf`/`nan` spelling on print. Mixed int/float arithmetic promotes to
  float exactly like Python; an int beyond the double range meeting a float
  (or `float()` of one) is the clean error `integer too large to convert
  to float` — the four arithmetic ops wrap their tail in try/except
  OverflowError (zero-cost on 3.11+, but do NOT wrap them in an extra
  function call — that cost ~10% on the arith bench). `int(f)` truncates
  toward zero; `int(inf)` and `int(nan)` are clean errors. Literals need
  digits on both sides of the dot (`1.5`, `1e5`, `2.5e-3` parse; `1.` and
  `.5` are parse errors — see 15.8).
- **bool** is Python `bool`. Because Python `bool` is a subclass of `int`,
  every type check in the pipeline uses *exact* checks (`type(v) is not t`).
  `TRUE` passed where `int` *or* `float` is declared is a type error, not a
  quiet `1`; likewise `1 < TRUE` is a runtime error — bools are not numbers
  in Roly even though they are in Python.
- **str** is Python `str`. `+` concatenates str+str; `int + str` is an error.
- **list** is Python `list` but **immutable by discipline**: `push`/`set`
  return *new* lists and callers must rebind (`l = push(l, x)`). `l[i] = x`
  is a parse error and will stay one. No aliasing is possible in user code.

**Equality.** `==`/`!=` route through `roly_equal` — recursive structural
comparison where numbers compare by value across int and float
(`1 == 1.0`, `[1] == [1.0]`), everything else requires strict per-element
types: `[TRUE] != [1]`, `[[1,2]]` compares element-wise. There is no
ordering across types.

**Truthiness.** `truthy()` (interpreter.py:348) accepts: `bool` → itself,
`int`/`float` → `!= 0` (so `if (1)` is legal and true), anything else (str,
list) → runtime error `condition must be a number, got {value!r}`. Note the
asymmetry: ints are valid conditions, but bools are NOT valid numbers where
exact types still matter (arithmetic, NativeFn params).

**Subscript desugaring.** `s[i]` is exactly `char(s, i)` and `l[i]` is
exactly `get(l, i)` — same rules, same error messages. The compiler's
subscript path dispatches str→`char`, everything else→`get`, so `5[0]`
produces `get`'s "expects a list" error. Both are 0-based, no negative
indexes, out-of-range is a runtime error.

**List literals.** `[1, "a", TRUE, [2, 3]]` — mixed types allowed, items
evaluate left-to-right, trailing comma is a parse error (matching fn params),
and postfix indexing works directly: `[10, 20][1]` is `20`.

## 5. Scoping Model

Three separate visibility rules stack:

1. **User functions** see exactly two scopes: their own call frame and
   globals. Never another function's locals. (History: the first
   implementation was dynamically scoped — callees read and *wrote* caller
   frames, causing silent clobbering. Redesigned 2026-09-10.)
2. **Lib functions** are module functions (imported via `!import`), so they
   see their own frame + their module's globals — never user globals. This
   module-machinery isolation replaced the old `lib_depth` frame lock, which
   fixed the original leak where `digit_sum`'s internal `s` overwrote a
   user's global `s`.
3. **Module functions** see their own frame + their module's globals. The
   `module_frames` stack records which module each frame belongs to; a bare
   assignment inside a *user* fn is always local (there is no way to write a
   global from inside a user fn), while a module fn whose name exists in the
   module globals writes through to the module.

Lookup order: frame → globals (with `ModuleAlias` unwrapping on read, §11).
The compiler's fast path (§12) inlines this when `locals_stack` is empty.

## 6. Functions

```
fn name (a, b) { ... return expr }
```

- Top-level only (like `import`). Bodies are blocks and cannot be empty
  (except the `{ ... }` placeholder).
  `return expr` is optional — a fn that falls off the end returns the
  `MISSING` sentinel; using that result in an expression raises
  `did not return a value`, calling it as a statement line is fine.
- **Pre-registered before execution**: all `FnDef`s are collected and
  registered first, then statements run. Recursion, mutual recursion and
  call-before-def all work. Functions are NOT first-class — a separate
  functions table, no fn values; `x = f` errors with
  `'f' is a function, call it as f(...)`. Names collide both ways: a global
  assign over a fn name (either source order — pre-registration makes the
  fn visible to earlier statements too) raises
  `'{name}' is already a function name` in `Interpreter.assign`, on the
  global write path only (params/locals may shadow freely).
- **Params are bare names** — `FnDef.params` is `list[str]`, a call frame is
  `dict(zip(params, args))`. Any value is accepted (Python duck typing);
  a type mismatch surfaces at the first operation that needs the value
  (`fn h (x) { return x + 0.5 } h("s")` → `operator '+' requires numeric
  operands`). An optional `: type` annotation is allowed and PURELY
  COSMETIC — parsed, validated to be one of the five type names (anything
  else stays a parse error), then dropped; old annotated code runs
  unchanged. Names must be unique and not keyword / builtin names —
  checked at registration with the matching message (§14).
- **Invocation order** (`call_compiled` → `invoke_function`), in exact order:
  1. `count_step()` — a call is a step.
  2. Builtins checked FIRST (`BUILTINS` before the user fn table — a user
     cannot shadow a builtin at runtime, and defining one is rejected at
     registration anyway).
  3. `check_arity` — on the *arg closures*, i.e. length only, BEFORE any
     argument is evaluated. Side effects in args must not run on arity
     errors (there is a regression test asserting `print` stays silent).
  4. Arguments evaluated left-to-right.
  5. `NativeFn` ONLY: per-param exact type checks
     (`argument 'a' of 'f' must be int, got ...`) — native functions are
     host code that cannot duck-type safely. User functions skip this
     step entirely.
  6. Depth check (200) → frame push (recording `module_frames`
     state) → body → `ReturnSignal` unwinding.
- `MAX_CALL_DEPTH = 200` with `sys.setrecursionlimit(10000)` headroom for the
  host-side closure stack; a genuine runaway is wrapped by `run_source` into
  a clean `call depth of 200 exceeded` message instead of a Python traceback.
- `NativeFn` (§10) short-circuits invocation: no frame push, no depth count —
  they are pure Python functions.

## 7. Comparison Chains

`1 < x <= 10` is a true Python-style chain, not `(1 < x) and (x <= 10)`
re-associated. `parse_comparison` builds a `Chain` node only when at least
one comparison operator appears. Evaluation (`f_chain`):

- Pairs evaluate left-to-right and **short-circuit at the first false pair**
  (the shared operand is evaluated once, not twice).
- Every pair must produce a bool — non-bool intermediate results raise
  `comparison must produce a bool`.

History: chains were the bug-hunt round 2 headline — `1 == 1 == 1` used to
evaluate as `(1 == 1) == 1` → silently `False`. Chains are deliberate
AST, not sugar.

## 8. Control Flow Signals

`BreakSignal`, `ContinueSignal`, `ReturnSignal` (runtime.py) propagate as
Python exceptions through the compiled closures:

- `break`/`continue` bind to the **innermost `while` only**, enforced at
  parse time via `loop_depth` — using them outside a loop is a parse error,
  not a runtime one.
- `return` overrides both: raising `ReturnSignal` inside a loop inside a fn
  still exits the fn. Signal priority falls out of exception unwinding.
- `if` is a two-branch node: `If(cond, then_block, else_block)` with one
  optional `else`. There is no `else if` (removed 2026-09-18, user decision
  — Phase 40): longer chains nest an `if` inside `else`, so a ladder now
  costs real parser depth against MAX_NESTING = 100.

## 9. Builtins (18)

| Name | Arity | Behavior notes |
|---|---|---|
| `int(x)` | 1 | Strict grammar: optional sign + ASCII digits only — no whitespace, underscores, unicode digits. `int(TRUE)` → `1` allowed. Rejects lists. `int(float)` truncates toward zero; `int(inf)`/`int(nan)` → `cannot convert inf to int`. |
| `float(x)` | 1 | float passes through; `int`/`bool` convert (`float(7)` → `7.0`). Strings follow Python's grammar minus the exotic spellings: optional sign, digits with optional dot on either side (`"1."`/`".5"` convert), optional exponent — no whitespace, underscores, `inf`/`nan` spellings. Rejects lists. |
| `str(x)` | 1 | `str(TRUE)` → `"True"` (matches what `print` shows). Lists render Roly-style: `[1, "a"]` — string elements double-quoted and escaped with every Roly string escape (`\\`, `\"`, `\n`, `\t` — backslash FIRST so the added escapes don't re-escape; `_escape_for_list`), nested lists recursed. Floats render in Python's spelling (`1.5`, `inf`). |
| `bool(x)` | 1 | Python-style truthiness: `""`/`0` → `FALSE`, non-empty str/int → `TRUE`. Rejects lists. |
| `len(x)` | 1 | str or list; exact types. |
| `char(s, i)` | 2 | Both args exact types (str, int); 0-based; OOB runtime error. |
| `ord(c)` | 1 | Exact str type; must be exactly one character (empty or longer → error). Returns the Unicode code point — the inverse of indexing a single char out. |
| `list()` / `list(s)` | 0–1 | Empty list, or str → list of 1-char strings. |
| `push(l, x)` | 2 | Returns NEW list. |
| `insert(l, i, x)` | 3 | Returns NEW list; 0-based, i may equal len (append), OOB errors like `get`. |
| `delete_at(l, i)` | 2 | Returns NEW list; 0-based, OOB errors like `get`. Replaced the lib's pure-Roly `remove_at` (deleted the same day). |
| `concat(l, m)` | 2 | Returns NEW list; both args must be lists (`+` between lists stays an error on purpose). |
| `map_equal(a, b)` | 2 | Order-independent multiset equality over `[key, value]` pair lists. Elements must be 2-item lists (`map_equal: element is not a [key, value] pair`); length mismatch or an unmatched pair → `False`. Matching CONSUMES pairs from a working copy of b — duplicate counts must agree, and the relation is symmetric (`map_equal(a,b) == map_equal(b,a)`). Comparisons via `roly_equal` so keys/values follow `==` semantics including int/float promotion. |
| `get(l, i)` | 2 | 0-based, OOB error, no negatives. |
| `set(l, i, x)` | 3 | Returns NEW list. |
| `fail(msg)` | 1 | Raises `RolyError(msg)` — the sanctioned way lib fns reject input. |
| `input(prompt)` | 1 | Prompt must be a str (required). Wraps Python's `input()`: writes the prompt to the REAL stdout, reads one line, returns it as a str with the trailing newline stripped. EOF → `input: end of input reached`. Always returns str — `int(input(...))` is the sanctioned numeric read. |
| `format(...)` | variadic | `{}` sequential and `{n}` reusable positional placeholders; `{{`/`}}` escapes; mixing auto and manual numbering is an error; messages match Python's `str.format` word-for-word. |

Dispatch rules that matter:

- `BUILTIN_ARITIES` drives arity checks; an **absent entry means variadic**
  (`format`, `list`). Arity is checked before arguments are evaluated.
- In the parser, `TYPE_TOKENS` + `(` parse as builtin calls in `parse_atom`;
  bare `x = int` is a parse error (same treatment as a keyword).
- Reading a builtin as a value fails honestly: `x = len` → `'len' is a
  builtin, not a value`.
- `format` is a host builtin on purpose: it was proven unwritable in pure
  Roly (no string disassembly + fixed typed arity). `len`/`char` are the two
  primitives that make every other string algorithm pure-Roly-expressible.

## 10. Standard Library

**The library is opt-in.** Nothing loads on its own — a lib module is a
normal module imported with `!import name` / `!import name {a, b}`, where the
exclamation mark means "resolve from the standard library directory, not from
`base_dir`". Until imported, lib names do not exist (`gcd(4, 6)` →
`undefined function 'gcd'`); lib names are NOT reserved — `fn gcd` is legal
unless `gcd` came in through braces (then the existing collision rules apply).

| Module | Functions |
|---|---|
| `math.roly` (9) | `abs min max clamp mod gcd lcm isqrt is_prime` |
| `fmt.roly` (7) | `digit_char to_base binary hex pad group roman` |
| `strings.roly` (13) | `char_upper char_lower upper lower trim starts_with ends_with index_from index_of contains count_sub reverse_str substr` |
| `lists.roly` (4) | `sum_list max_list min_list sublist` |
| `map.roly` (16) | internals `_hash _lower_bound _find _put_h _validate`; public `new_map map_set map_get map_has map_del map_size map_keys map_values map_items map_merge show` |
| `thfile.roly` (11 native) | `read write append delete exists size read_lines mkdir list_dir rename copy` |

Plus **14 native functions** (`NativeFn` in stdlib.py): the 3 `lists` members
`sort_list`/`join`/`reverse_list` (injected for speed, §10 rules below), and the
entire `thfile` module — file I/O is impossible in pure Roly, so all eleven of
its functions are native. `native_sort_list` scans for non-number elements
first purely so `join`'s `operator '+' requires numeric operands` error
surfaces bit-for-bit as before (the scan now admits floats alongside ints).

**thfile specifics** (file operations):

- `NativeFn` callables receive the interpreter first — the call shape in
  `invoke_function` is `function.callable(self, *args)` — because thfile needs
  `I.entry_base_dir` to resolve relative paths.
- `entry_base_dir` is captured once in `Interpreter.__init__` and NEVER swapped
  during module loading; `base_dir` itself points into `roly/lib/` while a
  module fn runs (the classic trap — see 15.52).
- Relative paths resolve against the entry program's directory (cwd for inline
  `exec`); absolute paths pass through.
- Every value is UTF-8 text; mutations return `TRUE`; every failure raises
  `RolyError` (fail-loud — `op: cannot <action> '<path>': <os reason>`, reason
  lowercased); `exists` never fails.
- `read_lines` splits on `\n`, strips one trailing `\r` per line and drops one
  trailing empty line; empty file → `[]`. A file that is not valid UTF-8
  raises `read: cannot read '<path>': the file is not valid UTF-8 text`
  (never a Python traceback — `UnicodeDecodeError` has no `strerror`).
- `rename` refuses when dst exists (POSIX would silently replace, Windows
  errors — the guard makes it deterministic); `copy` overwrites (same on both).
- `mkdir` is single-level (`parents=False`); `delete` is file-only.

**map specifics** (the pure-Roly hash map — no dict type exists, a map IS a
plain list value):

- **Representation**: a list of `[hash, key, value]` entries kept sorted by
  hash. Hash window is `[0, 1000003)`; the hash is djb2
  (`h = h*33 + ord(c)` from 5381) over the key's `str()` rendering — so
  EVERY value type can be a key, and key identity follows `str()`
  (`7` ≠ `"7"`, `1` ≠ `1.0` — deliberate divergence from Python's
  hash-equality; collisions are resolved by key equality, never by the
  hash alone).
- **No boxing**: values are stored as-is. Untyped params (§6) accept any
  value, so the v1 box family (`put`/`put_i`/`put_str`/.../`map_get_i`/
  `map_has_i`) collapsed into a single `map_set(m, k, v)` / `map_get(m, k)`
  pair when params became duck-typed.
- **Lookup** is `_lower_bound` (binary search on stored hashes) + `_find`
  (linear probing over the equal-hash chain). `_put_h` upserts: `set` in
  place on a key hit, otherwise `insert` at the lower bound — the array
  stays hash-sorted with no re-sorting. `map_merge` is a single ordered walk
  over both hash-sorted inputs (no rehashing; right side wins conflicts),
  and its duplicate check scans the WHOLE equal-hash chain in the right
  input — checking only the first same-hash entry missed colliding keys
  deeper in the run (`7` vs `"7"`), fixed 2026-09-18 (15.60).
- Every public function runs `_validate` first (shape: each entry a 3-item
  list — the `push` trick doubles as the type test). So one set/get costs
  O(n) validation plus the O(log n) search; the language has no cheaper
  mutation anyway (`insert`/`set`/`delete_at` all copy).
- **Two-tier validation messages**: a wrong-*shape* list fails with
  `map: invalid map entry`, but a non-list *element* surfaces push's own
  `builtin 'push' expects a list, got ...` — there is no error-free
  exact type test in pure Roly (15.58). Both are clean `RolyError`s.
- `map_keys`/`map_values`/`map_items`/`show` follow the stored hash order —
  deterministic for the same construction history, NOT key order.
  `map_items` emits `[[k, v], ...]` exactly for the `map_equal` builtin.
- Missing keys fail loud (`map: key b not found` — the key through
  `str()`, unquoted, so list keys read `map: key [1] not found`); guard
  with `map_has`. `show` renders `{name: Ali, age: 31}` (keys and values
  both through `str()`, which is why strings come out unquoted there —
  matches the user's requested shape).

**Lib files import each other with `!import`** — they are ordinary modules:
- `fmt.roly` starts with `!import math {mod}`
- `map.roly` starts with `!import math {mod}`
- `math`, `strings`, `lists` are self-contained.

Design rules:

- **Only functions with real logic enter the library.** One-liners and
  classic teaching loops (`is_even`, `factorial`, `fibonacci`, `sign`,
  `is_palindrome`, ...) were pruned 2026-09-12 — they are user-writable.
- Lib code reuses itself: `mod()` everywhere a remainder appears (gcd,
  is_prime, to_base, group); `pad` measures width with `len(str(m))`.
- Invalid input → `fail("...")`, never a wrong answer. Guards exist on
  to_base/roman/isqrt-style fns; `to_base` fails with
  "base must be between 2 and 16" outside that range.
- Impossible-by-design in pure Roly: `divmod`, generic binary search,
  sieves. (The old "typed params block `contains`/`index_of_item` for
  lists" limitation dissolved with duck-typed params — they are now
  user-writable in the lib, but still excluded by the real-logic rule.)
- **Lib call isolation** is the module isolation of §5/§11 — lib fns see
  their frame + their module's globals, never user globals.
- `resolve_lib_dir()`: when frozen (`sys.frozen`), the lib folder is resolved
  from the *executable's* directory; otherwise from `roly/__file__`. The
  interpreter reads `stdlib.LIB_DIR` lazily at `!import` time. A missing
  folder raises `cannot find the standard library directory '{dir}'` (the
  old `lib_functions()` loader, its `lru_cache`, the functions-only
  validation and the gc collect/freeze calls were deleted with the switch to
  explicit imports).

## 11. Modules & Import

```
import mathutils                 import mathutils {gcd, lcm}
x = mathutils.gcd(4, 6)          y = gcd(4, 6)      // brace form

!import math {gcd}               !import strings    // from roly/lib/
```

- `import` and `!import` are keywords, **top-level only**, like `fn`. The
  `!` is allowed only immediately before `import`, on the same line; the
  parser enforces this with the same-line rule (`'import' must follow '!' on
  the same line`).
- **`!import` resolves ONLY the lib dir** (`stdlib.LIB_DIR`); `import`
  resolves ONLY `base_dir`. Neither falls back to the other. A program may
  not take the same name from both sources: `import math` + `!import math`
  → `'math' is already imported` (tracked via `ModuleEntry.from_lib`).
- For `!import` of a module in `NATIVE_MODULE_FNS` (i.e. `lists`, `thfile`), the
  natives are injected into the module's function table right after a FRESH
  load only — never on a `module_cache` hit (the 2026-09-13 bug-hunt: a second
  importer re-injected into the same entry and died on the `defined twice`
  guard). The guard itself still protects against a lib file defining a fn
  with a native's name. For `thfile` the anchor file holds only a comment —
  the injected natives ARE the module.
- Everything else about a lib module is plain module behavior:
- **Braces never restrict.** All members are always reachable as
  `name.member` with or without braces; braces additionally bind the listed
  names directly into the importer (Python's `import m` + `from m import x`
  combined). The first design was a whitelist; the user corrected it.
- Modules resolve **next to the importing file** and run **once** (cache
  keyed by resolved path, shared across importers; the cache entry is
  written only after a successful load — a failed load can be retried).
- **Single-interpreter context swap**: loading a module swaps
  globals/functions/modules/base_dir (and `out`) on the one Interpreter, so
  modules share the single 10M-step budget and depth-200 limit. Per-module
  interpreters were rejected precisely because alternating calls would
  multiply the effective depth.
- **Circular imports are path-based**, checked in `execute_import` after the
  name-clash check: the resolved import path is compared against the loading
  chain's paths, giving `circular import: a -> b -> a`. The *entry script* is
  seeded into the loading chain (via `entry_path`), so a module importing the
  main program fails as `circular import: prog -> mod -> prog` — while an
  entry *named* like a lib module (`strings.roly` + `!import strings`) loads
  fine, because lib path and entry path differ.
- A module may reference **itself** qualified (`own.f()` works — its own
  entry is seeded into `imports` before execution).
- **Members** are the module's own fns + globals (lib/builtin names are
  never injected — a module wanting a lib fn must `!import` it itself, and
  then it can even re-export it: brace-importing from that module flattens
  the ref). Builtins are excluded from membership. Qualified access is
  read-only (`testme.x = 5` is a *parse* error); parens decide var read vs
  call (`testme.x` vs `testme.x()`).
- **Top-level prints are discarded on load** (`out=_silent_out` swap) but
  later calls print normally.
- **Errors**: load-time errors are wrapped `error in module 'x': ...`
  (`error in library 'x': ...` for `!import`); errors from later calls are
  raw. Not-found is `module 'x' not found (looked for {path})` vs
  `library 'x' not found (looked for {path})`. Unreadable or non-UTF-8
  source is `cannot read module 'x': {reason}` with the reason from
  `stdlib._io_reason` (15.55). Qualified module calls count steps.
- **Brace binding mechanics**:
  - Variables → `ModuleAlias(entry, name)` in the importer's globals,
    dereferenced LIVE on every read — the importer sees later module
    mutations. Assigning to a bare alias rebinds the *importer's* global;
    the module value is untouched.
  - Functions → `ModuleFunctionRef(entry, fn)` in the functions table. If a
    module re-exports a brace-imported name, refs flatten at
    registration/call time.
  - Collisions: brace fn over a user fn → `already defined`; brace var over
    a live fn name → `'x' is already a function name`; brace fn over a user
    variable → `'x' is already a variable name` (the two "split-brain"
    fixes — before them, a name could live in both tables at once, with
    reads seeing the variable and calls seeing the function). Brace vars
    may silently overwrite importer globals.
- Module fns cannot see caller frames (`module_frames` boundary, §5) — the
  same bug family as the old lib leak, fixed the same way.
- `run()` returns an alias-dereferenced copy of globals, so host code never
  sees `ModuleAlias` wrappers.

## 12. The Closure Compiler

`compile_expression` / `compile_statement` produce Python closures once;
evaluation is just calling them. This replaced tree-walking for a ~3.1x
speedup on the arith benchmark.

- **Top level**: every statement compiled eagerly at program start.
- **Fn bodies**: compiled lazily on first call, cached in `fn_compiled`
  keyed by `id(FnDef)` — the cache entry is a `(fn, body)` tuple that keeps
  a **strong reference** to the FnDef (so its `id` can't be recycled by GC),
  and the hit test is `cached[0] is function`, not just the id match.
- **Spines must compile to loops.** The parser builds BinOp chains as
  left-leaning *iterative* spines and postfix subscript chains the same way.
  A naive compiler would emit nested closures — one Python frame per term —
  and a 10,000-term flat expression then dies with `RecursionError` at run
  time. `f_binchain` (BinOp) and `f_subchain` (Subscript) are accumulator
  loops instead. Any new left-associative or postfix construct MUST follow
  this pattern.
- **Var fast path**: when `locals_stack` is empty (top level / module top
  level), `f_var` reads `I.globals.get(name, MISS)` and unwraps `ModuleAlias`
  inline in a small loop; anything else defers to `I.lookup`. `MISS` is a
  sentinel, not `None` (globals can hold falsy values).
- **Every statement closure starts with `I.count_step()`** — this is the
  step-accounting contract (§13). New statement types must preserve it.
- **Compound assignment order** is fixed: lookup → RHS value → op → assign.
  `f_cassign` implements it directly; changing the order changes observable
  behavior (the lookup error must fire before the RHS runs).
- Constants are inlined into closures; `sys.intern`ed identifiers make the
  dict lookups hit Python's identifier cache.
- Operators live in the `OPS` dict in compiler.py — including the
  `==`/`!=` entries that route through `roly_equal` and `op_add`'s str+str
  branch. An unknown operator is a compile-time `unknown operator` error.

Exact-parity rules from the performance pass (all preserved on purpose):
step accounting per statement execution, arity-before-args, compound-assign
order, and byte-identical error messages. If you touch the compiler, re-run
the full suite — those four properties are what the error tests and CLI
spot-checks guard.

## 13. Limits & Resource Guards

| Guard | Value | Where |
|---|---|---|
| Parser nesting | `MAX_NESTING = 100` | parser `enter`/`leave` on every recursive descent path (expressions AND blocks). Deep *flat* expressions don't hit it (iterative spines); deep *parenthesized* ones do. |
| Steps | `DEFAULT_MAX_STEPS = 10_000_000` | `count_step()` at the head of every compiled statement closure, plus one per call. A `Block` counts per execution, so a while body counts once per iteration. Modules share the single budget. |
| Call depth | `MAX_CALL_DEPTH = 200` | frame push check; `sys.setrecursionlimit(10000)` gives the closure stack headroom; `run_source` wraps any residual `RecursionError` into the clean depth message. |
| GC | disabled during run | `gc.disable()` on entry, restored after. Safe ONLY because Roly values cannot form reference cycles (no mutable lists, no first-class functions). Revisit if either ever changes. |

Other tunings: `@dataclass(slots=True)` on all AST nodes,
`sys.set_int_max_str_digits(0)`. (The gc collect/freeze after lib load was
dropped with the auto-load: `!import` happens mid-run while gc is disabled,
so the tuning was moot.)

## 14. Error Reporting

Three classes only (`roly/errors.py`): `LexError` (line/column),
`ParseError` (token description: `... got {describe(token)}`), `RolyError`
(everything runtime — with the module wrapper adding
`error in module 'x': ...` at load time only).

Message conventions that tests match on:

- Reserved names, two distinct messages: keywords (parse error), builtins
  (`'x' is a builtin and cannot be redefined`). Lib names are NOT reserved —
  a lib name is only taken once it arrives through `!import` braces, and
  then the normal module collision rules apply.
- Honest value reads: `x = len` → `'len' is a builtin, not a value`;
  `x = f` → `'f' is a function, call it as f(...)`.
- Arity: `function 'f' expects 2 arguments, got 1` (singular/plural handled).
- NativeFn argument types: `argument 'a' of 'f' must be int, got '1'` (value
  repr'd) — user functions never raise this; their type errors are the
  operators'/builtins' own messages at the use site.
- Modules: `no member 'x'`, `has no member 'x'` (brace), `is a function in
  module 'm'` / `is not a function in module 'm'`,
  `'m' is already imported` (import vs `!import` clash),
  `library 'x' not found (looked for {path})`.
- File reads (CLI entry + module loads + thfile): `cannot read ...: {reason}`
  from `stdlib._io_reason` — strerror with the first letter lowercased, or
  `the file is not valid UTF-8 text` for decode failures.

The CLI renders any of them as `error: {msg}` on stderr, exit 1. Only
`print()` output ever reaches stdout.

## 15. Gotchas & Sensitive Points

15.1 The lexer treats newlines as plain whitespace — the one-line rule is
entirely `Parser.prev_line` + `require_same_line()`. Don't look for it in
the lexer.

15.2 `require_same_line` is a no-op while `bracket_depth > 0`. The depth is
incremented/decremented manually at every `(`/`[` entry point (if/while/print
parens, call args, subscript, list literal, grouping). Adding a new bracketed
construct without touching `bracket_depth` silently changes line rules
inside it.

15.3 `parse_assignment` rewinds with `self.pos -= 1` when a leading
identifier isn't followed by `=`. This rewind is why only `Call`/`ModuleCall`
can be expression statements — the decision happens after a peek, and the
statement whitelist is enforced there.

15.4 Builtin call parsing keys off `TYPE_TOKENS`/`BUILTIN_NAMES` + `(` in
`parse_atom`. A new builtin that is also a type name needs `TYPE_TOKENS`
membership too, or `x = int`-style parse handling diverges.

15.5 Python's `bool ⊂ int` trap: all pipeline type checks are exact
(`type(v) is not t`). `TRUE` is not an `int` argument, nor a `float`
argument, nor a numeric operand (`1 + TRUE` errors); `1` is not a `bool`
element in `roly_equal`. Never "simplify" these to `isinstance`.

15.6 Truthiness is asymmetric with type strictness: `if (1)` and `if (0.5)`
are legal (numbers are conditions), but `"a"`/`[1]` as a condition is a
runtime error.

15.7 `/` floors only when BOTH operands are ints; any float makes it true
division. `mod()` is `n - n/d*d` *because* of the int flooring — if `/` ever
changes semantics, `mod` silently changes too.

15.8 Float lexing: the dot must be followed by a digit, so `1.` and `.5`
stay parse errors (DOT remains module-access only) while `1.5` lexes as a
single FLOAT token. An `e`/`E` is consumed only after a no-advance lookahead
confirms `[+-]?digit` follows — otherwise `1e` and `1e+` fall back to INT +
IDENT and the parser reports the error. `read_number` never advances on the
lookahead path.

15.9 Lists are immutable by discipline, not by wrapper type — the values are
plain Python lists. The immutability contract is enforced by having no
mutating operations (`push`/`set` return new lists; `l[i] = x` parse error).
Host code (builtins, natives) must never mutate a list it received.

15.10 Subscript desugars exactly to `char`/`get` — including error text. If
you change `char`'s OOB message, `s[i]` changes with it (same closure path).

15.11 Step counting is per *statement execution*: `Block` closures count
each time they run, so loop bodies count per iteration; a call is one extra
step. Any new statement branch must open with `count_step()` or the budget
silently loosens.

15.12 Arity is checked on the argument-closure list *before any argument is
evaluated*. `test_module_arity_checked_before_argument_effects` pins this —
side-effecting args must not fire on arity errors.

15.13 **BinOp spines and Subscript chains must compile to loop-based
closures** (`f_binchain`/`f_subchain`). Nested closures = RecursionError on
long flat expressions at run time, far from the cause. This is the single
most important compiler invariant.

15.14 `fn_compiled` is keyed by `id(FnDef)`; the `(fn, body)` tuple holds a
strong ref so ids can't be recycled; hits require `cached[0] is function`.
Dropping the strong ref reintroduces an id-reuse bug.

15.15 `f_var`'s fast path uses a `MISS` sentinel — never `None`, `0` or
`""`, all of which are legal global values.

15.16 Compound-assign evaluation order (lookup → value → op → assign) is
observable through error ordering; it is deliberately identical to the old
interpreter's.

15.17 `BUILTINS` is checked *before* the user fn table at every call, and
registration rejects collisions — but the parser ALSO reserves builtin names.
Three places must agree: parser reservation, registration check, dispatch.

15.18 **Adding a builtin can break user code that defines a fn of the same
name** — this actually happened: new builtins broke module tests defining
`fn get`/`fn set`. Before adding any name, grep lib, tests, syntax/ and
rolypip/ for `fn <name>` (builtins reserve names everywhere, lib files
included). Lib names need no sweep — they are unreserved since `!import`.

15.19 Lib fns are ordinary module fns since `!import` — isolation is the
module machinery (`module_frames`/`module_context`), not the deleted
`lib_depth` frame lock. The historical bug (`digit_sum`'s internal `s`
overwriting a user's global `s`) must stay impossible.

15.20 Bare assignment inside a user fn is ALWAYS local. There is no `global`
keyword and never will be — module write-through exists only for module fns.

15.21 `ModuleAlias` derefs live on read: brace-bound vars track later module
mutations; assigning to the bare name rebinds the importer's global only.

15.22 `ModuleFunctionRef` flattening (module re-exporting a brace import)
must happen at BOTH registration and call time — refs can sit in tables
unflattened.

15.23 Module cache is written only after successful load; load errors are
wrapped (`error in module 'x': ...`), later call errors are raw. Don't wrap
twice.

15.24 Circular-import detection is NAME-based at the top of
`execute_import`, before the seeded self entry; the entry script is seeded
via `entry_path`, which is what stops a module from importing the main
program.

15.25 Module top-level prints are discarded (`out=_silent_out`); the swap is
only active during the initial load run, not later calls.

15.26 One interpreter, one budget: alternating main/module calls can't
stack depth. Per-module interpreters would break this — rejected design.

15.27 Comparison chains short-circuit at the first false PAIR and each pair
must produce a bool. `1 == 1 == 1` is `TRUE`; before the fix it silently
evaluated `(1 == 1) == 1` → `FALSE`.

15.28 `else if` does NOT exist (removed 2026-09-18, user decision): `if`
takes at most one optional `else` block and chains nest an `if` inside
`else`. The flat `If.elifs` list from Phase 8 is gone with the syntax;
nested ladders pay real parser depth against MAX_NESTING = 100.

15.29 `break`/`continue` innermost-loop binding is a PARSE-time check
(`loop_depth`), and `ReturnSignal` naturally overrides both during
unwinding.

15.30 `int()`'s string grammar is deliberately strict (optional sign + ASCII
digits, nothing else). Do not "fix" it to accept whitespace — the strictness
is documented in the guide.

15.31 `str(TRUE)` is `"True"` (capital), matching `print`'s output — Python
parity, by decision.

15.32 `format` cannot mix `{}` and `{0}`; escapes are `{{`/`}}`; messages
mirror Python's `str.format` errors word-for-word. It is variadic —
therefore ABSENT from `BUILTIN_ARITIES` (absent = variadic is the convention).

15.33 `MAX_NESTING` guards recursive descent (parens/blocks), not flat
spines. A 10k-term flat sum parses fine; `((((...))))` 101 deep does not.

15.34 `gc.disable()` during runs is only sound because values can't form
cycles. First-class functions or mutable lists would invalidate the
assumption.

15.35 Native lib fns (`sort_list`/`join`/`reverse_list`) must reproduce the
old pure-Roly behavior bit-for-bit — ERRORS (the `native_sort_list`
non-number pre-scan exists so `join`'s `operator '+' requires numeric
operands` fires exactly as before) AND OUTPUT (`native_join` renders
elements through `to_str`, never Python `str` — Python renders `['a']`
single-quoted where Roly renders `["a"]`; found in the 2026-09-13 bug-hunt).
Changing one side without the other breaks parity.

15.36 `NativeFn`s bypass frame push and depth counting (pure host
functions). A native fn with anything stateful does not belong in that
shape.

15.37 A test file named `tests/builder.py` shadows the `builder/` package
under pytest (tests/ is on sys.path, no `__init__.py`). Any test file name
must not collide with a package name.

15.38 In frozen builds the lib folder must sit NEXT TO the exe — it is NOT
bundled inside. `resolve_lib_dir()` switches on `sys.frozen`.

15.39 `smoke.py` auto-discovers every `syntax/*.roly` and
`tests/rolypip/**/*.roly` by glob — a new showcase program is covered the
moment the file exists (and a broken one fails the suite). There is no
registration list anymore.

15.40 internals.md is a public, tracked file and the code is comment-free by
convention — this file is the only place rationale is recorded. Update it in
the same change as the code it describes.

15.41 The CLI shows ONLY `print()` output; anything the host prints (debug,
tracing) leaks into program output and breaks that contract.

15.42 `run_source` is the single entry point (CLI, tests, smoke). New
run-options belong there, not in ad-hoc `Interpreter` constructions.

15.43 `!` lexes as `T.BANG` only because `TWO_CHAR_OPS` is matched before
`ONE_CHAR_OPS` — `!=` is unaffected, but any future `!`-prefixed operator
must be registered in `TWO_CHAR_OPS`.

15.44 `import` resolves ONLY `base_dir`, `!import` ONLY the lib dir — no
fallback in either direction. `ModuleEntry.from_lib` is the discriminator
when a user file and a lib module share a name: the second import raises
`'{name}' is already imported`.

15.45 Module fn tables start EMPTY (they once merged the whole lib). A
module that calls a lib fn must `!import` it itself — lib cross-deps are
declared at the top of the lib files (`fmt` → `math {mod}`).

15.46 Native fns (`sort_list`/`join`/`reverse_list`, the `thfile` set) are
injected into the module after load and ONLY on the `from_lib` path AND only
on a fresh load — a `module_cache` hit must not re-inject (the double-import
bug). A user module named `lists` gets nothing, and a collision with a fn the
module itself defined raises "defined twice".

15.47 `stdlib.LIB_DIR` is read at `!import` time, never captured at Python
import time — that is what makes the missing-lib-dir test monkeypatchable.

15.48 A fn that falls off its body returns the `MISSING` sentinel from
`runtime.py` — NOT an exception. The error fires only where the value is
USED: `f_call`/`f_module_call` raise `did not return a value` unless the
call was compiled with `discard=True`, which only `ExprStmt` (a bare call
line) passes. The sentinel must never leak into a global, a list, or an
argument — every non-discard consumer checks it.

15.49 Empty blocks are rejected in `parse_block` at ONE place — every block
kind (fn, if, elif, else, while, bare) flows through it. New block-shaped
syntax must route through `parse_block` to inherit the check. `{ ... }`
goes through the same place: the ELLIPSIS must be followed immediately by
`}`.

15.50 `...` is lexed BEFORE the one-char `.` in `next_token` — a
three-dot lookahead ahead of `ONE_CHAR_OPS`. It is accepted ONLY in
`parse_block`'s empty-body slot; in any expression position it falls to
the atom error (`expected a number, ... got '...'`).

15.51 SEMI handling lives at the END of the `parse_statements` loop, after
every branch (statement, fn, import) — that single point is what makes
`fn f () { ... }; x = 1` and `import a; import b` work while trailing
`;` fails. There is no empty statement: `;` alone or `;;` is an error.

15.52 **Native fns receive the interpreter**: the `NativeFn` call in
`invoke_function` is `function.callable(self, *args)`. Anything needing
run context (path base, limits) must come through that `I` — never from a
module-level capture. `thfile` resolves relative paths against
`I.entry_base_dir`, which is captured once in `__init__` and never swapped;
using `I.base_dir` instead would resolve user paths into `roly/lib/`
whenever a module fn is on the stack, because `load_module`/`run_in_module`
swap `base_dir` to the module's own directory.

15.53 **Adding a native module** (the thfile pattern): implementations live
in `roly/stdlib.py` next to the other natives (user rule 2026-09-13: fold
features into existing files, do not create new Python modules), registered
in `NATIVE_MODULE_FNS`, plus an anchor `.roly` file in `roly/lib/` that can
be empty or comment-only — the module does not exist for `!import` without
the anchor. Arity/type checks come free through `NativeFn.params`. Errors
must be `RolyError`s carrying the full path, not Python tracebacks.

15.54 **The two tables make every bind site a dual check**: functions and
variables live in separate dicts, and any code path that writes into one
table must first prove the name is absent from the other — `assign()` and
fn pre-registration do this, and brace binding in `execute_import` must
too (both directions, 2026-09-13 and 2026-09-14 split-brain fixes). The
hole appears exactly where a bind bypasses `assign()`; the fix is a
one-line globals lookup in the fn branch, not a redesign.

15.55 **`UnicodeDecodeError` is a `ValueError`, not an `OSError`**: every
site that decodes a user file must catch it explicitly, or a non-UTF-8
file leaks a raw Python traceback. Three sites, one shared reason helper
(`stdlib._io_reason`): the CLI entry read (`roly.py`), module loads
(`load_module`), and thfile `read`/`read_lines`. Reusing the helper also
lowercases strerror everywhere, so read errors match the language's
lowercase message style.

15.56 **`input` bypasses `out` on purpose**: the prompt is written by
Python's `input()` to the REAL stdout, not through the interpreter's
redirectable `out` callback — so a prompt always reaches the terminal even
when `out` is captured (tests) or silenced (module load). Consequences: a
module calling `input` at load time prints its prompt and blocks on stdin
despite `_silent_out`; and `input` as a bare statement is a legal `Call`
ExprStmt — the line is read and discarded, matching Python. EOF must map
to a `RolyError` (`input: end of input reached`), never a raw
`EOFError` traceback.

15.57 **`roly/lib/map.roly` carries engineering comments** — the ONE
sanctioned exception to the comment-free convention (user grant
2026-09-15): the file documents a data-structure simulation (hashing,
probing, ordered merge) whose rationale is not derivable from reading the
code, and it is the reference example of "a program a user could have
written". Do not take this as license to comment other files — their "why"
lives here.

15.58 **There is no error-free exact type test in pure Roly** — `len`
accepts str and list, `push`/`get` accept list only but *error* instead of
returning false, and no builtin reports a value's type. The map's
`_validate` therefore uses the `push` trick (push only accepts lists, so
`len(push(x, 0))` both proves list-ness and measures length) and eats the
two-tier message consequence: non-list elements surface push's message,
wrong-shape lists get the map's own. Any future pure-Roly shape validation
hits the same wall; the exact tests that exist are narrow probes
(`v == TRUE` identifies bool, `v / 1 == v` numbers — the latter errors on
bool/str/list and still cannot split int from float without
`contains(".", str(v))`). If exact runtime type tests ever become
load-bearing, the answer is a host builtin, not more probing.

15.59 **Params duck-type, NativeFns do not** (Phase 37): user functions
accept any value and let the body fail at the operation that needs it,
but `invoke_function` still runs exact per-param checks on every
`NativeFn` — `sort_list("ab")` errors at the call, while a pure-Roly
`sum_list(["a"])` errors inside the loop. Both message families are
pinned by tests; do not "unify" them: host code cannot duck-type safely,
and lib guards depend on `fail()` inside the body. The annotation path
is also two-headed: `parse_parameter` validates `: type` against the five
known names (a typo like `: integr` stays a ParseError) and then drops
it — annotations are decoration, and the AST carries bare names only.

15.60 **`map_merge`'s duplicate check is chain-wide, not first-entry**
(fixed 2026-09-18): entries sort by stored hash and `7` vs `"7"` collide
(both render through `str()`), so a right-side key match must scan the
entire equal-hash run — the first-entry version kept BOTH keys and the left
value won (`map_get` returned a's value with the phantom pair still in the
map), violating the documented right-wins merge. The fixed walk emits a's
non-duplicate entries in place and defers the whole b run to the next hash
boundary, so a deduplicated key survives only in b's entry.

## 16. Decision History & Evolutionary Phases

- **Phase 0 (2026-09-06)** — skeleton: hand-written lexer/parser/interpreter,
  print, variables, `+ - * /` (floor), comparisons, if/else, while; `grammar`
  file; the three error classes. Everything stdlib-only Python.
- **Phase 1** — strings (double-quoted, `\" \\ \n \t` escapes).
- **Phase 2** — hardening: nesting limit, iterative evaluator, ASCII-only
  tokens, `BrokenPipeError` handling, strict type equality.
- **Phase 3** — `break`/`continue` (innermost only, parse-time check).
- **Phase 4** — `guide/index.html` (single page, cream/black, sharp corners,
  no animation).
- **Phase 5** — functions: typed params, separate fn table,
  pre-registration, depth 200, `ReturnSignal`.
- **Phase 6** — `TRUE`/`FALSE` literals, unary minus, conversion builtins.
  User decision: NO floats (reversed in Phase 30).
- **Phase 7** — `tests/rolypip/` per-feature showcases.
- **Phase 8** — else-if chains as a flat `elifs` list (depth-free).
  (Reversed in Phase 40.)
- **Phase 9** — standard library: auto-load, no import keyword, reserved
  names, `lib_depth` frame lock (after the `digit_sum` global-clobber bug).
- **Phase 10** — string builtins `format`/`len`/`char`; `format` proven
  unwritable in pure Roly → host builtin.
- **Phase 11** — modules/import. First build restricted members via braces;
  **user corrected: braces never restrict** — redesign to
  ModuleAlias/ModuleFunctionRef with live reads. Single-interpreter context
  swap over per-module interpreters.
- **Phase 12** — bug hunts: true comparison chains, `fail()` builtin, honest
  value-read errors (`x = len`), arity-before-args, `RecursionError`
  wrapping, brace split-brain collision fix.
- **Phase 13** — lists: phase 1 (11 builtins, immutability decision),
  phase 2 (read-only subscript operator, DOT/LBRACKET tokens), then list
  literals (trailing comma rejected).
- **Phase 14** — standalone exe: `builder/` package, lib-next-to-exe,
  frozen-path resolution, PyInstaller 6.22.2 as dev dep.
- **Phase 15** — expression statements (call/module-call lines) + the
  one-line rule with bracket exceptions.
- **Phase 16 (2026-09-12)** — performance pass: **compiler to closures**
  (evaluator deleted), loop-compiled spines, var fast path, native
  `sort_list`/`join`/`reverse_list`, `gc` tuning, `slots=True`, interned
  identifiers. ~3.1x on the arith bench.
- **Phase 17 (2026-09-12)** — library pruning: only real-logic functions
  stay; 40 lib names total (37 Roly + 3 native); `mod()` reuse rule.
- **Phase 18 (2026-09-12)** — test suite rewrite: error-only, 7 files,
  ~100 tests; correctness verified through the real CLI.
- **Phase 19 (2026-09-12)** — internals.md rewritten from a chronological
  log into this document (topical reference).
- **Phase 20 (2026-09-12)** — `!import`: the library becomes opt-in. Lib
  files are real modules resolved from `roly/lib/` (`!` prefix, no
  fallback, clash via `from_lib`); lib names un-reserved;
  `lib_depth`/`reserved` machinery deleted; natives injected into the
  `lists` module.
- **Phase 21 (2026-09-12)** — `digits` module removed (user decision);
  `pad` now measures width with `len(str(m))` instead of `digit_count`.
- **Phase 22 (2026-09-12)** — returns become optional: a fn falling off
  its body yields the `MISSING` sentinel, erroring only when the value is
  used; empty blocks (`{ }`) become parse errors everywhere.
- **Phase 23 (2026-09-12)** — `;` statement separator (strict — nothing
  trailing, never inside expressions) and `{ ... }` as the intentional
  empty-block placeholder.
- **Phase 24 (2026-09-13)** — bug-hunt fixes: circular imports detected by
  resolved path (entry named like a lib module no longer false-positives);
  one-line rule extended to the `(` after `if`/`while`/`print` and fn param
  lists; fn/var name collisions rejected on the global write path; lists
  render Roly-style (`[1, "a"]`) in `print`/`str`/`format` via `to_str`
  recursion (print now routes through `to_str` in the compiler).
- **Phase 25 (2026-09-13)** — `thfile` module: 11 native file operations
  (read/write/append/delete/exists/size/read_lines/mkdir/list_dir/rename/copy).
  `NativeFn` callables now receive the interpreter (`callable(I, *args)`);
  `entry_base_dir` added to support entry-relative paths. Fail-loud errors,
  `rename` dst guard, UTF-8 only. First native module after `lists` —
  establishes the anchor-file pattern (15.53).
- **Phase 26 (2026-09-13)** — bug-hunt round 3, three fixes: native injection
  moved to fresh-load-only (a native module imported by two importers died on
  a false `defined twice` — the cache-hit path re-injected); thfile binary
  reads raise a clean `not valid UTF-8 text` error instead of leaking a Python
  traceback (`UnicodeDecodeError` has no `strerror`); `native_join` renders
  through `to_str` restoring the pure-Roly output parity (`["a"]`, not
  Python's `['a']`).
- **Phase 27 (2026-09-14)** — bug-hunt round 2 continued: 6500-case
  differential fuzz against Python (arithmetic, precedence, comparison
  chains, format) found zero mismatches. One confirmed bug fixed: brace fn
  over an importer variable created a split-brain name (`print(x)` read the
  variable, `x(3)` called the module fn, `x = 6` errored). User chose the
  strict option after a language survey (Rust/Go/JS error on import
  collisions; Python silently rebinds): now `'x' is already a variable
  name`, completing the collision matrix (15.54).
- **Phase 28 (2026-09-14)** — bug-hunt round 2, second fix: non-UTF-8 entry
  files and module files leaked raw Python tracebacks (both read sites
  caught only `OSError`). Both now go through `stdlib._io_reason` —
  `the file is not valid UTF-8 text` — and the CLI's read errors are
  lowercase like every other Roly error (15.55).
- **Phase 29 (2026-09-15)** — `input(prompt)` builtin (12th): Python-style
  user input. User-pinned semantics: prompt REQUIRED and str-typed (unlike
  Python's optional prompt), return is ALWAYS str — `int(input(...))` is
  the numeric read; a bare `input(...)` statement reads and discards.
  EOF → clean `RolyError`. No rolypip showcase — an interactive script
  would hang the glob-discovered smoke run.
- **Phase 30 (2026-09-15)** — `float` type + `float()` builtin (13th).
  Python-parity semantics, user-pinned in four decisions: full promotion
  (`1 + 0.5` → `1.5`, `1 == 1.0`, `[1] == [1.0]`; bools stay excluded —
  `1 + TRUE` errors); `/` floors only two ints, any float operand makes it
  true division; `float()` strings follow Python's grammar minus
  whitespace/underscores/`inf`/`nan` (but `float(".5")`/`float("1.")`
  convert, unlike the literal grammar); `int(f)` truncates toward zero,
  `int(inf)`/`int(nan)` error. Operation error messages changed
  "requires integer operands" → "requires numeric operands" (compiler OPS
  + `_require_number_element`); `sort_list`/`sum_list`/`max_list`/`min_list`
  accept numbers. Lexer: dot must be followed by a digit, exponent via
  no-advance lookahead (15.8). Verified with a 4000-case differential fuzz
  against Python (0 mismatches) plus edge probes (inf, -0.0, 1e-400 → 0.0,
  big-int precision loss). Same-day bug hunt: int/float `+ - * /` and
  `float(int)` leaked raw `OverflowError` tracebacks when the int exceeded
  the double range — now the clean `integer too large to convert to float`
  (comparisons never overflow; Python compares int/float exactly), pinned
  by a 5000-case fuzz that mixed ~300-digit int leaves in (1678 overflow
  paths, 0 mismatches) and a 6000-case literal fuzz (0 crashes, 0 value
  mismatches).
- **Phase 31 (2026-09-15)** — `ord(c)` builtin (14th): the Unicode code
  point of a single character, the inverse of `char`-style indexing.
  Strict: a non-str argument or a str of length ≠ 1 is an error. The
  guide's keyword/builtin counts are no longer hardcoded per spot — a
  tiny script at the end of `guide/index.html` fills
  `<span data-count="keywords|builtins">` from one `counts` object;
  update THAT (and the Keywords row listing) when adding names.
- **Phase 32 (2026-09-15)** — `insert(l, i, x)` builtin (15th): places a
  value at a 0-based position, rest shift right. `i == len` appends (the
  one relaxation vs `set`/`get`, which require a position below len);
  negative or `> len` is an error. User-pinned 0-based indexing
  ("باید از 0 شروع بشه"). Replaced the guide's manual
  loop-based insertion example.
- **Phase 33 (2026-09-15)** — `delete_at(l, i)` builtin (16th): drops the
  element at a 0-based position, rest shift left. Strict `get`-style
  bounds (no `i == len` here; there is nothing to delete at the end
  position). The lib's pure-Roly `remove_at` was deleted in the same
  change (user decision) — `delete_at` fully replaces it; showcase,
  lib_err and invariant references migrated.
- **Phase 34 (2026-09-15)** — `concat(a, b)` builtin (17th): joins two
  lists into a new one. Deliberately a builtin rather than reopening `+`:
  the operator stays numbers-or-strings only, so `l + m` keeps erroring
  and the type story of `+` doesn't fork.
- **Phase 35 (2026-09-15)** — `map_equal(a, b)` builtin (18th):
  order-independent equality for `[[key, value], ...]` pair lists, the
  map idiom on top of plain lists (no dict type exists). Full spec was
  user-supplied: length mismatch → FALSE; each pair of a must find an
  equal pair in b; duplicate keys allowed; comparisons route through
  `roly_equal`. Same change, user decision: matching is multiset
  (consumed) — the first draft's non-consuming scan broke symmetry
  (`map_equal(a,b)` ≠ `map_equal(b,a)` on duplicate keys); the user
  supplied the comparison table proving consumed matching is the only
  symmetric, intuitive choice.
- **Phase 36 (2026-09-15)** — the `map` library module (26 pure-Roly
  functions): a hash map simulated over plain lists as `[[hash, key, box]]`
  sorted by hash, djb2/`mod` hashing in a 1000003 window, lower-bound
  binary search + linear probing over the collision chain, in-place upsert,
  hash-reusing ordered merge (right wins) and push-trick shape validation.
  Built on the five Phase 31–35 builtins (`ord`, `insert`, `delete_at`,
  `concat`, `map_equal`) exactly as the user planned — they were added for
  this module. Values are boxed in one-item lists because typed params
  cannot take "any value" (the user's put/put_str sketch); int keys get the
  `_i` family. `show` renders `{name: Ali, age: 31}` per the user's
  requested shape. Engineering comments are allowed in map.roly only
  (15.57).
- **Phase 37 (2026-09-15)** — duck-typed parameters (user decision: params
  accept anything, exactly like Python; the old strictness was a flaw, not
  a feature). `FnDef.params` became `list[str]`; a frame is
  `dict(zip(params, args))`. An optional `: type` annotation survives as
  pure decoration — still validated to be one of the five type names
  (unknown type stays a parse error), never enforced, old code runs
  unchanged. Type errors now surface at use sites
  (`operator '+' requires numeric operands`) instead of the call;
  `NativeFn` params (lists natives, thfile) KEEP their strict checks —
  host code cannot duck-type safely. map.roly collapsed the same day from
  26 to 16 functions: no boxing needed, one `map_set(m, k, v)` for every
  key/value type, hashing unified to djb2 over `str(key)` so every value
  type can be a key (identity follows `str()`: `7` ≠ `"7"`, `1` ≠ `1.0`).
- **Phase 38 (2026-09-18)** — hardening round: list rendering now emits
  every Roly string escape. `to_str`'s list branch routes string elements
  through `_escape_for_list` (`\\` first, then `\"`, `\n`, `\t`), so a
  printed list holding tabs/newlines/backslashes stays one re-lexable line
  instead of breaking the output (Phase 24 escaped `"` only). The one-line
  rule was widened to the remaining binding sites — the `if` after `else`
  (dropped with `else if` in Phase 40), the module name after
  `import`/`!import`, the import brace list, the
  member name after `.`, and the type after a parameter `:` — each pinned by
  a par_err test; and a lone identifier statement now reports the
  assignment fallback message instead of the misleading `'=' must follow`
  one (that message fires only when an `=`/compound operator really sits on
  the next line).
- **Phase 39 (2026-09-18)** — `map_merge` fix (15.60): duplicate detection
  now scans the full equal-hash chain in the right input, so colliding keys
  like `7`/`"7"` merge right-wins with no phantom extra entry; verified via
  CLI probes (collision pairs, disjoint and empty sides, 15-key overlap).
- **Phase 40 (2026-09-18)** — `else if` removed (user decision): `if` takes
  at most one optional `else` block; chains nest an `if` inside `else` and
  pay real parser depth. Touched: parser (`parse_if`), `If` node (`elifs`
  field deleted), compiler branch, grammar, guide, the par_err pin
  (`expected '{', got 'if'`), and the rolypip/invariant programs that used
  ladders (rewritten as nested `else { if ... }`).

## 17. Tests & Maintenance Rules

### Test philosophy (user rules, 2026-09-12)

- Tests assert ERRORS ONLY — the right exception class and message. Never
  program values, printed output, final env, or AST shapes.
- Minimal volume: the whole suite stays small enough for an agent to read
  every file. Currently 7 files / ~145 tests.
- A test is written only when forced to debug something. No speculative
  coverage.
- `smoke.py` is the exception: every `syntax/*.roly` and
  `tests/rolypip/**/*.roly` must run with no error (glob-discovered).
- `invariantTests/invariants.py` is the second exception: it asserts
  OUTPUT. Fixed deterministic battery of invariant programs over the whole
  language (arithmetic/string/list/boolean laws, control flow, recursion vs
  iteration, metamorphic transformations — dead code, renaming, reordering,
  `;` form — determinism, library laws, rendering, conversion round-trips,
  evaluation order). Each program prints its computed result; the test
  compares captured output against the expected lines. Any error, traceback
  or mismatch in these valid programs signals a possible engine bug.
- Correctness is verified through the real CLI:
  `.venv/bin/python roly.py run file.roly` / `roly.py exec "code"`.
- `pytest.ini`: `testpaths = tests`, `python_files = *.py` (no `test_` file
  prefix; test functions still use `test_`).

| File | Covers |
|---|---|
| `lex_err.py` | lexer errors (bad chars, unterminated strings, bad escapes) |
| `par_err.py` | parse errors (structure, nesting, one-line rule, reserved words) |
| `run_err.py` | runtime errors (types, division, undefined names, limits, builtins) |
| `lib_err.py` | lib rejections (guards, types, arity), `!import` errors, unimported-use errors, thfile errors |
| `mod_err.py` | module errors (circular, members, collisions, isolation, wrapping) |
| `cli_err.py` | CLI surface errors (bad usage, missing files) |
| `smoke.py` | every showcase program runs clean |
| `invariantTests/invariants.py` | output-comparison invariants over valid programs (the value-asserting exception) |

### Adding a builtin — checklist

1. Implementation + `BUILTINS` entry in `roly/builtins.py`.
2. Arity in `BUILTIN_ARITIES` — or deliberately absent if variadic.
3. If type-like: `TYPE_TOKENS` in `roly/tokens.py` + parser atom handling.
4. Name-collision sweep: keywords, lib files, and `fn <name>` across tests/,
   syntax/, tests/rolypip/ (the `fn get`/`fn set` incident).
5. Error-path test appended to the matching `*_err.py` file.
6. Guide entry.

### Adding a lib function — checklist

1. Goes in the matching `roly/lib/<topic>.roly` (math/fmt/strings/
   lists) — declare cross-deps with `!import` at the top (15.45).
2. Must pass the design rule: real logic only, no one-liners.
3. Reject invalid input with `fail("...")` — never return a wrong answer.
4. Reuse existing lib fns and builtins (`mod()` for remainders, string
   width via `len(str(n))`).
5. If it's a hot path, consider a `NativeFn` in `roly/stdlib.py` instead —
   register it in `NATIVE_MODULE_FNS`, error messages reproduced
   bit-for-bit (15.35).
6. Guide + a rolypip showcase (add the `!import` line).

### Adding a keyword / operator / statement — checklist

1. `roly/tokens.py`: `T` member + `KEYWORDS`/operator map.
2. `roly/lexer.py` tables if it's an operator.
3. `grammar` file first (it is authoritative — update it BEFORE the parser).
4. `roly/ast.py` node + `roly/parser.py` production (mind `loop_depth`,
   `fn_depth`, `bracket_depth`, top-level-only rules).
5. `roly/compiler.py`: both sides (expression and/or statement branch),
   statement branches open with `count_step()`.
6. Guide + `syntax/*.roly` example (smoke auto-covers it).
7. Error tests for every new rejection message.

### Adding an AST node

`ast.py` + parser producer + compiler consumer, in one change. There is no
second evaluator to forget — the compiler is the only consumer.

### Touching the compiler — parity checklist

Steps counted once per statement execution; arity before argument
evaluation; compound-assign order; byte-identical error messages; spines
loop-compiled. Re-run the full suite and spot-check via the CLI.

### Conventions

- No comments or docstrings in code — rationale lives here (15.40). The
  single exception: `roly/lib/map.roly` (15.57).
- Commit style: grouped section commits, short sentence, no signature.
- File extension `.roly`. Pipeline dependency is stdlib-only; pytest and
  PyInstaller are dev-only.

## 18. CLI & Standalone Executable

**CLI** (`roly.py`): `run file.roly` and `exec "inline code"`. Runs through
`run_source` with `base_dir`/`entry_path` set from the file so module
resolution works. Only program `print()` output goes to stdout; errors print
`error: {msg}` to stderr and exit 1; entry-file read failures (missing,
unreadable, non-UTF-8) print `error: cannot read '{file}': {reason}` via
`stdlib._io_reason`; `BrokenPipeError` is swallowed by
redirecting stdout to devnull (safe `| head` usage).

**Build** (`python build.py [--clean]`): thin argparse over `builder/` —
- `platform.py`: `exe_name()` → `roly.exe` on Windows, `roly` elsewhere.
- `engine.py`: `pyinstaller_command` is testable data; `run_pyinstaller`
  passes explicit `--distpath`/`--workpath`/`--specpath` so cwd doesn't
  matter.
- `libs.py`: `sync_lib` — rmtree + copytree of `roly/lib/` into the dist
  (the lib is NOT bundled by PyInstaller; 15.38).
- Builds are platform-native: build on the target OS. `*.spec` is gitignored.
- PyInstaller 6.22.2 is a dev dependency in `.venv`.

---

Maintained alongside the source code: any change to lexer, parser, compiler,
interpreter, builtins, lib, modules or build must update the matching
section, gotcha or checklist here in the same change.
