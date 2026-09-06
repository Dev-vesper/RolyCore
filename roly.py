#!/usr/bin/env python3

import argparse
import sys

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
            print(f"error: cannot read '{args.file}': {error.strerror}", file=sys.stderr)
            return 1
    else:
        source = args.code

    try:
        run_source(source)
    except (LexError, ParseError, RolyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
