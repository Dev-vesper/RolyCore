The purpose of this repository and the so-called programming language is to be used in another repository([CaseCode](https://github.com/Dev-vesper/CaseCode)) I'm working on. I also wanted to test submodules on GitHub, and to have a practice piece and portfolio item on my profile.

![Python](https://img.shields.io/badge/Python-3.13+-blue?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-9.1+-yellow?logo=pytest&logoColor=white)

# Running Roly

Roly is a tiny programming language implemented in pure Python with no runtime dependencies.

A complete single-page language guide (values, syntax, grammar, limits) is available at [guide/index.html](guide/index.html).

## Setup

Create a virtual environment and install the only dev dependency (pytest, needed only for running the test suite):

```bash
python3 -m venv .venv
.venv/bin/pip install pytest
```

## Running Roly code

Run a Roly source file (`.roly`):

```bash
.venv/bin/python roly.py run syntax/print_showcase.roly
```

Run inline code directly:

```bash
.venv/bin/python roly.py exec "x = 10 while (x > 0) { x -= 3 }"
```

After execution, the CLI prints only what the program prints with `print(...)` — final variable values are not dumped. Use `print(x)` to see a value.

## Running the tests

```bash
.venv/bin/python -m pytest
```

The suite executes the real Roly programs in `syntax/` as part of the tests, so those files must stay in place.

## Building the standalone executable

The engine can be packaged into a single executable with the standard library kept beside it as plain files. Executables are platform-native: build on the operating system you want to run it on.

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pyinstaller
python3 build.py
```

**Windows**

```bash
pip install pyinstaller
python build.py
```

The build writes the executable and the library folder to `dist/`:

| Platform | Executable | Library |
| --- | --- | --- |
| Linux / macOS | `dist/roly` | `dist/lib` |
| Windows | `dist\roly.exe` | `dist\lib` |

The `lib` folder must stay next to the executable — the engine loads the standard library from there when a program imports it with `!import`, and a missing folder is a clean error rather than a crash. Pass `--clean` (for example `python3 build.py --clean`) to remove `dist/` before building.

## Notes

- Any Python 3.13+ interpreter works; no third-party packages are needed to run the language itself.
- Exit code is `0` on success and `1` on any lex, parse, or runtime error, with the error message (including line/column for lex and parse errors) written to stderr.
- There is a step limit (10,000,000 executed statements and function calls) protecting against infinite loops like `while (1) { }`.
- Nesting of parentheses and blocks is limited to 100 levels; deeper programs fail with a clean parse error instead of a Python traceback.
- Integer division floors toward negative infinity: `7 / 2` is `3`.

## Using Roly as a library

The engine is a plain package — `import roly` and call `run_source`, no subprocess and no disk required if you supply the ports:

```python
import roly

out = []
roly.run_source('print("hi from " + str(2 * 21))', out=out.append)
print(out)  # ['hi from 42']
```

`run_source(source, ...)` takes the program as a string and returns the final global environment. Optional keywords: `max_steps`, `base_dir`, `entry_path`, plus the ports a host can replace — `out` (program output), `read_input` (the `input` prompt), `fs` (filesystem), `lib_dir` (where `!import` resolves), `native_fns` and `registry` (the builtin tables). Every one of them defaults to the real thing, so passing nothing behaves exactly like the CLI.

A custom port is any object with the right methods — for example an in-memory filesystem implementing `cwd`, `join`, `absolute`, `parent`, `stem`, `is_dir`, `is_file`, `exists`, `read_text`, `open`, `mkdir`, `listdir`, `stat_size`, `rename`, `unlink` and `copy`. Roly then never touches the disk:

```python
import roly

files = {"/mem/mod.roly": "fn twice (n: int) { return n * 2 }\n"}

class MemoryFS:
    def cwd(self): return "/mem"
    def is_absolute(self, path): return path.startswith("/")
    def join(self, base, path): return base + "/" + path
    def absolute(self, path): return path
    def parent(self, path): return path.rsplit("/", 1)[0]
    def stem(self, path): return path.rsplit("/", 1)[1].split(".")[0]
    def is_dir(self, path): return any(f.startswith(path + "/") for f in files)
    def is_file(self, path): return path in files
    def read_text(self, path): return files[path]

out = []
roly.run_source("import mod\nprint(mod.twice(21))", out=out.append, fs=MemoryFS())
print(out)  # ['42']
```

`roly` re-exports everything a host needs: `run_source`, `Interpreter`, `RolyError`, `LexError`, `ParseError`, `Registry`, `default_registry`, `FileSystem` and `terminal`. See "Ports & Embedding" in [internals.md](internals.md) for the port contracts and the layering rules that keep the core host-free.

## Internals

For a deep dive into the engine — architecture, module layout, design decisions, and the full evolution history — read [internals.md](internals.md).
