import sys


def is_windows():
    return sys.platform.startswith("win")


def exe_name():
    return "roly.exe" if is_windows() else "roly"
