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
- The TOTAL narration across all scenes must fit in 60 to 120 seconds
  (90-300 words total). Simpler input code deserves fewer, shorter scenes —
  going under 60 seconds is fine for trivial snippets; never exceed 120 seconds.
- Each scene should carry 10-30 seconds of narration (25-75 words).
- Choose the optimal scene count for the complexity of the input: a 3-line
  function might need only 2 scenes; a complex algorithm might need 6+.

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


def build_generation_user_message(user_code: str) -> str:
    return f"Explain this code:\n\n```python\n{user_code}\n```"


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
