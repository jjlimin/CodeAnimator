# Developer Documentation

## Architecture

The Code Animator Video Renderer is built on a **State-Driven Puppeteer** pattern with three core pillars:

### 1. The Dispatcher (The Brain)
**File**: `dispatcher.py`

Responsibilities:
- Loads and validates JSON storyboards
- Calculates animation timing based on narration length
- Provides step-by-step access to commands
- Validates command syntax

**Key Methods**:
```python
Dispatcher.load_from_file(filepath)  # Load and validate JSON
dispatcher.get_step(step_id)         # Get a specific step
dispatcher.get_all_steps()           # Get all steps
dispatcher.get_step_duration(id)     # Calculate timing
dispatcher.validate_command(cmd)     # Validate commands
```

**Timing Formula**:
```
duration = len(narration_text) * 0.05 seconds
```

### 2. The Object Registry (The Memory)
**File**: `object_registry.py`

Responsibilities:
- Maintains a live dictionary of all visual objects
- Tracks object lifecycle (create, read, update, delete)
- Prevents ID collisions
- Supports querying all objects

**Key Methods**:
```python
registry.register(obj_id, obj)   # Create
registry.get(obj_id)              # Read
registry.update(obj_id, new_obj)  # Update
registry.destroy(obj_id)          # Delete
registry.has(obj_id)              # Check existence
registry.list_all()               # List all objects
```

**Why It Matters**:
Instead of redrawing objects from scratch, the registry allows us to:
- Reuse and modify existing shapes
- Track object state throughout the animation
- Enable smooth transitions between steps

### 3. The Renderer (The Artist)
**File**: `renderer.py`

Visual Components:
- **ValueBox**: Single variable visualization (label + value)
- **BoxSeries**: Array/list of boxes
- **Pointer**: Arrow for indicating positions
- **ConsoleOutput**: Terminal output area

Animation Builders:
- **highlight_animation()**: Flash color effect
- **swap_animation()**: Arc motion swap between objects

## Command Execution Pipeline

```
JSON Input
    ↓
Schema Validator (validate JSON structure)
    ↓
Dispatcher (parse storyboard)
    ↓
For Each Step:
    ↓
AnimationScene.execute_step()
    ├─ display_narration_caption()
    ├─ For Each Command:
    │   ├─ parse command type
    │   ├─ locate objects in registry
    │   ├─ execute_command() 
    │   └─ apply Manim animation
    ├─ wait(step_duration)
    └─ Next step
    ↓
Output: MP4 Video File
```

## Command Execution Details

### Core Commands

#### CREATE_VARIABLE
Creates a single variable box on the canvas.

```json
{
  "command": "CREATE_VARIABLE",
  "id": "v1",
  "label": "x",
  "initial_value": "5"
}
```

**Flow**:
1. Create ValueBox instance
2. Position using auto-arrange grid
3. Add FadeIn animation
4. Register in ObjectRegistry

#### CREATE_COLLECTION
Creates an array/list visualization.

```json
{
  "command": "CREATE_COLLECTION",
  "id": "arr",
  "initial_value": [1, 2, 3]
}
```

**Flow**:
1. Create BoxSeries instance
2. Populate with initial values
3. Position using auto-arrange grid
4. Add FadeIn animation
5. Register in ObjectRegistry

#### UPDATE_VALUE
Morphs a variable to a new value.

```json
{
  "command": "UPDATE_VALUE",
  "target_id": "v1",
  "value": "10"
}
```

**Flow**:
1. Retrieve ValueBox from registry
2. Create new Text object with new value
3. Apply Transform animation (old → new)
4. Update registry

#### HIGHLIGHT
Flashes a color on an object.

```json
{
  "command": "HIGHLIGHT",
  "target_id": "v1",
  "color": "GREEN"
}
```

**Flow**:
1. Retrieve object from registry
2. Change stroke color → highlight color
3. Wait briefly
4. Change stroke color → original color
5. Animation completes

#### PRINT_TO_CONSOLE
Adds text to the console output area.

```json
{
  "command": "PRINT_TO_CONSOLE",
  "value": "5"
}
```

**Flow**:
1. Append line to ConsoleOutput
2. Update console text display
3. Trigger Transform animation (visual update)

#### SWAP
Swaps two elements in a collection using arc motion.

```json
{
  "command": "SWAP",
  "target_id": "arr",
  "index_a": 0,
  "index_b": 2
}
```

**Flow**:
1. Retrieve BoxSeries from registry
2. Get boxes at index_a and index_b
3. Execute swap_animation (arc motion)
4. Update internal values array

#### APPEND_ELEMENT
Adds an element to a collection.

```json
{
  "command": "APPEND_ELEMENT",
  "target_id": "arr",
  "element": "4"
}
```

**Flow**:
1. Retrieve BoxSeries
2. Append to values list
3. Recreate BoxSeries with new values
4. Apply Transform animation
5. Update registry

#### MOVE_POINTER
Moves a pointer to target another object.

```json
{
  "command": "MOVE_POINTER",
  "pointer_id": "ptr1",
  "target_id": "v1"
}
```

