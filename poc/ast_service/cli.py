"""CLI for the AST service."""
import argparse
import json
import sys
from . import parse_code


def run_code(code: str, language: str = "python") -> dict:
    """Programmatic helper to parse a code snippet and return the compact AST."""
    return parse_code(code, language)


def main(argv=None):
    """Entry point for CLI. Accepts optional argv list for programmatic invocation."""
    parser = argparse.ArgumentParser(description="Parse code to AST JSON")
    parser.add_argument("--language", "-l", default="python", help="Language to parse (default: python)")
    parser.add_argument("--file", "-f", help="Path to source file; if omitted reads stdin")
    parser.add_argument("--code", "-c", help="Code snippet to parse directly (takes precedence over --file and stdin)")
    args = parser.parse_args(argv)

    if args.code is not None:
        code = args.code
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            code = fh.read()
    else:
        code = sys.stdin.read()

    ast_obj = run_code(code, args.language)
    print(json.dumps(ast_obj, indent=2))


if __name__ == "__main__":
    main()
