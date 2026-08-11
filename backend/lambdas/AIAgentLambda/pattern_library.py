"""Curated pattern library for long-form algorithm visualizations.

Free-form LLM generation of a long, structurally rigid "full dry run"
animation (persistent array-of-boxes, moving index pointers, in-place
value swaps, all synced to a real execution trace) is unreliable at that
length — this module is the alternative for KNOWN algorithm shapes: a
small, hand-vetted library of Manim templates. When the user's code
structurally matches one AND is verified to behave the same way (executed
against sample data and compared to a canonical reference implementation),
the matched template is used instead of asking the model to freehand-write
the animation. Anything that doesn't match falls through to the existing
free-form pipeline untouched — a library bug or a near-miss must never
break a job that would have worked fine otherwise.

Registry shape mirrors poc/ast_service/registry.py's parser-registry idiom
elsewhere in this repo (not a functional dependency, just the same
convention): a list of PatternSpec entries, each pluggable independently.

Scope: exactly one pattern for now (bubble_sort). Add more the same way —
matcher + verifier + render_body — without touching existing entries.
"""

import ast
import logging
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger()

VERIFY_TIMEOUT_SECONDS = 10

DEFAULT_SAMPLE_DATA = [5, 2, 8, 1, 4]

_INTRO_STUB = (
    "from manim import *\n\n\n"
    "class Scene1(Scene):\n"
    "    def construct(self):\n"
    "        pass\n"
)


@dataclass
class MatchInfo:
    func_name: str
    sample_data: list


@dataclass
class PatternSpec:
    name: str
    matcher: Callable[[ast.Module], Optional[MatchInfo]]
    verifier: Callable[[str, MatchInfo], bool]
    render_body: Callable[[MatchInfo], str]


@dataclass
class MatchedPattern:
    spec: PatternSpec
    info: MatchInfo

    @property
    def name(self) -> str:
        return self.spec.name

    def build_scenes(self, intro_narration: str, dry_run_narration: str) -> list:
        """The fixed 2-scene skeleton for a matched job: scene 1 is the
        usual trivial intro stub (inject_code_display fills in the real
        full-code display, same as every other job); scene 2 is the
        template's own complete visualization, untouched by
        inject_code_display since long_form jobs skip step-scene
        injection (see prompts.py) — it already IS the whole scene."""
        return [
            {
                "scene_id": 1,
                "narration": intro_narration,
                "manim_code": _INTRO_STUB,
                "active_lines": [],
            },
            {
                "scene_id": 2,
                "narration": dry_run_narration,
                "manim_code": _wrap_scene(2, self.spec.render_body(self.info)),
                "active_lines": [],
            },
        ]


def _wrap_scene(scene_id: int, body: str) -> str:
    indented = textwrap.indent(body, " " * 8)
    return (
        "from manim import *\n\n\n"
        f"class Scene{scene_id}(Scene):\n"
        "    def construct(self):\n"
        f"{indented}"
    )


# ---------------------------------------------------------------------------
# bubble_sort
# ---------------------------------------------------------------------------

def _binop_plus_one(node, var_name: str) -> bool:
    """True if node is the AST for `<var_name> + 1`."""
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Add)
        and isinstance(node.left, ast.Name) and node.left.id == var_name
        and isinstance(node.right, ast.Constant) and node.right.value == 1
    )


def _adjacent_subscript(node, list_name: str, index_check) -> bool:
    """True if node is `<list_name>[<index matching index_check>]`."""
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name) and node.value.id == list_name
        and index_check(node.slice)
    )


def _find_swap(body, list_name: str, j_name: str) -> bool:
    """`<list_name>[j], <list_name>[j+1] = <list_name>[j+1], <list_name>[j]`
    anywhere in this statement list."""
    is_j = lambda n: isinstance(n, ast.Name) and n.id == j_name
    is_j1 = lambda n: _binop_plus_one(n, j_name)
    for stmt in body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target, value = stmt.targets[0], stmt.value
        if not (isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple)):
            continue
        if len(target.elts) != 2 or len(value.elts) != 2:
            continue
        t0, t1 = target.elts
        v0, v1 = value.elts
        if (
            _adjacent_subscript(t0, list_name, is_j)
            and _adjacent_subscript(t1, list_name, is_j1)
            and _adjacent_subscript(v0, list_name, is_j1)
            and _adjacent_subscript(v1, list_name, is_j)
        ):
            return True
    return False


def _find_compare_and_swap(body, list_name: str, j_name: str) -> bool:
    """`if <list_name>[j] > <list_name>[j+1]: <swap>` anywhere in this
    statement list."""
    is_j = lambda n: isinstance(n, ast.Name) and n.id == j_name
    is_j1 = lambda n: _binop_plus_one(n, j_name)
    for stmt in body:
        if not isinstance(stmt, ast.If):
            continue
        test = stmt.test
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1 and isinstance(test.ops[0], ast.Gt)
            and len(test.comparators) == 1
        ):
            continue
        if (
            _adjacent_subscript(test.left, list_name, is_j)
            and _adjacent_subscript(test.comparators[0], list_name, is_j1)
            and _find_swap(stmt.body, list_name, j_name)
        ):
            return True
    return False


