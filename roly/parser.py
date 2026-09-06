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
from roly.tokens import T

COMPOUND_OPS = {
    T.PLUS_ASSIGN: "+",
    T.MINUS_ASSIGN: "-",
    T.STAR_ASSIGN: "*",
    T.SLASH_ASSIGN: "/",
}

COMPARISON_OPS = {
    T.EQ: "==",
    T.NE: "!=",
    T.LT: "<",
    T.GT: ">",
    T.LE: "<=",
    T.GE: ">=",
}

ADDITIVE_OPS = {
    T.PLUS: "+",
    T.MINUS: "-",
}

MULTIPLICATIVE_OPS = {
    T.STAR: "*",
    T.SLASH: "/",
}

MAX_NESTING = 100


class ParseError(Exception):
    def __init__(self, message, token):
        self.token = token
        super().__init__(f"line {token.line}, column {token.column}: {message}")


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.depth = 0
        self.loop_depth = 0

    def parse(self):
        statements = self.parse_statements(T.EOF)
        return Program(statements)

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        token = self.tokens[self.pos]
        if token.type is not T.EOF:
            self.pos += 1
        return token

    def check(self, token_type):
        return self.current().type is token_type

    def match(self, token_type, expected):
        if self.check(token_type):
            return self.advance()
        raise ParseError(f"expected {expected}, got {self.describe(self.current())}", self.current())

    @staticmethod
    def describe(token):
        if token.value is None:
            return "end of input"
        return f"'{token.value}'"

    def enter(self):
        self.depth += 1
        if self.depth > MAX_NESTING:
            raise ParseError(
                f"nesting too deep (limit is {MAX_NESTING})", self.current()
            )

    def leave(self):
        self.depth -= 1

    def parse_statements(self, terminator):
        statements = []
        while not self.check(terminator):
            statements.append(self.parse_statement())
        return statements

    def parse_statement(self):
        token_type = self.current().type
        if token_type is T.IF:
            return self.parse_if()
        if token_type is T.WHILE:
            return self.parse_while()
        if token_type is T.PRINT:
            return self.parse_print()
        if token_type is T.BREAK:
            return self.parse_break()
        if token_type is T.CONTINUE:
            return self.parse_continue()
        if token_type is T.LBRACE:
            return self.parse_block()
        if token_type is T.IDENT:
            return self.parse_assignment()
        raise ParseError(
            f"expected a statement, got {self.describe(self.current())}",
            self.current(),
        )

    def parse_assignment(self):
        name_token = self.advance()
        token_type = self.current().type
        if token_type is T.ASSIGN:
            self.advance()
            return Assign(name_token.value, self.parse_expression())
        if token_type in COMPOUND_OPS:
            op = COMPOUND_OPS[token_type]
            self.advance()
            return CompoundAssign(name_token.value, op, self.parse_expression())
        raise ParseError(
            f"expected '=' or a compound assignment after '{name_token.value}', "
            f"got {self.describe(self.current())}",
            self.current(),
        )

    def parse_if(self):
        self.match(T.IF, "'if'")
        self.match(T.LPAREN, "'('")
        condition = self.parse_expression()
        self.match(T.RPAREN, "')'")
        then_block = self.parse_block()
        else_block = None
        if self.check(T.ELSE):
            self.advance()
            else_block = self.parse_block()
        return If(condition, then_block, else_block)

    def parse_break(self):
        token = self.advance()
        if self.loop_depth == 0:
            raise ParseError("'break' outside loop", token)
        return Break()

    def parse_continue(self):
        token = self.advance()
        if self.loop_depth == 0:
            raise ParseError("'continue' outside loop", token)
        return Continue()

    def parse_while(self):
        self.match(T.WHILE, "'while'")
        self.match(T.LPAREN, "'('")
        condition = self.parse_expression()
        self.match(T.RPAREN, "')'")
        self.loop_depth += 1
        body = self.parse_block()
        self.loop_depth -= 1
        return While(condition, body)

    def parse_print(self):
        self.match(T.PRINT, "'print'")
        self.match(T.LPAREN, "'('")
        value = self.parse_expression()
        self.match(T.RPAREN, "')'")
        return Print(value)

    def parse_block(self):
        self.enter()
        self.match(T.LBRACE, "'{'")
        statements = self.parse_statements(T.RBRACE)
        self.match(T.RBRACE, "'}'")
        self.leave()
        return Block(statements)

    def parse_expression(self):
        self.enter()
        node = self.parse_comparison()
        self.leave()
        return node

    def parse_comparison(self):
        node = self.parse_additive()
        while self.current().type in COMPARISON_OPS:
            op = COMPARISON_OPS[self.advance().type]
            node = BinOp(op, node, self.parse_additive())
        return node

    def parse_additive(self):
        node = self.parse_multiplicative()
        while self.current().type in ADDITIVE_OPS:
            op = ADDITIVE_OPS[self.advance().type]
            node = BinOp(op, node, self.parse_multiplicative())
        return node

    def parse_multiplicative(self):
        node = self.parse_primary()
        while self.current().type in MULTIPLICATIVE_OPS:
            op = MULTIPLICATIVE_OPS[self.advance().type]
            node = BinOp(op, node, self.parse_primary())
        return node

    def parse_primary(self):
        token = self.current()
        if token.type is T.INT:
            self.advance()
            return Num(token.value)
        if token.type is T.STRING:
            self.advance()
            return Str(token.value)
        if token.type is T.IDENT:
            self.advance()
            return Var(token.value)
        if token.type is T.LPAREN:
            self.advance()
            node = self.parse_expression()
            self.match(T.RPAREN, "')'")
            return node
        raise ParseError(
            f"expected a number, a string, an identifier, or '(', got {self.describe(token)}",
            token,
        )
