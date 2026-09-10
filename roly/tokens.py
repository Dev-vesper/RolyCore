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
    FN = auto()
    RETURN = auto()
    INT_TYPE = auto()
    STR_TYPE = auto()
    BOOL_TYPE = auto()
    LIST_TYPE = auto()
    TRUE = auto()
    FALSE = auto()
    IMPORT = auto()
    COLON = auto()
    COMMA = auto()
    DOT = auto()
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
    "fn": T.FN,
    "return": T.RETURN,
    "int": T.INT_TYPE,
    "str": T.STR_TYPE,
    "bool": T.BOOL_TYPE,
    "list": T.LIST_TYPE,
    "TRUE": T.TRUE,
    "FALSE": T.FALSE,
    "import": T.IMPORT,
}

TYPE_TOKENS = {
    T.INT_TYPE: int,
    T.STR_TYPE: str,
    T.BOOL_TYPE: bool,
    T.LIST_TYPE: list,
}
