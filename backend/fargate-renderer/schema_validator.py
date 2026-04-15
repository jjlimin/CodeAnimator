"""
JSON Schema Validator for Storyboard

This module validates the incoming JSON storyboard against the defined schema
to ensure all required fields and structure are correct before animation.
"""

import json
from jsonschema import validate, ValidationError
from typing import Dict, Any


# Define the complete storyboard schema
STORYBOARD_SCHEMA = {
    "type": "object",
    "required": ["metadata", "script"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["project_name"],
            "properties": {
                "project_name": {"type": "string"}
            }
        },
        "script": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["step_id", "line_number", "code_snippet", "narration", "visual_commands"],
                "properties": {
                    "step_id": {"type": "integer"},
                    "line_number": {"type": "integer"},
                    "code_snippet": {"type": "string"},
                    "narration": {"type": "string"},
                    "visual_commands": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["command"],
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "enum": [
                                        "CREATE_VARIABLE",
                                        "CREATE_COLLECTION",
                                        "UPDATE_VALUE",
                                        "HIGHLIGHT",
                                        "PRINT_TO_CONSOLE",
                                        "SWAP",
                                        "APPEND_ELEMENT",
                                        "MOVE_POINTER",
                                        "DESTROY_OBJECT"
                                    ]
                                },
                                "id": {"type": "string"},
                                "target_id": {"type": "string"},
                                "type": {"type": "string"},
                                "label": {"type": "string"},
                                "initial_value": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {"type": "number"},
                                        {"type": "boolean"},
                                        {"type": "array", "items": {"type": ["string", "number", "boolean"]}}
                                    ]
                                },
                                "value": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {"type": "number"},
                                        {"type": "boolean"},
                                        {"type": "array", "items": {"type": ["string", "number", "boolean"]}}
                                    ]
                                },
                                "color": {"type": "string"},
                                "position": {"type": "string"},
                                "index_a": {"type": "integer"},
                                "index_b": {"type": "integer"},
                                "element": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {"type": "number"},
                                        {"type": "boolean"},
                                        {"type": "array", "items": {"type": ["string", "number", "boolean"]}}
                                    ]
                                },
                                "pointer_id": {"type": "string"},
                                "duration": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    }
}


class SchemaValidator:
    """Validator for storyboard JSON against the defined schema."""

    @staticmethod
    def validate_storyboard(storyboard: Dict[str, Any]) -> bool:
        """
        Validate the storyboard JSON against the schema.

        Args:
            storyboard: The storyboard dictionary to validate.

        Returns:
            True if valid.

        Raises:
            ValidationError: If the storyboard does not conform to the schema.
        """
        try:
            validate(instance=storyboard, schema=STORYBOARD_SCHEMA)
            return True
        except ValidationError as e:
            raise ValidationError(f"Storyboard validation failed: {e.message}") from e

    @staticmethod
    def load_and_validate_json(filepath: str) -> Dict[str, Any]:
        """
        Load a JSON file and validate it against the schema.

        Args:
            filepath: Path to the JSON file.

        Returns:
            The validated storyboard dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValidationError: If the storyboard does not conform to the schema.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                storyboard = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Storyboard file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in file {filepath}: {e.msg}", e.doc, e.pos) from e

        SchemaValidator.validate_storyboard(storyboard)
        return storyboard

