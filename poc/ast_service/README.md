# ast_service

Small, extensible AST parsing service.

Usage examples:

- As a module:

```py
from poc.ast_service import parse_code

ast_dict = parse_code("def foo():\n    return 1", "python")
```

- CLI (compact AST by default):

```sh
# parse a file
python -m ast_service --file path/to/code.py

# parse a snippet directly from the command line
python -m ast_service --code "x = 1\nprint(x)\n"
```

Programmatic usage:

```py
from poc.ast_service import run_code, run_file

# parse a snippet string directly
ast = run_code("x = 1\nprint(x)\n", "python")
# parse a file by passing its path as a variable (no CLI)
ast_from_file = run_file("path/to/script.py")
```

Extending with new languages:

- Implement a class following `base.Parser` and register it via `registry.register("lang", parser_instance)`.
