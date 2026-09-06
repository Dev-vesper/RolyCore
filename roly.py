#!/usr/bin/env python3

import argparse
import sys


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
        with open(args.file, encoding="utf-8") as source_file:
            source = source_file.read()
    else:
        source = args.code

    print(f"Roly: received {len(source)} characters of source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
