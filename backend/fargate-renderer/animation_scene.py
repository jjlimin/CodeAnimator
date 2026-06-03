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
    WHITE, BLACK, GREEN, RED, BLUE, YELLOW, ORANGE, ManimColor,
    UP, DOWN, LEFT, RIGHT, ORIGIN, config,
    Indicate, Flash, Circumscribe,
)

from dispatcher import Dispatcher
from object_registry import ObjectRegistry
from renderer import (
    MONO_FONT, JOYFUL,
    ValueBox, StringBox, BooleanBox,
    BoxSeries, NodeGraph, Pointer,
    ConsoleOutput, AnimationBuilder,
    ComparisonDisplay, ConditionDisplay,
    HeaderBar, SidePanelDivider, auto_box_width,
)

# Timing constants (seconds)
_CAPTION_IN  = 0.2
_CAPTION_OUT = 0.3
_MIN_CMD_TIME = 0.25   # floor so very fast steps never feel broken
_FF_CMD_TIME  = 0.15   # fast-forward step timing
_AUDIO_PAD    = 0.35   # extra silence between audio clips to prevent overlap

# Narration caption safe wrap width (characters)
_WRAP_WIDTH = 70

# ---- Full-Frame 16:9 Layout (Manim coords: X ±7.1, Y ±4.0) ----

# Header bar (top strip, y = 3.3 to 4.0)
_HEADER_Y       =  3.65   # center y of header text

# Primary Stage — left ~65% of screen (x = -7.1 to +2.2)
_PRIMARY_CX     = -2.45   # center x
_PRIMARY_WIDTH  =  9.30   # usable width

# Side Panel — right ~35% (x = +2.4 to +7.1)
_DIVIDER_X      =  2.30   # vertical divider x
_SIDE_CX        =  4.75   # center x

# Shared vertical range for both panels (below header, above narration)
_PANEL_Y_MAX    =  3.22
_PANEL_Y_MIN    = -2.10

# Collections in Primary Stage
_VISUAL_Y_START  =  1.50
_VISUAL_Y_STEP   = -2.30

# Variables in Side Panel
_VAR_SIDE_Y_START =  2.50
_VAR_SIDE_Y_STEP  = -1.25

# Comparison display — fixed anchor inside primary stage
_CMP_ZONE = [-1.0, -1.10, 0]

# Narration footer (within primary stage x-range)
_NARRATION_CX   = _PRIMARY_CX   # -2.45
_NARRATION_Y    = -3.20
_NARRATION_MAX_W =  8.50

