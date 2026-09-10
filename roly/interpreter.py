import sys

from roly.ast import (
    Assign,
    BinOp,
    Block,
    Bool,
    Break,
    Call,
    CompoundAssign,
    Continue,
    FnDef,
    If,
    Neg,
    Num,
    Print,
    Program,
    Return,
    Str,
    Var,
    While,
)
from roly.builtins import BUILTINS
from roly.errors import RolyError

DEFAULT_MAX_STEPS = 10_000_000
MAX_CALL_DEPTH = 200


def _stdout_print(value):
    print(value)


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self, max_steps=DEFAULT_MAX_STEPS, out=None):
        self.max_steps = max_steps
        self.steps = 0
        self.globals = {}
        self.locals_stack = []
        self.functions = {}
        self.out = out if out is not None else _stdout_print
        self.call_depth = 0
        sys.setrecursionlimit(10_000)

    @property
    def env(self):
        if self.locals_stack:
            return self.locals_stack[-1]
        return self.globals

    def run(self, program):
        for statement in program.statements:
            if isinstance(statement, FnDef):
                if statement.name in self.functions:
                    raise RolyError(f"function '{statement.name}' already defined")
                self.functions[statement.name] = statement
        self.exec_statements(program.statements)
        return self.globals

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
        elif isinstance(statement, Break):
            raise BreakSignal()
        elif isinstance(statement, Continue):
            raise ContinueSignal()
        elif isinstance(statement, Return):
            raise ReturnSignal(self.eval(statement.value))
        elif isinstance(statement, FnDef):
            pass
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
                right = values.pop()
                left = values.pop()
                values.append(self.apply_op(item[1], left, right))
            elif isinstance(item, BinOp):
                work.append(("apply", item.op))
                work.append(item.right)
                work.append(item.left)
            elif isinstance(item, Neg):
                work.append(("negate",))
                work.append(item.operand)
            elif isinstance(item, (Num, Str, Bool)):
                values.append(item.value)
            elif isinstance(item, Var):
                values.append(self.lookup(item.name))
            elif isinstance(item, Call):
                values.append(self.call_function(item))
            else:
                raise RolyError(f"cannot evaluate {item!r}")
        return values[-1]

    def call_function(self, call):
        self.count_step()
        if call.name in BUILTINS:
            return self.call_builtin(call)
        if call.name not in self.functions:
            raise RolyError(f"undefined function '{call.name}'")
        function = self.functions[call.name]
        if len(call.args) != len(function.params):
            raise RolyError(
                f"function '{call.name}' expects {len(function.params)} "
                f"arguments, got {len(call.args)}"
            )
        args = [self.eval(arg) for arg in call.args]
        for (name, param_type), value in zip(function.params, args):
            if type(value) is not param_type:
                raise RolyError(
                    f"argument '{name}' of '{call.name}' must be "
                    f"{self.type_name(param_type)}, got {value!r}"
                )
        if self.call_depth >= MAX_CALL_DEPTH:
            raise RolyError(
                f"call depth of {MAX_CALL_DEPTH} exceeded "
                f"(possible runaway recursion)"
            )

        frame = dict(zip([name for name, _ in function.params], args))
        self.locals_stack.append(frame)
        self.call_depth += 1
        try:
            self.exec_statement(function.body)
        except ReturnSignal as signal:
            return signal.value
        finally:
            self.call_depth -= 1
            self.locals_stack.pop()
        raise RolyError(f"function '{call.name}' did not return a value")

    def call_builtin(self, call):
        if len(call.args) != 1:
            raise RolyError(
                f"builtin '{call.name}' expects 1 argument, "
                f"got {len(call.args)}"
            )
        return BUILTINS[call.name](self.eval(call.args[0]))

    def type_name(self, param_type):
        return {int: "int", str: "str", bool: "bool"}[param_type]

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
            return type(left) is type(right) and left == right
        if op == "!=":
            return not (type(left) is type(right) and left == right)
        raise RolyError(f"unknown operator '{op}'")

    def truthy(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        raise RolyError(f"condition must be a number, got {value!r}")

    def lookup(self, name):
        for scope in reversed(self.locals_stack):
            if name in scope:
                return scope[name]
        if name in self.globals:
            return self.globals[name]
        raise RolyError(f"undefined variable '{name}'")

    def assign(self, name, value):
        for scope in reversed(self.locals_stack):
            if name in scope:
                scope[name] = value
                return
        if name in self.globals or not self.locals_stack:
            self.globals[name] = value
        else:
            self.locals_stack[-1][name] = value

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
