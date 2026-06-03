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


def _download_audio(job_id: str, audio_map_s3_key: str, audio_dir: str) -> str:
    """
    Download audio files from S3 to audio_dir.
    Returns path to a local audio_map.json with 'path' keys instead of 's3_key'.
    """
    s3 = boto3.client('s3')
    os.makedirs(audio_dir, exist_ok=True)

    raw = s3.get_object(Bucket=S3_BUCKET, Key=audio_map_s3_key)
    payload = json.loads(raw['Body'].read().decode('utf-8'))
    # Lambda writes { job_id, audio_map: { step_id: { s3_key, duration } }, generated_at }
    remote_map = payload.get('audio_map', payload)

    local_map = {}
    for step_id, entry in remote_map.items():
        s3_key = entry['s3_key']
        local_path = os.path.join(audio_dir, f"step_{step_id}.mp3")
        s3.download_file(S3_BUCKET, s3_key, local_path)
        local_map[step_id] = {"path": os.path.abspath(local_path), "duration": entry['duration']}
        print(f"  Downloaded audio step {step_id}: {entry['duration']:.2f}s")

    local_map_path = os.path.join(audio_dir, "audio_map.json")
    with open(local_map_path, 'w') as f:
        json.dump(local_map, f)
    return local_map_path


def render_animation(storyboard_path: str, audio_map_path: str = "", output_format: str = "mp4") -> str | None:
    """
    Renders a Manim animation from a JSON storyboard file.
    Returns the local path of the rendered file, or None on failure.
    """
    if not os.path.exists(storyboard_path):
        raise FileNotFoundError(f"Storyboard file not found: {storyboard_path}")

    config.pixel_height = 1080
    config.pixel_width = 1920
    config.frame_rate = 30

    base_name = os.path.basename(storyboard_path).split('.')[0]
    file_ext = "mp4" if output_format == "mp4" else "gif"
    target_file_name = f"{base_name}.{file_ext}"

    temp_media_dir = "./temp_render_output"
    os.makedirs(temp_media_dir, exist_ok=True)

    # Escape backslashes for use inside the Python string literal in temp_scene.py
    safe_storyboard_path = storyboard_path.replace("\\", "\\\\")
    safe_audio_map_path = audio_map_path.replace("\\", "\\\\") if audio_map_path else ""

    temp_scene_file = "./temp_scene.py"
    audio_map_arg = f'"{safe_audio_map_path}"' if safe_audio_map_path else "None"
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
        if audio_map_path and os.path.exists("./temp_audio"):
            shutil.rmtree("./temp_audio", ignore_errors=True)


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
    audio_map_s3_key = script_data.get("audio_map_s3_key", "")

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

    local_audio_map_path = ""
    if audio_map_s3_key:
        print(f"Downloading audio from s3://{S3_BUCKET}/{audio_map_s3_key}")
        local_audio_map_path = _download_audio(job_id, audio_map_s3_key, "./temp_audio")
        print(f"Audio map ready: {local_audio_map_path}")
    else:
        print("No audio_map_s3_key — rendering without voiceover.")

    rendered_path = render_animation(tmp_storyboard_path, audio_map_path=local_audio_map_path, output_format="mp4")

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
