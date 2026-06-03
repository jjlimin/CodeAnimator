"""
Renderer - The Artist

Visual components for the CodeAnimator engine.
All Text uses MONO_FONT for consistent, readable, monospace rendering.
"""

from typing import List, Dict, Any, Optional, Tuple
from manim import (
    VGroup, Rectangle, RoundedRectangle, Text, Arrow, Line, Circle,
    FadeIn, FadeOut, Transform, AnimationGroup, ApplyMethod,
    UP, DOWN, LEFT, RIGHT, ORIGIN, WHITE, BLACK, GREEN, RED,
    YELLOW, BLUE, ORANGE, PURE_RED, ManimColor,
    VMobject,
)

# Defined here because PURE_GREEN is not exported by manim 0.18
PURE_GREEN = GREEN

# Primary monospace font — DejaVu Sans Mono ships with most Linux/Docker images.
# Swap to "Roboto Mono" or "Consolas" if installed in the container.
MONO_FONT = "DejaVu Sans Mono"

# Stroke colors keyed by variable type
TYPE_COLORS: Dict[str, Any] = {
    "int":   WHITE,
    "float": YELLOW,
    "str":   BLUE,
    "bool":  GREEN,
    "auto":  WHITE,
}

# Joyful / Solarized palette — for algorithm-role coloring
JOYFUL: Dict[str, Any] = {
    "current": ManimColor("#268BD2"),   # solarized blue  — element under examination
    "sorted":  ManimColor("#2AA198"),   # solarized cyan  — final sorted position
    "pivot":   ManimColor("#CB4B16"),   # solarized orange — quicksort pivot
    "compare": ManimColor("#B58900"),   # solarized yellow — pair being compared
    "accent":  ManimColor("#D33682"),   # solarized magenta — special highlight
    "success": ManimColor("#859900"),   # solarized green  — milestone achieved
    "default": WHITE,
}

# Subtle tinted fill for algorithm-role cells
JOYFUL_FILL: Dict[str, Any] = {
    "current": ManimColor("#0D2A40"),
    "sorted":  ManimColor("#0A2520"),
    "pivot":   ManimColor("#2A1408"),
    "compare": ManimColor("#28220A"),
    "accent":  ManimColor("#280A20"),
    "success": ManimColor("#1A2005"),
    "default": BLACK,
}


# ---------------------------------------------------------------------------
# Core box types
# ---------------------------------------------------------------------------

class ValueBox(VGroup):
    """Single numeric / generic variable: rounded box + label + value."""

    def __init__(
        self,
        label: str,
        value: str,
        var_type: str = "auto",
        box_width: float = 2.3,
        box_height: float = 0.95,
    ):
        stroke = TYPE_COLORS.get(var_type, WHITE)

        box = RoundedRectangle(
            corner_radius=0.12,
            width=box_width,
            height=box_height,
            stroke_color=stroke,
            stroke_width=2,
            fill_color=BLACK,
            fill_opacity=1,
        )
        label_text = Text(label, font=MONO_FONT, color=stroke, font_size=17)
        value_text = Text(str(value), font=MONO_FONT, color=WHITE, font_size=20)

        # Fit oversized text
        for t, limit in ((label_text, box_width - 0.2), (value_text, box_width - 0.2)):
            if t.width > limit:
                t.scale_to_fit_width(limit)

        label_text.move_to(box.get_center() + UP * 0.24)
        value_text.move_to(box.get_center() + DOWN * 0.24)

        super().__init__(box, label_text, value_text)
        self.box = box
        self.label_text = label_text
        self.value_text = value_text
        self.label = label
        self.value = str(value)
        self.var_type = var_type


class StringBox(VGroup):
    """String variable: blue stroke, value shown in double-quotes."""

    def __init__(
        self,
        label: str,
        value: str,
        box_width: float = 2.6,
        box_height: float = 0.95,
    ):
        box = RoundedRectangle(
            corner_radius=0.12,
            width=box_width,
            height=box_height,
            stroke_color=BLUE,
            stroke_width=2,
            fill_color=BLACK,
            fill_opacity=1,
        )
        label_text = Text(label, font=MONO_FONT, color=BLUE, font_size=17)
        value_text = Text(f'"{value}"', font=MONO_FONT, color=WHITE, font_size=18)

        for t, limit in ((label_text, box_width - 0.2), (value_text, box_width - 0.2)):
            if t.width > limit:
                t.scale_to_fit_width(limit)

        label_text.move_to(box.get_center() + UP * 0.24)
        value_text.move_to(box.get_center() + DOWN * 0.24)

        super().__init__(box, label_text, value_text)
        self.box = box
        self.label_text = label_text
        self.value_text = value_text
        self.label = label
        self.value = value
        self.var_type = "str"


