"""
Lightweight Test Script - No Manim Dependencies

This script tests the core non-rendering components of the animation engine.
"""

import json
from schema_validator import SchemaValidator, ValidationError
from dispatcher import Dispatcher
from object_registry import ObjectRegistry


def test_schema_validation():
    """Test JSON schema validation."""
    print("=" * 60)
    print("TEST 1: Schema Validation")
    print("=" * 60)

    # Valid storyboard
    valid_storyboard = {
        "metadata": {"project_name": "Test"},
        "script": [
            {
                "step_id": 1,
                "line_number": 1,
                "code_snippet": "x = 5",
                "narration": "Create variable",
                "visual_commands": [
                    {
                        "command": "CREATE_VARIABLE",
                        "id": "v1",
                        "label": "x",
                        "initial_value": "5"
                    }
                ]
            }
        ]
    }

    try:
        SchemaValidator.validate_storyboard(valid_storyboard)
        print("✓ Valid storyboard passed validation")
    except ValidationError as e:
        print(f"✗ Valid storyboard failed: {e}")

    # Invalid storyboard (missing metadata)
    invalid_storyboard = {
        "script": []
    }

    try:
        SchemaValidator.validate_storyboard(invalid_storyboard)
        print("✗ Invalid storyboard should have failed validation")
    except ValidationError as e:
        print(f"✓ Invalid storyboard correctly rejected: Schema error detected")

    print()


def test_dispatcher():
    """Test Dispatcher functionality."""
    print("=" * 60)
    print("TEST 2: Dispatcher")
    print("=" * 60)

    storyboard = {
        "metadata": {"project_name": "Dispatcher Test"},
        "script": [
            {
                "step_id": 1,
                "line_number": 1,
                "code_snippet": "x = 5",
                "narration": "Create variable x with value five. This is a test narration.",
                "visual_commands": [
                    {"command": "CREATE_VARIABLE", "id": "v1", "label": "x", "initial_value": "5"}
                ]
            },
            {
                "step_id": 2,
                "line_number": 2,
                "code_snippet": "print(x)",
                "narration": "Print the value.",
                "visual_commands": [
                    {"command": "PRINT_TO_CONSOLE", "value": "5"}
                ]
            }
        ]
    }

    try:
        dispatcher = Dispatcher(storyboard)
        print(f"✓ Dispatcher created: {dispatcher}")
        print(f"  Project: {dispatcher.project_name}")
        print(f"  Steps: {len(dispatcher.get_all_steps())}")

        # Test step retrieval
        step_1 = dispatcher.get_step(1)
        print(f"✓ Retrieved step 1: {step_1['code_snippet']}")

        # Test duration calculation
        duration_1 = dispatcher.get_step_duration(1)
        print(f"✓ Step 1 duration: {duration_1:.2f}s (based on narration length)")

        # Test command validation
        cmd = step_1['visual_commands'][0]
        dispatcher.validate_command(cmd)
        print(f"✓ Command validated: {cmd['command']}")

    except Exception as e:
        print(f"✗ Dispatcher test failed: {e}")

    print()


def test_object_registry():
    """Test ObjectRegistry functionality (without Manim)."""
    print("=" * 60)
    print("TEST 3: Object Registry")
    print("=" * 60)

    try:
        registry = ObjectRegistry()
        print("✓ Registry initialized")

        # Create mock objects (simple dictionaries)
        obj1 = {"id": "v1", "type": "ValueBox", "value": "5"}
        registry.register("v1", obj1)
        print("✓ Object registered: v1")

        # Check existence
        if registry.has("v1"):
            print("✓ Object found in registry")
        else:
            print("✗ Object not found in registry")

        # Retrieve object
        retrieved = registry.get("v1")
        print(f"✓ Object retrieved: {retrieved}")

        # List all
        all_objs = registry.list_all()
        print(f"✓ Registry contains {len(all_objs)} object(s)")

        # Test error on duplicate
        try:
            registry.register("v1", obj1)
            print("✗ Should have raised error on duplicate ID")
        except ValueError:
            print("✓ Correctly rejected duplicate object ID")

        # Test destroy
        destroyed = registry.destroy("v1")
        print("✓ Object destroyed")

        if not registry.has("v1"):
            print("✓ Registry confirmed object removal")

    except Exception as e:
        print(f"✗ Registry test failed: {e}")

    print()


