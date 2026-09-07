# test nvim editor
from roly.tokens import KEYWORDS, T, Token

TWO_CHAR_OPS = {
    "==": T.EQ,
    "!=": T.NE,
    "<=": T.LE,
    ">=": T.GE,
    "+=": T.PLUS_ASSIGN,
    "-=": T.MINUS_ASSIGN,
    "*=": T.STAR_ASSIGN,
    "/=": T.SLASH_ASSIGN,
}

ONE_CHAR_OPS = {
    "=": T.ASSIGN,
    "+": T.PLUS,
    "-": T.MINUS,
    "*": T.STAR,
    "/": T.SLASH,
    "<": T.LT,
    ">": T.GT,
    "(": T.LPAREN,
    ")": T.RPAREN,
    "{": T.LBRACE,
    "}": T.RBRACE,
    ":": T.COLON,
    ",": T.COMMA,
}

WHITESPACE = " \t\r\n"

DIGITS = "0123456789"

ESCAPES = {
    '"': '"',
    "\\": "\\",
    "n": "\n",
    "t": "\t",
}


class LexError(Exception):
    def __init__(self, message, line, column):
        self.line = line
        self.column = column
        super().__init__(f"line {line}, column {column}: {message}")


class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1

    def tokenize(self):
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.type is T.EOF:
                return tokens

    def next_token(self):
        self.skip_whitespace()
        start_line, start_column = self.line, self.column
        if self.pos >= len(self.source):
            return Token(T.EOF, None, start_line, start_column)

        char = self.source[self.pos]

        if char in DIGITS:
            return self.read_number(start_line, start_column)

        if char == '"':
            return self.read_string(start_line, start_column)

        if (char.isascii() and char.isalpha()) or char == "_":
            return self.read_identifier(start_line, start_column)

        pair = self.source[self.pos : self.pos + 2]
        if pair in TWO_CHAR_OPS:
            self.advance()
            self.advance()
            return Token(TWO_CHAR_OPS[pair], pair, start_line, start_column)

        if char in ONE_CHAR_OPS:
            self.advance()
            return Token(ONE_CHAR_OPS[char], char, start_line, start_column)

        raise LexError(f"unexpected character {char!r}", start_line, start_column)

    def read_number(self, start_line, start_column):
        start = self.pos
        while self.pos < len(self.source) and self.source[self.pos] in DIGITS:
            self.advance()
        text = self.source[start : self.pos]
        return Token(T.INT, int(text), start_line, start_column)

    def read_string(self, start_line, start_column):
        self.advance()
        chars = []
        while self.pos < len(self.source):
            char = self.source[self.pos]
            if char == '"':
                self.advance()
                return Token(T.STRING, "".join(chars), start_line, start_column)
            if char == "\n":
                raise LexError("unterminated string", start_line, start_column)
            if char == "\\":
                self.advance()
                if self.pos >= len(self.source):
                    raise LexError("unterminated string", start_line, start_column)
                escape_char = self.source[self.pos]
                if escape_char not in ESCAPES:
                    raise LexError(
                        f"unknown escape sequence '\\{escape_char}'",
                        start_line,
                        start_column,
                    )
                chars.append(ESCAPES[escape_char])
                self.advance()
            else:
                chars.append(char)
                self.advance()
        raise LexError("unterminated string", start_line, start_column)

    def read_identifier(self, start_line, start_column):
        start = self.pos
        while self.pos < len(self.source):
            char = self.source[self.pos]
            if not ((char.isascii() and char.isalnum()) or char == "_"):
                break
            self.advance()
        text = self.source[start : self.pos]
        return Token(KEYWORDS.get(text, T.IDENT), text, start_line, start_column)

    def skip_whitespace(self):
        while self.pos < len(self.source) and self.source[self.pos] in WHITESPACE:
            self.advance()

    def advance(self):
        if self.source[self.pos] == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1
