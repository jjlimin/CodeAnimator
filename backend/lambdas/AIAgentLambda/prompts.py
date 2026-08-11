"""System prompts and JSON schemas for the Manim scene-generation agent."""

import ast
import textwrap

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

LONG_FORM_LINE_THRESHOLD = 15


def is_long_form(user_code: str) -> bool:
    """Heuristic, deterministic (no model judgment): true when the input is
    complex/long enough that a per-step code snippet on every scene would
    clutter more than help — a loop nested inside another loop, or more
    than LONG_FORM_LINE_THRESHOLD non-blank/non-comment lines. Drives
    whether step scenes get the automatic code snippet at all (see
    inject_code_display) and which zone-guidance text the model sees
    (build_generation_system_prompt)."""
    try:
        tree = ast.parse(user_code)
    except SyntaxError:
        return False

    max_loop_depth = 0

    def _walk(node, depth):
        nonlocal max_loop_depth
        for child in ast.iter_child_nodes(node):
            child_depth = depth + 1 if isinstance(child, (ast.For, ast.While)) else depth
            max_loop_depth = max(max_loop_depth, child_depth)
            _walk(child, child_depth)

    _walk(tree, 0)
    nonblank = [
        ln for ln in user_code.split("\n")
        if ln.strip() and not ln.strip().startswith("#")
    ]
    return max_loop_depth >= 2 or len(nonblank) > LONG_FORM_LINE_THRESHOLD


