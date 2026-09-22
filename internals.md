# Roly — Language Internals

This document is the maintainer's map of Roly: how every piece works, why it
works that way, where the sharp edges are, and what has to be updated when
something changes. It is not a tutorial — `guide/index.html` is the user-facing
reference. The source code carries no comments or docstrings (project
convention), so the "why" lives here — the file is public and tracked in the
repository.

Facts below were verified against the source on 2026-09-22. When this document
and the code disagree, the code wins — then fix this document.

---

## 1. Project Layout & Module Responsibilities

| Path | Responsibility |
|---|---|
| `roly.py` | CLI entry point. `run file.roly` / `exec "code"`. Prints only program `print()` output; errors go to stderr as `error: {msg}` with exit code 1. Handles `BrokenPipeError` by redirecting stdout to devnull. |
| `roly/tokens.py` | `T` token enum, `Token` frozen dataclass (type/value/line/column), `KEYWORDS` map (17 entries), `TYPE_TOKENS` (int/str/bool/list/float/file). |
| `roly/lexer.py` | Hand-written scanner. Two-char/one-char operator tables, string escapes, `//` line comments, `sys.intern` on identifiers, ASCII-only identifier rule, line/column tracking. |
| `roly/parser.py` | Recursive-descent parser producing the AST. Owns the nesting limit, loop-depth and fn-depth tracking, the one-line rule, and all parse-time semantic checks. |
| `roly/ast.py` | 12 expression + 12 statement node types, all `@dataclass(slots=True)`. `If` is a two-branch node: `then_block` plus an optional `else_block`. `Member` is the single dot-access node (module member and built-in method alike). |
| `roly/errors.py` | `RolyError` only — the runtime error every other module imports. `LexError` lives in `lexer.py` (carries line/column) and `ParseError` in `parser.py` (carries the offending token). |
| `roly/builtins.py` | The 22 builtin implementations, `BUILTINS` dispatch dict, `BUILTIN_ARITIES`, `BUILTINS_WITH_INTERP` (the three that need the interpreter), the file-handle methods (`FILE_METHODS`/`FILE_METHOD_ARITIES`, `checked_method`, `member_value`), the `_io_reason`/`_io_fail` pair, `roly_equal`, `format_text`, list primitives. |
| `roly/stdlib.py` | Standard-library support: `resolve_lib_dir()` (frozen builds resolve next to the exe), the `NativeFn` class, the 3 native `lists` implementations, and `NATIVE_MODULE_FNS` mapping module names to their natives. Lib loading itself goes through the normal module machinery. |
| `roly/compiler.py` | Compiles the AST to nested Python closures. All evaluation logic lives here since the performance pass. |
| `roly/runtime.py` | Control-flow signals (`BreakSignal`/`ContinueSignal`/`ReturnSignal`), the `FileHandle` value type, and module wrappers (`ModuleEntry`/`ModuleAlias`/`ModuleFunctionRef`). Splits out to break the interpreter↔compiler import cycle. |
| `roly/interpreter.py` | `Interpreter`: program execution, function invocation, scoping, module machinery (load/import/context swap), step accounting, limits. |
| `roly/utils/runner.py` | `run_source()` — the single entry the CLI, tests and smoke all use. Wraps `RecursionError` into a clean depth message. |
| `roly/lib/*.roly` | The standard library itself: 5 modules — 49 pure-Roly functions in math/fmt/strings/lists/map — imported explicitly with `!import`. |
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
stack) was deleted in the performance pass. Do not resurrect it.

## 3. Grammar & Precedence

`grammar` is authoritative. Shape summary:

```
program     : (import | fn-decl | statement)*
statement   : assignment | compound-assign | if | while | print
            | break | continue | return | block
            | expression-statement        (call or member-call ONLY)
expression  : comparison
comparison  : additive ((== != < <= > >=) additive)*   ← Chain node only if ≥1 op
additive    : multiplicative ((+|-) multiplicative)*     ← iterative spine
multiplicative: unary ((*|/) unary)*                     ← iterative spine
unary       : '-' unary | primary
primary     : atom ('[' expression ']' | '.' IDENT call?)*  ← iterative postfix
atom        : INT | FLOAT | STRING | TRUE | FALSE | list-literal
            | IDENT call? | builtin-call | '(' expression ')'
```

(`-` is consumed in `parse_atom` and wraps `parse_primary`, so `-a[0]` is
`Neg(Subscript)` — the postfix binds first, as the unary rule above says.)

Precedence, loosest to tightest:

| Level | Forms | Notes |
|---|---|---|
| 1 | comparisons `== != < <= > >=` | flat chains, see §7 |
| 2 | `+ -` | numeric operands (int/float) or str+str for `+` |
| 3 | `* /` | `/` floors two ints, true division when either side is a float |
| 4 | unary `-` | `-a[0]` is `Neg(Subscript)` — postfix beats unary |
| 5 | postfix `()` `[]` `.` | call, subscript, member access; chains freely: `f()[0].x[1]`, `open("a", "r").read()` |

Assignment is a *statement*, never an expression. There are no `and`/`or`/`not`.

