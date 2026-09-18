import operator

from roly.ast import (
    Assign,
    BinOp,
    Block,
    Bool,
    Break,
    Chain,
    Call,
    CompoundAssign,
    Continue,
    ExprStmt,
    FnDef,
    Float,
    If,
    Import,
    ListLit,
    ModuleCall,
    ModuleVar,
    Neg,
    Num,
    Print,
    Return,
    Str,
    Subscript,
    Var,
    While,
)
from roly.builtins import roly_equal, to_str
from roly.errors import RolyError
from roly.runtime import (
    BreakSignal,
    ContinueSignal,
    MISSING,
    ModuleAlias,
    ReturnSignal,
)

MISS = object()


def _require_number(op, value):
    if type(value) is not int and type(value) is not float:
        raise RolyError(f"operator '{op}' requires numeric operands, got {value!r}")


def op_add(I, a, b):
    if type(a) is str:
        if type(b) is str:
            return a + b
        raise RolyError(f"operator '+' requires numeric operands, got {a!r}")
    _require_number("+", a)
    _require_number("+", b)
    try:
        return a + b
    except OverflowError:
        raise RolyError("integer too large to convert to float")


def op_sub(I, a, b):
    _require_number("-", a)
    _require_number("-", b)
    try:
        return a - b
    except OverflowError:
        raise RolyError("integer too large to convert to float")


def op_mul(I, a, b):
    _require_number("*", a)
    _require_number("*", b)
    try:
        return a * b
    except OverflowError:
        raise RolyError("integer too large to convert to float")


def op_div(I, a, b):
    _require_number("/", a)
    _require_number("/", b)
    if b == 0:
        raise RolyError("division by zero")
    if type(a) is float or type(b) is float:
        try:
            return a / b
        except OverflowError:
            raise RolyError("integer too large to convert to float")
    return a // b


def _cmp_op(symbol, fn):
    def op(I, a, b):
        _require_number(symbol, a)
        _require_number(symbol, b)
        return fn(a, b)

    return op


OPS = {
    "+": op_add,
    "-": op_sub,
    "*": op_mul,
    "/": op_div,
    "<": _cmp_op("<", operator.lt),
    ">": _cmp_op(">", operator.gt),
    "<=": _cmp_op("<=", operator.le),
    ">=": _cmp_op(">=", operator.ge),
    "==": lambda I, a, b: roly_equal(a, b),
    "!=": lambda I, a, b: not roly_equal(a, b),
}


def compile_expression(node, discard=False):
    if isinstance(node, (Num, Float, Str, Bool)):
        value = node.value
        return lambda I: value
    if isinstance(node, Var):
        name = node.name

        def f_var(I):
            if not I.locals_stack:
                v = I.globals.get(name, MISS)
                if v is not MISS:
                    while type(v) is ModuleAlias:
                        v = v.entry.globals[v.name]
                    return v
            return I.lookup(name)

        return f_var
    if isinstance(node, Neg):
        operand = compile_expression(node.operand)

        def f_neg(I):
            v = operand(I)
            if type(v) is not int and type(v) is not float:
                raise RolyError(
                    f"operator '-' requires numeric operands, got {v!r}"
                )
            return -v

        return f_neg
    if isinstance(node, BinOp):
        spine = []
        item = node
        while isinstance(item, BinOp):
            spine.append(item)
            item = item.left
        base = compile_expression(item)
        pairs = []
        for part in spine:
            op_fn = OPS.get(part.op)
            if op_fn is None:
                raise RolyError(f"unknown operator '{part.op}'")
            pairs.append((op_fn, compile_expression(part.right)))
        pairs.reverse()

        def f_binchain(I):
            acc = base(I)
            for op_fn, right_fn in pairs:
                acc = op_fn(I, acc, right_fn(I))
            return acc

        return f_binchain
    if isinstance(node, Subscript):
        chain = []
        item = node
        while isinstance(item, Subscript):
            chain.append(item.index)
            item = item.base
        base = compile_expression(item)
        index_fns = [compile_expression(index) for index in chain]
        index_fns.reverse()

        def f_subchain(I):
            v = base(I)
            for index_fn in index_fns:
                v = I.subscript(v, index_fn(I))
            return v

        return f_subchain
    if isinstance(node, ListLit):
        items = [compile_expression(element) for element in node.items]

        def f_list(I):
            return [item(I) for item in items]

        return f_list
    if isinstance(node, Chain):
        first = compile_expression(node.operands[0])
        pairs = [
            (OPS[op], compile_expression(operand))
            for op, operand in zip(node.ops, node.operands[1:])
        ]

        def f_chain(I):
            left = first(I)
            for op_fn, operand_fn in pairs:
                right = operand_fn(I)
                v = op_fn(I, left, right)
                if type(v) is not bool:
                    raise RolyError(
                        f"comparison must produce a bool, got {v!r}"
                    )
                if not v:
                    return False
                left = right
            return True

        return f_chain
    if isinstance(node, ModuleVar):
        module = node.module
        name = node.name

        def f_module_var(I):
            return I.read_module_var(module, name)

        return f_module_var
    if isinstance(node, Call):
        name = node.name
        args = [compile_expression(arg) for arg in node.args]

        def f_call(I):
            v = I.call_compiled(name, args)
            if v is MISSING and not discard:
                raise RolyError(f"function '{name}' did not return a value")
            return v

        return f_call
    if isinstance(node, ModuleCall):
        module = node.module
        name = node.name
        args = [compile_expression(arg) for arg in node.args]

        def f_module_call(I):
            v = I.call_module_compiled(module, name, args)
            if v is MISSING and not discard:
                raise RolyError(f"function '{name}' did not return a value")
            return v

        return f_module_call
    raise RolyError(f"cannot evaluate {node!r}")


