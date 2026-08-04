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
  - The `Code` mobject signature changed in ManimCE 0.19:
    `Code(code_string="...", language="python", add_line_numbers=False)`.
    The kwargs `code`, `style`, `insert_line_no`, `font`, and `font_size` no longer exist.
    It also has no `.code` attribute — never index into it like `code_mobject.code[i]`
    to reach individual lines (e.g. to highlight one with SurroundingRectangle). If
    individual lines need to be referenced, build them as separate Text/Paragraph
    mobjects instead of relying on a Code mobject's internals.
- Keep animations simple: Text, Code, MathTex, shapes, arrows, transforms,
  highlighting. No external files, no images, no SVGs, no network access.
- The on-screen animation of a scene should roughly match its narration length
  (use `self.wait(...)` to pad where needed).
- Code must be immediately runnable — it will be compiled and executed for
  validation before rendering.

## Visual style — make it colorful and engaging
- Use ManimCE's color palette deliberately instead of defaulting to plain
  white-on-black: e.g. BLUE, TEAL, GOLD, PURPLE, GREEN, ORANGE, PINK, YELLOW,
  or a specific shade (BLUE_C, TEAL_B, GOLD_D, ...).
- Give distinct elements distinct colors to visually separate concepts —
  e.g. variable names vs. their values, or the element currently being
  discussed vs. everything else.
- A muted dark background via `self.camera.background_color = "#1e1e2e"`
  (or similar) often makes foreground colors read better than pure black.
- Keep contrast high enough to stay readable — avoid low-contrast pairs
  (e.g. dark blue on a dark background), and never rely on color alone to
  convey information; pair it with position or a label too.
- Vary the palette across scenes when the content differs, rather than
  reusing the exact same two or three colors in every single scene.

## Code sidebar — reserve space, don't build it yourself
The full user code is always shown as a persistent sidebar on the LEFT edge
of the screen, in every scene, added automatically by the system — you do
NOT write any code to display it yourself. Your job:
- For each scene, set `active_lines` to the 1-indexed line number(s) — using
  the line numbers shown in the numbered code below — that this scene's
  narration is actually about. An empty list is fine for a scene that has no
  single specific line (e.g. a pure title/overview scene).
- Keep your OWN animation content (titles, explanations, diagrams, code
  snippets you build yourself) in the right ~65% of the frame. Leave the
  left portion of the screen empty — do not position your own mobjects at
  the far left edge, since the code sidebar occupies it.

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
- The `Code` mobject signature changed in ManimCE 0.19:
  `Code(code_string="...", language="python", add_line_numbers=False)`.
  The kwargs `code`, `style`, `insert_line_no`, `font`, and `font_size` no longer exist.
  It also has no `.code` attribute — never index into it like `code_mobject.code[i]`;
  build separate Text/Paragraph mobjects instead if individual lines need referencing.
- If an approach fundamentally cannot work, replace it with a simpler
  animation that conveys the same idea.
- Preserve the original scene's color choices where possible — don't quietly
  revert to plain white-on-black while fixing an unrelated error.