**The one-line rule.** An operator (binary or compound-assign `=`) and its
left-hand side must share a line. The parser tracks `prev_line` (line of the
last consumed token) and calls `require_same_line()` before every operator,
right operand, `[`, `(` and `.` — and at every other binding site: the member
name after `.`, the type after a parameter `:`, the module name after
`import`/`!import` and its whole brace list (after `{`, around each `,`,
before `}`), and the function name after `fn` must all stay on their line.
After every statement keyword, the `(` that opens `if`/`while`/`print` and a
function's parameter list must follow its keyword on the same line, and the
`{` that opens a required block must sit on its introducer's line
(`if (...)`, `else`, `while (...)`, `fn name(...)`) — a bare `{` statement,
having no introducer, is exempt. That check is a no-op while `bracket_depth >
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
(`self.pos -= 1`) and re-parses as an expression. Only `Call` nodes and
`Member` nodes *with* arguments survive as statements — `f()` and `mod.f()`
are legal lines, `1 + 2` and a bare `mod.f` / `f.read` are parse errors. This
is also why the rewind exists: statement-level parsing must not consume the
identifier before deciding.

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

Six value types, period: `int`, `str`, `bool`, `list`, `float`, `file`.

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
  A bool is not a number: `1 < TRUE` and `TRUE + 1` are runtime errors
  (`operator '<' requires numeric operands, got True`), not a quiet `1` —
  bools are not numbers in Roly even though they are in Python. The explicit
  doors are `int(TRUE)`/`float(TRUE)` (both `1`/`1.0`); `: type` annotations
  check nothing (§6), so they are not a third door.
- **str** is Python `str`. `+` concatenates str+str; `int + str` is an error.
- **list** is Python `list` but **immutable by discipline**: `push`/`set`
  return *new* lists and callers must rebind (`l = push(l, x)`). `l[i] = x`
  is a parse error and will stay one. No aliasing is possible in user code.
- **file** is `runtime.FileHandle` — an *open* or closed stream plus its
  path. Only `open(path, mode)` creates one (§9); it is a full value type:
  storable in lists, assignable, passable to functions, accepted by a
  `: file` annotation (cosmetic like every annotation), rendered as
  `file("path")` by `print`/`str`/`format`/list rendering (via the
  `to_str` fallback to `__repr__`). Equality is **identity** — both
  `roly_equal`'s strict-type fallback (`type(l) is type(r) and l == r`) and
  Python's default `==` give object identity, so two handles on the same
  path are different values. GC-wise a handle holds a Python file object
  and can never point back at a list, so the no-cycles assumption (§13)
  survives.

**Equality.** `==`/`!=` route through `roly_equal` — recursive structural
comparison where numbers compare by value across int and float
(`1 == 1.0`, `[1] == [1.0]`), everything else requires strict per-element
types: `[TRUE] != [1]`, `[[1,2]]` compares element-wise, and file handles
compare by identity. There is no ordering across types.

**Truthiness.** `truthy()` (interpreter.py:420) accepts: `bool` → itself,
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

1. **User functions** read and write their own call frame, then the frames
   captured lexically at their definition site (local fns only — §6), then
   globals. Never the caller's frame. (History: the first implementation was
   dynamically scoped — callees read and *wrote* caller frames, causing
   silent clobbering. The local-fn capture chain (§6) is not that model — it
   is fixed at the definition site, not the call site.)
2. **Lib functions** are module functions (imported via `!import`), so they
   see their own frame + their module's globals — never user globals. This
   module-machinery isolation replaced the old `lib_depth` frame lock, which
   fixed the original leak where `digit_sum`'s internal `s` overwrote a
   user's global `s`.
3. **Module functions** see their own frame + their module's globals. The
   `module_frames` stack records, per pushed frame, a *bool* — whether that
   frame belongs to a loaded module (`module_context is not None`) rather
   than the main program. A bare assignment inside a *user* fn is always
   local (there is no way to write a global from inside a user fn), while a
   module fn whose name exists in the module globals writes through to the
   module.

Lookup order: the frame chain — own frame, then captured frames innermost
first — → globals (with `ModuleAlias` unwrapping on read, §11). The
compiler's fast path (§12) inlines this when `locals_stack` is empty.

## 6. Functions

```
fn name (a, b) { ... return expr }
```

- Top level (like `import`) **or inside a function body at any block depth**
  (`fn_depth > 0`); a top-level `if`/`while` block still refuses, because
  pre-registration runs before conditions do. Bodies are blocks and cannot
  be empty (except the `{ ... }` placeholder).
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
- **Local fns bind at execution into the current frame.** A
  nested `fn` statement stores a `LocalFn(function, chain)` wrapper in
  `locals_stack[-1]`, where `chain` is the defining `frame_chain()` (its own
  frame plus the chain below it). No hoist: a call above the definition line
  is `undefined function`. `lookup`, `assign` and `call_compiled` walk the
  chain innermost-first, so a local fn calls siblings, calls itself
  (recursion) and reads AND writes the enclosing locals — lexical capture,
  never dynamic. Naming inside the frame is strict: over a bound fn →
  `function '{name}' already defined`, over a frame variable →
  `'{name}' is already a variable name`, assigning over it →
  `'{name}' is already a function name`; builtin and module names are
  refused as usual. Global names may be shadowed (params already do).
  Module fns are included — the chain holds frames only, so module globals
  still resolve through the normal swap.
- **Params are bare names** — `FnDef.params` is `list[str]`, a call frame is
  `dict(zip(params, args))`. Any value is accepted (Python duck typing);
  a type mismatch surfaces at the first operation that needs the value
  (`fn h (x) { return x + 0.5 } h("s")` → `operator '+' requires numeric
  operands`). An optional `: type` annotation is allowed and PURELY
  COSMETIC — parsed, validated to be one of the six type names (anything
  else stays a parse error), then dropped; old annotated code runs
  unchanged. Names must be unique (parse-time `duplicate parameter '{p}'`)
  and must not be builtin names (registration checks that one:
  `parameter '{p}' of '{f}' is a builtin and cannot be redefined`); a
  keyword can never get through — the parser matches `IDENT` for a
  parameter name.
- **Invocation order** (`call_compiled` → `invoke_function`), in exact order:
  1. `count_step()` — a call is a step.
  2. Builtins checked FIRST (`BUILTINS` before the user fn table — a user
     cannot shadow a builtin at runtime, and defining one is rejected at
     registration anyway); then the frame chain for a `LocalFn` (so a local
     fn shadows a global of the same name); then the global fn table.
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
  optional `else`. There is no `else if` (user decision): longer chains nest
  an `if` inside `else`, so a ladder now costs real parser depth against
  MAX_NESTING = 100.

## 9. Builtins (22) & File Methods

| Name | Arity | Behavior notes |
|---|---|---|
| `int(x)` | 1 | Strict grammar: optional sign + ASCII digits only — no whitespace, underscores, unicode digits. `int(TRUE)` → `1` allowed. Rejects lists. `int(float)` truncates toward zero; `int(inf)`/`int(nan)` → `cannot convert inf to int`. |
| `float(x)` | 1 | float passes through; `int`/`bool` convert (`float(7)` → `7.0`). Strings follow Python's grammar minus the exotic spellings: optional sign, digits with optional dot on either side (`"1."`/`".5"` convert), optional exponent — no whitespace, underscores, `inf`/`nan` spellings. Rejects lists. |
| `str(x)` | 1 | `str(TRUE)` → `"True"` (matches what `print` shows). Lists render Roly-style: `[1, "a"]` — string elements double-quoted and escaped with every Roly string escape (`\\`, `\"`, `\n`, `\t` — backslash FIRST so the added escapes don't re-escape; `_escape_for_list`), nested lists recursed. Floats render in Python's spelling (`1.5`, `inf`). |
| `bool(x)` | 1 | Python-style truthiness: `""`/`0` → `FALSE`, non-empty str/int → `TRUE`. Rejects lists. |
| `len(x)` | 1 | str or list; exact types. |
| `char(s, i)` | 2 | Both args exact types (str, int); 0-based; OOB runtime error. |
| `ord(c)` | 1 | Exact str type; must be exactly one character (empty or longer → error). Returns the Unicode code point — the inverse of indexing a single char out. |
| `chr(n)` | 1 | Exact int type (bools rejected like every numeric argument). The single character with code point `n` — the inverse of `ord`. A negative value, a value above `0x10FFFF`, or a surrogate (`0xD800`–`0xDFFF`) is a clean error; the surrogate guard exists because a lone surrogate would blow up at output time with a Python `UnicodeEncodeError`. |
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
| `format(...)` | variadic | `{}` sequential and `{n}` reusable positional placeholders; `{{`/`}}` escapes; mixing auto and manual numbering is an error; error messages are Roly's own (`format: cannot mix '{}' and '{n}' placeholders`). |
| `open(path, mode)` | 2 | Opens a file and returns a `file` handle. Mode is `"r"` (must exist), `"w"` (create/truncate), `"a"` (create, writes always append). Relative paths resolve against the entry program's directory. Needs the interpreter (path base) — see `BUILTINS_WITH_INTERP`. |
| `mkdir(path)` | 1 | Single-level directory creation (`parents=False`); `TRUE` on success, `mkdir: cannot make directory '<path>': <reason>` otherwise. |
| `list_dir(path)` | 1 | Sorted list of the entry names in a directory; `list_dir: cannot list '<path>': <reason>` otherwise. |

