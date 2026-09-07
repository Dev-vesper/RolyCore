from dataclasses import dataclass
from typing import Union

Expr = Union["Num", "Str", "Bool", "Neg", "Var", "BinOp", "Call"]
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
    "Block",
]


@dataclass
class Num:
    value: int


@dataclass
class Str:
    value: str


@dataclass
class Bool:
    value: bool


@dataclass
class Neg:
    operand: Expr


@dataclass
class Var:
    name: str


@dataclass
class BinOp:
    op: str
    left: Expr
    right: Expr


@dataclass
class Call:
    name: str
    args: "list[Expr]"


@dataclass
class Assign:
    name: str
    value: Expr


@dataclass
class CompoundAssign:
    name: str
    op: str
    value: Expr


@dataclass
class If:
    condition: Expr
    then_block: "Block"
    else_block: "Block | None"
    elifs: "list[tuple[Expr, 'Block']] | None" = None


@dataclass
class Print:
    value: Expr


@dataclass
class Break:
    pass


@dataclass
class Continue:
    pass


@dataclass
class While:
    condition: Expr
    body: "Block"


@dataclass
class Block:
    statements: "list[Statement]"


@dataclass
class Return:
    value: Expr


@dataclass
class FnDef:
    name: str
    params: "list[tuple[str, type]]"
    body: "Block"


@dataclass
class Program:
    statements: "list[Statement]"
