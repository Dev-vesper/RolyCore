class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class ModuleEntry:
    def __init__(self, name, path, globals, functions, imports):
        self.name = name
        self.path = path
        self.globals = globals
        self.functions = functions
        self.imports = imports


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
