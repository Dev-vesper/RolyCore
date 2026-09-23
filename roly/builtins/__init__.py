import sys

sys.set_int_max_str_digits(0)

from roly.builtins.collections import (
    list_concat,
    list_delete_at,
    list_get,
    list_insert,
    list_push,
    list_set,
    make_list,
    map_equal,
)
from roly.builtins.conversion import to_bool, to_float, to_int, to_str, roly_equal
from roly.builtins.io import (
    FILE_METHODS,
    FILE_METHOD_ARITIES,
    list_dir_native,
    make_dir,
    open_file,
    read_input,
)
from roly.builtins.text import format_text, text_char, text_chr, text_len, text_ord
from roly.diagnostics.errors import RolyError


def fail(message):
    if type(message) is not str:
        raise RolyError(f"builtin 'fail' expects a str, got {message!r}")
    raise RolyError(message)


BUILTINS = {
    "int": to_int,
    "str": to_str,
    "bool": to_bool,
    "float": to_float,
    "list": make_list,
    "len": text_len,
    "char": text_char,
    "ord": text_ord,
    "chr": text_chr,
    "format": format_text,
    "fail": fail,
    "input": read_input,
    "push": list_push,
    "insert": list_insert,
    "delete_at": list_delete_at,
    "concat": list_concat,
    "map_equal": map_equal,
    "get": list_get,
    "set": list_set,
    "open": open_file,
    "mkdir": make_dir,
    "list_dir": list_dir_native,
}

BUILTINS_WITH_INTERP = {"open", "mkdir", "list_dir"}

BUILTIN_ARITIES = {
    "int": 1,
    "str": 1,
    "bool": 1,
    "float": 1,
    "len": 1,
    "char": 2,
    "ord": 1,
    "chr": 1,
    "push": 2,
    "insert": 3,
    "delete_at": 2,
    "concat": 2,
    "map_equal": 2,
    "get": 2,
    "set": 3,
    "fail": 1,
    "input": 1,
    "open": 2,
    "mkdir": 1,
    "list_dir": 1,
}


class Registry:
    def __init__(self, functions, arities, with_interp, methods, method_arities):
        self.functions = functions
        self.arities = arities
        self.with_interp = with_interp
        self.methods = methods
        self.method_arities = method_arities


def default_registry():
    return Registry(
        BUILTINS,
        BUILTIN_ARITIES,
        BUILTINS_WITH_INTERP,
        FILE_METHODS,
        FILE_METHOD_ARITIES,
    )
