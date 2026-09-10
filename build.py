import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def main() -> int:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--clean",
            "--noconfirm",
            "--name",
            "roly.exe",
            str(ROOT / "roly.py"),
        ],
        check=True,
    )
    lib_target = DIST / "lib"
    if lib_target.exists():
        shutil.rmtree(lib_target)
    shutil.copytree(ROOT / "roly" / "lib", lib_target)
    print(f"built {DIST / 'roly.exe'}")
    print(f"bundled libraries in {lib_target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
