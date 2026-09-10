import subprocess
import sys

from builder.platform import exe_name


def pyinstaller_command(root, dist):
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(dist),
        "--workpath",
        str(root / "build"),
        "--specpath",
        str(root),
        "--name",
        exe_name(),
        str(root / "roly.py"),
    ]


def run_pyinstaller(root, dist):
    subprocess.run(pyinstaller_command(root, dist), check=True)
    return dist / exe_name()
