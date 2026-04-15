# Installation & Setup Guide

## Prerequisites

- Python 3.9+ (3.11 or 3.12 recommended for Manim compatibility)
- Virtual environment (recommended)

## Step 1: Create and Activate Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

## Step 2: Install Core Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **jsonschema**: JSON schema validation
- **pydantic**: Data validation library
- **pyyaml**: YAML parsing
- **numpy**: Numerical computing (required by Manim)

## Step 3: Install Manim (Optional - For Rendering Videos)

If you only need to test the core engine without rendering:

```bash
# Core dependencies are already installed
python test_components_lite.py  # Run tests without Manim
```

To render actual videos with Manim:

```bash
# Install Manim (this may take several minutes)
pip install manim

# Then verify installation
python -c "import manim; print(manim.__version__)"
```

### Manim Installation Troubleshooting

**Issue**: "ModuleNotFoundError: No module named 'manim'"

**Solution**: Manim requires FFmpeg and other system dependencies:

#### Windows

```bash
# Option 1: Using Chocolatey (recommended)
choco install ffmpeg

# Option 2: Manual download
# Download from: https://ffmpeg.org/download.html
```

#### macOS

```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

## Step 4: Verify Installation

```bash
# Test core components (no Manim needed)
python test_components_lite.py

# If Manim is installed, test everything
python test_components.py
```

## Next Steps

1. **Run an example animation**:
   ```bash
   python main.py storyboards/example_simple.json
   ```

2. **Create your own storyboard**:
   - Follow the JSON specification in `README.md`
   - Place your JSON in the `storyboards/` directory
   - Render with `python main.py your_storyboard.json`

3. **Output location**:
   - Videos are saved to: `./output/videos/`
   - Temporary files in: `./temp/`

## Architecture Overview

```
CodeAnimatorVideoRenderer/
├── schema_validator.py      # JSON validation
├── dispatcher.py            # Storyboard orchestration
├── object_registry.py       # Object lifecycle management
├── renderer.py              # Manim components
├── animation_scene.py       # Main Manim Scene
├── main.py                  # Entry point
├── test_components_lite.py  # Core tests (no Manim)
├── test_components.py       # Full tests (requires Manim)
└── storyboards/             # Example JSON files
```

## Common Issues & Solutions

### Issue: "Could not find FFmpeg"

**Solution**: 
- Ensure FFmpeg is installed and in your PATH
- Verify with: `ffmpeg -version`

### Issue: "ModuleNotFoundError" for specific packages

**Solution**:
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Issue: Slow video rendering

**Solution**: This is normal for Manim (first run may take 5-10+ minutes)
- Manim caches animations
- Subsequent renders are faster
- Use lower quality for testing: `python main.py storyboard.json --quality=low_quality`

### Issue: "No space left on device"

**Solution**: Manim generates temporary files
- Clear cache: `rm -rf ~/.manim/`
- Check disk space: `df -h`

## Performance Tips

1. **Start with simple animations**: Test with `example_simple.json` first
2. **Use low quality for testing**: Faster rendering
3. **Monitor memory**: Manim can be memory-intensive for complex scenes
4. **Batch process**: Render multiple videos in sequence for better stability

## Advanced Configuration

Edit `animation_scene.py` to customize:

```python
# Video quality (low_quality, medium_quality, high_quality)
config.quality = "high_quality"

# Frame rate (default 60)
config.frame_rate = 60

# Resolution
config.pixel_width = 1920
config.pixel_height = 1080

# Auto-arrange grid (for organizing objects)
self.objects_per_row = 3
self.row_height = 2.5
self.col_width = 2.5
```

## Documentation

- **README.md**: Architecture and command reference
- **schema_validator.py**: JSON schema specification
- **dispatcher.py**: Storyboard processing logic
- **renderer.py**: Visual components
- **animation_scene.py**: Command execution and animation logic

## Getting Help

1. Check the test output: `python test_components_lite.py`
2. Review example storyboards: `storyboards/example_*.json`
3. Read inline code documentation in each module
4. Check Manim documentation: https://docs.manim.community/

---

**Happy animating!** 🎬✨

