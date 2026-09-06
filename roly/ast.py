from dataclasses import dataclass
from typing import Union

Expr = Union["Num", "Str", "Var", "BinOp"]
Statement = Union["Assign", "CompoundAssign", "If", "While", "Print", "Block"]


@dataclass
class Num:
    value: int


@dataclass
class Str:
    value: str


@dataclass
class Var:
    name: str


@dataclass
class BinOp:
    op: str
    left: Expr
    right: Expr


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


@dataclass
class Print:
    value: Expr


@dataclass
class While:
    condition: Expr
    body: "Block"


@dataclass
class Block:
    statements: "list[Statement]"


@dataclass
class Program:
    statements: "list[Statement]"
