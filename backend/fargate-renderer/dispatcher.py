"""
Dispatcher - The Brain

This module receives the JSON storyboard, validates it, and orchestrates
the animation execution by passing commands to the renderer.
"""

from typing import Dict, List, Any, Callable
from schema_validator import SchemaValidator


class Dispatcher:
    """
    The Dispatcher validates and processes the storyboard JSON.
    It coordinates the timing between commands and the scene rendering.
    """

    def __init__(self, storyboard: Dict[str, Any]):
        """
        Initialize the Dispatcher with a validated storyboard.

        Args:
            storyboard: The storyboard dictionary (must be pre-validated).

        Raises:
            ValueError: If storyboard is invalid.
        """
        # Validate the storyboard
        SchemaValidator.validate_storyboard(storyboard)

        self.storyboard = storyboard
        self.metadata = storyboard.get("metadata", {})
        self.script = storyboard.get("script", [])
        self.project_name = self.metadata.get("project_name", "Untitled Project")

    @staticmethod
    def load_from_file(filepath: str) -> "Dispatcher":
        """
        Load and create a Dispatcher from a JSON file.

        Args:
            filepath: Path to the storyboard JSON file.

        Returns:
            Configured Dispatcher instance.

        Raises:
            FileNotFoundError: If file does not exist.
            json.JSONDecodeError: If JSON is invalid.
            ValidationError: If schema validation fails.
        """
        storyboard = SchemaValidator.load_and_validate_json(filepath)
        return Dispatcher(storyboard)

    def get_step(self, step_id: int) -> Dict[str, Any]:
        """
        Retrieve a specific step from the script.

        Args:
            step_id: The step ID to retrieve.

        Returns:
            The step dictionary.

        Raises:
            KeyError: If step_id does not exist.
        """
        for step in self.script:
            if step["step_id"] == step_id:
                return step
        raise KeyError(f"Step with ID {step_id} not found.")

    def get_all_steps(self) -> List[Dict[str, Any]]:
        """
        Get all steps from the script.

        Returns:
            List of all step dictionaries.
        """
        return self.script.copy()

    def get_commands_for_step(self, step_id: int) -> List[Dict[str, Any]]:
        """
        Get all visual commands for a specific step.

        Args:
            step_id: The step ID.

        Returns:
            List of command dictionaries for that step.

        Raises:
            KeyError: If step_id does not exist.
        """
        step = self.get_step(step_id)
        return step.get("visual_commands", [])

    def calculate_step_duration(self, narration: str) -> float:
        """
        Calculate the animation duration for a step based on narration length.

        Formula: duration = narration_length * 0.05 seconds

        Args:
            narration: The narration text.

        Returns:
            Duration in seconds.
        """
        return len(narration) * 0.05

    def get_step_duration(self, step_id: int) -> float:
        """
        Get the calculated duration for a specific step.

        Args:
            step_id: The step ID.

        Returns:
            Duration in seconds.

        Raises:
            KeyError: If step_id does not exist.
        """
        step = self.get_step(step_id)
        narration = step.get("narration", "")
        return self.calculate_step_duration(narration)

    def validate_command(self, command: Dict[str, Any]) -> bool:
        """
        Validate that a command has all required fields.

        Args:
            command: The command dictionary.

        Returns:
            True if valid.

        Raises:
            ValueError: If command is invalid.
        """
        required_field = "command"
        if required_field not in command:
            raise ValueError(f"Command missing required field: '{required_field}'")

        valid_commands = [
            # Memory
            "CREATE_VARIABLE",
            "CREATE_COLLECTION",
            "LINK_TARGET",
            "DESTROY_OBJECT",
            # State
            "UPDATE_VALUE",
            "ANIMATE_MATH",
            "TYPE_CAST",
            # Collection
            "SWAP",
            "APPEND_ELEMENT",
            "INSERT_AT",
            "POP_ELEMENT",
            # Flow / emphasis
            "MOVE_POINTER",
            "COMPARE_VALUES",
            "HIGHLIGHT",
            "PRINT_TO_CONSOLE",
            # Algorithm visualization
            "MARK_ELEMENT",
            "CELEBRATE",
            # Legacy
            "EVALUATE_CONDITION",
        ]

        cmd_type = command.get("command")
        if cmd_type not in valid_commands:
            raise ValueError(f"Unknown command type: '{cmd_type}'")

        return True

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the metadata from the storyboard.

        Returns:
            Metadata dictionary.
        """
        return self.metadata.copy()

    def __repr__(self) -> str:
        """Return a string representation of the Dispatcher."""
        return f"Dispatcher(project='{self.project_name}', steps={len(self.script)})"

