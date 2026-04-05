"""Python parser implementation using the stdlib ast module.

It converts ast.AST nodes to a serializable nested dict representation.
"""
import ast
from .base import Parser
from .registry import registry


def _compact(node):
    """Return a compact, human-friendly representation of AST `node` including line numbers.

    The compact representation keeps essential information and attaches a
    `lineno` attribute to statement and key nodes so original source lines
    can be remembered.
    """
    # Module
    if isinstance(node, ast.Module):
        return {"type": "Module", "body": [_compact(n) for n in node.body]}

    # Assign
    if isinstance(node, ast.Assign):
        return {
            "type": "Assign",
            "targets": [_compact(t) for t in node.targets],
            "value": _compact(node.value),
            "lineno": getattr(node, "lineno", None),
        }

    # Name -> include name and lineno
    if isinstance(node, ast.Name):
        res = {"type": "Name", "name": node.id}
        if hasattr(node, "lineno"):
            res["lineno"] = node.lineno
        return res

    # Constant -> primitive value (lineno usually on parent)
    if isinstance(node, ast.Constant):
        return node.value

    # Expr -> unwrap
    if isinstance(node, ast.Expr):
        return _compact(node.value)

    # Call
    if isinstance(node, ast.Call):
        func = _compact(node.func)
        args = [_compact(a) for a in node.args]
        return {"type": "Call", "func": func, "args": args, "lineno": getattr(node, "lineno", None)}

    # If
    if isinstance(node, ast.If):
        return {
            "type": "If",
            "test": _compact(node.test),
            "body": [_compact(n) for n in node.body],
            "orelse": [_compact(n) for n in node.orelse],
            "lineno": getattr(node, "lineno", None),
        }

    # Compare
    if isinstance(node, ast.Compare):
        ops = [op.__class__.__name__ for op in node.ops]
        comps = [_compact(c) for c in node.comparators]
        return {"type": "Compare", "left": _compact(node.left), "ops": ops, "comparators": comps, "lineno": getattr(node, "lineno", None)}

    # BinOp
    if isinstance(node, ast.BinOp):
        return {
            "type": "BinOp",
            "op": node.op.__class__.__name__,
            "left": _compact(node.left),
            "right": _compact(node.right),
            "lineno": getattr(node, "lineno", None),
        }

    # FunctionDef
    if isinstance(node, ast.FunctionDef):
        args = [a.arg for a in node.args.args]
        return {"type": "FunctionDef", "name": node.name, "args": args, "body": [_compact(n) for n in node.body], "lineno": getattr(node, "lineno", None)}

    # Return
    if isinstance(node, ast.Return):
        return {"type": "Return", "value": _compact(node.value), "lineno": getattr(node, "lineno", None)}

    # Fallback
    if isinstance(node, ast.AST):
        t = node.__class__.__name__
        res = {"type": t}
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                res[field] = _compact(value)
            elif isinstance(value, list):
                lst = [_compact(x) if isinstance(x, ast.AST) else x for x in value]
                if lst:
                    res[field] = lst
            else:
                if value not in (None, ""):
                    res[field] = value
        if hasattr(node, "lineno"):
            res["lineno"] = node.lineno
        return res

    # not an AST node (primitive)
    return node


class PythonParser(Parser):
    def parse(self, code: str) -> dict:
        tree = ast.parse(code)
        return _compact(tree)


# Register the Python parser by default
registry.register("python", PythonParser())
