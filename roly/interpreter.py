import sys
from pathlib import Path

from roly.ast import (
    Assign,
    BinOp,
    Block,
    Bool,
    Break,
    Call,
    Chain,
    CompoundAssign,
    Continue,
    ExprStmt,
    FnDef,
    If,
    Import,
    ListLit,
    ModuleCall,
    ModuleVar,
    Neg,
    Num,
    Print,
    Program,
    Return,
    Str,
    Subscript,
    Var,
    While,
)
from roly.builtins import BUILTINS, BUILTIN_ARITIES, list_get, roly_equal, text_char
from roly.errors import RolyError
from roly.lexer import LexError, Lexer
from roly.parser import ParseError, Parser
from roly.stdlib import lib_functions

DEFAULT_MAX_STEPS = 10_000_000
MAX_CALL_DEPTH = 200


def _stdout_print(value):
    print(value)


def _silent_out(value):
    pass


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
        self.execute_program(program)
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
        self.exec_statements(program.statements)

    def exec_statements(self, statements):
        for statement in statements:
            self.exec_statement(statement)

    def exec_statement(self, statement):
        self.count_step()
        if isinstance(statement, Assign):
            self.assign(statement.name, self.eval(statement.value))
        elif isinstance(statement, CompoundAssign):
            current = self.lookup(statement.name)
            operand = self.eval(statement.value)
            self.assign(
                statement.name, self.apply_op(statement.op, current, operand)
            )
        elif isinstance(statement, If):
            if self.truthy(self.eval(statement.condition)):
                self.exec_statement(statement.then_block)
            else:
                matched = False
                if statement.elifs is not None:
                    for condition, block in statement.elifs:
                        if self.truthy(self.eval(condition)):
                            self.exec_statement(block)
                            matched = True
                            break
                if not matched and statement.else_block is not None:
                    self.exec_statement(statement.else_block)
        elif isinstance(statement, Block):
            self.exec_statements(statement.statements)
        elif isinstance(statement, Print):
            self.out(self.eval(statement.value))
        elif isinstance(statement, ExprStmt):
            self.eval(statement.value)
        elif isinstance(statement, Break):
            raise BreakSignal()
        elif isinstance(statement, Continue):
            raise ContinueSignal()
        elif isinstance(statement, Return):
            raise ReturnSignal(self.eval(statement.value))
        elif isinstance(statement, FnDef):
            pass
        elif isinstance(statement, Import):
            self.execute_import(statement.module, statement.names)
        elif isinstance(statement, While):
            while self.truthy(self.eval(statement.condition)):
                try:
                    self.exec_statement(statement.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
        else:
            raise RolyError(f"cannot execute {statement!r}")

    def eval(self, expr):
        work = [expr]
        values = []
        while work:
            item = work.pop()
            if isinstance(item, tuple):
                if item[0] == "negate":
                    value = values.pop()
                    self.require_int("-", value)
                    values.append(-value)
                    continue
                if item[0] == "subscript":
                    index = values.pop()
                    base = values.pop()
                    values.append(self.subscript(base, index))
                    continue
                if item[0] == "listlit":
                    count = item[1]
                    items = [values.pop() for _ in range(count)]
                    items.reverse()
                    values.append(items)
                    continue
                right = values.pop()
                left = values.pop()
                values.append(self.apply_op(item[1], left, right))
            elif isinstance(item, BinOp):
                work.append(("apply", item.op))
                work.append(item.right)
                work.append(item.left)
            elif isinstance(item, Chain):
                values.append(self.eval_chain(item))
            elif isinstance(item, Neg):
                work.append(("negate",))
                work.append(item.operand)
            elif isinstance(item, Subscript):
                work.append(("subscript",))
                work.append(item.index)
                work.append(item.base)
            elif isinstance(item, ListLit):
                work.append(("listlit", len(item.items)))
                for element in reversed(item.items):
                    work.append(element)
            elif isinstance(item, (Num, Str, Bool)):
                values.append(item.value)
            elif isinstance(item, Var):
                values.append(self.lookup(item.name))
            elif isinstance(item, Call):
                values.append(self.call_function(item))
            elif isinstance(item, ModuleVar):
                values.append(self.read_module_var(item.module, item.name))
            elif isinstance(item, ModuleCall):
                values.append(
                    self.call_module_function(item.module, item.name, item.args)
                )
            else:
                raise RolyError(f"cannot evaluate {item!r}")
        return values[-1]

    def eval_chain(self, chain):
        left = self.eval(chain.operands[0])
        for op, operand in zip(chain.ops, chain.operands[1:]):
            right = self.eval(operand)
            if not self.truthy_bool(self.apply_op(op, left, right)):
                return False
            left = right
        return True

    def call_function(self, call):
        self.count_step()
        if call.name in BUILTINS:
            return self.call_builtin(call)
        if call.name not in self.functions:
            raise RolyError(f"undefined function '{call.name}'")
        function = self.functions[call.name]
        self.check_arity(call.name, function, call.args)
        args = [self.eval(arg) for arg in call.args]
        if isinstance(function, ModuleFunctionRef):
            return self.run_in_module(
                function.entry, call.name, function.function, args
            )
        return self.invoke_function(call.name, function, args)

    def check_arity(self, name, function, arg_exprs):
        if len(arg_exprs) != len(function.params):
            expected = len(function.params)
            raise RolyError(
                f"function '{name}' expects {expected} "
                f"argument{'s' if expected != 1 else ''}, got {len(arg_exprs)}"
            )

    def invoke_function(self, name, function, args):
        for (param_name, param_type), value in zip(function.params, args):
            if type(value) is not param_type:
                raise RolyError(
                    f"argument '{param_name}' of '{name}' must be "
                    f"{self.type_name(param_type)}, got {value!r}"
                )
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
            self.exec_statement(function.body)
        except ReturnSignal as signal:
            return signal.value
        finally:
            if is_lib:
                self.lib_depth -= 1
            self.call_depth -= 1
            self.locals_stack.pop()
            self.module_frames.pop()
        raise RolyError(f"function '{name}' did not return a value")

    def call_builtin(self, call):
        arity = BUILTIN_ARITIES.get(call.name)
        if arity is not None and len(call.args) != arity:
            raise RolyError(
                f"builtin '{call.name}' expects {arity} "
                f"argument{'s' if arity != 1 else ''}, got {len(call.args)}"
            )
        values = [self.eval(arg) for arg in call.args]
        return BUILTINS[call.name](*values)

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

    def call_module_function(self, module_name, member_name, arg_exprs):
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
        self.check_arity(member_name, function, arg_exprs)
        args = [self.eval(arg) for arg in arg_exprs]
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

    def apply_op(self, op, left, right):
        if op == "+":
            if type(left) is str and type(right) is str:
                return left + right
            self.require_int(op, left)
            self.require_int(op, right)
            return left + right
        if op in ("-", "*", "/"):
            self.require_int(op, left)
            self.require_int(op, right)
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if right == 0:
                raise RolyError("division by zero")
            return left // right
        if op in ("<", ">", "<=", ">="):
            self.require_int(op, left)
            self.require_int(op, right)
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            return left >= right
        if op == "==":
            return roly_equal(left, right)
        if op == "!=":
            return not roly_equal(left, right)
        raise RolyError(f"unknown operator '{op}'")

    def truthy(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        raise RolyError(f"condition must be a number, got {value!r}")

    def truthy_bool(self, value):
        if type(value) is bool:
            return value
        raise RolyError(f"comparison must produce a bool, got {value!r}")

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

    def require_int(self, op, value):
        if type(value) is not int:
            raise RolyError(
                f"operator '{op}' requires integer operands, got {value!r}"
            )

    def count_step(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise RolyError(
                f"step limit of {self.max_steps} exceeded (possible infinite loop)"
            )
