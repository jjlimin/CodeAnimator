"""Environment-adaptive validation of generated Manim scene code.

Tiers (each runs only if the previous one passed):
  1. Syntax check      — ast.parse, works everywhere.
  2. Static Manim lint — AST checks for required structure and known
                         removed/renamed ManimCE APIs, works everywhere.
  3. Dry-run execution — subprocess that executes the scene with
                         `config.dry_run = True` (no video output), then
                         checks every top-level mobject still on screen at
                         the end of the scene for pairwise bounding-box
                         overlap (this is what catches the model's own
                         visuals colliding with the automatic code snippet).
                         Runs only where the `manim` package is importable
                         (local dev, ECS, container-image Lambda). Skipped
                         automatically in a zip-package Lambda — AIAgentLambda
                         is deployed as one today (see ARCHITECTURE.md), so
                         this tier — overlap check included — is currently
                         dormant in production and only exercises via
                         local_test.py / a future manim-capable deployment.
"""

import ast
import importlib.util
import os
import re
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

# Marker the parent process greps for in stderr to tell an overlap failure
# apart from an ordinary crash (both exit non-zero from the subprocess).
OVERLAP_MARKER = "VALIDATION: overlapping mobjects detected"

# Minimum bounding-box intersection (in Manim scene units — the default
# frame is ~14.2 wide x 8 tall) before two elements count as "overlapping."
# Small enough to catch real collisions (the reported bug was ~1+ unit of
# overlap) while tolerating elements placed edge-to-edge by design.
_OVERLAP_TOLERANCE = 0.15

# Appended to the scene file for the dry-run subprocess. Finds the Scene
# subclass defined in the file itself, renders it with output disabled, then
# checks every top-level mobject still on screen at the end of the scene for
# pairwise bounding-box overlap. This is a real geometric check against the
# actual positions/sizes Manim computed — not a guess from the source code —
# but it only sees the scene's FINAL state (whatever wasn't faded out before
# the scene ends), so a collision that only exists mid-animation could slip
# through; that tradeoff keeps this simple and fast.
_DRY_RUN_DRIVER = textwrap.dedent(
    f"""

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

        _overlaps = []
        for _cls in _scene_classes:
            _scene = _cls()
            _scene.render()
            _mobs = [m for m in _scene.mobjects if m.width > 0 and m.height > 0]
            for _i in range(len(_mobs)):
                for _j in range(_i + 1, len(_mobs)):
                    _a, _b = _mobs[_i], _mobs[_j]
                    _x_overlap = min(_a.get_right()[0], _b.get_right()[0]) - max(_a.get_left()[0], _b.get_left()[0])
                    _y_overlap = min(_a.get_top()[1], _b.get_top()[1]) - max(_a.get_bottom()[1], _b.get_bottom()[1])
                    if _x_overlap > {_OVERLAP_TOLERANCE} and _y_overlap > {_OVERLAP_TOLERANCE}:
                        _overlaps.append(
                            f"{{type(_a).__name__}} and {{type(_b).__name__}} overlap by "
                            f"~{{min(_x_overlap, _y_overlap):.2f}} units"
                        )

        if _overlaps:
            print("{OVERLAP_MARKER}:", file=_sys.stderr)
            for _o in _overlaps:
                print(" - " + _o, file=_sys.stderr)
            _sys.exit(2)
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


# Callables whose string arguments are LaTeX source, not plain text — the
# argument MUST be a raw string, or Python's own escape processing corrupts
# backslash-letter LaTeX commands (\frac, \nu, \tau, \alpha, \beta, \vee,
# ...) before LaTeX ever sees them: \f/\n/\r/\t/\v/\a/\b are all real Python
# escape sequences that silently eat the backslash.
LATEX_CALLABLES = {"MathTex", "Tex", "SingleStringMathTex"}


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

    # Code mobject has no `.code` attribute in current ManimCE — models often
    # hallucinate `code_mobject.code[i]` to reach individual lines (e.g. for
    # SurroundingRectangle highlights). This crashes at render time with
    # AttributeError, which the static checks above cannot catch since it is
    # a runtime attribute lookup, not a call/kwarg — worth its own check.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "code"
        ):
            errors.append(
                f"`.code[...]` (line {node.lineno}): Code mobject has no `.code` "
                "attribute in current ManimCE — do not index into a Code "
                "mobject's lines this way. Build separate Text/Paragraph "
                "mobjects instead if individual lines need to be referenced "
                "or highlighted."
            )

    # MathTex/Tex string arguments must be raw strings (r"...") — a regular
    # string silently mangles LaTeX commands like \frac, \nu, \tau via
    # Python's own backslash-escape processing (confirmed root cause of a
    # real render crash: \frac{...} became a form-feed + "rac{...}").
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        func_name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else None
        )
        if func_name not in LATEX_CALLABLES:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                src = ast.get_source_segment(code, arg) or ""
                if not re.match(r"^[rR]['\"]", src):
                    errors.append(
                        f"`{func_name}(...)` (line {node.lineno}): LaTeX string "
                        "arguments must be raw strings, e.g. r\"\\frac{a}{b}\" — "
                        "a plain string silently corrupts backslash-letter LaTeX "
                        "commands (\\f, \\n, \\t, \\r, \\v, \\a, \\b are all real "
                        "Python escape sequences) before LaTeX ever sees them."
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
        if OVERLAP_MARKER in stderr_tail:
            return (
                "Overlap check failed — two or more on-screen elements' bounding "
                "boxes intersect at the end of the scene (this includes the "
                "automatic code snippet, which the model's own content must "
                "never overlap):\n" + stderr_tail
            )
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