Dispatch rules that matter:

- `BUILTIN_ARITIES` drives arity checks; an **absent entry means variadic**
  (`format`, `list`). Arity is checked before arguments are evaluated.
- `BUILTINS_WITH_INTERP = {"open", "mkdir", "list_dir"}` — those three are
  called `BUILTINS[name](self, *values)`; every other builtin gets values
  only. Anything needing run context (here `I.entry_base_dir`) must come
  through that first argument (the same rule as `NativeFn`, 15.52).
- In the parser, `BUILTIN_NAMES` (the five type-named builtins) + `(` parse
  as builtin calls in `parse_atom`; bare `x = int` is a parse error (same
  treatment as a keyword). The sixth type name, `file`, has no call form —
  its token in a value slot is a parse error with its own message.
- Reading a builtin as a value fails honestly: `x = len` → `'len' is a
  builtin, not a value`.
- `format` is a host builtin on purpose: it was proven unwritable in pure
  Roly (no string disassembly + fixed typed arity). `len`/`char` are the two
  primitives that make every other string algorithm pure-Roly-expressible.

**File handles and methods** (they replaced the `thfile` module).

`f = open("a.txt", "w")` returns the one handle that owns the whole
lifecycle. Eleven methods, all dispatched through `checked_method`:

| Method | Arity | Behavior notes |
|---|---|---|
| `f.read()` | 0 | Everything from the current position to EOF, decoded UTF-8. Position ends at EOF; a second `read()` returns `""`. |
| `f.read_lines()` | 0 | Same as `read` then split: on `\n`, one trailing `\r` per line dropped, one trailing empty line dropped. Empty text → `[]`. |
| `f.write(s)` | 1 | Encodes UTF-8, writes at the position, advances, **flushes immediately** (so `copy`/`size`/another process see the bytes), returns `TRUE`. |
| `f.seek(i)` | 1 | Absolute 0-based **byte** offset; negative is `seek: offset -1 out of range`. Seeking past EOF is allowed (Python semantics). Returns `TRUE`. |
| `f.tell()` | 0 | Current byte offset. |
| `f.close()` | 0 | Closes the stream. Idempotent — closing twice is a no-op, not an error. Returns `TRUE`. |
| `f.exists()` | 0 | Path exists — works after close. |
| `f.size()` | 0 | `stat().st_size` — a raw **byte** count, so `size(f) != len(f.read())` for multi-byte UTF-8 or CRLF (they measure different things). |
| `f.rename(dst)` | 1 | Refuses when dst exists (`rename: 'b.txt' already exists`); moves the handle onto the new path, so `f.name`/`f.path` follow and `print(f)` shows the new name. |
| `f.copy(dst)` | 1 | `shutil.copyfile` — overwrites an existing dst (unlike rename). Works while the handle is open (every write is already flushed). |
| `f.delete()` | 0 | Closes the stream first, then unlinks — deterministic on Windows too. |