def _is_range_call(node) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range"


def _match_function(func: ast.FunctionDef) -> Optional[str]:
    """Nested `for ... in range(...)` loops, inner one containing an
    adjacent-element compare-and-swap on the function's first parameter.
    Returns the parameter name on match, else None."""
    if not func.args.args:
        return None
    param_name = func.args.args[0].arg
    for outer in ast.walk(func):
        if not (isinstance(outer, ast.For) and isinstance(outer.target, ast.Name) and _is_range_call(outer.iter)):
            continue
        for inner in ast.walk(outer):
            if inner is outer or not (isinstance(inner, ast.For) and isinstance(inner.target, ast.Name) and _is_range_call(inner.iter)):
                continue
            if _find_compare_and_swap(inner.body, param_name, inner.target.id):
                return param_name
    return None


def _literal_int_list(node) -> Optional[list]:
    if not isinstance(node, ast.List):
        return None
    values = []
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, int) and not isinstance(elt.value, bool):
            values.append(elt.value)
        else:
            return None
    return values if 2 <= len(values) <= 8 else None


def _extract_sample_data(tree: ast.Module, func_name: str) -> list:
    """Best-effort: reuse the user's own example numbers if there's an
    obvious literal call site (`func([1, 2, 3])` or `x = [1, 2, 3]` then
    `func(x)`); falls back to DEFAULT_SAMPLE_DATA otherwise. Never errors —
    a miss here just means slightly less personalized numbers, not a
    broken job."""
    var_literals = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            lit = _literal_int_list(node.value)
            if lit is not None:
                var_literals[node.targets[0].id] = lit
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == func_name and node.args:
            arg = node.args[0]
            lit = _literal_int_list(arg)
            if lit is not None:
                return lit
            if isinstance(arg, ast.Name) and arg.id in var_literals:
                return var_literals[arg.id]
    return list(DEFAULT_SAMPLE_DATA)


def match_bubble_sort(tree: ast.Module) -> Optional[MatchInfo]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        param_name = _match_function(node)
        if param_name is None:
            continue
        sample_data = _extract_sample_data(tree, node.name)
        return MatchInfo(func_name=node.name, sample_data=sample_data)
    return None


# Canonical reference implementation, used only for behavioral verification
# (never shown to the user) — plain, unoptimized bubble sort.
_REFERENCE_BUBBLE_SORT = textwrap.dedent("""\
    def __ca_reference_bubble_sort(a):
        a = list(a)
        n = len(a)
        for i in range(n):
            for j in range(0, n - i - 1):
                if a[j] > a[j + 1]:
                    a[j], a[j + 1] = a[j + 1], a[j]
        return a
    """)


def verify_bubble_sort(user_code: str, info: MatchInfo) -> bool:
    """Sandboxed subprocess (same pattern as validator.py's
    _check_dry_run): call the user's own function on the sample data and
    compare its result to the canonical reference on the same input. If
    they diverge — or the call raises, times out, or does anything
    unexpected — the match is rejected."""
    driver = textwrap.dedent(f"""

        if __name__ == "__main__":
            sample = {info.sample_data!r}
            data_copy = list(sample)
            try:
                result = {info.func_name}(data_copy)
            except Exception as e:
                print("VERIFY_FAIL: exception " + repr(e))
                raise SystemExit(1)
            actual = list(result) if result is not None else data_copy
            expected = __ca_reference_bubble_sort(sample)
            if actual == expected:
                print("VERIFY_OK")
                raise SystemExit(0)
            print(f"VERIFY_FAIL: actual={{actual}} expected={{expected}}")
            raise SystemExit(1)
        """)
    script = user_code + "\n\n" + _REFERENCE_BUBBLE_SORT + driver

    with tempfile.TemporaryDirectory(prefix="pattern_verify_") as tmpdir:
        try:
            proc = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=VERIFY_TIMEOUT_SECONDS,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            logger.warning("pattern_library: bubble_sort verify timed out")
            return False

    if proc.returncode == 0 and "VERIFY_OK" in proc.stdout:
        return True
    logger.info("pattern_library: bubble_sort verify failed: %s", (proc.stdout or proc.stderr or "").strip())
    return False


