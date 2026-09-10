import argparse
import shutil
import sys
from pathlib import Path

from builder.engine import run_pyinstaller
from builder.libs import sync_lib
from builder.platform import exe_name

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="build",
        description="Build the standalone Roly executable.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove dist/ before building",
    )
    args = parser.parse_args(argv)

    if args.clean and DIST.exists():
        shutil.rmtree(DIST)
    run_pyinstaller(ROOT, DIST)
    sync_lib(ROOT / "roly" / "lib", DIST / "lib")
    print(f"built {DIST / exe_name()}")
    print(f"bundled libraries in {DIST / 'lib'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
