from dataclasses import dataclass
from enum import Enum, auto


class T(Enum):
    INT = auto()
    STRING = auto()
    IDENT = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    PRINT = auto()
    BREAK = auto()
    CONTINUE = auto()
    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    STAR_ASSIGN = auto()
    SLASH_ASSIGN = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: T
    value: object = None
    line: int = 1
    column: int = 1


KEYWORDS = {
    "if": T.IF,
    "else": T.ELSE,
    "while": T.WHILE,
    "print": T.PRINT,
    "break": T.BREAK,
    "continue": T.CONTINUE,
}
