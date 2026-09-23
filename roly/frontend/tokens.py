from dataclasses import dataclass
from enum import Enum, auto


class T(Enum):
    INT = auto()
    FLOAT = auto()
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
    FLOAT_TYPE = auto()
    FILE_TYPE = auto()
    TRUE = auto()
    FALSE = auto()
    IMPORT = auto()
    BANG = auto()
    COLON = auto()
    COMMA = auto()
    DOT = auto()
    SEMI = auto()
    ELLIPSIS = auto()
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
    LBRACKET = auto()
    RBRACKET = auto()
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
    "float": T.FLOAT_TYPE,
    "file": T.FILE_TYPE,
    "TRUE": T.TRUE,
    "FALSE": T.FALSE,
    "import": T.IMPORT,
}

TYPE_TOKENS = {
    T.INT_TYPE,
    T.STR_TYPE,
    T.BOOL_TYPE,
    T.LIST_TYPE,
    T.FLOAT_TYPE,
    T.FILE_TYPE,
}
