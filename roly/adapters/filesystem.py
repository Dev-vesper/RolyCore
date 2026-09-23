import shutil
from pathlib import Path


class FileSystem:
    def cwd(self):
        return Path.cwd()

    def is_absolute(self, path):
        return Path(path).is_absolute()

    def join(self, base, path):
        return Path(base) / path

    def parent(self, path):
        return path.parent

    def stem(self, path):
        return path.stem

    def absolute(self, path):
        return Path(path).resolve()

    def is_dir(self, path):
        return path.is_dir()

    def is_file(self, path):
        return path.is_file()

    def exists(self, path):
        return path.exists()

    def read_text(self, path):
        return path.read_text(encoding="utf-8")

    def open(self, path, mode):
        return path.open(mode)

    def mkdir(self, path):
        path.mkdir()

    def listdir(self, path):
        return sorted(entry.name for entry in path.iterdir())

    def stat_size(self, path):
        return path.stat().st_size

    def rename(self, source, target):
        source.rename(target)

    def unlink(self, path):
        path.unlink()

    def copy(self, source, target):
        shutil.copyfile(source, target)
