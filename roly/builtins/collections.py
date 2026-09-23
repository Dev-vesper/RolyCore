from roly.builtins.conversion import roly_equal
from roly.diagnostics.errors import RolyError


def make_list(*values):
    if len(values) > 1:
        raise RolyError("builtin 'list' expects no arguments or a str")
    if not values:
        return []
    value = values[0]
    if type(value) is not str:
        raise RolyError(f"builtin 'list' expects a str, got {value!r}")
    return list(value)


def require_list(name, value):
    if type(value) is not list:
        raise RolyError(f"builtin '{name}' expects a list, got {value!r}")


def require_index(name, index, length):
    if type(index) is not int:
        raise RolyError(f"builtin '{name}' expects an int index, got {index!r}")
    if index < 0 or index >= length:
        raise RolyError(
            f"{name}: index {index} out of range for length {length}"
        )


def list_push(items, value):
    require_list("push", items)
    return items + [value]


def list_insert(items, index, value):
    require_list("insert", items)
    if type(index) is not int:
        raise RolyError(f"builtin 'insert' expects an int index, got {index!r}")
    if index < 0 or index > len(items):
        raise RolyError(
            f"insert: index {index} out of range for length {len(items)}"
        )
    return items[:index] + [value] + items[index:]


def list_delete_at(items, index):
    require_list("delete_at", items)
    if type(index) is not int:
        raise RolyError(f"builtin 'delete_at' expects an int index, got {index!r}")
    if index < 0 or index >= len(items):
        raise RolyError(
            f"delete_at: index {index} out of range for length {len(items)}"
        )
    return items[:index] + items[index + 1 :]


def list_concat(left, right):
    require_list("concat", left)
    if type(right) is not list:
        raise RolyError(f"builtin 'concat' expects a list, got {right!r}")
    return left + right


def map_equal(a, b):
    require_list("map_equal", a)
    if type(b) is not list:
        raise RolyError(f"builtin 'map_equal' expects a list, got {b!r}")
    for pairs in (a, b):
        for pair in pairs:
            if type(pair) is not list or len(pair) != 2:
                raise RolyError("map_equal: element is not a [key, value] pair")
    if len(a) != len(b):
        return False
    remaining = list(b)
    for key, value in a:
        found = -1
        for i, (other_key, other_value) in enumerate(remaining):
            if roly_equal(key, other_key) and roly_equal(value, other_value):
                found = i
                break
        if found == -1:
            return False
        del remaining[found]
    return True


def list_get(items, index):
    require_list("get", items)
    require_index("get", index, len(items))
    return items[index]


def list_set(items, index, value):
    require_list("set", items)
    require_index("set", index, len(items))
    return items[:index] + [value] + items[index + 1 :]
