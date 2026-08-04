"""System prompts and JSON schemas for the Manim scene-generation agent."""

import textwrap

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
  - `MathTex(...)` / `Tex(...)` string arguments are LaTeX source and MUST be
    raw strings: `MathTex(r"\frac{a}{b}")`, never `MathTex("\frac{a}{b}")`.
    Without the `r` prefix, Python's own escape processing silently corrupts
    backslash-letter LaTeX commands (`\frac`, `\nu`, `\tau`, `\alpha`, `\beta`,
    `\vee`, ...) — `\f`, `\n`, `\r`, `\t`, `\v`, `\a`, `\b` are all real Python
    escape sequences that eat the backslash before LaTeX ever sees it.
- Keep animations simple: Text, MathTex, shapes, arrows, transforms,
  highlighting. No external files, no images, no SVGs, no network access.
- The on-screen animation of a scene should roughly match its narration length
  (use `self.wait(...)` to pad where needed).
- Code must be immediately runnable — it will be compiled and executed for
  validation before rendering.

## Visual flow — STRICT structure, all code display is automatic
Every video follows a fixed two-part structure. You never call `Code(...)`
or otherwise build/reproduce/paraphrase the source code yourself — every
appearance of code on screen is generated automatically from the real
source, guaranteeing it is always shown correctly.

1. **Scene 1 is always the intro.** Its narration is the preface/overview —
   what the code does, in general terms. The system automatically shows the
   FULL code, full-screen, using Manim's `Code` class, fading it in while
   this narration plays, holding it, then fading it out at the end of the
   scene — before any step scene begins. Your `manim_code` for scene 1 must
   have an EMPTY body: just `pass`. Do not create any mobjects in scene 1.
   Set `active_lines` to `[]` for scene 1 (it is not used).

2. **Every scene from scene 2 onward is a "step" scene**, each focused on
   ONE small piece of logic. Set `active_lines` to the exact 1-indexed line
   number(s) — from the numbered code in the user message — that this
   scene's narration is about. Keep it a small, usually contiguous range
   (1-4 lines): this is the ONLY code the system will show for this scene,
   automatically, as a snippet faded in near the top of the screen — never
   the full code again after scene 1.

3. **In step scenes, your own `manim_code` may add supporting visuals**
   (explanatory text, a diagram, a value trace) but:
   - Never build, display, or paraphrase code yourself — that is always
     handled automatically from `active_lines`.
   - Position your own content in the lower half of the frame (e.g. shift
     it DOWN, or keep it at/below ORIGIN) — the upper area is reserved for
     the automatic code snippet; never place your own mobjects there.
   - Keep it minimal, clean, and aligned: one or two short, purposeful
     elements per scene, not a scattered collage. Clarity over decoration.

Return the scenes in narrative order with sequential integer `scene_id` starting at 1.