_GENERATION_PROMPT_TEMPLATE = """\
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

## Loops that repeat many times — first passes, fast-forward, last pass, result
If the code has a loop (or nested loops) that would repeat many times over
the same data (a sort, a search, a simulation, ...), never create a scene
per pass — that is slow and repetitive to watch, and never just stop after
a few passes either — the viewer must see the run actually finish. Cover
the FULL run, first iteration to last, structured as:
1. Animate the first TWO iterations concretely, narrated, with real values
   — one iteration alone is not enough to establish the pattern.
2. Fast-forward through the remaining MIDDLE iterations in a single scene
   with NO per-iteration narration — this scene's narration should be one
   short line like "this repeats for the rest of the data," while the
   animation itself moves quickly through the remaining steps (short
   `run_time`s, minimal `self.wait`) rather than describing each one.
3. Animate the LAST iteration concretely, narrated, the same way as the
   first two — don't let the run just trail off into the fast-forward.
4. Finish with a scene showing the final result/state the loop produces
   (e.g. the fully sorted array), so the viewer sees where it ends up.

## Infinite or unbounded loops
If a loop has no reachable termination given the code shown (e.g.
`while True:` / `while 1:` with no `break` anywhere in its body, or a
condition that can never become false from what's visible), do NOT animate
it as if it completes — there is no final result to show. Instead: animate
ONE representative iteration concretely, and state plainly in the narration
that the loop runs indefinitely / until stopped externally — name the
specific condition if it's apparent from the code (e.g. "until `running` is
set to False elsewhere").

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
   scene's narration is about, even in jobs where no snippet will be shown
   (see below) — it's still required, just for internal bookkeeping there.
   Keep it a small, usually contiguous range (1-4 lines).

3. **In step scenes, your own `manim_code` may add supporting visuals** —
   real diagrams, not more text:
   - Never build, display, or paraphrase code yourself — that is always
     handled automatically from `active_lines`. This also means: do NOT
     recreate a code-like statement as your own Text/MathTex (e.g. writing
     out `n = 5` or `arr[i] = 3` to restate an assignment) — that just
     repeats what the automatic snippet already shows on screen and adds
     zero information.
   - Prefer actual diagrams over prose: rectangles/boxes for array or list
     elements (with index and value labels), arrows for pointers, swaps, or
     comparisons, circles/nodes for other structures, number lines, etc. A
     short label (e.g. a single variable name beside a box) is fine as an
     annotation ON a diagram, but a diagram — not a sentence or restated
     assignment — should carry the explanation.
   - If the code operates on data with no concrete values in view (e.g. a
     function parameter with no sample call shown), invent a small, simple
     example of your own (e.g. a 4-6 element array) purely for this visual
     — don't change what the narration says the code does, just ground the
     diagram in concrete numbers so there is something to actually animate.
__ZONE_GUIDANCE__
   - Center your content within the frame — horizontally near x = 0,
     vertically balanced within whatever region is available (see above) —
     and leave a visible margin from all four frame edges; nothing should
     touch or bleed off the screen border.
   - Keep it minimal, clean, and aligned: one or two short, purposeful
     elements per scene, not a scattered collage. Clarity over decoration.
   - Position from the object, not a guess: any pointer, arrow, or label
     tied to a specific element of a structure you drew (an array box, a
     node, ...) must derive its position from that element's own mobject —
     e.g. `.next_to(boxes[i], DOWN)` or `boxes[i].get_center()` — never a
     hand-picked coordinate. If the index changes within the same scene
     (each loop pass), move the SAME pointer mobject with
     `.animate.move_to(...)`; do not create a new pointer per step.
   - Replace the value, don't stack it: keep at most ONE Text mobject per
     tracked variable. When its value changes, `Transform(old, new)` (or
     `.animate.become(...)`) that same mobject in place — never `FadeIn`
     or `Write` a second value while the first is still visible on screen.
   - Size the box to the value, not the other way around: build the value
     Text first, then wrap it with `SurroundingRectangle(value, buff=...)`
     so the box always fits what's inside — a fixed box size chosen
     independently of the text is how values end up spilling past its
     border. Show a variable's name as a small label BELOW the box via
     `.next_to(box, DOWN, buff=...)`, not squeezed inside competing with
     the value.

## Reference examples — model these techniques, not this exact code
Four excerpts at the animation quality expected for a step scene's own
content. Never copy a title or a `Code(...)` call from these — that part of
the originals is exactly what the automatic code display already replaces.
Treat them as technique references: invent your own values/labels to fit
the actual code being explained, and follow the zone guidance above for
where content may go.

Example — tracing a reference/pointer (e.g. explaining `b = a`):
```python
box = Square(side_length=0.7, stroke_color=WHITE, fill_color=DARK_GRAY, fill_opacity=0.6)
value = Text("3", font_size=24).move_to(box.get_center())
obj = VGroup(box, value).move_to(DOWN * 2 + RIGHT * 1.5)

var_a = Text("a", font_size=28, color=YELLOW).move_to(DOWN * 1.2 + LEFT * 2)
pointer_a = Arrow(var_a.get_right(), obj.get_left(), color=YELLOW, buff=0.15)
var_b = Text("b", font_size=28, color=ORANGE).move_to(DOWN * 3.2 + LEFT * 2)
pointer_b = Arrow(var_b.get_right(), obj.get_bottom(), color=ORANGE, buff=0.15)

self.play(FadeIn(obj), FadeIn(var_a), GrowArrow(pointer_a))
self.wait(0.4)
self.play(FadeIn(var_b), GrowArrow(pointer_b))
self.play(pointer_a.animate.set_color(GREEN), pointer_b.animate.set_color(GREEN), run_time=0.4)
self.wait(0.6)
```
Good because: a real `Arrow` shows the relationship instead of a sentence
describing it, `GrowArrow` introduces each pointer as its own beat, and the
later `.animate.set_color(...)` traces which variable is active — three
distinct animation beats, not one fade-and-hold.

Example — comparing and swapping two array elements:
```python
values = [5, 2, 8]
boxes = VGroup(*[
    Square(side_length=0.9, fill_color=BLUE_E, fill_opacity=0.5) for _ in values
]).arrange(RIGHT, buff=0.3).move_to(DOWN * 1.4)
labels = VGroup(*[
    Text(str(v), font_size=28).move_to(b.get_center()) for v, b in zip(values, boxes)
])
self.play(FadeIn(boxes), FadeIn(labels))

pointer_j = Arrow(DOWN, UP, color=YELLOW, buff=0.1).next_to(boxes[0], DOWN, buff=0.2)
pointer_k = Arrow(DOWN, UP, color=ORANGE, buff=0.1).next_to(boxes[1], DOWN, buff=0.2)
self.play(FadeIn(pointer_j), FadeIn(pointer_k))

self.play(boxes[0].animate.set_stroke(YELLOW, width=4),
          boxes[1].animate.set_stroke(ORANGE, width=4), run_time=0.3)
self.play(Swap(labels[0], labels[1]), run_time=0.7)
self.play(boxes[0].animate.set_stroke(WHITE, width=2),
          boxes[1].animate.set_stroke(WHITE, width=2), run_time=0.3)
self.wait(0.4)
```
Good because: the array is real boxes with index pointers that could move
(`.animate.move_to(...)`) between steps, a comparison is shown by
highlighting stroke color rather than described in prose, and `Swap(...)` —
a real animation — moves the values, instead of redrawing text in place.

Example — a moving loop pointer with a value that gets reassigned:
```python
values = [4, 2, 5, 7]
boxes = VGroup(*[
    Square(side_length=0.8, fill_color=BLUE_E, fill_opacity=0.5) for _ in values
]).arrange(RIGHT, buff=0.3).move_to(DOWN * 2)
labels = VGroup(*[
    Text(str(v), font_size=28).move_to(b.get_center()) for v, b in zip(values, boxes)
])
self.play(FadeIn(boxes), FadeIn(labels))

pointer = Arrow(DOWN, UP, color=YELLOW, buff=0.1).next_to(boxes[0], DOWN, buff=0.2)
name = Text("num", font_size=24, color=YELLOW).next_to(pointer, DOWN, buff=0.15)
self.play(FadeIn(pointer), FadeIn(name))

value = Text(str(values[0]), font_size=32, color=YELLOW).next_to(pointer, UP, buff=0.3)
self.play(Write(value))

# num = num ** 2 — reassign in place, don't add a second value mobject
new_value = Text(str(values[0] ** 2), font_size=32, color=YELLOW).move_to(value)
self.play(Transform(value, new_value))
self.wait(0.4)

# next iteration — move the SAME pointer/name/value, don't recreate them
self.play(
    pointer.animate.next_to(boxes[1], DOWN, buff=0.2),
    name.animate.next_to(boxes[1], DOWN, buff=0.55),
    run_time=0.4,
)
self.play(Transform(value, Text(str(values[1]), font_size=32, color=YELLOW).next_to(pointer, UP, buff=0.3)))
self.wait(0.4)
```
Good because: the pointer's position always comes from `boxes[i]`, not a
guessed coordinate, so it stays aligned with the element it refers to; the
SAME `pointer`/`name`/`value` mobjects are reused and moved/transformed
across iterations instead of spawning new copies; and a reassignment
(`num ** 2`) transforms the existing value in place, so the old number is
never left on screen next to the new one.

Example — a value box that always fits its content:
```python
value = Text("7", font_size=32, color=WHITE)
box = SurroundingRectangle(value, color=BLUE_E, fill_color=BLUE_E, fill_opacity=0.5, buff=0.25)
name = Text("x", font_size=20, color=GRAY).next_to(box, DOWN, buff=0.15)
group = VGroup(box, value, name).move_to(DOWN * 2)
self.play(FadeIn(group))
```
Good because: `SurroundingRectangle` sizes itself from the value's actual
width/height plus `buff` — the box can never be smaller than what it holds,
regardless of digit count. The variable's name sits below as a small label
via `.next_to(box, DOWN, ...)`, never crammed inside the box competing with
the value.

Return the scenes in narrative order with sequential integer `scene_id` starting at 1.

## Video title
Also produce a short `title` for this video: 10-15 characters, in English,
Title Case, no trailing punctuation, naming what the code does (e.g.
"Bubble Sort", "Fibonacci Calc", "Login Flow"). This is what shows up in the
user's video list, so favor a short recognizable label over a full description.
"""