- **Stream model**: opened in *binary* mode (`r`→`rb+`, `w`→`wb+`, `a`→`ab+`)
  and encoded/decoded per operation, so `tell`/`seek` are honest byte
  offsets rather than opaque text cookies. The mode decides only whether the
  file must exist, is truncated, or appends (`a` = `O_APPEND`: writes land at
  EOF no matter where the position was seeked); the stream itself is
  unified, so `read` and `write` both work in every mode. A mid-character
  seek makes the next read a decode failure — the honest
  `read: cannot read 'f': the file is not valid UTF-8 text`.
- **After `close`** the path methods (`exists`, `size`, `rename`, `copy`,
  `delete`) still work and the value still prints; the stream methods raise
  `file is closed`. `rename`/`delete` close an open stream for you first.
- **Handles are path-bound snapshots**, not shared state: `f` and `g` opened
  on the same file are independent values (`f == g` is `FALSE` — identity),
  each with its own position; `f.delete()` leaves `g` open.
- **Error order** is receiver → method exists → arity → argument types, and
  arity is checked *before* the arguments evaluate (the effect-free-arity
  contract, 15.12). Inside a method the closed check precedes the argument
  type check.
- Messages: `method 'read' expects a file handle, got 'a.txt'`,
  `file has no method 'nope'`, `method 'write' expects 1 argument, got 0`,
  `method 'read' expects no arguments, got 1`,
  `method 'write' expects a str, got 1`, `file is closed`.
- A bare member read is always an error:
  `'read' is a method, call it as file("a.txt").read()` — the receiver is
  rendered with `repr(value)`, so a variable makes no difference to the
  wording and the message stays true for arbitrary receiver expressions.
  A non-handle receiver fails earlier, on the receiver check:
  `l.read` on a list is `method 'read' expects a file handle, got [1, 'a']`
  (Python repr, not Roly's `to_str` rendering).
- Absolute paths pass through; relative ones resolve against the entry
  program's directory (`I.entry_base_dir`, never the swapped `base_dir`).
  Directory creation has no undo (`delete` is file-only), so the rolypip
  showcase exercises `list_dir` but not `mkdir`.

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

Plus **3 native functions** (`NativeFn` in stdlib.py): the `lists` members
`sort_list`/`join`/`reverse_list`, injected for speed. `native_sort_list`
scans for non-number elements first purely so `join`'s
`operator '+' requires numeric operands` error surfaces bit-for-bit as
before (the scan admits floats alongside ints).

**File I/O lives in the core**: `open`/`mkdir`/`list_dir` are
builtins and the operations are methods, so no import is needed for files.
The semantics are documented in §9 (file handles and methods); two design
points worth the "why" here:

- The stream is opened in **binary mode** and encoded/decoded per operation
  instead of using Python's text mode with `newline=""` (which dropped CR
  bytes). Binary is what makes `seek`/`tell` mean *bytes*
  rather than opaque text cookies, and byte-faithful CRLF round-trips fall
  out for free. `size` stays `stat().st_size`, a byte count, so
  `size(f) != len(f.read())` for CRLF or multi-byte UTF-8 is expected —
  they measure different things.
- Decode failures are still the clean
  `read: cannot read '<name>': the file is not valid UTF-8 text`
  (`_io_reason`), and every failure is a `RolyError`, never a Python
  traceback.
- The **source** reads are a different code path and still use universal
  newlines: the entry read in `roly.py` and `load_module` in the interpreter.
  A raw CR inside a source string literal therefore becomes a line break →
  `unterminated string` (harmless in practice, and CRLF source files
  normalize cleanly). Only file-handle I/O is byte-faithful.

**map specifics** (the pure-Roly hash map — no dict type exists, a map IS a
plain list value):

- **Representation**: a list of `[hash, key, value]` entries kept sorted by
  hash. Hash window is `[0, 1000003)`; the hash is djb2
  (`h = h*33 + ord(c)` from 5381) over the key's `str()` rendering — so
  EVERY value type can be a key. Lookup mixes two layers: `_lower_bound`
  finds the equal-hash run, then `_find` compares keys with `==`. Both must
  agree for a hit, so `7`/`"7"` (same hash, `==` false) and `1`/`1.0`
  (`==` true, different hashes `"1"`/`"1.0"`) are each distinct keys —
  deliberate divergence from Python's hash-equality.
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
  deeper in the run (`7` vs `"7"`, 15.60).
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
  `is_palindrome`, ...) were pruned — they are user-writable.
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

- `import` and `!import` are keywords, **top-level only** (stricter than
  `fn`, which also nests inside function bodies). The
  `!` is allowed only immediately before `import`, on the same line; the
  parser enforces this with the same-line rule (`'import' must follow '!' on
  the same line`).
- **`!import` resolves ONLY the lib dir** (`stdlib.LIB_DIR`); `import`
  resolves ONLY `base_dir`. Neither falls back to the other. A program may
  not take the same name from both sources: `import math` + `!import math`
  → `'math' is already imported` (tracked via `ModuleEntry.from_lib`).
- **A module name is a third table** (`modules`) and follows the 15.54
  dual-check: it can never coexist with a value of the same name. Assigning
  over an imported module (global or local) is `'{name}' is already
  imported`; importing a name already bound as a value is `'{name}' is
  already a variable name` / `'{name}' is already a function name` — in
  both source orders, since `FnDef` pre-registration makes a later
  `fn name` visible to an earlier `import name` line.