class BooleanBox(VGroup):
    """Boolean variable: green stroke for True, red for False."""

    def __init__(
        self,
        label: str,
        value,
        box_width: float = 2.3,
        box_height: float = 0.95,
    ):
        bool_val = str(value).strip().lower() in ("true", "1", "yes")
        color = GREEN if bool_val else RED
        display = "True" if bool_val else "False"

        box = RoundedRectangle(
            corner_radius=0.12,
            width=box_width,
            height=box_height,
            stroke_color=color,
            stroke_width=2.5,
            fill_color=BLACK,
            fill_opacity=1,
        )
        label_text = Text(label, font=MONO_FONT, color=color, font_size=17)
        value_text = Text(display, font=MONO_FONT, color=color, font_size=20, weight="BOLD")

        for t, limit in ((label_text, box_width - 0.2), (value_text, box_width - 0.2)):
            if t.width > limit:
                t.scale_to_fit_width(limit)

        label_text.move_to(box.get_center() + UP * 0.24)
        value_text.move_to(box.get_center() + DOWN * 0.24)

        super().__init__(box, label_text, value_text)
        self.box = box
        self.label_text = label_text
        self.value_text = value_text
        self.label = label
        self.value = display
        self.var_type = "bool"
        self.bool_val = bool_val


# ---------------------------------------------------------------------------
# Collection types
# ---------------------------------------------------------------------------

class BoxSeries(VGroup):
    """List / array as horizontal cells with index numbers below.

    cell_states: optional dict mapping cell index (int) to a role string
    ("current", "sorted", "pivot", "compare", "accent", "default").
    Cells with a role get a Joyful accent color and tinted fill.
    """

    def __init__(
        self,
        values: List[str],
        label: str = "",
        box_width: float = 0.95,
        box_height: float = 0.90,
        spacing: float = 0.06,
        stroke_color=WHITE,
        stroke_width: float = 2,
        cell_states: Optional[Dict[int, str]] = None,
    ):
        cell_states = cell_states or {}
        cells = []
        for i, val in enumerate(values):
            role = cell_states.get(i, "default")
            border_color = JOYFUL.get(role, stroke_color)
            fill_color   = JOYFUL_FILL.get(role, BLACK)
            text_color   = border_color if role != "default" else WHITE
            bw = stroke_width if role == "default" else stroke_width + 1.0

            cell_box = RoundedRectangle(
                corner_radius=0.08,
                width=box_width,
                height=box_height,
                stroke_color=border_color,
                stroke_width=bw,
                fill_color=fill_color,
                fill_opacity=1,
            )
            cell_text = Text(str(val), font=MONO_FONT, color=text_color, font_size=16)
            if cell_text.width > box_width - 0.1:
                cell_text.scale_to_fit_width(box_width - 0.1)
            cell_text.move_to(cell_box.get_center())

            idx_text = Text(str(i), font=MONO_FONT, color=YELLOW, font_size=11)
            idx_text.next_to(cell_box, DOWN, buff=0.05)

            cell = VGroup(cell_box, cell_text, idx_text)
            cell.shift(RIGHT * i * (box_width + spacing))
            cells.append(cell)

        parts: List[VGroup] = list(cells)
        if label and cells:
            lbl = Text(label, font=MONO_FONT, color=YELLOW, font_size=18)
            lbl.next_to(VGroup(*cells), UP, buff=0.15)
            parts.append(lbl)

        super().__init__(*parts)
        self.values = list(values)
        self.label = label
        self.box_width = box_width
        self.spacing = spacing
        self.cell_states: Dict[int, str] = dict(cell_states)
        self.cells: List[VGroup] = cells  # direct access to individual cell VGroups