_ZONE_GUIDANCE_STANDARD = """\
   - The top ~third of the frame (roughly y > 0, up to the very top) is
     reserved for the automatic code snippet and is completely off-limits —
     this applies to EVERY mobject you create, with no exception for
     titles, captions, or headings. Do not add a title/heading text at the
     top of a step scene at all; if a diagram needs a label, place it
     directly beside or above the diagram itself, still within the
     allowed lower region below. Never use `.to_edge(UP)` or similar.
   - Your own content's TOP EDGE — not just its center — must stay at or
     below y = 0: a large/tall mobject centered exactly at ORIGIN still
     overflows upward into the reserved zone, so size and place it with
     that in mind (`.move_to(DOWN * 2)` is a safe default anchor).\
"""

_ZONE_GUIDANCE_LONG_FORM = """\
   - No automatic code snippet appears in step scenes for this job — the
     code is long/complex enough that a per-step snippet would clutter more
     than it would help. You have the WHOLE frame for the visualization;
     still no title/heading text anywhere (keep the frame about the
     algorithm's state, not chrome). A centered default like
     `.move_to(ORIGIN)` is fine now — there is no reserved zone to avoid.\
"""


def build_generation_system_prompt(long_form: bool = False) -> str:
    """Assemble the full generation system prompt. `long_form` (see
    is_long_form) swaps in different zone guidance: standard jobs reserve
    the top ~third for the automatic step-scene snippet; long-form jobs get
    no step snippet at all (see inject_code_display) so the model is told
    it has the whole frame instead."""
    zone = _ZONE_GUIDANCE_LONG_FORM if long_form else _ZONE_GUIDANCE_STANDARD
    return _GENERATION_PROMPT_TEMPLATE.replace("__ZONE_GUIDANCE__", zone)

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