- For `!import` of a module in `NATIVE_MODULE_FNS` (i.e. `lists`), the
  natives are injected into the module's function table right after a FRESH
  load only — never on a `module_cache` hit (a fixed bug: a second
  importer re-injected into the same entry and died on the `defined twice`
  guard). The guard itself still protects against a lib file defining a fn
  with a native's name. A native-only module needs an anchor `.roly` file in
  `roly/lib/` (comment-only is fine) or `!import` cannot find it (15.53).
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
- **`.` is resolved at RUN time, not parse time**. The parser
  cannot know what a name means — `import` may sit below the expression, and
  a fn body parses before later imports — so `a.b` is one `Member` node and
  the compiler's `f_member_chain` decides: a **plain name that is currently
  an imported module** takes the module path (`read_module_var` /
  `call_module_compiled`, all messages unchanged), everything else is a
  built-in method on the value. Consequence, accepted on purpose: `x = m.a`
  with an *unimported* `m` is now `undefined variable 'm'` (it used to be
  `module 'm' is not imported`) — the honest message for `f.read`-style
  typos, since the name might just as well have been a variable.
- **Top-level prints are discarded on load** (`out=_silent_out` swap) but
  later calls print normally.
- **Errors**: load-time errors are wrapped `error in module 'x': ...`
  (`error in library 'x': ...` for `!import`); errors from later calls are
  raw. Not-found is `module 'x' not found (looked for {path})` vs
  `library 'x' not found (looked for {path})`. Unreadable or non-UTF-8
  source is `cannot read module 'x': {reason}` with the reason from
  `builtins._io_reason` (15.55). Qualified module calls count steps.
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
- Module fns cannot see caller frames — visibility is the frame chain (own
  frame + the chain captured at the definition site, which is empty for a
  global/module fn) followed by the swapped-in globals; the caller's frame
  is simply not on that list. `module_frames` is a separate per-frame BOOL
  and governs only write-through vs local assignment (§5). The same bug
  family as the old lib leak, fixed the same way.
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
  time. `f_binchain` (BinOp), `f_subchain` (Subscript) and `f_member_chain`
  (Member) are accumulator loops instead. Any new left-associative or
  postfix construct MUST follow this pattern.
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
| GC | disabled during run | `gc.disable()` on entry, restored after. Values still cannot form cycles by themselves (no mutable lists, no first-class functions; a `FileHandle` only points at its path strings and its Python stream) with ONE exception: a `LocalFn` stored in a frame holds that frame chain, so a fn with captured locals is a real reference cycle — it stays uncollected for the rest of the run and is reclaimed when `run`'s `finally` re-enables GC. |

Other tunings: `@dataclass(slots=True)` on all AST nodes,
`sys.set_int_max_str_digits(0)`. (The gc collect/freeze after lib load was
dropped with the auto-load: `!import` happens mid-run while gc is disabled,
so the tuning was moot.)

## 14. Error Reporting

Three exception classes, each defined where it is raised: `LexError` in
`lexer.py` (carries line/column), `ParseError` in `parser.py` (carries the
token; message shape `... got {describe(token)}`), and `RolyError` in
`errors.py` — the only one other modules import (everything runtime — with
the module wrapper adding `error in module 'x': ...` at load time only).

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
- File reads (CLI entry + module loads + `FileHandle.read`/`read_lines`):
  `cannot read ...: {reason}` from `builtins._io_reason` — strerror with the
  first letter lowercased, or `the file is not valid UTF-8 text` for decode
  failures. The helper lives in `builtins.py` because it is the lowest module
  both `interpreter.py` and `roly.py` can import.
- Methods: `expects a file handle`, `file has no method 'x'`,
  `'x' is a method, call it as {owner}.x()` — receiver, method-exists, arity
  and then argument types, in that order. Stream methods add
  `file is closed`; `open` adds `mode must be "r", "w" or "a"`.

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
identifier isn't followed by `=`. This rewind is why the statement whitelist
lives after the peek — only a `Call` or a `Member` with a non-None `args`
list may stand as an expression statement.

15.4 Builtin call parsing keys off `parser.BUILTIN_NAMES` + `(` in
`parse_atom` — a five-entry table of the type-named builtins
(`int/str/bool/list/float`), NOT all of `TYPE_TOKENS`. A new builtin that is
also a type name needs an entry in BOTH (`BUILTIN_NAMES` here,
`TYPE_TOKENS` for annotations), or `x = int`-style parse handling diverges.
Type names are not values: the `file` token in an expression slot is a
parse error (`'file' is a type, not a value — open(path, mode) returns a
file handle`); the annotation check also reads `TYPE_TOKENS`, so a new type
name is one edit in `tokens.py` plus whatever the parser needs.

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

15.13 **BinOp spines, Subscript chains and Member chains must compile to
loop-based closures** (`f_binchain`/`f_subchain`/`f_member_chain`). Nested
closures = RecursionError on long flat expressions at run time, far from the
cause. This is the single most important compiler invariant.

15.14 `fn_compiled` is keyed by `id(FnDef)`; the `(fn, body)` tuple holds a
strong ref so ids can't be recycled; hits require `cached[0] is function`.
Dropping the strong ref reintroduces an id-reuse bug.

15.15 `f_var`'s fast path uses a `MISS` sentinel — never `None`, `0` or
`""`, all of which are legal global values.

15.16 Compound-assign evaluation order (lookup → value → op → assign) is
observable through error ordering; it is deliberately identical to the old
interpreter's.

15.17 `BUILTINS` is checked *before* the user fn table at every call, and
registration rejects collisions — but the parser's reservation covers only
the five type-named builtins (`parser.BUILTIN_NAMES`); every other builtin
name is an ordinary IDENT at parse time, so `x = len` parses and fails at
run time. Three places must agree: parser reservation (the type-named
five), registration check (all 22 names), dispatch.

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

