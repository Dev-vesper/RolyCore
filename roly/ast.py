from dataclasses import dataclass
from typing import Union

Expr = Union["Num", "Str", "Bool", "Neg", "Var", "BinOp", "Chain", "Call", "ModuleVar", "ModuleCall", "Subscript", "ListLit"]
Statement = Union[
    "Assign",
    "CompoundAssign",
    "If",
    "While",
    "Print",
    "Break",
    "Continue",
    "Return",
    "FnDef",
    "Import",
    "Block",
    "ExprStmt",
]


@dataclass(slots=True)
class Num:
    value: int


@dataclass(slots=True)
class Str:
    value: str


@dataclass(slots=True)
class Bool:
    value: bool


@dataclass(slots=True)
class Neg:
    operand: Expr


@dataclass(slots=True)
class Var:
    name: str


@dataclass(slots=True)
class BinOp:
    op: str
    left: Expr
    right: Expr


@dataclass(slots=True)
class Chain:
    operands: "list[Expr]"
    ops: "list[str]"


@dataclass(slots=True)
class Call:
    name: str
    args: "list[Expr]"


@dataclass(slots=True)
class Assign:
    name: str
    value: Expr


@dataclass(slots=True)
class CompoundAssign:
    name: str
    op: str
    value: Expr


@dataclass(slots=True)
class If:
    condition: Expr
    then_block: "Block"
    else_block: "Block | None"
    elifs: "list[tuple[Expr, 'Block']] | None" = None


@dataclass(slots=True)
class Print:
    value: Expr


@dataclass(slots=True)
class Break:
    pass


@dataclass(slots=True)
class Continue:
    pass


@dataclass(slots=True)
class While:
    condition: Expr
    body: "Block"


@dataclass(slots=True)
class Block:
    statements: "list[Statement]"


@dataclass(slots=True)
class ExprStmt:
    value: Expr


@dataclass(slots=True)
class Return:
    value: Expr


@dataclass(slots=True)
class FnDef:
    name: str
    params: "list[tuple[str, type]]"
    body: "Block"


@dataclass(slots=True)
class Import:
    module: str
    names: "list[str] | None"
    from_lib: bool = False


@dataclass(slots=True)
class ModuleVar:
    module: str
    name: str


@dataclass(slots=True)
class ModuleCall:
    module: str
    name: str
    args: "list[Expr]"


@dataclass(slots=True)
class Subscript:
    base: Expr
    index: Expr


@dataclass(slots=True)
class ListLit:
    items: "list[Expr]"


@dataclass(slots=True)
class Program:
    statements: "list[Statement]"
