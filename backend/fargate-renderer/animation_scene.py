"""
AnimationScene - The Main Orchestrator

This is the core Manim Scene class that brings everything together:
- Uses Dispatcher to read storyboard
- Uses ObjectRegistry to track objects
- Uses Renderer components to create visuals
- Executes commands sequentially with proper timing
"""

import json
from typing import Dict, Any, List, Optional
from manim import (
    Scene, Text, FadeIn, FadeOut, Transform, Wait, ApplyMethod,
    WHITE, BLACK, GREEN, RED, BLUE, YELLOW,
    UP, DOWN, LEFT, RIGHT, ORIGIN, config
)
from dispatcher import Dispatcher
from object_registry import ObjectRegistry
from renderer import (
    ValueBox, BoxSeries, Pointer, ConsoleOutput, AnimationBuilder,
    ComparisonDisplay, ConditionDisplay
)


class AnimationScene(Scene):
    """
    Main Manim Scene that orchestrates all animations.
    """

    def __init__(self, storyboard_path: str, audio_map_path: Optional[str] = None, *args, **kwargs):
        """
        Initialize the AnimationScene.

        Args:
            storyboard_path: Path to the storyboard JSON file.
            audio_map_path: Optional path to audio map JSON produced by tts_generator.
                            Keys are step_id strings; values are {path, duration} dicts.
        """
        super().__init__(*args, **kwargs)
        self.camera.background_color = BLACK

        # Load and validate storyboard
        self.dispatcher = Dispatcher.load_from_file(storyboard_path)

        # Load voiceover audio map (step_id -> {path, duration})
        self._audio_map: Dict[str, Dict] = {}
        if audio_map_path:
            try:
                with open(audio_map_path) as f:
                    raw = json.load(f)
                # Normalise keys to strings to match step_id lookups
                self._audio_map = {str(k): v for k, v in raw.items()}
                print(f"Loaded voiceover audio map: {len(self._audio_map)} entries")
            except Exception as e:
                print(f"Warning: could not load audio map from {audio_map_path}: {e}")

        # Initialize registry and console
        self.registry = ObjectRegistry()
        self.console = ConsoleOutput()
        self.add(self.console)

        # Position tracking for auto-arrange
        self.next_position = ORIGIN
        self.objects_per_row = 3
        self.row_height = 2.5
        self.col_width = 2.5

        # Keep track of current caption for cleanup
        self.current_caption = None

    def construct(self):
        """Main animation construction method."""
        print(f"Starting animation: {self.dispatcher.project_name}")
        print(f"Total steps: {len(self.dispatcher.get_all_steps())}")

        # Process each step sequentially
        for step in self.dispatcher.get_all_steps():
            self.execute_step(step)

        # Final wait
        self.wait(1)

    def execute_step(self, step: Dict[str, Any]) -> None:
        """
        Execute a single step from the storyboard.

        Args:
            step: The step dictionary.
        """
        step_id = step.get("step_id")
        narration = step.get("narration", "")
        visual_commands = step.get("visual_commands", [])

        print(f"\n--- Step {step_id} ---")
        print(f"Narration: {narration[:50]}...")

        # Remove old caption if it exists
        if self.current_caption is not None:
            self.remove(self.current_caption)
            self.current_caption = None

        # Schedule voiceover audio before any animations so it plays concurrently
        audio_entry = self._audio_map.get(str(step_id))
        if audio_entry:
            self.add_sound(audio_entry["path"])
            audio_duration: Optional[float] = audio_entry["duration"]
            print(f"  Voiceover queued: {audio_entry['path']} ({audio_duration:.2f}s)")
        else:
            audio_duration = None

        # Display narration as caption
        self.current_caption = self.display_narration_caption(narration)

        # Execute all visual commands sequentially (animations run while audio plays)
        for command in visual_commands:
            try:
                self.execute_command(command)
            except Exception as e:
                print(f"Error executing command: {e}")
                raise

        # Hold until voiceover finishes; fall back to narration-length estimate
        if audio_duration is not None:
            self.wait(audio_duration)
        else:
            duration = self.dispatcher.calculate_step_duration(narration)
            self.wait(duration)

        # Fade out the caption
        if self.current_caption:
            self.play(FadeOut(self.current_caption))

    def display_narration_caption(self, narration: str):
        """
        Display the narration as a caption at the bottom.

        Args:
            narration: The narration text.
            
        Returns:
            The caption object for later removal.
        """
        # Create narration text
        caption = Text(
            narration,
            color=WHITE,
            font_size=14
        )
        # Set max width if needed
        if caption.width > config.frame_width - 1:
            caption.width = config.frame_width - 1
        caption.to_edge(DOWN, buff=0.3)

        # Fade in, display, then fade out
        self.add(caption)
        self.play(FadeIn(caption))
        self.wait(0.3)
        
        return caption

    def execute_command(self, command: Dict[str, Any]) -> None:
        """
        Execute a single command and create the corresponding animation.

        Args:
            command: The command dictionary.

        Raises:
            KeyError: If referenced object does not exist.
            ValueError: If command parameters are invalid.
        """
        cmd_type = command.get("command")

        if cmd_type == "CREATE_VARIABLE":
            self.cmd_create_variable(command)
        elif cmd_type == "CREATE_COLLECTION":
            self.cmd_create_collection(command)
        elif cmd_type == "UPDATE_VALUE":
            self.cmd_update_value(command)
        elif cmd_type == "HIGHLIGHT":
            self.cmd_highlight(command)
        elif cmd_type == "PRINT_TO_CONSOLE":
            self.cmd_print_to_console(command)
        elif cmd_type == "SWAP":
            self.cmd_swap(command)
        elif cmd_type == "APPEND_ELEMENT":
            self.cmd_append_element(command)
        elif cmd_type == "MOVE_POINTER":
            self.cmd_move_pointer(command)
        elif cmd_type == "DESTROY_OBJECT":
            self.cmd_destroy_object(command)
        elif cmd_type == "COMPARE_VALUES":
            self.cmd_compare_values(command)
        elif cmd_type == "EVALUATE_CONDITION":
            self.cmd_evaluate_condition(command)
        else:
            raise ValueError(f"Unknown command: {cmd_type}")

    # ===== COMMAND IMPLEMENTATIONS =====

    def cmd_create_variable(self, command: Dict[str, Any]) -> None:
        """Create a variable box and add it to the scene."""
        obj_id = command.get("id")
        label = command.get("label")
        value = command.get("initial_value")

        if not all([obj_id, label, value is not None]):
            raise ValueError("CREATE_VARIABLE requires: id, label, initial_value")

        # Create the ValueBox
        value_box = ValueBox(label=label, value=str(value))

        # Position it (auto-arrange)
        position = self.get_next_position()
        value_box.move_to(position)

        # Add to scene and registry
        self.play(FadeIn(value_box))
        self.registry.register(obj_id, value_box)

        print(f"  Created variable: {obj_id} = {value}")

    def cmd_create_collection(self, command: Dict[str, Any]) -> None:
        """Create a collection (list/array) box."""
        obj_id = command.get("id")
        values = command.get("initial_value", [])

        if not obj_id:
            raise ValueError("CREATE_COLLECTION requires: id")

        # Ensure values is a list
        if not isinstance(values, list):
            values = [values]

        # Create the BoxSeries
        box_series = BoxSeries(values=[str(v) for v in values])

        # Position it
        position = self.get_next_position()
        box_series.move_to(position)

        # Add to scene and registry
        self.play(FadeIn(box_series))
        self.registry.register(obj_id, box_series)

        print(f"  Created collection: {obj_id} = {values}")

    def cmd_update_value(self, command: Dict[str, Any]) -> None:
        """Update the value of an existing variable."""
        target_id = command.get("target_id")
        new_value = command.get("value")

        if not target_id or new_value is None:
            raise ValueError("UPDATE_VALUE requires: target_id, value")

        # Get the object
        obj = self.registry.get(target_id)

        # If it's a ValueBox, update the value text
        if isinstance(obj, ValueBox):
            old_value_text = obj.value_text
            new_value_text = Text(
                str(new_value),
                color=WHITE,
                font_size=18,
            )
            new_value_text.move_to(old_value_text.get_center())

            # Animate the transformation
            self.play(Transform(old_value_text, new_value_text))
            obj.value_text = new_value_text
            obj.value = str(new_value)

            print(f"  Updated {target_id} to {new_value}")
        else:
            raise ValueError(f"Object {target_id} is not a ValueBox")

    def cmd_highlight(self, command: Dict[str, Any]) -> None:
        """Highlight an object with a color."""
        target_id = command.get("target_id")
        color_str = command.get("color", "GREEN")

        if not target_id:
            raise ValueError("HIGHLIGHT requires: target_id")

        # Convert string color to Manim color object
        color_map = {
            "GREEN": GREEN,
            "RED": RED,
            "BLUE": BLUE,
            "YELLOW": YELLOW,
            "WHITE": WHITE,
        }
        color = color_map.get(color_str, GREEN)

        # Get the object
        obj = self.registry.get(target_id)

        # If it's a ValueBox, highlight the box component
        if isinstance(obj, ValueBox):
            box = obj.box
            original_stroke = box.stroke_color
            original_width = 2
            
            # Flash effect: increase stroke width and change color
            self.play(ApplyMethod(box.set_stroke, color, 4))
            self.wait(0.2)
            # Return to normal
            self.play(ApplyMethod(box.set_stroke, original_stroke, original_width))
            self.wait(0.1)
            # One more flash for emphasis
            self.play(ApplyMethod(box.set_stroke, color, 4))
            self.wait(0.2)
            self.play(ApplyMethod(box.set_stroke, original_stroke, original_width))
        else:
            # For other objects, try to apply the highlight
            self.play(ApplyMethod(obj.set_stroke, color, 4))
            self.wait(0.2)
            self.play(ApplyMethod(obj.set_stroke, WHITE, 2))

        print(f"  Highlighted {target_id} with color {color_str}")

    def cmd_print_to_console(self, command: Dict[str, Any]) -> None:
        """Print output to the console."""
        value = command.get("value")

        if value is None:
            raise ValueError("PRINT_TO_CONSOLE requires: value")

        # Add to console
        self.console.add_line(str(value))
        
        # Update the display by creating a new text and transforming
        new_output_text = Text(
            self.console.output_text.text,
            color=WHITE,
            font_size=16,
        )
        new_output_text.move_to(self.console.background.get_center())
        
        self.play(Transform(self.console.output_text, new_output_text))

        print(f"  Printed to console: {value}")

    def cmd_swap(self, command: Dict[str, Any]) -> None:
        """Swap two elements in a collection."""
        target_id = command.get("target_id")
        index_a = command.get("index_a")
        index_b = command.get("index_b")

        if not target_id or index_a is None or index_b is None:
            raise ValueError("SWAP requires: target_id, index_a, index_b")

        # Get the object
        obj = self.registry.get(target_id)

        if isinstance(obj, BoxSeries):
            # Get the two boxes
            boxes = list(obj.submobjects)
            if index_a >= len(boxes) or index_b >= len(boxes):
                raise ValueError(f"Index out of range for {target_id}")

            box_a = boxes[index_a]
            box_b = boxes[index_b]

            # Create swap animation
            anim = AnimationBuilder.swap_animation(box_a, box_b, duration=0.5)
            self.play(anim)

            # Update values list
            obj.values[index_a], obj.values[index_b] = obj.values[index_b], obj.values[index_a]

            print(f"  Swapped {target_id}[{index_a}] and [{index_b}]")
        else:
            raise ValueError(f"Object {target_id} is not a BoxSeries")

    def cmd_append_element(self, command: Dict[str, Any]) -> None:
        """Append an element to a collection."""
        target_id = command.get("target_id")
        element = command.get("element")

        if not target_id or element is None:
            raise ValueError("APPEND_ELEMENT requires: target_id, element")

        # Get the object
        obj = self.registry.get(target_id)

        if isinstance(obj, BoxSeries):
            obj.values.append(str(element))
            # Recreate the BoxSeries (simplified approach)
            # In a production system, you'd animate this more smoothly
            new_series = BoxSeries(values=obj.values)
            new_series.move_to(obj.get_center())
            self.play(Transform(obj, new_series))
            self.registry.update(target_id, new_series)

            print(f"  Appended {element} to {target_id}")
        else:
            raise ValueError(f"Object {target_id} is not a BoxSeries")

    def cmd_move_pointer(self, command: Dict[str, Any]) -> None:
        """Move a pointer to a new position."""
        pointer_id = command.get("pointer_id")
        target_id = command.get("target_id")

        if not pointer_id or not target_id:
            raise ValueError("MOVE_POINTER requires: pointer_id, target_id")

        # Get pointer and target
        pointer = self.registry.get(pointer_id)
        target = self.registry.get(target_id)

        # Move pointer next to target
        new_position = target.get_center() + UP * 0.8
        self.play(pointer.animate.move_to(new_position))

        print(f"  Moved {pointer_id} to {target_id}")

    def cmd_destroy_object(self, command: Dict[str, Any]) -> None:
        """Remove an object from the scene."""
        target_id = command.get("target_id")

        if not target_id:
            raise ValueError("DESTROY_OBJECT requires: target_id")

        # Get and remove from registry
        obj = self.registry.destroy(target_id)

        # Fade out from scene
        self.play(FadeOut(obj))

        print(f"  Destroyed {target_id}")

    def cmd_compare_values(self, command: Dict[str, Any]) -> None:
        """
        Create a visual comparison display between two values.
        Shows: [left_value] <operator> [right_value]
        """
        left_val = command.get("left")
        right_val = command.get("right")
        result_id = command.get("result_id")
        operator = command.get("operator", ">")

        if not all([left_val is not None, right_val is not None, result_id]):
            raise ValueError("COMPARE_VALUES requires: left, right, result_id")

        # Determine the operator (try to infer if not provided)
        if operator == ">":
            comparison_result = left_val > right_val
        elif operator == "<":
            comparison_result = left_val < right_val
        elif operator == "==":
            comparison_result = left_val == right_val
        elif operator == "!=":
            comparison_result = left_val != right_val
        elif operator == ">=":
            comparison_result = left_val >= right_val
        elif operator == "<=":
            comparison_result = left_val <= right_val
        else:
            # Default to greater-than
            comparison_result = left_val > right_val
            operator = ">"

        # Create the comparison display
        comparison_display = ComparisonDisplay(
            left_value=str(left_val),
            right_value=str(right_val),
            operator=operator,
        )

        # Position and add to scene
        position = self.get_next_position()
        comparison_display.move_to(position)
        self.play(FadeIn(comparison_display))

        # Store the comparison result in registry for EVALUATE_CONDITION to use
        self.registry.register(result_id, comparison_display)
        self.registry.set_metadata(result_id, "comparison_result", comparison_result)

        print(f"  Compared: {left_val} {operator} {right_val} = {comparison_result}")

    def cmd_evaluate_condition(self, command: Dict[str, Any]) -> None:
        """
        Display the result of a condition evaluation (TRUE or FALSE).
        Shows a colored circle with the result.
        """
        condition_id = command.get("condition_id")

        if not condition_id:
            raise ValueError("EVALUATE_CONDITION requires: condition_id")

        # Get the comparison result from metadata
        try:
            comparison_result = self.registry.get_metadata(condition_id, "comparison_result")
        except (KeyError, AttributeError):
            # If metadata not found, default to True
            comparison_result = True

        # Create the condition display
        condition_display = ConditionDisplay(result=comparison_result)

        # Position it below the comparison display
        comparison_obj = self.registry.get(condition_id)
        if comparison_obj:
            position = comparison_obj.get_center() + DOWN * 1.5
        else:
            position = self.get_next_position()

        condition_display.move_to(position)
        self.play(FadeIn(condition_display))

        # Register the condition display
        result_display_id = f"{condition_id}_result"
        self.registry.register(result_display_id, condition_display)

        print(f"  Evaluated condition: {condition_id} = {comparison_result}")

    # ===== HELPER METHODS =====

    def get_next_position(self):
        """
        Get the next auto-arranged position for a new object.

        Returns:
            The next position as a numpy array [x, y, z].
        """
        # Simple grid layout
        row = len(self.registry.list_all()) // self.objects_per_row
        col = len(self.registry.list_all()) % self.objects_per_row

        x = col * self.col_width - (self.objects_per_row - 1) * self.col_width / 2
        y = 2 - row * self.row_height

        return [x, y, 0]

