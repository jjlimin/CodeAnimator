"""
Renderer - The Artist

This module contains visual components and animation logic.
It translates high-level commands into smooth Manim animations.
"""

from typing import Tuple, Optional, List
from manim import (
    VGroup, Rectangle, Text, Arrow,
    FadeIn, FadeOut, Transform, AnimationGroup, ApplyMethod,
    UP, DOWN, LEFT, RIGHT, ORIGIN, WHITE, BLACK, GREEN, RED,
    YELLOW, BLUE, PURE_BLUE, PURE_RED,
    Mobject, VMobject, RoundedRectangle, Circle, Line
)


class ValueBox(VGroup):
    """
    A visual representation of a single variable.
    Contains: RoundedRectangle (box) + Text (label) + Text (value)
    """

    def __init__(
        self,
        label: str,
        value: str,
        box_width: float = 2,
        box_height: float = 0.8,
        label_color: str = WHITE,
        value_color: str = WHITE,
        stroke_color: str = WHITE,
        stroke_width: float = 2,
    ):
        """
        Initialize a ValueBox.

        Args:
            label: Variable name.
            value: Initial value to display.
            box_width: Width of the box.
            box_height: Height of the box.
            label_color: Color of the label text.
            value_color: Color of the value text.
            stroke_color: Color of the box outline.
            stroke_width: Width of the box outline.
        """
        # Create the rectangle
        box = Rectangle(
            width=box_width,
            height=box_height,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            fill_color=BLACK,
            fill_opacity=1,
        )

        # Create label text (top)
        label_text = Text(
            label,
            color=label_color,
            font_size=20,
        )

        # Create value text (bottom)
        value_text = Text(
            str(value),
            color=value_color,
            font_size=18,
        )

        # Arrange vertically within the box
        label_text.move_to(box.get_center() + UP * 0.2)
        value_text.move_to(box.get_center() + DOWN * 0.25)

        # Group all components
        super().__init__(box, label_text, value_text)

        # Store references for easy access
        self.box = box
        self.label_text = label_text
        self.value_text = value_text
        self.label = label
        self.value = value


class BoxSeries(VGroup):
    """
    A visual representation of a list/array.
    Contains multiple boxes arranged horizontally.
    """

    def __init__(
        self,
        values: List[str],
        box_width: float = 0.8,
        box_height: float = 0.8,
        spacing: float = 0.3,
        stroke_color: str = WHITE,
        stroke_width: float = 2,
    ):
        """
        Initialize a BoxSeries.

        Args:
            values: List of initial values.
            box_width: Width of each box.
            box_height: Height of each box.
            spacing: Space between boxes.
            stroke_color: Color of box outlines.
            stroke_width: Width of box outlines.
        """
        boxes = []
        for i, val in enumerate(values):
            box = RoundedRectangle(
                width=box_width,
                height=box_height,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                fill_color=BLACK,
                fill_opacity=1,
            )

            text = Text(
                str(val),
                color=WHITE,
                font_size=16,
            )
            text.move_to(box.get_center())

            element = VGroup(box, text)
            element.shift(RIGHT * (i * (box_width + spacing)))
            boxes.append(element)

        super().__init__(*boxes)
        self.values = values.copy()
        self.box_width = box_width
        self.spacing = spacing


class Pointer(VGroup):
    """
    An arrow pointer for indicating positions or iterators.
    """

    def __init__(
        self,
        target_position: Tuple[float, float, float] = ORIGIN,
        color: str = WHITE,
        width: float = 0.3,
    ):
        """
        Initialize a Pointer.

        Args:
            target_position: Initial position of the pointer.
            color: Color of the pointer arrow.
            width: Width of the arrow.
        """
        arrow = Arrow(
            start=target_position + UP * 0.5,
            end=target_position,
            color=color,
            stroke_width=width,
            buff=0,
        )
        super().__init__(arrow)
        self.arrow = arrow
        self.current_position = target_position


class ConsoleOutput(VGroup):
    """
    A fixed text area at the bottom of the screen for console output.
    """

    def __init__(
        self,
        x: float = -5,
        y: float = -3.5,
        width: float = 10,
        height: float = 1.5,
    ):
        """
        Initialize ConsoleOutput.

        Args:
            x: X position (left edge).
            y: Y position (bottom edge).
            width: Width of the console area.
            height: Height of the console area.
        """
        # Create the background rectangle
        background = Rectangle(
            width=width,
            height=height,
            stroke_color=WHITE,
            stroke_width=2,
            fill_color=BLACK,
            fill_opacity=1,
        )
        background.to_edge(DOWN, buff=0.5)

        # Create the text area
        self.output_text = Text(
            "",
            color=WHITE,
            font_size=16,
        )
        self.output_text.next_to(background, DOWN, buff=0.1)

        super().__init__(background, self.output_text)
        self.background = background
        self.console_lines: List[str] = []

    def add_line(self, line: str) -> None:
        """
        Add a line to the console output.

        Args:
            line: Text to add.
        """
        self.console_lines.append(line)
        full_text = "\n".join(self.console_lines[-5:])  # Keep last 5 lines
        self.output_text.text = full_text
        self.output_text.move_to(self.background.get_center())


