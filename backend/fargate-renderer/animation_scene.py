"""
AnimationScene - The Main Orchestrator

Reads the storyboard, maintains the ObjectRegistry, and executes each visual
command as a timed Manim animation. When an audio_map_path is provided (from
the VoiceoverGenerator Lambda), timing locks to actual audio duration and
add_sound() syncs the MP3 to the animation. Falls back to narration-length
timing when no audio is present.
"""

import json
import re
import textwrap
from typing import Dict, Any, List, Optional

from manim import (
    Scene, Text, FadeIn, FadeOut, Transform, ReplacementTransform,
    Wait, ApplyMethod, Arrow,
    WHITE, BLACK, GREEN, RED, BLUE, YELLOW, ORANGE,
    UP, DOWN, LEFT, RIGHT, ORIGIN, config,
)

from dispatcher import Dispatcher
from object_registry import ObjectRegistry
from renderer import (
    MONO_FONT,
    ValueBox, StringBox, BooleanBox,
    BoxSeries, NodeGraph, Pointer,
    ConsoleOutput, AnimationBuilder,
    ComparisonDisplay, ConditionDisplay,
)

# Timing constants (seconds)
_CAPTION_IN  = 0.2
_CAPTION_OUT = 0.3
_MIN_CMD_TIME = 0.25   # floor so very fast steps never feel broken

# Narration caption safe width (characters before wrapping)
_WRAP_WIDTH = 85


def _wrap_narration(text: str) -> str:
    """Hard-wrap long narration into multiple lines for legible captioning."""
    return textwrap.fill(text, width=_WRAP_WIDTH)


def _eval_comparison(left, operator: str, right) -> bool:
    """Safely evaluate a comparison between two scalar values."""
    try:
        if operator == ">":
            return left > right
        if operator == "<":
            return left < right
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator == ">=":
            return left >= right
        if operator == "<=":
            return left <= right
    except TypeError:
        pass
    return False