# ---------------------------------------------------------------------------
# Pattern-matched narration — used only when pattern_library.match_pattern()
# finds and verifies a known algorithm shape (see pattern_library.py). The
# animation code is already fixed (a hand-vetted template, not LLM-authored)
# so this prompt asks for narration text only, nothing else.
# ---------------------------------------------------------------------------

PATTERN_NARRATION_SYSTEM_PROMPT = """\
You are a Python educator writing narration for a pre-built animation.

The visualization for this video is already written and fixed — you are
NOT writing any Manim code, only narration text for two scenes:

1. `intro_narration`: preface/overview for the intro scene (the system
   shows the user's full source code on screen automatically while this
   plays) — what the algorithm does, in general terms. 15-30 seconds
   (40-75 words).
2. `dry_run_narration`: narration for the scene that visually runs the
   full algorithm on a small example array from start to finish (every
   comparison and swap, fast-paced) — a short overview of what to watch
   for (e.g. "watch the two pointers compare neighbors and swap them when
   they're out of order, sweeping through the array pass after pass until
   it's sorted"). Do NOT narrate individual comparisons or swaps one by
   one — the animation is fast and self-explanatory; describe the pattern
   once. 15-30 seconds (40-75 words).

Also produce a short `title`: 10-15 characters, in English, Title Case, no
trailing punctuation, naming what the algorithm does (e.g. "Bubble Sort").
"""

PATTERN_NARRATION_SCHEMA = {
    "type": "json_schema",
    "name": "pattern_narration",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "intro_narration": {"type": "string"},
            "dry_run_narration": {"type": "string"},
        },
        "required": ["title", "intro_narration", "dry_run_narration"],
        "additionalProperties": False,
    },
}


def build_pattern_narration_user_message(user_code: str, pattern_name: str) -> str:
    return (
        f"The user's code implements: {pattern_name.replace('_', ' ')}.\n\n"
        "Original source (shown automatically in the intro, for your "
        "context only — do not transcribe it):\n\n"
        f"```python\n{user_code}\n```"
    )


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
        "count that fits the input's complexity. When a step involves a "
        "variable, array/list, or other standard data structure changing, "
        "add a simple visual for it (e.g. labeled boxes) synced to that "
        "moment in the narration — only where it genuinely aids "
        "understanding, not for every line."
    ),
    "detailed": (
        "Requested depth: DETAILED WALKTHROUGH. Go step by step through the logic, "
        "how the data changes, and notable edge cases. Be thorough: use more "
        "scenes as needed, total narration 120-180 seconds. When a step "
        "involves a variable, array/list, or other standard data "
        "structure/memory, draw and update it on screen (e.g. labeled "
        "boxes, index markers, values changing) precisely in sync with the "
        "narration as the code manipulates it — this is expected at this "
        "depth. Keep each diagram clean and minimal and stay faithful to "
        "what the code actually does; don't let it crowd the frame or "
        "drift from the code's real behavior."
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


def inject_code_display(manim_code: str, user_code: str, scene: dict, long_form: bool = False) -> str:
    """Splice the appropriate deterministic snippet (intro for scene_id 1,
    step snippet otherwise) right after `def construct(self):`. If the
    marker isn't found (shouldn't happen — the lint tier requires a
    construct method), the code is returned unchanged rather than raising.

    `long_form` (see is_long_form): step scenes (scene_id != 1) get NO
    snippet at all — the intro's full-code display is still shown as
    normal, only the repeated per-step boxes are skipped."""
    idx = manim_code.find(CONSTRUCT_MARKER)
    if idx == -1:
        return manim_code
    if scene.get("scene_id") == 1:
        body = build_intro_code_snippet(user_code, intro_hold_seconds(scene.get("narration", "")))
    elif long_form:
        return manim_code
    else:
        body = build_step_code_snippet(user_code, scene.get("active_lines", []))
    if not body:
        return manim_code
    insert_at = manim_code.index("\n", idx) + 1
    snippet = textwrap.indent(body, " " * 8)
    return manim_code[:insert_at] + snippet + manim_code[insert_at:]
