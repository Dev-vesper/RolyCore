from roly.ast import (
    Assign,
    BinOp,
    Block,
    Break,
    CompoundAssign,
    Continue,
    If,
    Num,
    Print,
    Program,
    Str,
    Var,
    While,
)

DEFAULT_MAX_STEPS = 10_000_000


def _stdout_print(value):
    print(value)


class RolyError(Exception):
    pass


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class Interpreter:
    def __init__(self, max_steps=DEFAULT_MAX_STEPS, out=None):
        self.max_steps = max_steps
        self.steps = 0
        self.env = {}
        self.out = out if out is not None else _stdout_print

    def run(self, program):
        self.exec_statements(program.statements)
        return self.env

    def exec_statements(self, statements):
        for statement in statements:
            self.exec_statement(statement)

    def exec_statement(self, statement):
        self.count_step()
        if isinstance(statement, Assign):
            self.env[statement.name] = self.eval(statement.value)
        elif isinstance(statement, CompoundAssign):
            current = self.lookup(statement.name)
            operand = self.eval(statement.value)
            self.env[statement.name] = self.apply_op(statement.op, current, operand)
        elif isinstance(statement, If):
            if self.truthy(self.eval(statement.condition)):
                self.exec_statement(statement.then_block)
            elif statement.else_block is not None:
                self.exec_statement(statement.else_block)
        elif isinstance(statement, Block):
            self.exec_statements(statement.statements)
        elif isinstance(statement, Print):
            self.out(self.eval(statement.value))
        elif isinstance(statement, Break):
            raise BreakSignal()
        elif isinstance(statement, Continue):
            raise ContinueSignal()
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
                right = values.pop()
                left = values.pop()
                values.append(self.apply_op(item[1], left, right))
            elif isinstance(item, BinOp):
                work.append(("apply", item.op))
                work.append(item.right)
                work.append(item.left)
            elif isinstance(item, (Num, Str)):
                values.append(item.value)
            elif isinstance(item, Var):
                values.append(self.lookup(item.name))
            else:
                raise RolyError(f"cannot evaluate {item!r}")
        return values[-1]

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
        if name not in self.env:
            raise RolyError(f"undefined variable '{name}'")
        return self.env[name]

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