## Video title
Also produce a short `title` for this video: 10-15 characters, in English,
Title Case, no trailing punctuation, naming what the code does (e.g.
"Bubble Sort", "Fibonacci Calc", "Login Flow"). This is what shows up in the
user's video list, so favor a short recognizable label over a full description.
"""

GENERATION_SCHEMA = {
    "type": "json_schema",
    "name": "manim_scenes",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "integer"},
                        "narration": {"type": "string"},
                        "manim_code": {"type": "string"},
                        "active_lines": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": ["scene_id", "narration", "manim_code", "active_lines"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["title", "scenes"],
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
- `MathTex(...)`/`Tex(...)` string arguments MUST be raw strings, e.g.
  `MathTex(r"\frac{a}{b}")` — a plain string corrupts backslash-letter LaTeX
  commands via Python's own escape processing (this is a common real cause
  of a "latex error converting to dvi" failure).
- Never call `Code(...)` or otherwise build/reproduce the source code — all
  code display is handled automatically outside this correction step. If
  scene 1 is among the failed scenes, its fixed body must still be just
  `pass` (it has no other content). For any other scene, keep your own
  content (if any) in the lower half of the frame — the upper area is
  reserved for the automatic code snippet.
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


def _numbered_code(user_code: str) -> str:
    """Line-numbered view of the user's code, shown to the model so it can
    set each scene's `active_lines` accurately — the numbers correspond
    exactly to a plain `user_code.split("\\n")` (1-indexed), matching how
    the automatic code snippets are extracted."""
    lines = user_code.split("\n")
    width = len(str(len(lines)))
    return "\n".join(f"{i:>{width}}  {line}" for i, line in enumerate(lines, start=1))


def build_generation_user_message(user_code: str, complexity: str = DEFAULT_COMPLEXITY) -> str:
    directive = COMPLEXITY_DIRECTIVES.get(complexity, COMPLEXITY_DIRECTIVES[DEFAULT_COMPLEXITY])
    return (
        f"{directive}\n\n"
        "Explain this code (line numbers below are for `active_lines` "
        "reference only, not part of the source):\n\n"
        f"```python\n{_numbered_code(user_code)}\n```"
    )


def build_buggy_generation_user_message(
    user_code: str, code_error: str, complexity: str = DEFAULT_COMPLEXITY
) -> str:
    """Generation message for broken/non-compiling code. Scene 1's automatic
    full-code intro shows the ORIGINAL broken code (never a rewritten
    version); step scenes point at the broken line(s) via active_lines."""
    directive = COMPLEXITY_DIRECTIVES.get(complexity, COMPLEXITY_DIRECTIVES[DEFAULT_COMPLEXITY])
    return (
        f"{directive}\n\n"
        "The following Python code does NOT compile / has an error (line "
        "numbers below are for `active_lines` reference only, not part of "
        "the source):\n\n"
        f"```python\n{_numbered_code(user_code)}\n```\n\n"
        f"The error is: {code_error}\n\n"
        "Create scenes that:\n"
        "- Scene 1: intro narration describing that this code has a bug "
        "(the system shows the original broken code automatically).\n"
        "- Step scenes: use `active_lines` to point at the broken line(s), "
        "and explain in the narration how it could have been written so "
        "it would work — do not display a rewritten version of the code "
        "yourself, the automatic snippet always shows the original.\n"
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


# ---------------------------------------------------------------------------
# Code display injection — deterministic, NOT LLM-authored.
#
# Applied once in AIAgentLambda after every scene's own content has already
# passed validation/correction, so the self-correction loop never has to see
# or reason about this boilerplate, and the model never risks the `.code[i]`
# / removed-kwarg pitfalls that come from hand-authoring Code mobject calls.
#
# Two flows, matching the required visual structure:
#   - Scene 1 ("intro"): the FULL code, full-screen, FadeIn -> hold -> FadeOut,
#     before any step scene begins.
#   - Scene 2+ ("step"): ONLY the scene's active_lines, extracted verbatim
#     from user_code (never LLM-transcribed) as a short snippet, FadeIn near
#     the top of the frame. No full code is ever shown again after scene 1.
# ---------------------------------------------------------------------------

CONSTRUCT_MARKER = "def construct(self):"
INTRO_MIN_HOLD_SECONDS = 3.0
INTRO_MAX_HOLD_SECONDS = 20.0


def intro_hold_seconds(narration: str) -> float:
    """How long the full-code intro should hold on screen, matched to how
    long scene 1's narration takes to speak (~150 words/minute), clamped to
    a sane range."""
    words = len((narration or "").split())
    seconds = (words / 150) * 60
    return max(INTRO_MIN_HOLD_SECONDS, min(INTRO_MAX_HOLD_SECONDS, seconds))


def build_intro_code_snippet(user_code: str, hold_seconds: float) -> str:
    """construct()-body statements for the intro scene: the full user code,
    shown large and centered via the real Code mobject, held for
    `hold_seconds`, then faded out."""
    code_literal = repr(user_code)
    return textwrap.dedent(f"""\
        __ca_full_code = {code_literal}
        __ca_intro_code = Code(
            code_string=__ca_full_code, language="python",
            add_line_numbers=True, paragraph_config={{"font_size": 20}},
        )
        __ca_intro_code.scale_to_fit_width(config.frame_width * 0.85)
        if __ca_intro_code.height > config.frame_height * 0.85:
            __ca_intro_code.scale_to_fit_height(config.frame_height * 0.85)
        __ca_intro_code.move_to(ORIGIN)
        self.play(FadeIn(__ca_intro_code))
        self.wait({hold_seconds})
        self.play(FadeOut(__ca_intro_code))
        """)


def build_step_code_snippet(user_code: str, active_lines) -> str:
    """construct()-body statements for a step scene: ONLY the given
    1-indexed lines, extracted verbatim from user_code, shown as a small
    Code snippet faded in near the top of the frame. Returns "" (no-op) if
    there are no valid active_lines."""
    src_lines = user_code.split("\n")
    total = len(src_lines)
    active = sorted({ln for ln in (active_lines or []) if isinstance(ln, int) and 1 <= ln <= total})
    if not active:
        return ""
    snippet_text = "\n".join(src_lines[ln - 1] for ln in active)
    code_literal = repr(snippet_text)
    return textwrap.dedent(f"""\
        __ca_snippet = {code_literal}
        __ca_step_code = Code(
            code_string=__ca_snippet, language="python",
            add_line_numbers=False, paragraph_config={{"font_size": 30}},
        )
        if __ca_step_code.width > config.frame_width * 0.8:
            __ca_step_code.scale_to_fit_width(config.frame_width * 0.8)
        __ca_step_code.move_to(UP * 2.4)
        self.play(FadeIn(__ca_step_code))
        """)


def inject_code_display(manim_code: str, user_code: str, scene: dict) -> str:
    """Splice the appropriate deterministic snippet (intro for scene_id 1,
    step snippet otherwise) right after `def construct(self):`. If the
    marker isn't found (shouldn't happen — the lint tier requires a
    construct method), the code is returned unchanged rather than raising."""
    idx = manim_code.find(CONSTRUCT_MARKER)
    if idx == -1:
        return manim_code
    if scene.get("scene_id") == 1:
        body = build_intro_code_snippet(user_code, intro_hold_seconds(scene.get("narration", "")))
    else:
        body = build_step_code_snippet(user_code, scene.get("active_lines", []))
    if not body:
        return manim_code
    insert_at = manim_code.index("\n", idx) + 1
    snippet = textwrap.indent(body, " " * 8)
    return manim_code[:insert_at] + snippet + manim_code[insert_at:]