15.24 Circular-import detection is PATH-based: after the name/clash checks
and after `resolve_import_path`, `execute_import` tests the resolved path
against the `loading` stack (`if path in [p for _, p in self.loading]` —
the stack holds `(name, path)` pairs, hence the list comprehension). The
entry script is seeded into that stack via `entry_path` in `__init__`, which
is what stops a module from importing the main program.

15.25 Module top-level prints are discarded (`out=_silent_out`); the swap is
only active during the initial load run, not later calls.

15.26 One interpreter, one budget: alternating main/module calls can't
stack depth. Per-module interpreters would break this — rejected design.

15.27 Comparison chains short-circuit at the first false PAIR. `1 == 1 == 1`
is `TRUE`; before the fix it silently evaluated `(1 == 1) == 1` → `FALSE`.

15.28 `else if` does NOT exist (user decision): `if`
takes at most one optional `else` block and chains nest an `if` inside
`else`. The flat `If.elifs` list is gone with the syntax;
nested ladders pay real parser depth against MAX_NESTING = 100.

15.29 `break`/`continue` innermost-loop binding is a PARSE-time check
(`loop_depth`), and `ReturnSignal` naturally overrides both during
unwinding.

15.30 `int()`'s string grammar is deliberately strict (optional sign + ASCII
digits, nothing else). Do not "fix" it to accept whitespace — the strictness
is documented in the guide.

15.31 `str(TRUE)` is `"True"` (capital), matching `print`'s output — Python
parity, by decision.

15.32 `format` cannot mix `{}` and `{0}`; escapes are `{{`/`}}`; errors are
Roly's own (`format: cannot mix '{}' and '{n}' placeholders`). It is
variadic — therefore ABSENT from `BUILTIN_ARITIES` (absent = variadic is
the convention).

15.33 `MAX_NESTING` guards recursive descent (parens/blocks), not flat
spines. A 10k-term flat sum parses fine; `enter()` raises once the counter
goes past 100, so what matters is the PEAK — an enclosing construct holds
its slot while the nested one runs, including the innermost statement's own
`parse_expression`. From source: 99 nested parens parse and 100 fail
(`nesting too deep (limit is 100)`), 99 nested bare blocks parse and 100
fail, but only 98 nested `if` blocks inside a fn body — the innermost
condition adds one level on top of the fn body's own block.

15.34 `gc.disable()` during runs assumes values can't form cycles — true
except for local fns: a `LocalFn` in a frame holds the frame
chain, a cycle that survives the run until `run`'s `finally` re-enables GC
(§13 table). First-class functions or mutable lists would break the
assumption outright.

