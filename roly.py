#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path

from roly.interpreter import RolyError
from roly.lexer import LexError
from roly.parser import ParseError
from roly.utils.runner import run_source


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="roly",
        description="Run Roly language files or inline code.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run a .roly source file")
    run_cmd.add_argument("file", help="Path to the Roly source file")

    inline_cmd = sub.add_parser("exec", help="Execute inline Roly code")
    inline_cmd.add_argument("code", help="Roly source passed as a string")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            with open(args.file, encoding="utf-8") as source_file:
                source = source_file.read()
        except OSError as error:
            try:
                print(f"error: cannot read '{args.file}': {error.strerror}", file=sys.stderr)
            except OSError:
                pass
            return 1
        source_path = Path(args.file).resolve()
    else:
        source = args.code
        source_path = None

    try:
        if source_path is not None:
            run_source(source, base_dir=source_path.parent, entry_path=source_path)
        else:
            run_source(source)
    except (LexError, ParseError, RolyError) as error:
        try:
            print(f"error: {error}", file=sys.stderr)
        except OSError:
            pass
        return 1
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
