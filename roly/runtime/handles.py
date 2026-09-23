MISSING = object()


class FileHandle:
    __slots__ = ("path", "name", "base", "stream")

    def __init__(self, path, name, base, stream):
        self.path = path
        self.name = name
        self.base = base
        self.stream = stream

    def __repr__(self):
        text = (
            self.name.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f'file("{text}")'


class ModuleEntry:
    def __init__(self, name, path, globals, functions, imports, from_lib=False):
        self.name = name
        self.path = path
        self.globals = globals
        self.functions = functions
        self.imports = imports
        self.from_lib = from_lib


class ModuleAlias:
    def __init__(self, entry, name):
        self.entry = entry
        self.name = name


class ModuleFunctionRef:
    def __init__(self, entry, function):
        self.entry = entry
        self.function = function

    @property
    def params(self):
        return self.function.params


class LocalFn:
    def __init__(self, function, chain):
        self.function = function
        self.chain = chain


class NativeFn:
    def __init__(self, params, callable):
        self.params = params
        self.callable = callable
