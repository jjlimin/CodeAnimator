"""
JSON Schema Validator for Storyboard

Validates the incoming storyboard JSON before animation starts.
"""

import json
from jsonschema import validate, ValidationError
from typing import Dict, Any

# Scalar-or-array shorthand reused in several places
_SCALAR_OR_ARRAY = {
    "oneOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "boolean"},
        {"type": "array", "items": {"type": ["string", "number", "boolean"]}},
        {"type": "object"},   # dict → NodeGraph
    ]
}

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
                    "step_id":      {"type": "integer"},
                    "line_number":  {"type": "integer"},
                    "code_snippet": {"type": "string"},
                    "narration":    {"type": "string"},
                    "visual_commands": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["command"],
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "enum": [
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
                                        # Legacy
                                        "EVALUATE_CONDITION",
                                    ]
                                },
                                # Object identity
                                "id":          {"type": "string"},
                                "target_id":   {"type": "string"},
                                "source_id":   {"type": "string"},
                                "pointer_id":  {"type": "string"},
                                "condition_id":{"type": "string"},
                                "result_id":   {"type": "string"},
                                # Variable creation
                                "label":         {"type": "string"},
                                "type":          {"type": "string"},
                                "initial_value": _SCALAR_OR_ARRAY,
                                # Value mutation
                                "value":         _SCALAR_OR_ARRAY,
                                "new_type":      {"type": "string"},
                                # Math animation
                                "expression":    {"type": "string"},
                                "result":        {"type": ["string", "number", "boolean"]},
                                # Collection operations (integer OR variable expression, e.g. "j+1")
                                "index":   {"type": ["integer", "string"]},
                                "index_a": {"type": ["integer", "string"]},
                                "index_b": {"type": ["integer", "string"]},
                                "element": _SCALAR_OR_ARRAY,
                                # Comparison
                                "operator": {"type": "string"},
                                "left":  {"type": ["string", "number", "boolean"]},
                                "right": {"type": ["string", "number", "boolean"]},
                                # Styling / misc
                                "color":    {"type": "string"},
                                "position": {"type": "string"},
                                "duration": {"type": "number"},
                            }
                        }
                    }
                }
            }
        }
    }
}


class SchemaValidator:
    """Validates storyboard JSON against STORYBOARD_SCHEMA."""

    @staticmethod
    def validate_storyboard(storyboard: Dict[str, Any]) -> bool:
        try:
            validate(instance=storyboard, schema=STORYBOARD_SCHEMA)
            return True
        except ValidationError as e:
            raise ValidationError(f"Storyboard validation failed: {e.message}") from e

    @staticmethod
    def load_and_validate_json(filepath: str) -> Dict[str, Any]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                storyboard = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Storyboard file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {filepath}: {e.msg}", e.doc, e.pos
            ) from e

        SchemaValidator.validate_storyboard(storyboard)
        return storyboard
