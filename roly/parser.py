from roly.ast import (
    Assign,
    BinOp,
    Block,
    Bool,
    Break,
    Call,
    Chain,
    CompoundAssign,
    Continue,
    ExprStmt,
    FnDef,
    If,
    Import,
    ListLit,
    ModuleCall,
    ModuleVar,
    Neg,
    Num,
    Print,
    Program,
    Return,
    Str,
    Subscript,
    Var,
    While,
)
from roly.tokens import TYPE_TOKENS, T

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

PARAM_TYPES = {
    T.INT_TYPE: int,
    T.STR_TYPE: str,
    T.BOOL_TYPE: bool,
    T.LIST_TYPE: list,
}

BUILTIN_NAMES = {
    T.INT_TYPE: "int",
    T.STR_TYPE: "str",
    T.BOOL_TYPE: "bool",
    T.LIST_TYPE: "list",
}


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
        self.fn_depth = 0
        self.bracket_depth = 0
        self.prev_line = 0

    def parse(self):
        statements = self.parse_statements(T.EOF)
        return Program(statements)

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        token = self.tokens[self.pos]
        if token.type is not T.EOF:
            self.pos += 1
        self.prev_line = token.line
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

    def new_line(self):
        return self.bracket_depth == 0 and self.current().line > self.prev_line

    def require_same_line(self):
        if self.new_line():
            raise ParseError(
                "an expression cannot continue on the next line — "
                "keep it on one line or use parentheses",
                self.current(),
            )

    def parse_statements(self, terminator):
        statements = []
        while not self.check(terminator):
            if self.check(T.FN):
                if terminator is not T.EOF:
                    raise ParseError(
                        "function declarations are only allowed at top level",
                        self.current(),
                    )
                statements.append(self.parse_function())
            elif self.check(T.IMPORT):
                if terminator is not T.EOF:
                    raise ParseError(
                        "imports are only allowed at top level",
                        self.current(),
                    )
                statements.append(self.parse_import())
            elif self.check(T.BANG):
                if terminator is not T.EOF:
                    raise ParseError(
                        "imports are only allowed at top level",
                        self.current(),
                    )
                self.advance()
                if self.new_line():
                    raise ParseError(
                        "'import' must follow '!' on the same line",
                        self.current(),
                    )
                statements.append(self.parse_import(from_lib=True))
            else:
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
        if token_type is T.RETURN:
            return self.parse_return()
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
        if self.new_line():
            raise ParseError(
                f"'=' must follow '{name_token.value}' on the same line",
                self.current(),
            )
        token_type = self.current().type
        if token_type is T.ASSIGN:
            self.advance()
            self.require_same_line()
            return Assign(name_token.value, self.parse_expression())
        if token_type in COMPOUND_OPS:
            op = COMPOUND_OPS[token_type]
            self.advance()
            self.require_same_line()
            return CompoundAssign(name_token.value, op, self.parse_expression())
        self.pos -= 1
        expr = self.parse_expression()
        if not isinstance(expr, (Call, ModuleCall)):
            raise ParseError(
                f"expected '=' or a compound assignment after "
                f"'{name_token.value}', or a call like {name_token.value}(...)",
                name_token,
            )
        return ExprStmt(expr)

    def parse_if(self):
        self.match(T.IF, "'if'")
        self.match(T.LPAREN, "'('")
        self.bracket_depth += 1
        condition = self.parse_expression()
        self.match(T.RPAREN, "')'")
        self.bracket_depth -= 1
        then_block = self.parse_block()
        elifs = []
        else_block = None
        while self.check(T.ELSE):
            self.advance()
            if self.check(T.IF):
                self.advance()
                self.match(T.LPAREN, "'('")
                self.bracket_depth += 1
                elif_condition = self.parse_expression()
                self.match(T.RPAREN, "')'")
                self.bracket_depth -= 1
                elifs.append((elif_condition, self.parse_block()))
            else:
                else_block = self.parse_block()
                break
        return If(condition, then_block, else_block, elifs or None)

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
        self.bracket_depth += 1
        condition = self.parse_expression()
        self.match(T.RPAREN, "')'")
        self.bracket_depth -= 1
        self.loop_depth += 1
        body = self.parse_block()
        self.loop_depth -= 1
        return While(condition, body)

    def parse_print(self):
        self.match(T.PRINT, "'print'")
        self.match(T.LPAREN, "'('")
        self.bracket_depth += 1
        value = self.parse_expression()
        self.match(T.RPAREN, "')'")
        self.bracket_depth -= 1
        return Print(value)

    def parse_return(self):
        token = self.advance()
        if self.fn_depth == 0:
            raise ParseError("'return' outside function", token)
        self.require_same_line()
        return Return(self.parse_expression())

    def parse_function(self):
        self.match(T.FN, "'fn'")
        name_token = self.match(T.IDENT, "a function name")
        params = []
        seen = set()
        self.match(T.LPAREN, "'('")
        if not self.check(T.RPAREN):
            first = self.parse_parameter()
            params.append(first)
            seen.add(first[0])
            while self.check(T.COMMA):
                self.advance()
                name = self.current()
                param = self.parse_parameter()
                if param[0] in seen:
                    raise ParseError(
                        f"duplicate parameter '{param[0]}'",
                        name,
                    )
                seen.add(param[0])
                params.append(param)
        self.match(T.RPAREN, "')' or ','")

        self.fn_depth += 1
        saved_loop_depth = self.loop_depth
        self.loop_depth = 0
        body = self.parse_block()
        self.loop_depth = saved_loop_depth
        self.fn_depth -= 1
        return FnDef(name_token.value, params, body)

    def parse_import(self, from_lib=False):
        self.match(T.IMPORT, "'import' after '!'" if from_lib else "'import'")
        name_token = self.match(T.IDENT, "a module name")
        names = None
        if self.check(T.LBRACE):
            self.advance()
            names = [self.match(T.IDENT, "a member name").value]
            while self.check(T.COMMA):
                self.advance()
                names.append(self.match(T.IDENT, "a member name").value)
            self.match(T.RBRACE, "'}' or ','")
        return Import(name_token.value, names, from_lib)

    def parse_parameter(self):
        name_token = self.match(T.IDENT, "a parameter name")
        self.match(T.COLON, "':'")
        type_token = self.current()
        if type_token.type not in PARAM_TYPES:
            raise ParseError(
                f"unknown type {self.describe(type_token)} "
                f"(expected int, str, bool, or list)",
                type_token,
            )
        self.advance()
        return (name_token.value, PARAM_TYPES[type_token.type])

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
        if self.current().type not in COMPARISON_OPS:
            return node
        operands = [node]
        ops = []
        while self.current().type in COMPARISON_OPS:
            self.require_same_line()
            ops.append(COMPARISON_OPS[self.advance().type])
            self.require_same_line()
            operands.append(self.parse_additive())
        return Chain(operands, ops)

    def parse_additive(self):
        node = self.parse_multiplicative()
        while self.current().type in ADDITIVE_OPS:
            self.require_same_line()
            op = ADDITIVE_OPS[self.advance().type]
            self.require_same_line()
            node = BinOp(op, node, self.parse_multiplicative())
        return node

    def parse_multiplicative(self):
        node = self.parse_primary()
        while self.current().type in MULTIPLICATIVE_OPS:
            self.require_same_line()
            op = MULTIPLICATIVE_OPS[self.advance().type]
            self.require_same_line()
            node = BinOp(op, node, self.parse_primary())
        return node

    def parse_call_tail(self, name):
        return Call(name, self.parse_arguments())

    def parse_arguments(self):
        self.match(T.LPAREN, "'('")
        self.bracket_depth += 1
        args = []
        if not self.check(T.RPAREN):
            args.append(self.parse_expression())
            while self.check(T.COMMA):
                self.advance()
                args.append(self.parse_expression())
        self.match(T.RPAREN, "')' or ','")
        self.bracket_depth -= 1
        return args

    def parse_primary(self):
        node = self.parse_atom()
        while self.check(T.LBRACKET):
            self.require_same_line()
            self.advance()
            self.bracket_depth += 1
            index = self.parse_expression()
            self.match(T.RBRACKET, "']'")
            self.bracket_depth -= 1
            node = Subscript(node, index)
        return node

    def parse_atom(self):
        token = self.current()
        if token.type is T.INT:
            self.advance()
            return Num(token.value)
        if token.type is T.STRING:
            self.advance()
            return Str(token.value)
        if token.type is T.TRUE:
            self.advance()
            return Bool(True)
        if token.type is T.FALSE:
            self.advance()
            return Bool(False)
        if token.type is T.IDENT:
            self.advance()
            if self.check(T.LPAREN):
                self.require_same_line()
                return self.parse_call_tail(token.value)
            if self.check(T.DOT):
                self.require_same_line()
                self.advance()
                member = self.match(T.IDENT, "a member name after '.'")
                if self.check(T.LPAREN):
                    self.require_same_line()
                    return ModuleCall(
                        token.value, member.value, self.parse_arguments()
                    )
                return ModuleVar(token.value, member.value)
            return Var(token.value)
        if token.type in BUILTIN_NAMES:
            self.advance()
            if self.check(T.LPAREN):
                self.require_same_line()
                return self.parse_call_tail(BUILTIN_NAMES[token.type])
            raise ParseError(
                f"expected '(' after '{token.value}', "
                f"got {self.describe(self.current())}",
                self.current(),
            )
        if token.type is T.MINUS:
            self.advance()
            self.require_same_line()
            self.enter()
            node = Neg(self.parse_primary())
            self.leave()
            return node
        if token.type is T.LBRACKET:
            self.advance()
            self.bracket_depth += 1
            items = []
            if not self.check(T.RBRACKET):
                items.append(self.parse_expression())
                while self.check(T.COMMA):
                    self.advance()
                    items.append(self.parse_expression())
            self.match(T.RBRACKET, "']'")
            self.bracket_depth -= 1
            return ListLit(items)
        if token.type is T.LPAREN:
            self.advance()
            self.bracket_depth += 1
            node = self.parse_expression()
            self.match(T.RPAREN, "')'")
            self.bracket_depth -= 1
            return node
        raise ParseError(
            f"expected a number, a string, a boolean, an identifier, "
            f"a list, '-', or '(', got {self.describe(token)}",
            token,
        )
