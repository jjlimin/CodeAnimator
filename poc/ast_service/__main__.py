"""Entrypoint that works both with `python -m ast_service` and
when running this file directly (e.g. `python ast_service/__main__.py`).

When run as a script, the package may not be on sys.path, so we add its
parent directory to sys.path and import the absolute package module.
"""


def _get_main_callable():
    try:
        # Preferred path when run as a package: python -m ast_service
        from .cli import main
        return main
    except Exception:
        # Fallback when executed directly as a script: python ast_service/__main__.py
        import os
        import sys

        pkg_dir = os.path.dirname(__file__)
        parent = os.path.dirname(pkg_dir)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        from poc.ast_service.cli import main
        return main


if __name__ == "__main__":
    _get_main_callable()()