def render_bubble_sort_body(info: MatchInfo) -> str:
    """construct()-body statements for the full bubble-sort dry run: the
    array as boxes, moving j/j+1 pointers, real compare-highlight-swap per
    step, sorted elements turning green — every iteration, no skipping,
    fast per-step run_times. No title, no Code(...) widget (those are the
    pipeline's automatic intro/step display elsewhere); uses the whole
    frame since long_form jobs get no competing snippet (see prompts.py)."""
    return textwrap.dedent(f"""\
        data = {info.sample_data!r}
        n = len(data)

        box_size = 0.9
        boxes = []
        numbers = []
        array_group = VGroup()

        for idx, val in enumerate(data):
            box = Square(side_length=box_size, stroke_color=WHITE, fill_color=BLUE_E, fill_opacity=0.5)
            box.move_to(RIGHT * idx * 1.1)
            num = Text(str(val), font_size=28).move_to(box.get_center())
            idx_label = Text(f"[{{idx}}]", font_size=16, color=GRAY).next_to(box, DOWN, buff=0.15)
            unit = VGroup(box, num, idx_label)
            array_group.add(unit)
            boxes.append(box)
            numbers.append(num)

        array_group.center().shift(UP * 0.6)
        array_label = Text("arr =", font_size=24).next_to(array_group, LEFT, buff=0.3)
        self.play(Create(array_group), Write(array_label))

        # Shorter than a default Arrow(DOWN, UP) (~2 units) on purpose: at
        # the DOWN * 1.3 offset below each box used for pos_j/pos_j1, a
        # full-length arrow's top end reaches back up into the box/index
        # label above it — confirmed by the overlap validator tier, not a
        # style choice.
        pointer_j = Arrow(DOWN * 0.6, UP * 0.6, color=YELLOW, max_stroke_width_to_length_ratio=5, buff=0.1)
        label_j = Text("j", color=YELLOW, font_size=22).next_to(pointer_j, DOWN, buff=0.1)
        group_j = VGroup(pointer_j, label_j)

        pointer_j1 = Arrow(DOWN * 0.6, UP * 0.6, color=ORANGE, max_stroke_width_to_length_ratio=5, buff=0.1)
        label_j1 = Text("j+1", color=ORANGE, font_size=22).next_to(pointer_j1, DOWN, buff=0.1)
        group_j1 = VGroup(pointer_j1, label_j1)

        for i in range(n):
            swapped = False
            for j in range(0, n - i - 1):
                pos_j = boxes[j].get_bottom() + DOWN * 1.3
                pos_j1 = boxes[j + 1].get_bottom() + DOWN * 1.3

                if j == 0 and i == 0:
                    group_j.move_to(pos_j)
                    group_j1.move_to(pos_j1)
                    self.play(FadeIn(group_j), FadeIn(group_j1))
                else:
                    self.play(
                        group_j.animate.move_to(pos_j),
                        group_j1.animate.move_to(pos_j1),
                        run_time=0.3,
                    )

                self.play(
                    boxes[j].animate.set_stroke(YELLOW, width=4),
                    boxes[j + 1].animate.set_stroke(ORANGE, width=4),
                    run_time=0.2,
                )

                if data[j] > data[j + 1]:
                    data[j], data[j + 1] = data[j + 1], data[j]
                    # Explicit position-swap (not Swap()/CyclicReplace):
                    # confirmed via the overlap validator that Swap() leaves
                    # a Group artifact that doesn't land cleanly inside
                    # either box. .animate.move_to(boxes[...].get_center())
                    # keeps each Text its own mobject, position always
                    # derived from the actual box.
                    self.play(
                        numbers[j].animate.move_to(boxes[j + 1].get_center()),
                        numbers[j + 1].animate.move_to(boxes[j].get_center()),
                        run_time=0.5,
                    )
                    numbers[j], numbers[j + 1] = numbers[j + 1], numbers[j]
                    swapped = True

                self.play(
                    boxes[j].animate.set_stroke(WHITE, width=2),
                    boxes[j + 1].animate.set_stroke(WHITE, width=2),
                    run_time=0.15,
                )

            sorted_idx = n - i - 1
            self.play(boxes[sorted_idx].animate.set_fill(GREEN_D, opacity=0.8), run_time=0.3)

            if not swapped:
                for k in range(n - i - 1):
                    boxes[k].set_fill(GREEN_D, opacity=0.8)
                break

        self.play(FadeOut(group_j), FadeOut(group_j1))
        self.wait(0.5)
        """)


PATTERN_SPECS = [
    PatternSpec(
        name="bubble_sort",
        matcher=match_bubble_sort,
        verifier=verify_bubble_sort,
        render_body=render_bubble_sort_body,
    ),
]


def match_pattern(user_code: str) -> Optional[MatchedPattern]:
    """Try every registered pattern in order; return the first that
    structurally matches AND verifies, or None. Any exception anywhere in
    matching/verification is treated as "no match" — a library bug must
    never break a job that would have worked through the free-form
    pipeline."""
    try:
        tree = ast.parse(user_code)
    except SyntaxError:
        return None

    for spec in PATTERN_SPECS:
        try:
            info = spec.matcher(tree)
            if info is None:
                continue
            if not spec.verifier(user_code, info):
                continue
            return MatchedPattern(spec=spec, info=info)
        except Exception:
            logger.exception("pattern_library: spec %s errored during match/verify", spec.name)
            continue
    return None
