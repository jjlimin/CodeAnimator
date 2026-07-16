"""Zip the ffmpeg layer with executable permissions preserved (0755)."""
import os
import zipfile

scratch = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(scratch, "ffmpeg-layer")
dst = os.path.join(scratch, "ffmpeg-layer.zip")

if os.path.exists(dst):
    os.remove(dst)

with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            full = os.path.join(root, name)
            arc = os.path.relpath(full, src).replace(os.sep, "/")
            info = zipfile.ZipInfo(arc)
            # 0755 so the bundled ffmpeg binary is executable in Lambda
            info.external_attr = (0o755 << 16)
            with open(full, "rb") as f:
                zf.writestr(info, f.read(), zipfile.ZIP_DEFLATED)

print(f"created {dst}: {os.path.getsize(dst) / 1024 / 1024:.1f} MB")
