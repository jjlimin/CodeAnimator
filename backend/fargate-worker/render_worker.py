import json
import os
import boto3
import shutil
import subprocess
import sys
import tempfile
import textwrap
from openai import OpenAI

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Your globally unique bucket name
BUCKET_NAME = 'code-animator-media-bucket-2026'
TABLE_NAME = 'CodeAnimatorJobs'

TTS_MODEL = os.environ.get('TTS_MODEL', 'gpt-4o-mini-tts')
TTS_VOICE = os.environ.get('TTS_VOICE', 'alloy')
CORRECTION_MODEL = os.environ.get('CORRECTION_MODEL', 'gpt-4.1-mini')

FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')

# ---------------------------------------------------------------------------
# Last-mile dry-run + self-correction.
#
# AIAgentLambda's own dry-run/overlap validation tier (validator.py) only
# runs where `manim` is importable — never true in production, since that
# Lambda is a zip package without manim by design. This container is the
# first place a scene's code actually runs against real manim before the
# real render — so this is where a genuine crash or a real geometric
# overlap between on-screen elements gets caught and, if possible, fixed,
# instead of silently reaching a rendered video. Entirely local to this one
# task: no Step Functions changes, no writing corrected code back anywhere
# else — only the final rendered mp4 this task uploads is ever seen again.
# ---------------------------------------------------------------------------

MAX_CORRECTION_ROUNDS = int(os.environ.get('MAX_CORRECTION_ROUNDS', '2'))
DRY_RUN_TIMEOUT_SECONDS = int(os.environ.get('DRY_RUN_TIMEOUT_SECONDS', '30'))

# Marker the parent process greps for in stderr to tell an overlap failure
# apart from an ordinary crash (mirrors validator.py's OVERLAP_MARKER —
# duplicated rather than imported since AIAgentLambda's zip and this Docker
# image are separate deploy artifacts with no shared import path).
OVERLAP_MARKER = "VALIDATION: overlapping mobjects detected"
_OVERLAP_TOLERANCE = 0.15

_DRY_RUN_DRIVER = textwrap.dedent(f"""

    if __name__ == "__main__":
        import sys as _sys
        from manim import Scene as _Scene, config as _config

        _config.dry_run = True
        _config.disable_caching = True
        _config.verbosity = "ERROR"
        _config.progress_bar = "none"

        _scene_classes = [
            _obj for _obj in list(globals().values())
            if isinstance(_obj, type)
            and issubclass(_obj, _Scene)
            and _obj.__module__ == "__main__"
        ]
        if not _scene_classes:
            print("VALIDATION: no Scene subclass defined in the file", file=_sys.stderr)
            _sys.exit(1)

        _overlaps = []
        for _cls in _scene_classes:
            _scene = _cls()
            _scene.render()
            _mobs = [m for m in _scene.mobjects if m.width > 0 and m.height > 0]
            for _i in range(len(_mobs)):
                for _j in range(_i + 1, len(_mobs)):
                    _a, _b = _mobs[_i], _mobs[_j]
                    _x_overlap = min(_a.get_right()[0], _b.get_right()[0]) - max(_a.get_left()[0], _b.get_left()[0])
                    _y_overlap = min(_a.get_top()[1], _b.get_top()[1]) - max(_a.get_bottom()[1], _b.get_bottom()[1])
                    if _x_overlap > {_OVERLAP_TOLERANCE} and _y_overlap > {_OVERLAP_TOLERANCE}:
                        _overlaps.append(
                            f"{{type(_a).__name__}} and {{type(_b).__name__}} overlap by "
                            f"~{{min(_x_overlap, _y_overlap):.2f}} units"
                        )

        if _overlaps:
            print("{OVERLAP_MARKER}:", file=_sys.stderr)
            for _o in _overlaps:
                print(" - " + _o, file=_sys.stderr)
            _sys.exit(2)
    """)


