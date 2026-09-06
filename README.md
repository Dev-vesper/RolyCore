![Python](https://img.shields.io/badge/Python-3.13+-blue?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-9.1+-yellow?logo=pytest&logoColor=white)

# Running Roly

Roly is a tiny programming language implemented in pure Python with no runtime dependencies.

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

After execution, the CLI prints every final variable value as `name = value`, sorted by name. Anything printed with `print(...)` appears first, before the variable dump.

## Running the tests

```bash
.venv/bin/python -m pytest
```

The suite executes the real Roly programs in `syntax/` as part of the tests, so those files must stay in place.

## Notes

- Any Python 3.13+ interpreter works; no third-party packages are needed to run the language itself.
- Exit code is `0` on success and `1` on any lex, parse, or runtime error, with the error message (including line/column for lex and parse errors) written to stderr.
- There is a step limit (10,000,000 statements) protecting against infinite loops like `while (1) { }`.
- Integer division floors toward negative infinity: `7 / 2` is `3`.
