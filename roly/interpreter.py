import gc
import sys
from pathlib import Path

from roly.ast import FnDef
from roly.builtins import BUILTINS, BUILTIN_ARITIES, list_get, text_char
from roly.compiler import compile_statement
from roly.errors import RolyError
from roly.lexer import LexError, Lexer
from roly.parser import ParseError, Parser
from roly.runtime import (
    ModuleAlias,
    ModuleEntry,
    ModuleFunctionRef,
    ReturnSignal,
)
from roly.stdlib import NativeFn, lib_functions

DEFAULT_MAX_STEPS = 10_000_000
MAX_CALL_DEPTH = 200


def _stdout_print(value):
    print(value)


def _silent_out(value):
    pass


class Interpreter:
    def __init__(self, max_steps=DEFAULT_MAX_STEPS, out=None, base_dir=None, entry_path=None):
        self.max_steps = max_steps
        self.steps = 0
        self.globals = {}
        self.locals_stack = []
        self.functions = dict(lib_functions())
        self.reserved = set(self.functions)
        self.builtin_names = set(BUILTINS)
        self.out = out if out is not None else _stdout_print
        self.call_depth = 0
        self.lib_depth = 0
        self.module_frames = []
        self.module_context = None
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        self.modules = {}
        self.module_cache = {}
        self.loading = []
        self.fn_compiled = {}
        if entry_path is not None:
            entry = Path(entry_path).resolve()
            self.loading.append((entry.stem, entry))
        sys.setrecursionlimit(10_000)

    @property
    def env(self):
        if self.locals_stack:
            return self.locals_stack[-1]
        return self.globals

    def run(self, program):
        gc_enabled = gc.isenabled()
        gc.disable()
        try:
            self.execute_program(program)
        finally:
            if gc_enabled:
                gc.enable()
        return {name: self.deref(value) for name, value in self.globals.items()}

    def deref(self, value):
        while isinstance(value, ModuleAlias):
            value = value.entry.globals[value.name]
        return value

    def execute_program(self, program):
        for statement in program.statements:
            if isinstance(statement, FnDef):
                if statement.name in self.builtin_names:
                    raise RolyError(
                        f"'{statement.name}' is a builtin "
                        f"and cannot be redefined"
                    )
                if statement.name in self.reserved:
                    raise RolyError(
                        f"function '{statement.name}' is reserved "
                        f"by the standard library"
                    )
                for param_name, _ in statement.params:
                    if param_name in self.builtin_names:
                        raise RolyError(
                            f"parameter '{param_name}' of '{statement.name}' "
                            f"is a builtin and cannot be redefined"
                        )
                    if param_name in self.reserved:
                        raise RolyError(
                            f"parameter '{param_name}' of '{statement.name}' "
                            f"is reserved by the standard library"
                        )
                if statement.name in self.functions:
                    raise RolyError(f"function '{statement.name}' already defined")
                self.functions[statement.name] = statement
        for statement in program.statements:
            compile_statement(statement, self)(self)

    def compiled_body(self, function):
        cached = self.fn_compiled.get(id(function))
        if cached is not None and cached[0] is function:
            return cached[1]
        body = compile_statement(function.body, self)
        self.fn_compiled[id(function)] = (function, body)
        return body

    def call_compiled(self, name, arg_fns):
        self.count_step()
        if name in BUILTINS:
            return self.call_builtin_compiled(name, arg_fns)
        if name not in self.functions:
            raise RolyError(f"undefined function '{name}'")
        function = self.functions[name]
        self.check_arity(name, function, arg_fns)
        args = [arg_fn(self) for arg_fn in arg_fns]
        if isinstance(function, ModuleFunctionRef):
            return self.run_in_module(
                function.entry, name, function.function, args
            )
        return self.invoke_function(name, function, args)

    def check_arity(self, name, function, args):
        if len(args) != len(function.params):
            expected = len(function.params)
            raise RolyError(
                f"function '{name}' expects {expected} "
                f"argument{'s' if expected != 1 else ''}, got {len(args)}"
            )

    def call_builtin_compiled(self, name, arg_fns):
        arity = BUILTIN_ARITIES.get(name)
        if arity is not None and len(arg_fns) != arity:
            raise RolyError(
                f"builtin '{name}' expects {arity} "
                f"argument{'s' if arity != 1 else ''}, got {len(arg_fns)}"
            )
        values = [arg_fn(self) for arg_fn in arg_fns]
        return BUILTINS[name](*values)

    def invoke_function(self, name, function, args):
        for (param_name, param_type), value in zip(function.params, args):
            if type(value) is not param_type:
                raise RolyError(
                    f"argument '{param_name}' of '{name}' must be "
                    f"{self.type_name(param_type)}, got {value!r}"
                )
        if isinstance(function, NativeFn):
            return function.callable(*args)
        if self.call_depth >= MAX_CALL_DEPTH:
            raise RolyError(
                f"call depth of {MAX_CALL_DEPTH} exceeded "
                f"(possible runaway recursion)"
            )

        frame = dict(zip([n for n, _ in function.params], args))
        is_lib = name in self.reserved
        module_fn = self.module_context is not None and not is_lib
        self.locals_stack.append(frame)
        self.module_frames.append(module_fn)
        self.call_depth += 1
        if is_lib:
            self.lib_depth += 1
        try:
            self.compiled_body(function)(self)
        except ReturnSignal as signal:
            return signal.value
        finally:
            if is_lib:
                self.lib_depth -= 1
            self.call_depth -= 1
            self.locals_stack.pop()
            self.module_frames.pop()
        raise RolyError(f"function '{name}' did not return a value")

    def execute_import(self, module_name, names):
        if module_name in [n for n, _ in self.loading]:
            chain = [n for n, _ in self.loading] + [module_name]
            raise RolyError(f"circular import: {' -> '.join(chain)}")
        entry = self.modules.get(module_name)
        if entry is None:
            path = (self.base_dir / f"{module_name}.roly").resolve()
            entry = self.module_cache.get(path)
            if entry is None:
                entry = self.load_module(module_name, path)
            self.modules[module_name] = entry
        if names is None:
            return
        self.validate_members(entry, module_name, names)
        for name in names:
            function = self.own_function(entry, name)
            if function is not None:
                existing = self.functions.get(name)
                if existing is not None and not isinstance(
                    existing, ModuleFunctionRef
                ):
                    raise RolyError(f"function '{name}' is already defined")
                self.functions[name] = self.module_function_ref(entry, function)
            if name in entry.globals:
                if name in self.functions and self.own_function(entry, name) is None:
                    raise RolyError(f"'{name}' is already a function name")
                self.globals[name] = ModuleAlias(entry, name)

    def own_function(self, entry, name):
        function = entry.functions.get(name)
        if function is not None and name not in self.reserved:
            return function
        return None

    def module_function_ref(self, entry, function):
        while isinstance(function, ModuleFunctionRef):
            entry = function.entry
            function = function.function
        return ModuleFunctionRef(entry, function)

    def validate_members(self, entry, module_name, names):
        for name in names:
            if self.own_function(entry, name) is None and name not in entry.globals:
                raise RolyError(f"module '{module_name}' has no member '{name}'")

    def load_module(self, module_name, path):
        if not path.is_file():
            raise RolyError(
                f"module '{module_name}' not found (looked for {path})"
            )
        self.loading.append((module_name, path))
        try:
            try:
                source = path.read_text(encoding="utf-8")
            except OSError as error:
                raise RolyError(
                    f"cannot read module '{module_name}': {error.strerror}"
                )
            try:
                tokens = Lexer(source).tokenize()
                program = Parser(tokens).parse()
            except (LexError, ParseError) as error:
                raise RolyError(f"error in module '{module_name}': {error}")
            module_globals = {}
            module_functions = dict(lib_functions())
            module_imports = {}
            entry = ModuleEntry(
                module_name,
                path,
                module_globals,
                module_functions,
                module_imports,
            )
            module_imports[module_name] = entry
            saved = (
                self.globals,
                self.functions,
                self.modules,
                self.base_dir,
                self.out,
                self.module_context,
            )
            self.globals = module_globals
            self.functions = module_functions
            self.modules = module_imports
            self.base_dir = path.parent
            self.out = _silent_out
            self.module_context = entry
            try:
                try:
                    self.execute_program(program)
                except RolyError as error:
                    raise RolyError(f"error in module '{module_name}': {error}")
            finally:
                (
                    self.globals,
                    self.functions,
                    self.modules,
                    self.base_dir,
                    self.out,
                    self.module_context,
                ) = saved
            self.module_cache[path] = entry
            return entry
        finally:
            self.loading.pop()

    def read_module_var(self, module_name, member_name):
        entry = self.modules.get(module_name)
        if entry is None:
            raise RolyError(f"module '{module_name}' is not imported")
        if member_name in entry.globals:
            return self.deref(entry.globals[member_name])
        if self.own_function(entry, member_name) is not None:
            raise RolyError(
                f"'{member_name}' is a function in module '{module_name}', "
                f"call it as {module_name}.{member_name}(...)"
            )
        raise RolyError(f"module '{module_name}' has no member '{member_name}'")

    def call_module_compiled(self, module_name, member_name, arg_fns):
        self.count_step()
        entry = self.modules.get(module_name)
        if entry is None:
            raise RolyError(f"module '{module_name}' is not imported")
        function = self.own_function(entry, member_name)
        if function is None:
            if member_name in entry.globals:
                raise RolyError(
                    f"'{member_name}' is not a function in module '{module_name}'"
                )
            raise RolyError(f"module '{module_name}' has no member '{member_name}'")
        while isinstance(function, ModuleFunctionRef):
            entry = function.entry
            function = function.function
        self.check_arity(member_name, function, arg_fns)
        args = [arg_fn(self) for arg_fn in arg_fns]
        return self.run_in_module(entry, member_name, function, args)

    def run_in_module(self, entry, name, function, args):
        saved = (
            self.globals,
            self.functions,
            self.modules,
            self.base_dir,
            self.module_context,
        )
        self.globals = entry.globals
        self.functions = entry.functions
        self.modules = entry.imports
        self.base_dir = entry.path.parent
        self.module_context = entry
        try:
            return self.invoke_function(name, function, args)
        finally:
            (
                self.globals,
                self.functions,
                self.modules,
                self.base_dir,
                self.module_context,
            ) = saved

    def type_name(self, param_type):
        return {int: "int", str: "str", bool: "bool", list: "list"}[param_type]

    def truthy(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        raise RolyError(f"condition must be a number, got {value!r}")

    def subscript(self, base, index):
        if type(base) is str:
            return text_char(base, index)
        return list_get(base, index)

    def lookup(self, name):
        if self.lib_depth > 0:
            frame = self.locals_stack[-1]
            if name in frame:
                return frame[name]
            raise RolyError(f"undefined variable '{name}'")
        if self.locals_stack:
            frame = self.locals_stack[-1]
            if name in frame:
                return frame[name]
        if name in self.globals:
            return self.deref(self.globals[name])
        if name in self.builtin_names:
            raise RolyError(f"'{name}' is a builtin, not a value")
        if name in self.functions:
            raise RolyError(f"'{name}' is a function, call it as {name}(...)")
        raise RolyError(f"undefined variable '{name}'")

    def assign(self, name, value):
        if name in self.builtin_names:
            raise RolyError(f"'{name}' is a builtin and cannot be redefined")
        if name in self.reserved:
            raise RolyError(f"name '{name}' is reserved by the standard library")
        if self.lib_depth > 0:
            self.locals_stack[-1][name] = value
            return
        if self.locals_stack:
            frame = self.locals_stack[-1]
            if name in frame:
                frame[name] = value
                return
            if not self.module_frames[-1] or name not in self.globals:
                frame[name] = value
                return
        self.globals[name] = value

    def count_step(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise RolyError(
                f"step limit of {self.max_steps} exceeded (possible infinite loop)"
            )
