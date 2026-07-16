# Lambda Layers

The pipeline's Lambdas rely on two layers (both published in the account, us-east-1):

## `openai-linux-layer` (used by AIAgentLambda)

Contains the `openai` Python package (v2.45.0) built for linux/x86_64 + python3.12.
Rebuild with:

```bash
pip install openai --platform manylinux2014_x86_64 --only-binary=:all: --target layer/python
cd layer && zip -r ../openai-linux-layer.zip python
aws lambda publish-layer-version --layer-name openai-linux-layer \
  --compatible-runtimes python3.12 --zip-file fileb://../openai-linux-layer.zip
```

## `ffmpeg-layer` (used by concatVideosLambda)

Contains the `imageio-ffmpeg` pip package, which bundles a static linux ffmpeg
binary. The Lambda resolves the binary path with `imageio_ffmpeg.get_ffmpeg_exe()`
— ffmpeg is NOT part of the Lambda runtime, this layer is what provides it.

Build (from Windows or any OS):

```bash
pip install imageio-ffmpeg --platform manylinux2014_x86_64 --only-binary=:all: --target ffmpeg-layer/python
python build_ffmpeg_layer_zip.py   # zips with 0755 perms so the binary is executable
aws lambda publish-layer-version --layer-name ffmpeg-layer \
  --compatible-runtimes python3.12 --zip-file fileb://ffmpeg-layer.zip
```

IMPORTANT: zip the layer with `build_ffmpeg_layer_zip.py` (or `zip` on Linux/macOS),
NOT with PowerShell `Compress-Archive` — the latter drops Unix execute permissions
and the ffmpeg binary will fail with "Permission denied" at runtime.