def compile_statement(statement, interp):
    if isinstance(statement, Assign):
        name = statement.name
        value = compile_expression(statement.value)

        def f_assign(I):
            I.count_step()
            I.assign(name, value(I))

        return f_assign
    if isinstance(statement, CompoundAssign):
        name = statement.name
        op_fn = OPS[statement.op]
        value = compile_expression(statement.value)

        def f_cassign(I):
            I.count_step()
            current = I.lookup(name)
            I.assign(name, op_fn(I, current, value(I)))

        return f_cassign
    if isinstance(statement, If):
        condition = compile_expression(statement.condition)
        then_fn = compile_statement(statement.then_block, interp)
        else_fn = (
            compile_statement(statement.else_block, interp)
            if statement.else_block is not None
            else None
        )

        def f_if(I):
            I.count_step()
            if I.truthy(condition(I)):
                then_fn(I)
                return
            if else_fn is not None:
                else_fn(I)

        return f_if
    if isinstance(statement, While):
        condition = compile_expression(statement.condition)
        body = compile_statement(statement.body, interp)

        def f_while(I):
            I.count_step()
            while I.truthy(condition(I)):
                try:
                    body(I)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        return f_while
    if isinstance(statement, Block):
        body = [compile_statement(s, interp) for s in statement.statements]

        def f_block(I):
            I.count_step()
            for fn in body:
                fn(I)

        return f_block
    if isinstance(statement, Print):
        value = compile_expression(statement.value)

        def f_print(I):
            I.count_step()
            I.out(to_str(value(I)))

        return f_print
    if isinstance(statement, ExprStmt):
        value = compile_expression(statement.value, discard=True)

        def f_expr(I):
            I.count_step()
            value(I)

        return f_expr
    if isinstance(statement, Break):

        def f_break(I):
            I.count_step()
            raise BreakSignal()

        return f_break
    if isinstance(statement, Continue):

        def f_continue(I):
            I.count_step()
            raise ContinueSignal()

        return f_continue
    if isinstance(statement, Return):
        value = compile_expression(statement.value)

        def f_return(I):
            I.count_step()
            raise ReturnSignal(value(I))

        return f_return
    if isinstance(statement, FnDef):

        def f_fndef(I):
            I.count_step()

        return f_fndef
    if isinstance(statement, Import):
        module = statement.module
        names = statement.names
        from_lib = statement.from_lib

        def f_import(I):
            I.count_step()
            I.execute_import(module, names, from_lib)

        return f_import
    raise RolyError(f"cannot execute {statement!r}")
