"""Simple AST service package

Public API:
- parse_code(code: str, language: str='python') -> dict

This package is designed to be easily extended with additional language parsers
using the registry in `registry.py`.
"""
from .registry import registry
# Import language implementations so they register themselves on package import
from . import python_parser  # noqa: F401

__all__ = ["parse_code", "registry", "run_code", "run_file"]


def run_code(code: str, language: str = "python") -> dict:
    """Convenience wrapper that parses a code snippet and returns compact AST.

    This makes it easy to start the service programmatically and provide the
    snippet string directly.
    """
    return parse_code(code, language)


def run_file(path: str, language: str = "python") -> dict:
    """Read a source file and return the compact AST.

    This helper lets you pass a file path as a variable inside your code
    (no CLI involved). Example:
        ast = run_file("/path/to/script.py")
    """
    with open(path, "r", encoding="utf-8") as fh:
        code = fh.read()
    return run_code(code, language)


def parse_code(code: str, language: str = "python") -> dict:
    """Parse code for a given language and return a serializable compact AST dict.

    Parsers MUST return the compact representation by default.

    Raises ValueError if no parser is registered for the requested language.
    """
    parser = registry.get(language)
    if parser is None:
        raise ValueError(f"No parser registered for language '{language}'")
    return parser.parse(code)
