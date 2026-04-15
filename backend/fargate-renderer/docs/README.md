# Code Animator Video Renderer

A state-driven Python animation engine using **Manim** that transforms pre-processed Visual AST storyboards into stunning code animation videos.

## 🎯 Architecture Overview

The engine is built on three core pillars:

### 1. **The Dispatcher** (The Brain)
- Reads and validates the Storyboard JSON
- Synchronizes timing based on narration length
- Orchestrates command execution

### 2. **The Object Registry** (The Memory)
- Maintains a live dictionary of all visual objects
- Allows modification instead of redrawing
- Tracks object lifecycle

### 3. **The Renderer** (The Artist)
- Implements visual components (ValueBox, BoxSeries, Pointer, ConsoleOutput)
- Translates high-level commands into smooth Manim animations
- Handles pre-calculated animations (e.g., swap with arc motion)

## 📁 Project Structure

```
CodeAnimatorVideoRenderer/
├── requirements.txt           # Python dependencies
├── schema_validator.py        # JSON schema validation
├── dispatcher.py              # Storyboard orchestrator
├── object_registry.py         # Visual object tracker
├── renderer.py                # Manim components & animations
├── animation_scene.py         # Main Manim Scene class
├── main.py                    # Entry point script
├── storyboards/               # Example JSON storyboards
│   ├── example_simple.json
│   ├── example_array_swap.json
│   └── example_update_values.json
└── output/                    # Generated videos (created automatically)
    └── videos/
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Render an Animation

```bash
python main.py storyboards/example_simple.json
```

The output video will be saved to `./output/videos/`.

### 3. Create Your Own Storyboard

Create a JSON file following the Storyboard Specification (see below).

## 📋 Storyboard JSON Specification

### High-Level Structure

```json
{
  "metadata": {
    "project_name": "My Animation"
  },
  "script": [
    {
      "step_id": 1,
      "line_number": 1,
      "code_snippet": "x = 5",
      "narration": "We create a variable...",
      "visual_commands": [...]
    }
  ]
}
```

### Visual Commands

#### CREATE_VARIABLE
Create a single variable box.

```json
{
  "command": "CREATE_VARIABLE",
  "id": "v1",
  "type": "ValueBox",
  "label": "x",
  "initial_value": "5"
}
```

#### CREATE_COLLECTION
Create an array/list visualization.

```json
{
  "command": "CREATE_COLLECTION",
  "id": "arr",
  "type": "BoxSeries",
  "initial_value": [1, 2, 3]
}
```

#### UPDATE_VALUE
Morph a variable to a new value.

```json
{
  "command": "UPDATE_VALUE",
  "target_id": "v1",
  "value": "10"
}
```

#### HIGHLIGHT
Flash a color highlight on an object.

```json
{
  "command": "HIGHLIGHT",
  "target_id": "v1",
  "color": "GREEN"
}
```

#### PRINT_TO_CONSOLE
Add output to the console area.

```json
{
  "command": "PRINT_TO_CONSOLE",
  "target_id": "v1",
  "value": "5"
}
```

#### SWAP
Swap two elements in a collection using arc motion.

```json
{
  "command": "SWAP",
  "target_id": "arr",
  "index_a": 0,
  "index_b": 2
}
```

#### APPEND_ELEMENT
Add an element to a collection.

```json
{
  "command": "APPEND_ELEMENT",
  "target_id": "arr",
  "element": "4"
}
```

#### MOVE_POINTER
Move a pointer to target another object.

```json
{
  "command": "MOVE_POINTER",
  "pointer_id": "ptr1",
  "target_id": "v1"
}
```

#### DESTROY_OBJECT
Remove an object from the scene.

```json
{
  "command": "DESTROY_OBJECT",
  "target_id": "v1"
}
```

## ⏱️ Timing Specification

The animation duration for each step is calculated based on narration length:

```
duration = len(narration_text) * 0.05 seconds
```

**Example:**
- Narration: "We create a variable" (22 characters)
- Duration: 22 * 0.05 = 1.1 seconds

This ensures that animations have sufficient time to be seen and understood.

## 🎨 Visual Design

- **Background**: Black
- **Default Outlines**: White
- **Emphasis/Highlights**: Green (positive), Red (negative)
- **Layout**: Auto-arranged in a grid (no fixed positions)
- **Components**:
  - **ValueBox**: RoundedRectangle + Label + Value
  - **BoxSeries**: Multiple boxes for arrays/lists
  - **ConsoleOutput**: Fixed area at bottom for terminal output

## 🔧 Core Modules

### `schema_validator.py`
Validates JSON storyboards against the defined schema. Throws `ValidationError` on schema violations.

**Key Classes:**
- `SchemaValidator`: Static methods for validation

### `dispatcher.py`
Reads storyboard and orchestrates execution.

**Key Classes:**
- `Dispatcher`: Loads, validates, and provides access to storyboard data

### `object_registry.py`
Tracks all visual objects on the canvas.

**Key Classes:**
- `ObjectRegistry`: Register, retrieve, update, and destroy objects

### `renderer.py`
Visual components and animation builders.

**Key Classes:**
- `ValueBox`: Single variable visualization
- `BoxSeries`: Array/list visualization
- `Pointer`: Arrow indicator
- `ConsoleOutput`: Terminal output area
- `AnimationBuilder`: Helper for complex animations

### `animation_scene.py`
Main Manim Scene orchestrator.

**Key Classes:**
- `AnimationScene`: Manim Scene with command execution logic

### `main.py`
Entry point for rendering.

## 📝 Example Storyboard

```json
{
  "metadata": {
    "project_name": "Bubble Sort Visualization"
  },
  "script": [
    {
      "step_id": 1,
      "line_number": 1,
      "code_snippet": "arr = [5, 3, 8, 1]",
      "narration": "We begin with an unsorted array containing four elements: five, three, eight, and one. These are displayed as boxes on the canvas.",
      "visual_commands": [
        {
          "command": "CREATE_COLLECTION",
          "id": "arr",
          "type": "BoxSeries",
          "initial_value": [5, 3, 8, 1]
        }
      ]
    },
    {
      "step_id": 2,
      "line_number": 2,
      "code_snippet": "arr[0], arr[1] = arr[1], arr[0]",
      "narration": "We swap the first two elements. Five and three exchange positions using a smooth arc animation.",
      "visual_commands": [
        {
          "command": "SWAP",
          "target_id": "arr",
          "index_a": 0,
          "index_b": 1
        }
      ]
    }
  ]
}
```

## 🐛 Error Handling

The engine validates all inputs and throws descriptive errors:

- **FileNotFoundError**: Storyboard file not found
- **JSONDecodeError**: Invalid JSON syntax
- **ValidationError**: Schema validation failure
- **KeyError**: Referenced object not found in registry
- **ValueError**: Invalid command parameters

## 📊 Advanced Configuration

Edit `animation_scene.py` for fine-tuning:

```python
# Video quality
config.pixel_height = 1080
config.pixel_width = 1920
config.frame_rate = 60

# Auto-arrange grid
self.objects_per_row = 3
self.row_height = 2.5
self.col_width = 2.5
```

## 🚧 Future Enhancements

- [ ] Audio/TTS integration for narration
- [ ] Custom styling templates
- [ ] Interactive debugging mode
- [ ] Performance optimizations
- [ ] More visual components (NodeGraph, ScopeFrame, etc.)
- [ ] Export to different formats (GIF, PNG sequences)

## 📄 License

MIT License

## 👤 Author

Built with ❤️ for code visualization education.

---

**Ready to animate your code? Start with one of the example storyboards!**