def check_scene(manim_code):
    """Dry-run the scene (no video output) and check for overlapping
    on-screen mobjects at its final frame. Returns (passed, error) — error
    is None on success, else the crash traceback or overlap description."""
    with tempfile.TemporaryDirectory(prefix='dry_run_') as tmpdir:
        scene_path = os.path.join(tmpdir, 'scene_under_test.py')
        with open(scene_path, 'w', encoding='utf-8') as f:
            f.write(manim_code + _DRY_RUN_DRIVER)
        try:
            proc = subprocess.run(
                [sys.executable, scene_path],
                capture_output=True,
                text=True,
                timeout=DRY_RUN_TIMEOUT_SECONDS,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            return False, f"Dry-run exceeded {DRY_RUN_TIMEOUT_SECONDS}s — likely an infinite loop or too heavy."

    if proc.returncode == 0:
        return True, None
    stderr_tail = (proc.stderr or proc.stdout or 'no error output').strip()[-3000:]
    return False, stderr_tail


CORRECTION_SYSTEM_PROMPT = """\
You are an expert Manim Community Edition (ManimCE) debugger.

The following scene passed static checks earlier in the pipeline, but a
real dry-run just found a problem: either an execution crash, or two or
more on-screen elements whose bounding boxes overlap at the end of the
scene. You will get the current code and the exact error/overlap output.

Fix ONLY what is necessary to eliminate the problem, keeping the scene's
visual intent and pacing the same. For an overlap: reposition or resize
the colliding mobject(s) (e.g. `.next_to(...)`, `.shift(...)`, a smaller
`font_size`/`side_length`) — derive new positions from the other mobjects
already in the scene, don't guess a coordinate. For a crash: fix the
underlying error. Return the COMPLETE corrected code, not a diff — it must
stay self-contained: `from manim import *` plus exactly one Scene subclass
with a `construct` method.
"""

CORRECTION_SCHEMA = {
    "type": "json_schema",
    "name": "scene_fix",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"manim_code": {"type": "string"}},
        "required": ["manim_code"],
        "additionalProperties": False,
    },
}