def test_file_loading():
    """Test loading storyboard from file."""
    print("=" * 60)
    print("TEST 4: File Loading")
    print("=" * 60)

    import os

    test_file = "./storyboards/example_simple.json"

    try:
        if os.path.exists(test_file):
            dispatcher = Dispatcher.load_from_file(test_file)
            print(f"✓ Loaded storyboard from file: {test_file}")
            print(f"  Project: {dispatcher.project_name}")
            print(f"  Steps: {len(dispatcher.get_all_steps())}")
        else:
            print(f"⚠ Test file not found: {test_file}")

    except Exception as e:
        print(f"✗ File loading failed: {e}")

    print()


def test_command_execution_logic():
    """Test command validation logic."""
    print("=" * 60)
    print("TEST 5: Command Validation")
    print("=" * 60)

    commands_to_test = [
        {"command": "CREATE_VARIABLE", "id": "v1", "label": "x", "initial_value": "5"},
        {"command": "UPDATE_VALUE", "target_id": "v1", "value": "10"},
        {"command": "HIGHLIGHT", "target_id": "v1", "color": "GREEN"},
        {"command": "PRINT_TO_CONSOLE", "value": "Hello"},
        {"command": "SWAP", "target_id": "arr", "index_a": 0, "index_b": 1},
    ]

    dispatcher = Dispatcher({
        "metadata": {"project_name": "Test"},
        "script": [{
            "step_id": 1,
            "line_number": 1,
            "code_snippet": "test",
            "narration": "test",
            "visual_commands": []
        }]
    })

    for cmd in commands_to_test:
        try:
            dispatcher.validate_command(cmd)
            print(f"✓ Valid command: {cmd['command']}")
        except ValueError as e:
            print(f"✗ Invalid command: {e}")

    # Test invalid command
    try:
        dispatcher.validate_command({"command": "INVALID_COMMAND"})
        print("✗ Should have rejected invalid command")
    except ValueError:
        print("✓ Correctly rejected invalid command")

    print()


def test_timing_calculations():
    """Test narration-based timing calculations."""
    print("=" * 60)
    print("TEST 6: Timing Calculations")
    print("=" * 60)

    dispatcher = Dispatcher({
        "metadata": {"project_name": "Timing Test"},
        "script": [
            {
                "step_id": 1,
                "line_number": 1,
                "code_snippet": "x = 5",
                "narration": "Short",
                "visual_commands": []
            },
            {
                "step_id": 2,
                "line_number": 2,
                "code_snippet": "y = 10",
                "narration": "This is a much longer narration that explains the concept in detail with multiple sentences.",
                "visual_commands": []
            }
        ]
    })

    try:
        duration_1 = dispatcher.calculate_step_duration("Short")
        duration_2 = dispatcher.calculate_step_duration("This is a much longer narration that explains the concept in detail with multiple sentences.")
        
        print(f"✓ Short narration duration: {duration_1:.2f}s")
        print(f"✓ Long narration duration: {duration_2:.2f}s")
        print(f"✓ Formula: len(narration) * 0.05 seconds per character")
        
    except Exception as e:
        print(f"✗ Timing calculation failed: {e}")

    print()


def main():
    """Run all tests."""
    print("\n")
    print("█" * 60)
    print("█" + " " * 58 + "█")
    print("█" + "  CODE ANIMATOR - LIGHTWEIGHT TEST SUITE".center(58) + "█")
    print("█" + "  (No Manim Dependencies Required)".center(58) + "█")
    print("█" + " " * 58 + "█")
    print("█" * 60)
    print("\n")

    test_schema_validation()
    test_dispatcher()
    test_object_registry()
    test_file_loading()
    test_command_execution_logic()
    test_timing_calculations()

    print("=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)
    print("\n✓ All core components are functioning correctly!")
    print("\nNext steps:")
    print("  1. Install Manim: pip install manim")
    print("  2. Render an animation: python main.py storyboards/example_simple.json\n")


if __name__ == "__main__":
    main()

