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
python -m venv .venv
.venv\Scripts\activate
python -m pip install pyinstaller
python build.py
```

The build writes the executable and the library folder to `dist/`:

| Platform | Executable | Library |
| --- | --- | --- |
| Linux / macOS | `dist/roly` | `dist/lib` |
| Windows | `dist\roly.exe` | `dist\lib` |

The `lib` folder must stay next to the executable — the engine loads the standard library from there at startup, and a missing folder is a clean error rather than a crash. Pass `--clean` (for example `python3 build.py --clean`) to remove `dist/` before building.

## Notes

- Any Python 3.13+ interpreter works; no third-party packages are needed to run the language itself.
- Exit code is `0` on success and `1` on any lex, parse, or runtime error, with the error message (including line/column for lex and parse errors) written to stderr.
- There is a step limit (10,000,000 executed statements and function calls) protecting against infinite loops like `while (1) { }`.
- Nesting of parentheses and blocks is limited to 100 levels; deeper programs fail with a clean parse error instead of a Python traceback.
- Integer division floors toward negative infinity: `7 / 2` is `3`.
