import shutil


def sync_lib(source, target):
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return target
