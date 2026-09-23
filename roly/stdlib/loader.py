import sys
from pathlib import Path


def resolve_lib_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "lib"
    return Path(__file__).resolve().parent / "modules"