15.35 Native lib fns (`sort_list`/`join`/`reverse_list`) must reproduce the
old pure-Roly behavior bit-for-bit — ERRORS (the `native_sort_list`
non-number pre-scan exists so `join`'s `operator '+' requires numeric
operands` fires exactly as before) AND OUTPUT (`native_join` renders
elements through `to_str`, never Python `str` — Python renders `['a']`
single-quoted where Roly renders `["a"]`).
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

15.46 Native fns (`sort_list`/`join`/`reverse_list`) are injected into the
`lists` module after load and ONLY on the `from_lib` path AND only on a
fresh load — a `module_cache` hit must not re-inject (the double-import
bug). A user module named `lists` gets nothing, and a collision with a fn
the module itself defined raises "defined twice".

15.47 `stdlib.LIB_DIR` is read at `!import` time, never captured at Python
import time — that is what makes the missing-lib-dir test monkeypatchable.

15.48 A fn that falls off its body returns the `MISSING` sentinel from
`runtime.py` — NOT an exception. The error fires only where the value is
USED: `f_call`/`f_module_call` raise `did not return a value` unless the
call was compiled with `discard=True`, which only `ExprStmt` (a bare call
line) passes. The sentinel must never leak into a global, a list, or an
argument — every non-discard consumer checks it.

15.49 Empty blocks are rejected in `parse_block` at ONE place — every block
kind (fn, if, else, while, bare) flows through it. New block-shaped
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

15.52 **Host functions receive the interpreter**: the `NativeFn` call in
`invoke_function` and the `BUILTINS_WITH_INTERP` dispatch in the builtin
call path (`BUILTINS[name](self, *values)` for `open`/`mkdir`/`list_dir`)
both hand over the running `I`. Anything needing run context (path base,
limits) must come through that `I` — never from a module-level capture.
User file paths resolve against `I.entry_base_dir`, captured once in
`__init__` and never swapped; using `I.base_dir` instead would resolve user
paths into `roly/lib/` whenever a module fn is on the stack, because
`load_module`/`run_in_module` swap `base_dir` to the module's own directory.
Builtins without that membership set keep the plain `BUILTINS[name](*values)`
shape.

15.53 **Adding a native module** (the `lists` pattern): implementations live
in `roly/stdlib.py` next to the other natives (user rule: fold
features into existing files, do not create new Python modules), registered
in `NATIVE_MODULE_FNS`, plus an anchor `.roly` file in `roly/lib/` that can
be empty or comment-only — the module does not exist for `!import` without
the anchor. Arity/type checks come free through `NativeFn.params`. Errors
must be `RolyError`s carrying the full path, not Python tracebacks. FILE I/O
is deliberately NOT in this shape — it is core builtins plus methods (§9),
which is why `thfile` no longer exists.

15.54 **The two tables make every bind site a dual check**: functions and
variables live in separate dicts, and any code path that writes into one
table must first prove the name is absent from the other — `assign()` and
fn pre-registration do this, and brace binding in `execute_import` must
too (both directions, the split-brain fixes). The
hole appears exactly where a bind bypasses `assign()`; the fix is a
one-line globals lookup in the fn branch, not a redesign. The `modules`
table is a third table under the same rule: the module name is
bound only after `assign()`'s check would have refused it, so both bind
sites — `assign()` and the import's name bind — do the cross-table lookup.
Call frames are the fourth pairing under the same rule: a local
fn and a frame variable cannot share a name, refused from both sides —
binding and `assign()` walk the frame chain innermost-first.

15.55 **`UnicodeDecodeError` is a `ValueError`, not an `OSError`**: every
site that decodes a user file must catch it explicitly, or a non-UTF-8
file leaks a raw Python traceback. Three sites, one shared reason helper
(`builtins._io_reason`): the CLI entry read (`roly.py`), module loads
(`load_module`), and the file methods `read`/`read_lines`. Reusing the
helper also lowercases strerror everywhere, so read errors match the
language's lowercase message style.

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
sanctioned exception to the comment-free convention (user grant): the file
documents a data-structure simulation (hashing, probing, ordered merge)
whose rationale is not derivable from reading the code, and it is the
reference example of "a program a user could have written". Do not take
this as license to comment other files — their "why"
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

15.59 **Params duck-type, NativeFns do not**: user functions
accept any value and let the body fail at the operation that needs it,
but `invoke_function` still runs exact per-param checks on every
`NativeFn` — `sort_list("ab")` errors at the call, while a pure-Roly
`sum_list(["a"])` errors inside the loop. Both message families are
pinned by tests; do not "unify" them: host code cannot duck-type safely,
and lib guards depend on `fail()` inside the body. The annotation path
is also two-headed: `parse_parameter` validates `: type` against the six
known names (a typo like `: integr` stays a ParseError) and then drops
it — annotations are decoration, and the AST carries bare names only.

15.60 **`map_merge`'s duplicate check is chain-wide, not first-entry**:
entries sort by stored hash and `7` vs `"7"` collide (both render through
`str()`), so a right-side key match must scan the
entire equal-hash run — the first-entry version kept BOTH keys and the left
value won (`map_get` returned a's value with the phantom pair still in the
map), violating the documented right-wins merge. The fixed walk emits a's
non-duplicate entries in place and defers the whole b run to the next hash
boundary, so a deduplicated key survives only in b's entry.

15.61 **`.` is resolved at RUN time, not parse time**: the parser
cannot know whether `m.x` is a module member or a built-in method — a fn
body parses before any later `import` runs. `f_member_chain` therefore keys
on `owner in I.modules` (a plain-name base that is currently a module alias)
and routes to `read_module_var`/`call_module_compiled`; everything else goes
through `member_value`/`checked_method`. Consequence, accepted and pinned:
`x = m.a` on a name that was never imported is now `undefined variable 'm'`
(it used to say `module 'm' is not imported`). Do not "fix" the parser into
a static resolution — a body defined before its import must keep working.

15.62 **File handles are path-bound, stream-backed snapshots**: the
`FileHandle` carries `path`/`name`/`base` plus an optional Python stream.
`close()` drops the stream but leaves the path methods alive; `rename`
rebinds `path`/`name` so the same handle keeps addressing the (moved) file,
and any OTHER handle still points at the old path. `open` always creates
the file in `"w"`/`"a"` — there is no "only if missing" mode, so `exists()`
before a write-mode open is always FALSE after it. `delete`/`rename`/`size`
work on closed handles; `read`/`write`/`seek`/`tell`/`read_lines` do not.
There is no `rmdir` — `mkdir` is create-only and that is the whole
directory surface.

15.63 **`close()` is idempotent and `delete()` closes first**: calling
`close()` twice is legal — no error, no state change — and `delete()`
silently closes an open stream before unlinking so a handle
never leaks a file descriptor. `seek` and `tell` are BYTE offsets (Python
parity), so `tell()` after a multi-byte write is the encoded length, and a
seek into the middle of a UTF-8 character surfaces the honest decode error
on the next read rather than being rounded.

15.64 Local fns capture lexically at the definition site: the
`LocalFn` wrapper stores the defining `frame_chain()` — own frame plus the
chain below it, never the caller's frame. Binding happens when the
statement executes (no hoist: a call above the line is `undefined
function`), a frame name binds once (strict), and `lookup`/`assign`/
`call_compiled` walk the chain innermost-first — reading a `LocalFn` as a
value raises `'{name}' is a function, call it as {name}(...)`.
`invoke_function` gained the `chain` argument; arity-before-args, step
accounting and the depth-200 guard are shared with global fns. One asymmetry
to know: `local_fn()` walks the chain and SKIPS non-`LocalFn` bindings, so a
parameter named like an outer local fn shadows the READ
(`print(g)` shows the parameter) while the CALL still reaches the enclosing
`LocalFn` — binding a value and calling the same name resolve differently.

## 16. Design Decisions & Rationale

The choices that still shape the language, each with the reason it was made —
reversing one means reversing its reason first. The dated record of when each
change landed lives in `git log`; this file keeps the "why".

**Surface & semantics**

- **Braces never restrict** module members: the first design was a whitelist
  and the user corrected it; every member stays reachable as `name.member`
  (§11).
- **No `else if`**: `if` takes one optional `else` block and longer ladders
  nest — the flat `elifs` list was deleted with the syntax (§8).
- **Comparisons are real chains** (`Chain` AST), not `(a < b) and (b < c)`
  re-association — `1 == 1 == 1` used to silently evaluate `FALSE` (§7).
- **A fn falling off its body yields the `MISSING` sentinel**, never an
  exception; the error belongs at the use site (15.48).
- **Empty blocks are parse errors**; `{ ... }` is the placeholder and `;` is
  the strict separator (15.49–15.51).
- **Lists are immutable by discipline** (callers rebind), indexing is
  0-based, and `concat` is a builtin rather than a widened `+` — `+` stays
  numbers-or-strings so its type story does not fork.
- **Floats are Python-parity by user decision**: promotion on mixed
  arithmetic, `/` floors only two ints, `float()` takes a strict string
  grammar, and the arithmetic ops turn `OverflowError` into a clean message
  (15.5, 15.7).
- **`input`'s prompt is required and str-typed, the return always str** —
  Python's optional prompt was deliberately not copied.
- **Params duck-type like Python** (the old strictness was a flaw, not a
  feature); `: type` stays decorative; `NativeFn` params keep exact checks
  because host code cannot duck-type safely (15.59).
- **No dict type exists**: `map` is a lib module over plain lists, and duck
  typing let its functions collapse to one `map_set(m, k, v)` /
  `map_get(m, k)` for every key/value type (§11).

**Structure & scope**

- **Functions are not first-class and are pre-registered** before execution,
  so recursion, mutual recursion and call-before-def all work (§6).
- **Scope is lexical, never dynamic** — the first implementation let callees
  read and write caller frames and silently clobbered them (§5).
- **One interpreter, one budget, one context swap**; per-module interpreters
  were rejected because alternating calls would multiply the effective
  depth/budget (§11).
- **The library is opt-in** (`!import`): it was auto-loaded first, and the
  `lib_depth` frame lock existed only to contain that design — both are gone,
  isolation is the module machinery (§5, §10).
- **Name collisions are refused strictly**, both directions and both source
  orders — the Rust/Go/JS answer, not Python's silent rebind (15.54).
- **File I/O lives in the core**: `thfile` was deleted for the `file` value
  type, its 11 methods and `open`/`mkdir`/`list_dir` (§9).

**Execution engine**

- **The tree-walking evaluator was deleted for the closure compiler** (~3.1x
  on the arith benchmark); spines compile to loops and gc is disabled during
  runs (§12, 15.34).
- **Natives are the escape hatch for hot paths and inject on a fresh load
  only** (15.46); they must reproduce the pure-Roly behavior bit-for-bit —
  errors and output alike (15.35).

## 17. Tests & Maintenance Rules

### Test philosophy (user rules)

- Tests assert ERRORS ONLY — the right exception class and message. Never
  program values, printed output, final env, or AST shapes.
- Minimal volume: the whole suite stays small enough for an agent to read
  every file. Currently 7 files / 155 tests.
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
  Semantics changes are additionally checked by differential fuzzing against
  Python (arithmetic, precedence, comparison chains, format, float edges)
  where the two languages are meant to agree.
- `pytest.ini`: `testpaths = tests`, `python_files = *.py` (no `test_` file
  prefix; test functions still use `test_`).

| File | Covers |
|---|---|
| `lex_err.py` | lexer errors (bad chars, unterminated strings, bad escapes) |
| `par_err.py` | parse errors (structure, nesting, one-line rule, reserved words) |
| `run_err.py` | runtime errors (types, division, undefined names, limits, builtins, file handles and their methods) |
| `lib_err.py` | lib rejections (guards, types, arity), `!import` errors, unimported-use errors |
| `mod_err.py` | module errors (circular, members, collisions, isolation, wrapping) |
| `cli_err.py` | CLI surface errors (bad usage, missing files) |
| `smoke.py` | every showcase program runs clean |
| `invariantTests/invariants.py` | output-comparison invariants over valid programs (the value-asserting exception) |

### Adding a builtin — checklist

1. Implementation + `BUILTINS` entry in `roly/builtins.py`.
2. Arity in `BUILTIN_ARITIES` — or deliberately absent if variadic.
3. If it needs the interpreter (path bases, limits), add it to
   `BUILTINS_WITH_INTERP` and give it the `(I, *values)` shape (15.52).
4. If it is also a type name: `TYPE_TOKENS` in `roly/tokens.py` AND
   `parser.BUILTIN_NAMES` (a type-only name like `file` is an explicit
   `parse_atom` branch instead, with its own message).
5. Name-collision sweep: keywords, lib files, and `fn <name>` across tests/,
   syntax/, tests/rolypip/ (the `fn get`/`fn set` incident).
6. Error-path test appended to the matching `*_err.py` file.
7. Guide entry — and bump the `counts` object at the end of
   `guide/index.html`: it fills every `<span data-count="keywords|builtins">`
   from that one place, so the prose lists stay free of hardcoded numbers.

### Adding a method — checklist

1. Implementation in `roly/builtins.py` with the `(handle, *args)` shape —
   the handle is always the first parameter; error messages name the method
   (`method 'x' expects ...`), never the receiver type only.
2. Register in `FILE_METHODS` and `FILE_METHOD_ARITIES`; the arity table is
   checked before arguments are evaluated (15.12), so a wrong arity must not
   reach the body.
3. Type checks inside the body are exact (`type(v) is not str`), and any
   stream access starts with `_require_stream` so `file is closed` wins over
   argument-type errors.
4. Error-path test in `run_err.py` (the file-method family).
5. Guide entry + the `grammar` member-call rule if the call shape changed.

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
6. Guide + `syntax/*.roly` example (smoke auto-covers it); a new keyword also
   bumps the `counts` object (see the builtin checklist).
7. Error tests for every new rejection message.

### Adding an AST node

`ast.py` + parser producer + compiler consumer, in one change. There is no
second evaluator to forget — the compiler is the only consumer.

### Touching the compiler — parity checklist

Steps counted once per statement execution; arity before argument
evaluation; compound-assign order; byte-identical error messages; spines
(BinOp, Subscript, Member) loop-compiled. Re-run the full suite and
spot-check via the CLI.

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
`builtins._io_reason`; `BrokenPipeError` is swallowed by
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