**Flow**:
1. Retrieve both pointer and target
2. Calculate new position (above target)
3. Animate pointer movement
4. Update registry

#### DESTROY_OBJECT
Removes an object from the scene.

```json
{
  "command": "DESTROY_OBJECT",
  "target_id": "v1"
}
```

**Flow**:
1. Retrieve object from registry
2. Apply FadeOut animation
3. Destroy object in registry

## Extending the Engine

### Adding a New Command

1. **Define in dispatcher.py**:
   ```python
   # Add to valid_commands list
   valid_commands = [..., "MY_NEW_COMMAND"]
   ```

2. **Implement in animation_scene.py**:
   ```python
   def cmd_my_new_command(self, command: Dict[str, Any]) -> None:
       """Execute my new command."""
       param1 = command.get("param1")
       param2 = command.get("param2")
       
       # Get objects from registry
       obj = self.registry.get(param1)
       
       # Create animation
       animation = ...
       self.play(animation)
   ```

3. **Add to command dispatcher**:
   ```python
   elif cmd_type == "MY_NEW_COMMAND":
       self.cmd_my_new_command(command)
   ```

4. **Document in README.md**

### Adding a New Visual Component

1. **Create in renderer.py**:
   ```python
   class MyComponent(VGroup):
       def __init__(self, ...):
           # Create visual elements
           # Group them
           super().__init__(...)
   ```

2. **Use in animation_scene.py**:
   ```python
   component = MyComponent(...)
   self.play(FadeIn(component))
   self.registry.register(obj_id, component)
   ```

## Visual Design System

### Colors
- **Background**: BLACK (`#000000`)
- **Default outline**: WHITE (`#FFFFFF`)
- **Positive/Emphasis**: GREEN (`#00FF00`)
- **Negative/Error**: RED (`#FF0000`)
- **Accent**: BLUE (`#0000FF`)
- **Highlight**: YELLOW (`#FFFF00`)

### Typography
- **Labels**: 20pt
- **Values**: 18pt
- **Console**: 16pt

### Layout
- **Grid-based**: 3 objects per row
- **Row height**: 2.5 units
- **Column width**: 2.5 units
- **Auto-arrange**: Objects position incrementally

## Testing

### Unit Tests (No Manim Required)
```bash
python test_components_lite.py
```

Tests:
- Schema validation
- Dispatcher functionality
- Object registry lifecycle
- File loading
- Command validation
- Timing calculations

### Integration Tests (Requires Manim)
```bash
python test_components.py
```

## File Structure

```
object_registry.py
├── ObjectRegistry
│   ├── register()
│   ├── get()
│   ├── update()
│   ├── destroy()
│   ├── has()
│   ├── list_all()
│   └── clear()
```

```
dispatcher.py
├── Dispatcher
│   ├── load_from_file()
│   ├── get_step()
│   ├── get_all_steps()
│   ├── get_commands_for_step()
│   ├── calculate_step_duration()
│   └── validate_command()
```

```
renderer.py
├── ValueBox
├── BoxSeries
├── Pointer
├── ConsoleOutput
└── AnimationBuilder
    ├── highlight_animation()
    └── swap_animation()
```

```
animation_scene.py
├── AnimationScene
│   ├── construct()
│   ├── execute_step()
│   ├── execute_command()
│   ├── cmd_create_variable()
│   ├── cmd_create_collection()
│   ├── cmd_update_value()
│   ├── cmd_highlight()
│   ├── cmd_print_to_console()
│   ├── cmd_swap()
│   ├── cmd_append_element()
│   ├── cmd_move_pointer()
│   ├── cmd_destroy_object()
│   └── get_next_position()
```

## Performance Considerations

1. **Object Registry**: O(1) lookup/insert/delete
2. **Grid Auto-arrange**: O(n) where n = number of objects
3. **Animation Rendering**: Depends on Manim's OpenGL backend
4. **Memory**: Each ValueBox ≈ 100KB, BoxSeries element ≈ 50KB

## Future Enhancements

- [ ] Audio/TTS integration
- [ ] Custom styling templates
- [ ] Interactive debugging mode
- [ ] Tree/Graph visualization components
- [ ] Scope frame for function boundaries
- [ ] Real-time variable tracking
- [ ] Performance profiling
- [ ] Parallel animation execution

## Debugging

### Enable Debug Output
```python
# In animation_scene.py, constructor
self.debug_mode = True
```

### Common Issues

**Objects not appearing**:
- Check auto-arrange grid isn't off-screen
- Verify FadeIn animation is playing
- Check registry has object

**Narration too fast**:
- Increase narration text length
- Manually add wait times in JSON

**Animations stuttering**:
- Reduce number of objects
- Simplify complex animations
- Use lower video quality

## Code Style

- **Docstrings**: Google-style for all functions
- **Type hints**: Required for all parameters and returns
- **Comments**: Use for "why", not "what"
- **Line length**: Soft limit 100 characters
- **Imports**: Group by standard library, third-party, local

## Contributing

1. Write tests first (TDD)
2. Update documentation
3. Follow code style guide
4. Test with example storyboards
5. Verify backwards compatibility

---

**Last Updated**: 2026-03-25

