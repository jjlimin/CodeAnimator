"""Environment-adaptive validation of generated Manim scene code.

Tiers (each runs only if the previous one passed):
  1. Syntax check      — ast.parse, works everywhere.
  2. Static Manim lint — AST checks for required structure and known
                         removed/renamed ManimCE APIs, works everywhere.
  3. Dry-run execution — subprocess that executes the scene with
                         `config.dry_run = True` (no video output). Runs only
                         where the `manim` package is importable (local dev,
                         ECS, container-image Lambda). Skipped automatically
                         in a zip-package Lambda.
"""

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from typing import Optional

MANIM_AVAILABLE = importlib.util.find_spec("manim") is not None

# ManimCE APIs that gpt models frequently hallucinate from the legacy
# (manimgl / pre-CE) API, mapped to the guidance fed back to the model.
REMOVED_APIS = {
    "ShowCreation": "removed in ManimCE — use Create(...)",
    "ShowCreationThenFadeOut": "removed in ManimCE — use Succession(Create(m), FadeOut(m))",
    "TextMobject": "removed in ManimCE — use Text(...) or Tex(...)",
    "TexMobject": "removed in ManimCE — use MathTex(...) or Tex(...)",
    "GraphScene": "removed in ManimCE — use a plain Scene with Axes and axes.plot(...)",
    "FadeInFrom": "removed in ManimCE — use FadeIn(mobject, shift=direction)",
    "FadeInFromDown": "removed in ManimCE — use FadeIn(mobject, shift=DOWN)",
    "FadeOutAndShift": "removed in ManimCE — use FadeOut(mobject, shift=direction)",
    "FadeOutAndShiftDown": "removed in ManimCE — use FadeOut(mobject, shift=DOWN)",
    "ContinualAnimation": "removed in ManimCE — use mobject.add_updater(...)",
    "get_graph": "removed in ManimCE — use axes.plot(...)",
    "get_graph_label": "removed in ManimCE — use axes.get_graph_label(...) on plot output",
    "ShowIncreasingSubsets": "renamed — use AddTextLetterByLetter or LaggedStart",
}

# Keyword arguments renamed in recent ManimCE releases, keyed by
# (callable name, old kwarg) -> guidance. Catches e.g. Code(code=...) which
# Manim 0.19 renamed to Code(code_string=...); a raw TypeError would not tell
# the LLM the new name, so the lint message must.
RENAMED_KWARGS = {
    ("Code", "code"): "renamed in ManimCE 0.19 — use Code(code_string=...)",
    ("Code", "file_name"): "renamed in ManimCE 0.19 — use Code(code_file=...)",
    ("Code", "style"): "renamed in ManimCE 0.19 — use Code(formatter_style=...)",
    ("Code", "insert_line_no"): "renamed in ManimCE 0.19 — use Code(add_line_numbers=True/False)",
    ("Code", "line_no_from"): "renamed in ManimCE 0.19 — use Code(line_numbers_from=...)",
    ("Code", "font"): "removed in ManimCE 0.19 — pass paragraph_config={'font': ...}",
    ("Code", "font_size"): "removed in ManimCE 0.19 — pass paragraph_config={'font_size': ...}",
    ("Code", "line_spacing"): "removed in ManimCE 0.19 — pass paragraph_config={'line_spacing': ...}",
    ("Code", "background_stroke_width"): "removed in ManimCE 0.19 — pass background_config={'stroke_width': ...} or omit",
    ("Code", "background_stroke_color"): "removed in ManimCE 0.19 — pass background_config={'stroke_color': ...} or omit",
}

# Appended to the scene file for the dry-run subprocess. Finds the Scene
# subclass defined in the file itself and renders it with output disabled.
_DRY_RUN_DRIVER = textwrap.dedent(
    """

    if __name__ == "__main__":
        import sys as _sys
        from manim import Scene as _Scene, config as _config

        _config.dry_run = True
        _config.disable_caching = True
        _config.verbosity = "ERROR"
        _config.progress_bar = "none"

        _scene_classes = [
            _obj for _obj in list(globals().values())
            if isinstance(_obj, type)
            and issubclass(_obj, _Scene)
            and _obj.__module__ == "__main__"
        ]
        if not _scene_classes:
            print("VALIDATION: no Scene subclass defined in the file", file=_sys.stderr)
            _sys.exit(1)
        for _cls in _scene_classes:
            _cls().render()
    """
)


@dataclass
class ValidationResult:
    passed: bool
    tier: str  # "syntax" | "lint" | "dry_run"
    error: Optional[str] = None


def _check_syntax(code: str) -> Optional[str]:
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} (line {e.lineno}, offset {e.offset})\n  {e.text or ''}".rstrip()


def _check_lint(code: str) -> Optional[str]:
    tree = ast.parse(code)
    errors = []

    imports_manim = any(
        (isinstance(node, ast.ImportFrom) and node.module == "manim")
        or (isinstance(node, ast.Import) and any(a.name == "manim" for a in node.names))
        for node in ast.walk(tree)
    )
    if not imports_manim:
        errors.append("Missing `from manim import *` — the code never imports manim.")

    scene_classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(b, ast.Name) and b.id.endswith("Scene"))
            or (isinstance(b, ast.Attribute) and b.attr.endswith("Scene"))
            for b in node.bases
        )
    ]
    if not scene_classes:
        errors.append("No Scene subclass found — define exactly one `class X(Scene):`.")
    else:
        for cls in scene_classes:
            has_construct = any(
                isinstance(item, ast.FunctionDef) and item.name == "construct"
                for item in cls.body
            )
            if not has_construct:
                errors.append(f"Class `{cls.name}` has no `construct(self)` method.")

    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        if name in REMOVED_APIS:
            errors.append(
                f"`{name}` (line {node.lineno}): {REMOVED_APIS[name]}"
            )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else None
        )
        for kw in node.keywords:
            guidance = RENAMED_KWARGS.get((func_name, kw.arg))
            if guidance:
                errors.append(
                    f"`{func_name}({kw.arg}=...)` (line {node.lineno}): {guidance}"
                )

    if errors:
        return "Static Manim lint failed:\n" + "\n".join(f"- {e}" for e in errors)
    return None


def _check_dry_run(code: str, timeout: int) -> Optional[str]:
    with tempfile.TemporaryDirectory(prefix="manim_val_") as tmpdir:
        scene_path = os.path.join(tmpdir, "scene_under_test.py")
        with open(scene_path, "w", encoding="utf-8") as f:
            f.write(code + _DRY_RUN_DRIVER)
        try:
            proc = subprocess.run(
                [sys.executable, scene_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            return (
                f"Dry-run execution exceeded {timeout}s — the scene likely has an "
                "infinite loop or is far too heavy. Simplify the animation."
            )
    if proc.returncode != 0:
        # The traceback is the last, most relevant part of stderr.
        stderr_tail = (proc.stderr or proc.stdout or "no error output").strip()[-3000:]
        return f"Dry-run execution failed (exit code {proc.returncode}):\n{stderr_tail}"
    return None


def validate_scene(code: str, timeout: int = 30) -> ValidationResult:
    """Validate one scene's Manim code without rendering any video."""
    error = _check_syntax(code)
    if error:
        return ValidationResult(passed=False, tier="syntax", error=error)

    error = _check_lint(code)
    if error:
        return ValidationResult(passed=False, tier="lint", error=error)

    if MANIM_AVAILABLE:
        error = _check_dry_run(code, timeout)
        if error:
            return ValidationResult(passed=False, tier="dry_run", error=error)
        return ValidationResult(passed=True, tier="dry_run")

    return ValidationResult(passed=True, tier="lint")
