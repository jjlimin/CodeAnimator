import sys
import os
import json
import shutil
import subprocess
import boto3
from botocore.exceptions import NoCredentialsError
from manim import config

# S3 Configuration
S3_BUCKET = os.getenv("AWS_S3_BUCKET", "code-animator-assets")


def upload_to_s3(local_file_path, s3_key):
    """
    Uploads a local file to S3 using the Fargate task IAM role (no explicit credentials needed).
    """
    s3 = boto3.client('s3')
    try:
        print(f"Uploading {local_file_path} to s3://{S3_BUCKET}/{s3_key}")
        s3.upload_file(local_file_path, S3_BUCKET, s3_key)
        print(f"Successfully uploaded to: s3://{S3_BUCKET}/{s3_key}")
        os.remove(local_file_path)
        print(f"Local file {local_file_path} removed.")
    except FileNotFoundError:
        print(f"Error: The local file {local_file_path} was not found.")
        raise
    except NoCredentialsError:
        print("Error: No AWS credentials available.")
        raise
    except Exception as e:
        print(f"S3 upload error: {e}")
        raise


def _generate_voiceovers(storyboard_path: str, audio_dir: str) -> str:
    """
    Pre-generate TTS audio for every step in the storyboard.

    Returns the path to the written audio_map JSON file, or an empty string
    if TTS is unavailable (missing API key or import error).
    """
    from tts_generator import generate_step_audio, get_audio_duration

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set — skipping voiceover generation.")
        return ""

    with open(storyboard_path) as f:
        storyboard = json.load(f)

    steps = storyboard.get("script", [])
    audio_map = {}

    for step in steps:
        step_id = step.get("step_id")
        narration = step.get("narration", "").strip()
        if not narration:
            continue
        try:
            audio_path = generate_step_audio(step_id, narration, audio_dir)
            duration = get_audio_duration(audio_path)
            audio_map[step_id] = {"path": audio_path, "duration": duration}
            print(f"  Voiceover step {step_id}: {duration:.2f}s -> {audio_path}")
        except Exception as e:
            print(f"  Warning: TTS failed for step {step_id}: {e}")

    if not audio_map:
        return ""

    audio_map_path = os.path.join(audio_dir, "audio_map.json")
    with open(audio_map_path, "w") as f:
        json.dump(audio_map, f)

    print(f"Audio map written to: {audio_map_path}")
    return audio_map_path


def render_animation(storyboard_path: str, output_format: str = "mp4") -> str | None:
    """
    Renders a Manim animation from a JSON storyboard file.
    Returns the local path of the rendered file, or None on failure.
    """
    if not os.path.exists(storyboard_path):
        raise FileNotFoundError(f"Storyboard file not found: {storyboard_path}")

    config.pixel_height = 1080
    config.pixel_width = 1920
    config.frame_rate = 60

    base_name = os.path.basename(storyboard_path).split('.')[0]
    file_ext = "mp4" if output_format == "mp4" else "gif"
    target_file_name = f"{base_name}.{file_ext}"

    temp_media_dir = "./temp_render_output"
    audio_dir = "./temp_audio"
    os.makedirs(temp_media_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # Pre-generate voiceovers before Manim starts (audio files must exist at render time)
    print("Generating voiceovers...")
    audio_map_path = _generate_voiceovers(storyboard_path, audio_dir)

    # Escape backslashes for use inside the Python string literal in temp_scene.py
    safe_storyboard_path = storyboard_path.replace("\\", "\\\\")
    safe_audio_map_path = audio_map_path.replace("\\", "\\\\")

    temp_scene_file = "./temp_scene.py"
    audio_map_arg = f'"{safe_audio_map_path}"' if audio_map_path else "None"
    scene_code = f'''
from animation_scene import AnimationScene
class CodeAnimatorScene(AnimationScene):
    def __init__(self):
        super().__init__(
            storyboard_path="{safe_storyboard_path}",
            audio_map_path={audio_map_arg},
        )
'''
    with open(temp_scene_file, "w") as f:
        f.write(scene_code)

    try:
        print(f"Starting Manim render for: {target_file_name}")

        cmd = [
            "manim",
            "-o", target_file_name,
            "-v", "WARNING",
            "--media_dir", temp_media_dir,
            temp_scene_file,
            "CodeAnimatorScene"
        ]
        if output_format == "gif":
            cmd.append("-i")

        subprocess.run(cmd, check=True)

        rendered_local_path = None
        for root, dirs, files in os.walk(temp_media_dir):
            if target_file_name in files:
                rendered_local_path = os.path.join(root, target_file_name)
                break

        if rendered_local_path:
            print(f"Render complete: {rendered_local_path}")
            return rendered_local_path
        else:
            print("Error: Render finished but the output file could not be located.")
            return None

    except subprocess.CalledProcessError as e:
        print(f"Manim rendering failed: {e}")
        return None
    finally:
        if os.path.exists(temp_scene_file):
            os.remove(temp_scene_file)
        # Clean up temporary audio files after rendering
        if os.path.exists(audio_dir):
            shutil.rmtree(audio_dir, ignore_errors=True)
            print("Temporary audio files cleaned up.")


def fargate_main():
    """
    Entry point when running in AWS Fargate.
    Reads SCRIPT_DATA env var (injected by Step Functions), downloads the storyboard
    from S3, renders it, and uploads the video back to S3.
    """
    script_data_raw = os.getenv("SCRIPT_DATA")
    if not script_data_raw:
        print("Error: SCRIPT_DATA environment variable is not set.")
        sys.exit(1)

    try:
        script_data = json.loads(script_data_raw)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse SCRIPT_DATA as JSON: {e}")
        sys.exit(1)

    script_s3_key = script_data.get("script_s3_key")
    job_id = script_data.get("ProjectID")

    if not script_s3_key or not job_id:
        print(f"Error: Missing 'script_s3_key' or 'ProjectID' in SCRIPT_DATA: {script_data}")
        sys.exit(1)

    print(f"Job ID: {job_id}")
    print(f"Downloading storyboard from s3://{S3_BUCKET}/{script_s3_key}")

    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=S3_BUCKET, Key=script_s3_key)
    s3_content = json.loads(response['Body'].read().decode('utf-8'))

    # The ScriptGenerator wraps the storyboard in {job_id, user_id, script, generated_at}
    storyboard = s3_content.get("script", s3_content)

    tmp_storyboard_path = f"/tmp/{job_id}_storyboard.json"
    with open(tmp_storyboard_path, 'w') as f:
        json.dump(storyboard, f)
    print(f"Storyboard saved to {tmp_storyboard_path}")

    rendered_path = render_animation(tmp_storyboard_path, output_format="mp4")

    if rendered_path:
        s3_output_key = f"projects/{job_id}/animation.mp4"
        upload_to_s3(rendered_path, s3_output_key)
    else:
        print("Rendering failed — no file to upload.")
        sys.exit(1)


def local_main():
    """Entry point for local CLI use: python main.py <storyboard.json> [mp4|gif]"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_storyboard.json> [mp4|gif]")
        sys.exit(1)

    path = sys.argv[1]
    fmt = sys.argv[2] if len(sys.argv) > 2 else "mp4"

    rendered_path = render_animation(path, fmt)
    if rendered_path:
        s3_prefix = os.getenv("AWS_S3_PREFIX", "projects/")
        base_name = os.path.basename(rendered_path)
        upload_to_s3(rendered_path, s3_prefix + base_name)


if __name__ == "__main__":
    if os.getenv("SCRIPT_DATA"):
        fargate_main()
    else:
        local_main()