def request_fix(manim_code, error):
    """One targeted correction call, using the same OpenAI client already
    constructed for TTS below — no new credential wiring."""
    user_message = (
        f"Broken code:\n```python\n{manim_code}\n```\n\n"
        f"Dry-run error:\n```\n{error}\n```\n"
    )
    response = client.responses.create(
        model=CORRECTION_MODEL,
        input=[
            {"role": "system", "content": CORRECTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        text={"format": CORRECTION_SCHEMA},
        temperature=0.2,
    )
    return json.loads(response.output_text)["manim_code"]


def media_duration(path):
    """Return media duration in seconds via ffprobe."""
    result = subprocess.run(
        [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', path],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def mux_narration(video_path, audio_path, output_path):
    """Merge the voiceover into the video.

    The final scene lasts max(video, audio): if the narration is longer the
    last video frame is frozen (tpad); if the video is longer the audio is
    padded with silence (apad + -shortest). Output is re-encoded with fixed
    codecs/params so all scenes are stream-compatible for the fast
    `-c copy` concat performed later by concatVideosLambda.
    """
    video_len = media_duration(video_path)
    audio_len = media_duration(audio_path)
    freeze = max(0.0, audio_len - video_len + 0.3)  # short tail after speech

    subprocess.run([
        FFMPEG, '-y', '-i', video_path, '-i', audio_path,
        '-filter_complex',
        f'[0:v]tpad=stop_mode=clone:stop_duration={freeze:.3f}[v];[1:a]apad[a]',
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '20',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2', '-b:a', '128k',
        '-shortest', output_path
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def add_silent_track(video_path, output_path):
    """Scenes without narration still need an audio track, otherwise the
    `-c copy` concat would produce a broken stream mix."""
    subprocess.run([
        FFMPEG, '-y', '-i', video_path,
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '20',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2', '-b:a', '128k',
        '-shortest', output_path
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main():
    # Retrieve context from environment variables passed by Step Functions
    job_id = os.environ.get('JOB_ID')
    scene_id = os.environ.get('SCENE_ID')
    narration = os.environ.get('NARRATION', '')
    manim_code = os.environ.get('MANIM_CODE', '')

    if not job_id or scene_id is None:
        print("Error: Missing JOB_ID or SCENE_ID")
        sys.exit(1)

    if not FFMPEG or not FFPROBE:
        print("Error: ffmpeg/ffprobe not found in container")
        sys.exit(1)

    tmp_dir = '/tmp'
    audio_path = os.path.join(tmp_dir, f'voiceover_{scene_id}.mp3')
    code_path = os.path.join(tmp_dir, f'scene_{scene_id}.py')
    final_path = os.path.join(tmp_dir, f'final_{scene_id}.mp4')

    # 1. Generate TTS using OpenAI
    if narration:
        print(f"Generating TTS for scene {scene_id} ({TTS_MODEL})...")
        with client.audio.speech.with_streaming_response.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=narration
        ) as response:
            response.stream_to_file(audio_path)

    # 2. Write Manim code to a temporary file
    with open(code_path, 'w') as f:
        f.write(manim_code)

    # 2.5. Last-mile dry-run + self-correction (see the module-level
    # comment above check_scene/request_fix for why this lives here).
    current_code = manim_code
    for round_num in range(MAX_CORRECTION_ROUNDS + 1):
        passed, dry_run_error = check_scene(current_code)
        if passed:
            break
        if round_num == MAX_CORRECTION_ROUNDS:
            print(f"Scene {scene_id}: still failing after {MAX_CORRECTION_ROUNDS} correction round(s):")
            print(dry_run_error)
            sys.exit(1)
        print(f"Scene {scene_id}: dry-run check failed (round {round_num + 1}/{MAX_CORRECTION_ROUNDS}), requesting a fix...")
        print(dry_run_error)
        current_code = request_fix(current_code, dry_run_error)
    if current_code != manim_code:
        with open(code_path, 'w') as f:
            f.write(current_code)

    # 3. Run Manim via subprocess
    print(f"Starting Manim render for scene {scene_id}...")
    try:
        # Using -qm for medium quality
        subprocess.run(
            ['manim', '-qm', code_path],
            cwd=tmp_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8')
        print(f"Manim Error: {error_msg}")
        sys.exit(1)

    # 4. Locate the rendered MP4 file
    mp4_files = []
    for root, dirs, files in os.walk(tmp_dir):
        for file in files:
            if file.endswith('.mp4') and not file.startswith('final_'):
                mp4_files.append(os.path.join(root, file))

    if not mp4_files:
        print("Error: No MP4 file found after Manim rendering")
        sys.exit(1)

    # Get the most recently created MP4 file
    rendered_video = max(mp4_files, key=os.path.getmtime)

    # 5. Merge the narration into the video (this was missing before —
    #    the voiceover was generated but never attached to the video)
    if narration and os.path.exists(audio_path):
        print(f"Muxing narration into scene {scene_id}...")
        mux_narration(rendered_video, audio_path, final_path)
    else:
        print(f"No narration for scene {scene_id}, adding silent track...")
        add_silent_track(rendered_video, final_path)

    # 6. Upload the final scene to S3
    s3_key = f"jobs/{job_id}/scenes/scene_{scene_id}.mp4"
    print(f"Uploading video to S3: {s3_key}...")

    s3.upload_file(
        final_path,
        BUCKET_NAME,
        s3_key,
        ExtraArgs={"ContentType": "video/mp4"}
    )

    # 7. Best-effort: bump the job's rendered-scene counter for the frontend's
    # progress meter. Never fail the task over this — the video already landed.
    try:
        dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={'job_id': {'S': job_id}},
            UpdateExpression='ADD scenes_done :incr',
            ExpressionAttributeValues={':incr': {'N': '1'}},
        )
    except Exception as e:
        print(f"Warning: failed to update scenes_done for job {job_id}: {e}")

    print("Render task completed successfully!")


if __name__ == "__main__":
    main()
