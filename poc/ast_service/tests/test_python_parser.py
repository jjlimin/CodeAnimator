from poc.ast_service import parse_code


def test_parse_simple_function():
    code = """def add(a, b):
    return a + b
"""
    ast_obj = parse_code(code, "python")
    assert ast_obj["type"] == "Module"
    body = ast_obj["body"]
    assert isinstance(body, list) and len(body) == 1
    func = body[0]
    assert func["type"] == "FunctionDef"
    assert func["name"] == "add"
    assert func["args"] == ["a", "b"]
    assert func.get("lineno") == 1


def test_if_statement_lineno():
    code = """number = 10
if number % 2 == 0:
    print("Even")
else:
    print("Odd")
"""
    ast_obj = parse_code(code, "python")
    assert ast_obj["type"] == "Module"
    body = ast_obj["body"]
    assert len(body) == 2

    assign = body[0]
    assert assign["type"] == "Assign"
    assert assign["targets"][0]["type"] == "Name"
    assert assign["targets"][0]["name"] == "number"
    assert assign.get("lineno") == 1

    if_stmt = body[1]
    assert if_stmt["type"] == "If"
    assert if_stmt.get("lineno") == 2
    then_call = if_stmt["body"][0]
    assert then_call["type"] == "Call"
    assert then_call["func"]["name"] == "print"
    assert then_call["args"] == ["Even"]
    assert then_call.get("lineno") == 3
