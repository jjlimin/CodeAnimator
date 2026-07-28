"""System prompts and JSON schemas for the Manim scene-generation agent."""

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

GENERATION_SYSTEM_PROMPT = """\
You are an expert Manim Community Edition (ManimCE) animation developer and Python educator.

The user will provide a Python code snippet. Break the explanation of this code into a
logical sequence of short animated scenes with voice narration.

## Scene count and pacing — YOU decide the number of scenes
- Narration is spoken at roughly 150 words per minute.
- Follow the "Requested depth" directive in the user message for the target
  total length and level of detail — it overrides any default duration.
- Each scene should carry 10-30 seconds of narration (25-75 words).
- Choose the optimal scene count for the requested depth and the complexity of
  the input: a simple high-level pass might need only 2 scenes; a detailed
  walkthrough of a complex algorithm might need 6+.

## Manim code requirements (each scene's `manim_code` value)
- Self-contained: starts with `from manim import *` and defines exactly ONE
  Scene subclass (e.g. `class Scene1(Scene):`) with a `construct` method.
- Use ONLY current ManimCE APIs. Common pitfalls to avoid:
  - `ShowCreation` was removed — use `Create`.
  - `TextMobject` / `TexMobject` were removed — use `Text` / `MathTex` / `Tex`.
  - `GraphScene` was removed — use `Axes` inside a plain `Scene` and `axes.plot(...)`.
  - `FadeInFrom` / `FadeOutAndShift` were removed — use `FadeIn(m, shift=...)` / `FadeOut(m, shift=...)`.
  - The `Code` mobject signature changed in ManimCE 0.19:
    `Code(code_string="...", language="python", add_line_numbers=False)`.
    The kwargs `code`, `style`, `insert_line_no`, `font`, and `font_size` no longer exist.
- Keep animations simple: Text, Code, MathTex, shapes, arrows, transforms,
  highlighting. No external files, no images, no SVGs, no network access.
- The on-screen animation of a scene should roughly match its narration length
  (use `self.wait(...)` to pad where needed).
- Code must be immediately runnable — it will be compiled and executed for
  validation before rendering.

Return the scenes in narrative order with sequential integer `scene_id` starting at 1.
"""

GENERATION_SCHEMA = {
    "type": "json_schema",
    "name": "manim_scenes",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "integer"},
                        "narration": {"type": "string"},
                        "manim_code": {"type": "string"},
                    },
                    "required": ["scene_id", "narration", "manim_code"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["scenes"],
        "additionalProperties": False,
    },
}

# ---------------------------------------------------------------------------
# Correction
# ---------------------------------------------------------------------------

CORRECTION_SYSTEM_PROMPT = """\
You are an expert Manim Community Edition (ManimCE) debugger.

You previously generated Manim scene code, and some scenes failed validation.
For each failed scene you will receive its narration, the broken `manim_code`,
and the exact error output (traceback, syntax error, or lint finding).

Fix ONLY what is necessary to make each scene run, while keeping the animation
faithful to its narration. Rules:
- Return the COMPLETE corrected code for every failed scene (not a diff).
- Each fix must be self-contained: `from manim import *` plus exactly one
  Scene subclass with a `construct` method.
- Use only current ManimCE APIs (`Create` not `ShowCreation`, `Text`/`MathTex`
  not `TextMobject`/`TexMobject`, `Axes` not `GraphScene`, etc.).
- The `Code` mobject signature changed in ManimCE 0.19:
  `Code(code_string="...", language="python", add_line_numbers=False)`.
  The kwargs `code`, `style`, `insert_line_no`, `font`, and `font_size` no longer exist.
- If an approach fundamentally cannot work, replace it with a simpler
  animation that conveys the same idea.
"""

CORRECTION_SCHEMA = {
    "type": "json_schema",
    "name": "manim_scene_fixes",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "fixes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "integer"},
                        "manim_code": {"type": "string"},
                    },
                    "required": ["scene_id", "manim_code"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["fixes"],
        "additionalProperties": False,
    },
}


# Requested-depth directives, chosen by the user in the UI. Controls the total
# length and how deep the explanation goes. Default is "balanced".
COMPLEXITY_DIRECTIVES = {
    "high_level": (
        "Requested depth: HIGH-LEVEL OVERVIEW. Focus on the big picture — the "
        "code's overall purpose and the main idea. Keep it short: 2-3 scenes, "
        "total narration 30-60 seconds. Avoid line-by-line detail and edge cases."
    ),
    "balanced": (
        "Requested depth: BALANCED. Explain the key steps and how the code works "
        "at a comfortable pace. Total narration 60-120 seconds; pick the scene "
        "count that fits the input's complexity."
    ),
    "detailed": (
        "Requested depth: DETAILED WALKTHROUGH. Go step by step through the logic, "
        "how the data changes, and notable edge cases. Be thorough: use more "
        "scenes as needed, total narration 120-180 seconds."
    ),
}
DEFAULT_COMPLEXITY = "balanced"


def build_generation_user_message(user_code: str, complexity: str = DEFAULT_COMPLEXITY) -> str:
    directive = COMPLEXITY_DIRECTIVES.get(complexity, COMPLEXITY_DIRECTIVES[DEFAULT_COMPLEXITY])
    return f"{directive}\n\nExplain this code:\n\n```python\n{user_code}\n```"


def build_buggy_generation_user_message(
    user_code: str, code_error: str, complexity: str = DEFAULT_COMPLEXITY
) -> str:
    """Generation message for broken/non-compiling code. The video must keep
    showing the ORIGINAL broken code (never a rewritten/fixed version) and
    explain how it could have been written so it would work."""
    directive = COMPLEXITY_DIRECTIVES.get(complexity, COMPLEXITY_DIRECTIVES[DEFAULT_COMPLEXITY])
    return (
        f"{directive}\n\n"
        "The following Python code does NOT compile / has an error:\n\n"
        f"```python\n{user_code}\n```\n\n"
        f"The error is: {code_error}\n\n"
        "Create scenes that:\n"
        "- Display the ORIGINAL broken code exactly as written (do NOT show a "
        "rewritten or corrected version of the code on screen).\n"
        "- Point out where and why it fails.\n"
        "- Explain how it could have been written so that it would work "
        "(describe the correction in the narration), while the broken code "
        "stays on screen as the reference.\n"
        "Keep it clear and educational."
    )


def build_correction_user_message(user_code: str, failed_scenes: list) -> str:
    """failed_scenes: list of dicts with scene_id, narration, manim_code, error."""
    parts = [
        "The animation explains this user code:\n"
        f"```python\n{user_code}\n```\n",
        "The following scenes failed validation. Fix each one.\n",
    ]
    for scene in failed_scenes:
        parts.append(
            f"---\n"
            f"SCENE {scene['scene_id']}\n"
            f"Narration: {scene['narration']}\n\n"
            f"Broken code:\n```python\n{scene['manim_code']}\n```\n\n"
            f"Validation error:\n```\n{scene['error']}\n```\n"
        )
    return "\n".join(parts)