# Console inside side panel (lower portion)
_CONSOLE_CX     =  4.75
_CONSOLE_CY     = -3.00
_CONSOLE_W      =  4.40
_CONSOLE_H      =  1.80


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

        # ---- Console visibility detection ----
        meta_flag = self.dispatcher.metadata.get("has_console_output")
        if meta_flag is not None:
            self._has_console = bool(meta_flag)
        else:
            all_commands = [
                cmd
                for step in self.dispatcher.get_all_steps()
                for cmd in step.get("visual_commands", [])
            ]
            self._has_console = any(c.get("command") == "PRINT_TO_CONSOLE" for c in all_commands)

        # ---- Static chrome: header bar + side panel divider ----
        algo_name    = self.dispatcher.metadata.get("algorithm_type", "").replace("_", " ").title()
        self._algo_display_name = algo_name or self.dispatcher.project_name

        self._header = HeaderBar(self._algo_display_name)
        self.add(self._header)

        self.add(SidePanelDivider(_DIVIDER_X, _PANEL_Y_MAX, _PANEL_Y_MIN))

        # ---- Console (side panel, lower portion) ----
        self.console = ConsoleOutput(width=_CONSOLE_W, height=_CONSOLE_H, max_lines=5)
        self.console.move_to([_CONSOLE_CX, _CONSOLE_CY, 0])
        if self._has_console:
            self.add(self.console)
        else:
            print("Console hidden — no output detected.")

        # ---- Layout counters ----
        self._var_count    = 0   # side panel variables
        self._visual_count = 0   # primary stage collections

        # Fallback generic grid (for misc objects)
        self._layout_count   = 0
        self._objects_per_row = 3
        self._row_height = 2.6
        self._col_width  = 2.8

        # One-in-one-out tracker for comparison displays
        self._active_comparison: Optional[Any] = None
        self._active_comparison_id: Optional[str] = None

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
        step_id      = step.get("step_id")
        narration    = step.get("narration", "")
        commands     = step.get("visual_commands", [])
        fast_forward = step.get("fast_forward", False)
        step_title   = step.get("step_title", "")

        self._current_step_id = step_id
        print(f"\n--- Step {step_id}{' [FF]' if fast_forward else ''} ---")

        # Update header bar title (instant swap, no animation cost)
        if step_title:
            full = f"{self._algo_display_name}  —  {step_title}"
            new_title = Text(full, font=MONO_FONT, color=ManimColor("#7FAACC"), font_size=17)
            new_title.move_to(self._header.bg.get_center())
            if new_title.width > config.frame_width - 0.8:
                new_title.scale_to_fit_width(config.frame_width - 0.8)
            self.remove(self._header.title_obj)
            self._header.title_obj = new_title
            self.add(self._header.title_obj)

        # Fast-forward: skip caption, use tight timing, no tail wait
        if fast_forward:
            if self.current_caption is not None:
                self.remove(self.current_caption)
                self.current_caption = None
            for cmd in commands:
                try:
                    self.execute_command(cmd, run_time=_FF_CMD_TIME)
                except Exception as e:
                    print(f"  Error in command {cmd.get('command')}: {e}")
            self.wait(0.05)
            return

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
        actual_cmd_count = len(commands)
        n_cmds = max(1, actual_cmd_count)  # floor=1 for per_cmd division only
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

        # Wait for audio tail before fading caption.
        # Use actual_cmd_count (not n_cmds) so 0-command steps (overview, milestone)
        # don't under-estimate elapsed time and cut the tail short.
        if audio_duration is not None:
            elapsed = _CAPTION_IN + per_cmd * actual_cmd_count
            tail = max(0.10, audio_duration - elapsed - _CAPTION_OUT + _AUDIO_PAD)
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
            font_size=18,
            line_spacing=1.25,
        )
        # Clamp width to primary stage (avoids overlapping side panel)
        if caption.width > _NARRATION_MAX_W:
            caption.scale_to_fit_width(_NARRATION_MAX_W)
        caption.move_to([_NARRATION_CX, _NARRATION_Y, 0])
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
            # Algorithm visualization
            "MARK_ELEMENT":       self.cmd_mark_element,
            "CELEBRATE":          self.cmd_celebrate,
            # Legacy
            "EVALUATE_CONDITION": self.cmd_evaluate_condition,
        }
        handler = dispatch.get(cmd_type)
        if handler is None:
            step_id = getattr(self, "_current_step_id", "?")
            print(f"  WARNING: Unknown command '{cmd_type}' in step {step_id} — skipping. Full command: {command}")
            return
        handler(command, run_time=run_time)

    # ------------------------------------------------------------------
    # Memory commands
    # ------------------------------------------------------------------

    def cmd_create_variable(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        obj_id  = command.get("id")
        label   = command.get("label", "")
        value   = command.get("initial_value")
        var_type = command.get("type", "auto")

        if not obj_id:
            raise ValueError("CREATE_VARIABLE requires: id")
        # Treat LLM-generated null as a sensible default so render doesn't crash
        if value is None:
            value = "" if var_type == "str" else 0

        # Choose the right box type
        if var_type == "str" or (var_type == "auto" and isinstance(value, str)):
            box = StringBox(label=label, value=str(value))
        elif var_type == "bool" or (var_type == "auto" and isinstance(value, bool)):
            box = BooleanBox(label=label, value=value)
        else:
            box = ValueBox(label=label, value=str(value), var_type=var_type)

        box.move_to(self._next_var_position())
        self.play(FadeIn(box, run_time=run_time))
        self.registry.register(obj_id, box)
        print(f"  CREATE_VARIABLE {obj_id} = {value!r}")

    def cmd_create_collection(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        obj_id  = command.get("id")
        values  = command.get("initial_value")
        if values is None:
            values = command.get("initial_elements", [])
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
            bw = auto_box_width(len(values), available_width=_PRIMARY_WIDTH - 0.80)
            visual = BoxSeries(values=[str(v) for v in values], label=label, box_width=bw)

        visual.move_to(self._next_visual_position())
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

        if not target_id:
            raise ValueError("UPDATE_VALUE requires: target_id")
        if new_value is None:
            new_value = 0  # treat LLM null as numeric zero

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
        # Carry cell_states: roles follow values across the swap
        old_states = getattr(obj, "cell_states", {})
        new_states: Dict[int, str] = {}
        for idx, role in old_states.items():
            if idx == index_a:
                new_states[index_b] = role
            elif idx == index_b:
                new_states[index_a] = role
            else:
                new_states[idx] = role
        new_series = BoxSeries(values=new_values, label=obj.label,
                               box_width=obj.box_width, cell_states=new_states)
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

        if element is None:
            element = ""
        new_values = obj.values + [str(element)]
        bw = auto_box_width(len(new_values), _PRIMARY_WIDTH - 0.80)
        new_series = BoxSeries(values=new_values, label=obj.label, box_width=bw)
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
        bw = auto_box_width(len(new_values), _PRIMARY_WIDTH - 0.80)
        new_series = BoxSeries(values=new_values, label=obj.label, box_width=bw)
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
            bw = auto_box_width(len(new_values), _PRIMARY_WIDTH - 0.80)
            new_series = BoxSeries(values=new_values, label=obj.label, box_width=bw)
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
        """Show a comparison display at a fixed anchor — one-in, one-out."""
        left_val  = command.get("left")
        right_val = command.get("right")
        operator  = command.get("operator", "==")
        result_id = command.get("result_id")

        if left_val is None or right_val is None:
            raise ValueError("COMPARE_VALUES requires: left, right")

        # ── One-in, one-out: remove the previous comparison immediately ──
        if self._active_comparison is not None:
            if run_time <= _FF_CMD_TIME:
                self.remove(self._active_comparison)
            else:
                self.play(FadeOut(self._active_comparison, run_time=0.12))
            if self._active_comparison_id and self.registry.has(self._active_comparison_id):
                self.registry.destroy(self._active_comparison_id)
            self._active_comparison = None
            self._active_comparison_id = None

        result      = _eval_comparison(left_val, operator, right_val)
        flash_color = GREEN if result else RED

        display = ComparisonDisplay(
            left_value=str(left_val),
            right_value=str(right_val),
            operator=operator,
            result=result,
        )
        # Fixed anchor — never drifts, never stacks
        display.move_to(_CMP_ZONE)

        self.play(FadeIn(display, run_time=run_time * 0.55))
        self.play(ApplyMethod(display.set_stroke, flash_color, 5), run_time=run_time * 0.25)
        self.play(ApplyMethod(display.set_stroke, WHITE, 2),        run_time=run_time * 0.20)

        self._active_comparison    = display
        self._active_comparison_id = result_id

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
    # Algorithm visualization commands
    # ------------------------------------------------------------------

    def cmd_mark_element(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        """Recolor a specific BoxSeries cell to reflect its algorithmic role."""
        target_id = command.get("target_id")
        index     = command.get("index")
        role      = command.get("role", "default")

        if not target_id or index is None:
            raise ValueError("MARK_ELEMENT requires: target_id, index")

        obj = self.registry.get(target_id)
        if not isinstance(obj, BoxSeries):
            raise ValueError(f"{target_id} is not a BoxSeries")

        new_states = dict(getattr(obj, "cell_states", {}))
        new_states[int(index)] = role

        new_series = BoxSeries(
            values=obj.values, label=obj.label,
            box_width=obj.box_width, cell_states=new_states
        )
        new_series.move_to(obj.get_center())
        self.play(ReplacementTransform(obj, new_series, run_time=run_time))
        self.registry.update(target_id, new_series)
        print(f"  MARK_ELEMENT {target_id}[{index}] = {role}")

    def cmd_celebrate(self, command: Dict[str, Any], run_time: float = 1.0) -> None:
        """Play a joyful effect on a target element (milestone reached)."""
        target_id = command.get("target_id")
        index     = command.get("index")
        style     = command.get("style", "flash").lower()

        if not target_id:
            raise ValueError("CELEBRATE requires: target_id")

        obj = self.registry.get(target_id)

        # Resolve the target mobject — specific cell if index given
        mob = obj
        if isinstance(obj, BoxSeries) and index is not None:
            idx = self._resolve_index(index)
            if 0 <= idx < len(obj.cells):
                mob = obj.cells[idx]

        success_color = JOYFUL["success"]

        if style == "indicate":
            self.play(Indicate(mob, color=success_color, scale_factor=1.35, run_time=run_time))
        elif style == "circumscribe":
            self.play(Circumscribe(mob, color=success_color, run_time=run_time))
        else:
            self.play(Flash(mob, color=success_color, line_length=0.25, run_time=run_time))

        print(f"  CELEBRATE {target_id}" + (f"[{index}]" if index is not None else "") + f" ({style})")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _next_var_position(self):
        """Side Panel: stack variables top-to-bottom, overflow to second column."""
        n   = self._var_count
        col = n // 4
        row = n % 4
        self._var_count += 1
        x = _SIDE_CX - col * 1.35
        y = _VAR_SIDE_Y_START + row * _VAR_SIDE_Y_STEP
        return [x, y, 0]

    def _next_visual_position(self):
        """Primary Stage: center collections vertically."""
        n = self._visual_count
        self._visual_count += 1
        x = _PRIMARY_CX
        y = _VISUAL_Y_START + n * _VISUAL_Y_STEP
        return [x, y, 0]

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
