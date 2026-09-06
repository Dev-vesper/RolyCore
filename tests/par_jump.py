import pytest

from roly.ast import Block, Break, Continue, Var, While
from roly.lexer import Lexer
from roly.parser import ParseError, Parser
from roly.tokens import T


def parse(source):
    return Parser(Lexer(source).tokenize()).parse()


def first_statement(source):
    return parse(source).statements[0]


def test_break_lexes_as_keyword():
    tokens = Lexer("break").tokenize()
    assert tokens[0].type is T.BREAK


def test_continue_lexes_as_keyword():
    tokens = Lexer("continue").tokenize()
    assert tokens[0].type is T.CONTINUE


def test_break_prefixed_identifier_stays_ident():
    tokens = Lexer("breakpoint continue_x").tokenize()
    assert all(t.type is T.IDENT for t in tokens[:2])


def test_break_statement_shape():
    assert first_statement("while (x) { break }") == While(
        Var("x"),
        Block([Break()]),
    )


def test_continue_statement_shape():
    program = parse("while (x) { continue }")
    assert program.statements[0].body == Block([Continue()])


def test_break_and_continue_together():
    program = parse("while (x) { if (x) { continue } break }")
    body = program.statements[0].body.statements
    assert body[0].then_block.statements == [Continue()]
    assert body[1] == Break()


def test_break_inside_nested_if_block():
    program = parse("while (x) { if (x) { if (x) { break } } }")
    inner = program.statements[0].body.statements[0].then_block.statements[0]
    assert inner.then_block.statements == [Break()]


def test_break_inside_nested_while_parses():
    program = parse("while (x) { while (y) { break } }")
    inner_body = program.statements[0].body.statements[0].body
    assert inner_body.statements == [Break()]


def test_bare_break_statement():
    program = parse("while (x) { break }")
    assert program.statements[0].body.statements == [Break()]


@pytest.mark.parametrize(
    "source, message",
    [
        ("break", "'break' outside loop"),
        ("x = 1 break", "'break' outside loop"),
        ("continue", "'continue' outside loop"),
        ("x = 1 continue", "'continue' outside loop"),
        ("if (x) { break }", "'break' outside loop"),
        ("if (x) { continue }", "'continue' outside loop"),
        ("{ break }", "'break' outside loop"),
        ("{ { continue } }", "'continue' outside loop"),
    ],
)
def test_jump_outside_loop_raises(source, message):
    with pytest.raises(ParseError, match=message):
        parse(source)


def test_break_after_loop_body_is_outside():
    with pytest.raises(ParseError, match="'break' outside loop"):
        parse("while (x) { } break")


def test_continue_after_loop_body_is_outside():
    with pytest.raises(ParseError, match="'continue' outside loop"):
        parse("while (x) { break } continue")


def test_break_error_points_at_keyword():
    with pytest.raises(ParseError) as excinfo:
        parse("x = 1\n  break")
    assert excinfo.value.token.line == 2
    assert excinfo.value.token.column == 3


def test_loop_depth_resets_after_loop():
    parse("while (x) { break } while (y) { continue }")


def test_break_inside_loop_condition_is_parse_error():
    with pytest.raises(ParseError):
        parse("while (break) { }")


def test_jump_keywords_not_expressions():
    with pytest.raises(ParseError):
        parse("x = break")
    with pytest.raises(ParseError):
        parse("x = continue")