class NodeGraph(VGroup):
    """Dictionary as vertical [key]→[value] rows."""

    def __init__(
        self,
        pairs: Dict[str, Any],
        label: str = "",
        key_width: float = 1.5,
        val_width: float = 1.7,
        row_height: float = 0.75,
        row_gap: float = 0.15,
    ):
        rows: List[VGroup] = []

        for i, (key, val) in enumerate(pairs.items()):
            # Key cell
            kb = RoundedRectangle(
                corner_radius=0.08, width=key_width, height=row_height,
                stroke_color=YELLOW, stroke_width=2,
                fill_color=BLACK, fill_opacity=1,
            )
            kt = Text(str(key), font=MONO_FONT, color=YELLOW, font_size=13)
            if kt.width > key_width - 0.1:
                kt.scale_to_fit_width(key_width - 0.1)
            kt.move_to(kb.get_center())
            key_grp = VGroup(kb, kt)

            # Arrow
            arr = Arrow(
                start=ORIGIN, end=RIGHT * 0.45,
                color=WHITE, stroke_width=2,
                max_tip_length_to_length_ratio=0.5, buff=0,
            )

            # Value cell
            vb = RoundedRectangle(
                corner_radius=0.08, width=val_width, height=row_height,
                stroke_color=WHITE, stroke_width=2,
                fill_color=BLACK, fill_opacity=1,
            )
            vt = Text(str(val), font=MONO_FONT, color=WHITE, font_size=13)
            if vt.width > val_width - 0.1:
                vt.scale_to_fit_width(val_width - 0.1)
            vt.move_to(vb.get_center())
            val_grp = VGroup(vb, vt)

            arr.next_to(key_grp, RIGHT, buff=0.1)
            val_grp.next_to(arr, RIGHT, buff=0.1)

            row = VGroup(key_grp, arr, val_grp)
            row.shift(DOWN * i * (row_height + row_gap))
            rows.append(row)

        parts: List[VGroup] = list(rows)
        if label and rows:
            lbl = Text(label, font=MONO_FONT, color=ORANGE, font_size=18)
            lbl.next_to(VGroup(*rows), UP, buff=0.15)
            parts.append(lbl)

        super().__init__(*parts)
        self.pairs = dict(pairs)
        self.label = label


# ---------------------------------------------------------------------------
# Pointer & Console
# ---------------------------------------------------------------------------

class Pointer(VGroup):
    """Downward-pointing arrow for iterator / index indicators."""

    def __init__(self, color=YELLOW, height: float = 0.55):
        arrow = Arrow(
            start=UP * height,
            end=ORIGIN,
            color=color,
            stroke_width=3,
            buff=0,
            max_tip_length_to_length_ratio=0.40,
        )
        super().__init__(arrow)
        self.arrow = arrow
        self.pointer_color = color


class ConsoleOutput(VGroup):
    """Fixed console panel — anchored to bottom-right of frame."""

    def __init__(self, width: float = 7.5, height: float = 2.0, max_lines: int = 6):
        background = RoundedRectangle(
            corner_radius=0.12,
            width=width,
            height=height,
            stroke_color=GREEN,
            stroke_width=2,
            fill_color=BLACK,
            fill_opacity=0.92,
        )
        background.to_corner(DOWN + RIGHT, buff=0.3)

        prompt = Text(">>> output", font=MONO_FONT, color=GREEN, font_size=13)
        prompt.move_to(background.get_top() + DOWN * 0.22)

        self.output_text = Text("", font=MONO_FONT, color=WHITE, font_size=13)
        self.output_text.move_to(background.get_center() + DOWN * 0.12)

        super().__init__(background, prompt, self.output_text)
        self.background = background
        self.console_lines: List[str] = []
        self.max_lines = max_lines

    def add_line(self, line: str) -> None:
        self.console_lines.append(str(line))
        visible = self.console_lines[-self.max_lines :]
        self.output_text.text = "\n".join(visible)
        self.output_text.move_to(self.background.get_center() + DOWN * 0.12)


# ---------------------------------------------------------------------------
# Full-frame chrome: HeaderBar, SidePanelDivider
# ---------------------------------------------------------------------------

class HeaderBar(VGroup):
    """Top banner strip: algorithm name + current step title."""

    HEIGHT = 0.72

    def __init__(self, title: str = ""):
        from manim import config as _cfg
        bg = Rectangle(
            width=_cfg.frame_width,
            height=self.HEIGHT,
            fill_color=ManimColor("#0D1B2A"),
            fill_opacity=1.0,
            stroke_color=ManimColor("#1E3A5C"),
            stroke_width=1.5,
        )
        bg.to_edge(UP, buff=0)

        title_obj = Text(
            title, font=MONO_FONT,
            color=ManimColor("#7FAACC"), font_size=17,
        )
        title_obj.move_to(bg.get_center())
        if title and title_obj.width > _cfg.frame_width - 0.8:
            title_obj.scale_to_fit_width(_cfg.frame_width - 0.8)

        super().__init__(bg, title_obj)
        self.bg        = bg
        self.title_obj = title_obj