- Keep your content clear of the left ~35% of the frame — a code sidebar is
  added there automatically after your fix, outside this correction step.
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
    the code sidebar is built."""
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
    """Generation message for broken/non-compiling code. The code sidebar
    (added automatically) always shows the ORIGINAL broken code — the model
    explains how it could have been written so it would work, and points
    at the broken line(s) via active_lines rather than rendering the code
    itself."""
    directive = COMPLEXITY_DIRECTIVES.get(complexity, COMPLEXITY_DIRECTIVES[DEFAULT_COMPLEXITY])
    return (
        f"{directive}\n\n"
        "The following Python code does NOT compile / has an error (line "
        "numbers below are for `active_lines` reference only, not part of "
        "the source):\n\n"
        f"```python\n{_numbered_code(user_code)}\n```\n\n"
        f"The error is: {code_error}\n\n"
        "Create scenes that:\n"
        "- Point out where and why it fails, using `active_lines` to "
        "highlight the broken line(s) in the code sidebar (added "
        "automatically — do not render the code yourself).\n"
        "- Explain how it could have been written so that it would work "
        "(describe the correction in the narration; do not display a "
        "rewritten version of the code — the sidebar always shows the "
        "original).\n"
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
# Code sidebar injection — deterministic, NOT LLM-authored.
#
# Applied once in AIAgentLambda after every scene's own content has already
# passed validation/correction, so the self-correction loop never has to see
# or reason about this boilerplate.
#
# Uses the real `Code` mobject (syntax highlighting, line numbers) rather
# than plain Text — but NOT `.code[i]` to reach individual lines, which
# doesn't exist in current ManimCE and crashed real renders earlier (see the
# RENAMED_KWARGS/REMOVED_APIS notes above). The correct attribute, confirmed
# by introspecting an actual Code instance locally (ManimCE 0.19.1), is
# `.code_lines[i]` (0-indexed) — each entry is the VGroup for that source
# line, usable directly with SurroundingRectangle-style positioning.
#
# Verified by real local render (not just ast.parse): a Code mobject's own
# internal background must be added BEFORE the highlight rectangles, or the
# highlight is hidden behind it — self.add(panel_bg, code_mob, *hl_rects),
# highlights last so they sit visibly on top.
#
# Also verified: `.width` read AFTER move_to/align_to repositioning is
# unreliable on a Code mobject (returned a stale/wrong value in testing,
# while get_left()/get_right() stayed correct) — so the width used for the
# highlight rectangles is captured once right after scaling, before any
# repositioning, and reused as a fixed value rather than re-read later.
# ---------------------------------------------------------------------------

CONSTRUCT_MARKER = "def construct(self):"


def build_code_panel_snippet(user_code: str, active_lines) -> str:
    """Manim source (construct()-body statements) rendering `user_code` as an
    always-visible left sidebar (a `Code` mobject), with `active_lines`
    (1-indexed) highlighted. The background band always spans the full frame
    height at a fixed width, regardless of how many lines the code has — so
    it reads as one constant sidebar strip across every scene, not a box
    that resizes per scene."""
    src_lines = user_code.split("\n")
    total = len(src_lines)
    active = sorted({ln for ln in (active_lines or []) if isinstance(ln, int) and 1 <= ln <= total})
    code_literal = repr(user_code)
    active_literal = repr(set(active))
    return textwrap.dedent(f"""\
        __ca_full_code = {code_literal}
        __ca_active = {active_literal}
        __ca_panel_w = config.frame_width * 0.32
        __ca_panel_h = config.frame_height - 0.4
        __ca_panel_bg = Rectangle(
            width=__ca_panel_w, height=__ca_panel_h,
            fill_color="#1E1E2E", fill_opacity=0.92, stroke_color="#3A3A4A", stroke_width=1.5,
        ).to_edge(LEFT, buff=0.2)
        __ca_code = Code(
            code_string=__ca_full_code, language="python",
            add_line_numbers=True, paragraph_config={{"font_size": 16}},
        )
        if __ca_code.width > __ca_panel_w - 0.5:
            __ca_code.scale_to_fit_width(__ca_panel_w - 0.5)
        if __ca_code.height > __ca_panel_h - 0.5:
            __ca_code.scale_to_fit_height(__ca_panel_h - 0.5)
        __ca_code_w = __ca_code.width
        __ca_code.move_to(__ca_panel_bg.get_top(), aligned_edge=UP).shift(DOWN * 0.3)
        __ca_code.align_to(__ca_panel_bg, LEFT).shift(RIGHT * 0.25)
        __ca_code_center_x = (__ca_code.get_left()[0] + __ca_code.get_right()[0]) / 2
        __ca_hl_rects = [
            Rectangle(width=__ca_code_w - 0.1, height=__ca_code.code_lines[i - 1].height + 0.08,
                      fill_color="#FFD866", fill_opacity=0.22, stroke_width=0)
            .move_to(__ca_code_center_x * RIGHT + __ca_code.code_lines[i - 1].get_center()[1] * UP)
            for i in __ca_active
        ]
        self.add(__ca_panel_bg, __ca_code, *__ca_hl_rects)
        """)


def inject_code_panel(manim_code: str, user_code: str, active_lines) -> str:
    """Splice the deterministic code-sidebar snippet right after
    `def construct(self):` in a scene's manim_code. If the marker isn't
    found (shouldn't happen — the lint tier requires a construct method),
    the code is returned unchanged rather than raising."""
    idx = manim_code.find(CONSTRUCT_MARKER)
    if idx == -1:
        return manim_code
    insert_at = manim_code.index("\n", idx) + 1
    snippet = textwrap.indent(build_code_panel_snippet(user_code, active_lines), " " * 8)
    return manim_code[:insert_at] + snippet + manim_code[insert_at:]
