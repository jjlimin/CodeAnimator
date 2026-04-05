from poc.ast_service import run_code
from poc.ast_service import cli


def test_run_code_helper():
    code = """x = 1\nprint(x)\n"""
    ast_obj = run_code(code, "python")
    assert ast_obj["type"] == "Module"
    assert len(ast_obj["body"]) == 2


def test_cli_main_with_code_arg(capsys):
    argv = ["--code", "x = 2\nprint(x)\n"]
    cli.main(argv)
    captured = capsys.readouterr()
    assert "Module" in captured.out
    assert "Assign" in captured.out
    assert "Call" in captured.out


def test_run_file_tmp_path(tmp_path):
    p = tmp_path / "snippet.py"
    p.write_text("x = 3\nprint(x)\n")
    from poc.ast_service import run_file
    ast_obj = run_file(str(p))
    assert ast_obj["type"] == "Module"
    # ensure we can see an Assign and Call in the body
    types = [n.get("type") for n in ast_obj["body"]]
    assert "Assign" in types and "Call" in types