class AnimationScene(Scene):
    """Main Manim scene that orchestrates all animations."""

    def __init__(
        self,
        storyboard_path: str,
        audio_map_path: Optional[str] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.camera.background_color = BLACK

        self.dispatcher = Dispatcher.load_from_file(storyboard_path)

        self._audio_map: Dict[str, Dict] = {}
        if audio_map_path:
            try:
                with open(audio_map_path) as f:
                    raw = json.load(f)
                self._audio_map = {str(k): v for k, v in raw.items()}
                print(f"Loaded audio map: {len(self._audio_map)} entries")
            except Exception as e:
                print(f"Warning: could not load audio map: {e}")

        self.registry = ObjectRegistry()
        self.console = ConsoleOutput()
        self.add(self.console)

        # Auto-layout grid state
        self._layout_count = 0
        self._objects_per_row = 3
        self._row_height = 2.6
        self._col_width  = 2.8

        self.current_caption: Optional[Any] = None

    # ------------------------------------------------------------------
    # Scene entry point
    # ------------------------------------------------------------------

    def construct(self):
        print(f"Starting: {self.dispatcher.project_name}")
        print(f"Steps: {len(self.dispatcher.get_all_steps())}")
        for step in self.dispatcher.get_all_steps():
            self.execute_step(step)
        self.wait(1)

    # ------------------------------------------------------------------
    # Step execution with dynamic timing
    # ------------------------------------------------------------------

    def execute_step(self, step: Dict[str, Any]) -> None:
        step_id   = step.get("step_id")
        narration = step.get("narration", "")
        commands  = step.get("visual_commands", [])

        print(f"\n--- Step {step_id} ---")

        # Clean up previous caption
        if self.current_caption is not None:
            self.remove(self.current_caption)
            self.current_caption = None

        # Queue voiceover (must happen before any play() calls in this step)
        audio_entry = self._audio_map.get(str(step_id))
        if audio_entry:
            self.add_sound(audio_entry["path"])
            audio_duration: Optional[float] = audio_entry["duration"]
            print(f"  Audio: {audio_duration:.2f}s")
        else:
            audio_duration = None

        # Caption
        self.current_caption = self._display_caption(narration)

        # Per-command time budget
        n_cmds = max(1, len(commands))
        if audio_duration is not None:
            budget = max(0.0, audio_duration - _CAPTION_IN - _CAPTION_OUT)
            per_cmd = max(_MIN_CMD_TIME, budget / n_cmds)
        else:
            per_cmd = max(_MIN_CMD_TIME, self.dispatcher.calculate_step_duration(narration) / n_cmds)

        # Execute commands
        for cmd in commands:
            try:
                self.execute_command(cmd, run_time=per_cmd)
            except Exception as e:
                print(f"  Error in command {cmd.get('command')}: {e}")
                raise

        # Wait for audio tail before fading caption
        if audio_duration is not None:
            elapsed = _CAPTION_IN + per_cmd * n_cmds
            tail = max(0.05, audio_duration - elapsed - _CAPTION_OUT)
            self.wait(tail)
        else:
            self.wait(0.4)

        # Fade out caption
        if self.current_caption:
            self.play(FadeOut(self.current_caption, run_time=_CAPTION_OUT))
            self.current_caption = None

    # ------------------------------------------------------------------
    # Caption rendering
    # ------------------------------------------------------------------

    def _display_caption(self, narration: str):
        wrapped = _wrap_narration(narration)
        caption = Text(
            wrapped,
            font=MONO_FONT,
            color=WHITE,
            font_size=19,
            line_spacing=1.25,
        )
        # Hard-clamp to safe zone (above console panel)
        max_w = config.frame_width - 1.0
        if caption.width > max_w:
            caption.scale_to_fit_width(max_w)
        caption.to_edge(DOWN, buff=2.6)  # sits above the console panel
        self.add(caption)
        self.play(FadeIn(caption, run_time=_CAPTION_IN))
        return caption

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def execute_command(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        cmd_type = command.get("command")
        dispatch = {
            # Memory
            "CREATE_VARIABLE":    self.cmd_create_variable,
            "CREATE_COLLECTION":  self.cmd_create_collection,
            "LINK_TARGET":        self.cmd_link_target,
            "DESTROY_OBJECT":     self.cmd_destroy_object,
            # State
            "UPDATE_VALUE":       self.cmd_update_value,
            "ANIMATE_MATH":       self.cmd_animate_math,
            "TYPE_CAST":          self.cmd_type_cast,
            # Collection
            "SWAP":               self.cmd_swap,
            "APPEND_ELEMENT":     self.cmd_append_element,
            "INSERT_AT":          self.cmd_insert_at,
            "POP_ELEMENT":        self.cmd_pop_element,
            # Flow / emphasis
            "MOVE_POINTER":       self.cmd_move_pointer,
            "COMPARE_VALUES":     self.cmd_compare_values,
            "HIGHLIGHT":          self.cmd_highlight,
            "PRINT_TO_CONSOLE":   self.cmd_print_to_console,
            # Legacy
            "EVALUATE_CONDITION": self.cmd_evaluate_condition,
        }
        handler = dispatch.get(cmd_type)
        if handler is None:
            raise ValueError(f"Unknown command: {cmd_type}")
        handler(command, run_time=run_time)

    # ------------------------------------------------------------------
    # Memory commands
    # ------------------------------------------------------------------

    def cmd_create_variable(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        obj_id  = command.get("id")
        label   = command.get("label", "")
        value   = command.get("initial_value")
        var_type = command.get("type", "auto")

        if not obj_id or value is None:
            raise ValueError("CREATE_VARIABLE requires: id, initial_value")

        # Choose the right box type
        if var_type == "str" or (var_type == "auto" and isinstance(value, str)):
            box = StringBox(label=label, value=str(value))
        elif var_type == "bool" or (var_type == "auto" and isinstance(value, bool)):
            box = BooleanBox(label=label, value=value)
        else:
            box = ValueBox(label=label, value=str(value), var_type=var_type)

        box.move_to(self._next_position())
        self.play(FadeIn(box, run_time=run_time))
        self.registry.register(obj_id, box)
        print(f"  CREATE_VARIABLE {obj_id} = {value!r}")

    def cmd_create_collection(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        obj_id  = command.get("id")
        values  = command.get("initial_value") or command.get("initial_elements", [])
        label   = command.get("label", "")

        if not obj_id:
            raise ValueError("CREATE_COLLECTION requires: id")

        # LLM sometimes sends the list as a JSON string, e.g. "[1, 2, 3]"
        if isinstance(values, str):
            try:
                values = json.loads(values)
            except (json.JSONDecodeError, ValueError):
                values = [values]

        if isinstance(values, dict):
            visual = NodeGraph(pairs=values, label=label)
        else:
            if not isinstance(values, list):
                values = [values]
            visual = BoxSeries(values=[str(v) for v in values], label=label)

        visual.move_to(self._next_position())
        self.play(FadeIn(visual, run_time=run_time))
        self.registry.register(obj_id, visual)
        print(f"  CREATE_COLLECTION {obj_id}")

    def cmd_link_target(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        link_id   = command.get("id")
        source_id = command.get("source_id")
        target_id = command.get("target_id")

        if not source_id or not target_id:
            raise ValueError("LINK_TARGET requires: source_id, target_id")

        source = self.registry.get(source_id)
        target = self.registry.get(target_id)

        arrow = Arrow(
            start=source.get_right(),
            end=target.get_left(),
            color=YELLOW,
            stroke_width=2.5,
            buff=0.08,
            max_tip_length_to_length_ratio=0.2,
        )
        self.play(FadeIn(arrow, run_time=run_time))
        if link_id:
            self.registry.register(link_id, arrow)
        print(f"  LINK_TARGET {source_id} → {target_id}")

    def cmd_destroy_object(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        target_id = command.get("target_id")
        if not target_id:
            raise ValueError("DESTROY_OBJECT requires: target_id")

        obj = self.registry.destroy(target_id)
        self.play(FadeOut(obj, run_time=run_time))
        print(f"  DESTROY_OBJECT {target_id}")

    # ------------------------------------------------------------------
    # State commands
    # ------------------------------------------------------------------

    def cmd_update_value(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        """Morph the existing box into a new one with the updated value."""
        target_id = command.get("target_id")
        new_value = command.get("value") if command.get("value") is not None else command.get("new_value")

        if not target_id or new_value is None:
            raise ValueError("UPDATE_VALUE requires: target_id, value (or new_value)")

        old_obj = self.registry.get(target_id)
        new_obj = self._rebuild_box(old_obj, value=str(new_value))
        new_obj.move_to(old_obj.get_center())
        self.play(ReplacementTransform(old_obj, new_obj, run_time=run_time))
        self.registry.update(target_id, new_obj)
        print(f"  UPDATE_VALUE {target_id} → {new_value!r}")

    def cmd_animate_math(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        """Display an expression and optionally morph it into its result."""
        expression = command.get("expression", "")
        result     = command.get("result")
        target_id  = command.get("target_id")
        obj_id     = command.get("id")

        expr_text = Text(expression, font=MONO_FONT, color=YELLOW, font_size=24)

        if target_id and self.registry.has(target_id):
            obj = self.registry.get(target_id)
            expr_text.next_to(obj, UP, buff=0.4)
        else:
            expr_text.move_to(self._next_position())

        if result is not None:
            result_text = Text(str(result), font=MONO_FONT, color=GREEN, font_size=24)
            result_text.move_to(expr_text.get_center())
            self.play(FadeIn(expr_text, run_time=run_time * 0.45))
            self.play(ReplacementTransform(expr_text, result_text, run_time=run_time * 0.55))
            if obj_id:
                self.registry.register(obj_id, result_text)
        else:
            self.play(FadeIn(expr_text, run_time=run_time))
            if obj_id:
                self.registry.register(obj_id, expr_text)

        print(f"  ANIMATE_MATH {expression!r} → {result!r}")

    def cmd_type_cast(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        """Morph a variable box into a different type box."""
        target_id = command.get("target_id")
        new_type  = command.get("new_type", "auto")

        if not target_id:
            raise ValueError("TYPE_CAST requires: target_id")

        old_obj = self.registry.get(target_id)
        label = getattr(old_obj, "label", "")
        value = getattr(old_obj, "value", "")

        if new_type == "str":
            new_obj = StringBox(label=label, value=value)
        elif new_type == "bool":
            new_obj = BooleanBox(label=label, value=value)
        else:
            new_obj = ValueBox(label=label, value=value, var_type=new_type)

        new_obj.move_to(old_obj.get_center())
        self.play(ReplacementTransform(old_obj, new_obj, run_time=run_time))
        self.registry.update(target_id, new_obj)
        print(f"  TYPE_CAST {target_id} → {new_type}")

    # ------------------------------------------------------------------
    # Collection commands
    # ------------------------------------------------------------------

    def cmd_swap(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        target_id = command.get("target_id") or command.get("collection_id")
        index_a   = command.get("index_a")
        index_b   = command.get("index_b")

        if target_id is None or index_a is None or index_b is None:
            raise ValueError("SWAP requires: target_id (or collection_id), index_a, index_b")

        index_a = self._resolve_index(index_a)
        index_b = self._resolve_index(index_b)

        obj = self.registry.get(target_id)
        if not isinstance(obj, BoxSeries):
            raise ValueError(f"{target_id} is not a BoxSeries")
        if index_a >= len(obj.values) or index_b >= len(obj.values):
            raise ValueError(f"Index out of range for {target_id}")

        new_values = obj.values.copy()
        new_values[index_a], new_values[index_b] = new_values[index_b], new_values[index_a]
        new_series = BoxSeries(values=new_values, label=obj.label)
        new_series.move_to(obj.get_center())
        self.play(ReplacementTransform(obj, new_series, run_time=run_time))
        self.registry.update(target_id, new_series)
        print(f"  SWAP {target_id}[{index_a}] ↔ [{index_b}]")

    def cmd_append_element(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        target_id = command.get("target_id")
        element   = command.get("element")

        if not target_id or element is None:
            raise ValueError("APPEND_ELEMENT requires: target_id, element")

        obj = self.registry.get(target_id)
        if not isinstance(obj, BoxSeries):
            raise ValueError(f"{target_id} is not a BoxSeries")

        new_values = obj.values + [str(element)]
        new_series = BoxSeries(values=new_values, label=obj.label)
        new_series.move_to(obj.get_center())
        self.play(ReplacementTransform(obj, new_series, run_time=run_time))
        self.registry.update(target_id, new_series)
        print(f"  APPEND_ELEMENT {target_id} ← {element!r}")

    def cmd_insert_at(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        target_id = command.get("target_id")
        index     = command.get("index", 0)
        element   = command.get("element")

        if not target_id or element is None:
            raise ValueError("INSERT_AT requires: target_id, index, element")

        obj = self.registry.get(target_id)
        if not isinstance(obj, BoxSeries):
            raise ValueError(f"{target_id} is not a BoxSeries")

        new_values = obj.values.copy()
        new_values.insert(index, str(element))
        new_series = BoxSeries(values=new_values, label=obj.label)
        new_series.move_to(obj.get_center())
        self.play(ReplacementTransform(obj, new_series, run_time=run_time))
        self.registry.update(target_id, new_series)
        print(f"  INSERT_AT {target_id}[{index}] = {element!r}")

    def cmd_pop_element(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        target_id = command.get("target_id")
        index     = command.get("index", -1)

        if not target_id:
            raise ValueError("POP_ELEMENT requires: target_id")

        obj = self.registry.get(target_id)
        if not isinstance(obj, BoxSeries):
            raise ValueError(f"{target_id} is not a BoxSeries")
        if not obj.values:
            raise ValueError(f"Cannot pop from empty collection {target_id}")

        new_values = obj.values.copy()
        popped = new_values.pop(index)

        if new_values:
            new_series = BoxSeries(values=new_values, label=obj.label)
            new_series.move_to(obj.get_center())
            self.play(ReplacementTransform(obj, new_series, run_time=run_time))
            self.registry.update(target_id, new_series)
        else:
            # Last element removed — destroy the whole series
            self.play(FadeOut(obj, run_time=run_time))
            self.registry.destroy(target_id)

        print(f"  POP_ELEMENT {target_id}[{index}] = {popped!r}")

    # ------------------------------------------------------------------
    # Flow / emphasis commands
    # ------------------------------------------------------------------

    def cmd_move_pointer(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        """Glide an existing pointer (or create one) to above a target object."""
        pointer_id = command.get("pointer_id")
        target_id  = command.get("target_id")
        index      = command.get("index")  # for BoxSeries: point to specific cell

        if not target_id:
            raise ValueError("MOVE_POINTER requires: target_id")
        # Auto-generate pointer_id when the LLM omits it
        if not pointer_id:
            pointer_id = f"ptr_{target_id}"

        if index is not None:
            index = self._resolve_index(index)

        target = self.registry.get(target_id)

        # Determine destination: cell top if BoxSeries+index, else object top
        if isinstance(target, BoxSeries) and index is not None:
            cells = list(target.submobjects)
            if 0 <= index < len(cells):
                dest = cells[index].get_top() + UP * 0.45
            else:
                dest = target.get_top() + UP * 0.45
        else:
            dest = target.get_top() + UP * 0.45

        if self.registry.has(pointer_id):
            pointer = self.registry.get(pointer_id)
            self.play(pointer.animate.move_to(dest), run_time=run_time)
        else:
            pointer = Pointer()
            pointer.move_to(dest)
            self.play(FadeIn(pointer, run_time=run_time))
            self.registry.register(pointer_id, pointer)

        print(f"  MOVE_POINTER {pointer_id} → {target_id}" + (f"[{index}]" if index is not None else ""))

    def cmd_compare_values(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        """Show a comparison display, then flash Green (True) or Red (False)."""
        left_val  = command.get("left")
        right_val = command.get("right")
        operator  = command.get("operator", "==")
        result_id = command.get("result_id")

        if left_val is None or right_val is None:
            raise ValueError("COMPARE_VALUES requires: left, right")

        result = _eval_comparison(left_val, operator, right_val)
        flash_color = GREEN if result else RED

        display = ComparisonDisplay(
            left_value=str(left_val),
            right_value=str(right_val),
            operator=operator,
            result=result,
        )
        display.move_to(self._next_position())

        # FadeIn then color-flash the result
        self.play(FadeIn(display, run_time=run_time * 0.55))
        self.play(ApplyMethod(display.set_stroke, flash_color, 5), run_time=run_time * 0.25)
        self.play(ApplyMethod(display.set_stroke, WHITE, 2),        run_time=run_time * 0.20)

        if result_id:
            self.registry.register(result_id, display)
            self.registry.set_metadata(result_id, "comparison_result", result)

        print(f"  COMPARE_VALUES {left_val} {operator} {right_val} = {result}")

    def cmd_highlight(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        target_id = command.get("target_id")
        color_str = command.get("color", "GREEN").upper()

        if not target_id:
            raise ValueError("HIGHLIGHT requires: target_id")

        color_map = {
            "GREEN": GREEN, "RED": RED, "BLUE": BLUE,
            "YELLOW": YELLOW, "WHITE": WHITE, "ORANGE": ORANGE,
        }
        color = color_map.get(color_str, GREEN)
        obj   = self.registry.get(target_id)
        box   = getattr(obj, "box", obj)

        flash_t = run_time / 2
        self.play(ApplyMethod(box.set_stroke, color, 5), run_time=flash_t)
        self.play(ApplyMethod(box.set_stroke, WHITE,  2), run_time=flash_t)
        print(f"  HIGHLIGHT {target_id} ({color_str})")

    def cmd_print_to_console(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        value = command.get("value")
        if value is None:
            raise ValueError("PRINT_TO_CONSOLE requires: value")

        self.console.add_line(str(value))
        new_text = Text(
            self.console.output_text.text,
            font=MONO_FONT,
            color=WHITE,
            font_size=13,
        )
        new_text.move_to(self.console.background.get_center() + DOWN * 0.12)
        self.play(Transform(self.console.output_text, new_text, run_time=run_time))
        print(f"  PRINT_TO_CONSOLE: {value!r}")

    # ------------------------------------------------------------------
    # Legacy: EVALUATE_CONDITION (kept for backward compatibility)
    # ------------------------------------------------------------------

    def cmd_evaluate_condition(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        condition_id = command.get("condition_id")
        if not condition_id:
            raise ValueError("EVALUATE_CONDITION requires: condition_id")

        try:
            result = self.registry.get_metadata(condition_id, "comparison_result")
        except KeyError:
            result = True

        cond_display = ConditionDisplay(result=result)

        cmp_obj = self.registry.get(condition_id) if self.registry.has(condition_id) else None
        if cmp_obj:
            cond_display.move_to(cmp_obj.get_center() + DOWN * 1.6)
        else:
            cond_display.move_to(self._next_position())

        self.play(FadeIn(cond_display, run_time=run_time))
        self.registry.register(f"{condition_id}_result", cond_display)
        print(f"  EVALUATE_CONDITION {condition_id} = {result}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _next_position(self):
        """Auto-grid: place each new object in the next available cell."""
        n   = self._layout_count
        row = n // self._objects_per_row
        col = n % self._objects_per_row
        self._layout_count += 1
        x = col * self._col_width - (self._objects_per_row - 1) * self._col_width / 2
        y = 2.0 - row * self._row_height
        return [x, y, 0]

    def _resolve_index(self, val) -> int:
        """Resolve an index to a concrete integer.

        Accepts integers directly, or variable-expression strings like "j" or "j+1"
        by looking up the current value in the registry (also tries "<name>_ptr").
        """
        if isinstance(val, int):
            return val
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
        m = re.match(r'^([A-Za-z_]\w*)([+-]\d+)?$', str(val).strip())
        if m:
            var_name, offset_str = m.group(1), m.group(2)
            offset = int(offset_str) if offset_str else 0
            for candidate in (var_name, var_name + "_ptr"):
                if self.registry.has(candidate):
                    raw = getattr(self.registry.get(candidate), "value", None)
                    if raw is not None:
                        try:
                            return int(str(raw)) + offset
                        except (ValueError, TypeError):
                            pass
        raise ValueError(f"Cannot resolve index expression: {val!r}")

    def _rebuild_box(self, old_obj, *, value: str):
        """Create a same-typed replacement box with a new value."""
        label    = getattr(old_obj, "label", "")
        var_type = getattr(old_obj, "var_type", "auto")

        if isinstance(old_obj, StringBox):
            return StringBox(label=label, value=value)
        if isinstance(old_obj, BooleanBox):
            return BooleanBox(label=label, value=value)
        return ValueBox(label=label, value=value, var_type=var_type)