class AnimationBuilder:
    """
    Helper class to build complex animations.
    """

    @staticmethod
    def highlight_animation(
        obj: VMobject,
        color: str = GREEN,
        duration: float = 0.3,
    ) -> AnimationGroup:
        """
        Create a highlight animation (color flash and back).

        Args:
            obj: Object to highlight.
            color: Highlight color.
            duration: Duration of the animation.

        Returns:
            Animation group.
        """
        original_color = obj.stroke_color if hasattr(obj, 'stroke_color') else WHITE

        return AnimationGroup(
            ApplyMethod(obj.set_stroke, color),
            ApplyMethod(obj.set_stroke, original_color),
            lag_ratio=0.5,
        )

    @staticmethod
    def swap_animation(
        box_a: VMobject,
        box_b: VMobject,
        duration: float = 0.5,
    ) -> AnimationGroup:
        """
        Create a swap animation between two boxes using arc motion.

        Args:
            box_a: First box.
            box_b: Second box.
            duration: Duration of the swap.

        Returns:
            Animation group.
        """
        pos_a = box_a.get_center().copy()
        pos_b = box_b.get_center().copy()

        return AnimationGroup(
            ApplyMethod(box_a.move_to, pos_b),
            ApplyMethod(box_b.move_to, pos_a),
            lag_ratio=0,
        )


class ComparisonDisplay(VGroup):
    """
    A visual representation of a comparison between two values.
    Shows: [value_left] <comparison_operator> [value_right]
    """

    def __init__(
        self,
        left_value: str,
        right_value: str,
        operator: str = ">",
        box_width: float = 1.2,
        box_height: float = 0.6,
        operator_size: float = 24,
    ):
        """
        Initialize a ComparisonDisplay.

        Args:
            left_value: Value on the left side of comparison.
            right_value: Value on the right side of comparison.
            operator: Comparison operator (>, <, ==, !=, >=, <=).
            box_width: Width of each value box.
            box_height: Height of each value box.
            operator_size: Font size of the operator.
        """
        # Create left value box
        left_box = RoundedRectangle(
            width=box_width,
            height=box_height,
            stroke_color=YELLOW,
            stroke_width=2,
            fill_color=BLACK,
            fill_opacity=1,
        )
        left_text = Text(str(left_value), color=YELLOW, font_size=18)
        left_text.move_to(left_box.get_center())
        left_display = VGroup(left_box, left_text)

        # Create operator text
        operator_text = Text(operator, color=WHITE, font_size=operator_size)

        # Create right value box
        right_box = RoundedRectangle(
            width=box_width,
            height=box_height,
            stroke_color=YELLOW,
            stroke_width=2,
            fill_color=BLACK,
            fill_opacity=1,
        )
        right_text = Text(str(right_value), color=YELLOW, font_size=18)
        right_text.move_to(right_box.get_center())
        right_display = VGroup(right_box, right_text)

        # Arrange horizontally
        left_display.shift(LEFT * 2)
        right_display.shift(RIGHT * 2)

        super().__init__(left_display, operator_text, right_display)

        self.left_display = left_display
        self.operator_text = operator_text
        self.right_display = right_display
        self.left_value = left_value
        self.operator = operator
        self.right_value = right_value


class ConditionDisplay(VGroup):
    """
    A visual representation of a condition result (TRUE or FALSE).
    Shows a colored circle with TRUE/FALSE text inside.
    """

    def __init__(
        self,
        result: bool,
        radius: float = 0.8,
        true_color: str = PURE_GREEN,
        false_color: str = PURE_RED,
    ):
        """
        Initialize a ConditionDisplay.

        Args:
            result: Boolean result of the condition (True or False).
            radius: Radius of the result circle.
            true_color: Color when result is True (default: GREEN).
            false_color: Color when result is False (default: RED).
        """
        # Determine color and text based on result
        display_color = true_color if result else false_color
        result_text = "TRUE" if result else "FALSE"

        # Create the result circle
        circle = Circle(
            radius=radius,
            stroke_color=display_color,
            stroke_width=3,
            fill_color=BLACK,
            fill_opacity=1,
        )

        # Create result text
        text = Text(
            result_text,
            color=display_color,
            font_size=20,
            weight="bold",
        )
        text.move_to(circle.get_center())

        super().__init__(circle, text)

        self.circle = circle
        self.text = text
        self.result = result


# Define green and red constants for compatibility
PURE_GREEN = GREEN
PURE_RED = RED