class SidePanelDivider(VGroup):
    """Subtle vertical rule + zone label separating primary stage from side panel."""

    def __init__(self, x: float = 2.30, y_top: float = 3.22, y_bottom: float = -2.10):
        line = Line(
            start=[x, y_top, 0], end=[x, y_bottom, 0],
            color=ManimColor("#1A3050"), stroke_width=1.5,
        )
        label = Text(
            "Variables", font=MONO_FONT,
            color=ManimColor("#4A6880"), font_size=11,
        )
        label.move_to([x + 2.45, y_top - 0.26, 0])
        super().__init__(line, label)


# ---------------------------------------------------------------------------
# Auto-scaling helper
# ---------------------------------------------------------------------------

def auto_box_width(n_elements: int, available_width: float = 8.50) -> float:
    """Per-cell width so a BoxSeries fills available_width with n_elements."""
    if n_elements <= 0:
        return 1.00
    per_slot = available_width / n_elements
    return max(0.58, min(1.40, per_slot - 0.10))


# ---------------------------------------------------------------------------
# Comparison & Condition displays
# ---------------------------------------------------------------------------

class ComparisonDisplay(VGroup):
    """Shows [left] <op> [right] with an optional T/F result indicator."""

    def __init__(
        self,
        left_value: str,
        right_value: str,
        operator: str = "==",
        result: Optional[bool] = None,
        box_width: float = 1.35,
        box_height: float = 0.68,
    ):
        result_color = GREEN if result is True else RED if result is False else YELLOW

        def _val_box(text: str, color=YELLOW) -> VGroup:
            b = RoundedRectangle(
                corner_radius=0.08, width=box_width, height=box_height,
                stroke_color=color, stroke_width=2,
                fill_color=BLACK, fill_opacity=1,
            )
            t = Text(text, font=MONO_FONT, color=color, font_size=16)
            if t.width > box_width - 0.1:
                t.scale_to_fit_width(box_width - 0.1)
            t.move_to(b.get_center())
            return VGroup(b, t)

        left_grp = _val_box(left_value)
        op_text  = Text(operator, font=MONO_FONT, color=WHITE, font_size=22)
        right_grp = _val_box(right_value)

        left_grp.shift(LEFT * 1.7)
        right_grp.shift(RIGHT * 1.7)

        parts = [left_grp, op_text, right_grp]

        if result is not None:
            circ = Circle(
                radius=0.32,
                stroke_color=result_color,
                stroke_width=2.5,
                fill_color=BLACK,
                fill_opacity=1,
            )
            circ_label = Text(
                "T" if result else "F",
                font=MONO_FONT, color=result_color, font_size=16, weight="BOLD",
            )
            circ_label.move_to(circ.get_center())
            indicator = VGroup(circ, circ_label)
            indicator.shift(RIGHT * 3.0)
            parts.append(indicator)

        super().__init__(*parts)
        self.left_display = left_grp
        self.op_text = op_text
        self.right_display = right_grp
        self.result = result


class ConditionDisplay(VGroup):
    """Large TRUE / FALSE circle — used by EVALUATE_CONDITION."""

    def __init__(
        self,
        result: bool,
        radius: float = 0.85,
        true_color=PURE_GREEN,
        false_color=PURE_RED,
    ):
        color = true_color if result else false_color
        label = "TRUE" if result else "FALSE"

        circle = Circle(
            radius=radius,
            stroke_color=color,
            stroke_width=3,
            fill_color=BLACK,
            fill_opacity=1,
        )
        text = Text(label, font=MONO_FONT, color=color, font_size=20, weight="BOLD")
        text.move_to(circle.get_center())

        super().__init__(circle, text)
        self.circle = circle
        self.text = text
        self.result = result


# ---------------------------------------------------------------------------
# Animation helpers
# ---------------------------------------------------------------------------

class AnimationBuilder:
    """Static animation factories."""

    @staticmethod
    def swap_animation(
        box_a: VMobject, box_b: VMobject, duration: float = 0.5
    ) -> AnimationGroup:
        """Arc-swap two boxes to each other's position."""
        pos_a = box_a.get_center().copy()
        pos_b = box_b.get_center().copy()
        return AnimationGroup(
            ApplyMethod(box_a.move_to, pos_b),
            ApplyMethod(box_b.move_to, pos_a),
            lag_ratio=0,
            run_time=duration,
        )
