import sys
import os
import subprocess
import boto3
import json
from botocore.exceptions import NoCredentialsError
from manim import config

# S3 Configuration
S3_BUCKET = os.getenv("AWS_S3_BUCKET", "code-animator-assets")
S3_PREFIX = os.getenv("AWS_S3_PREFIX", "projects/")

# AWS Credentials from environment variables (Fargate Task Role handles this automatically if provided)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_TOKEN = os.getenv("AWS_SESSION_TOKEN")


def get_s3_client():
    """
    Initializes S3 client. If keys are missing, it relies on Task Role.
    """
    if all([AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_TOKEN]):
        return boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            aws_session_token=AWS_TOKEN
        )
    return boto3.client('s3')


def download_from_s3(s3_key, local_path):
    """
    Downloads the storyboard JSON from S3 to a local path.
    """
    s3 = get_s3_client()
    try:
        print(f"Downloading s3://{S3_BUCKET}/{s3_key} to {local_path}...")
        s3.download_file(S3_BUCKET, s3_key, local_path)
        return True
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        return False


def upload_to_s3(local_file_path, s3_file_name):
    """
    Uploads the rendered video to S3.
    """
    s3 = get_s3_client()
    try:
        print(f"Uploading {local_file_path} to S3...")
        s3.upload_file(local_file_path, S3_BUCKET, S3_PREFIX + s3_file_name)
        print(f"Successfully uploaded to: s3://{S3_BUCKET}/{S3_PREFIX}{s3_file_name}")
        os.remove(local_file_path)
    except Exception as e:
        print(f"An unexpected error occurred during S3 upload: {e}")


def render_animation(storyboard_path: str, output_format: str = "mp4") -> None:
    # ... (Keep your existing render_animation logic here) ...
    # Make sure it uses the storyboard_path provided
    if not os.path.exists(storyboard_path):
        raise FileNotFoundError(f"Storyboard file not found: {storyboard_path}")

    config.pixel_height = 1080
    config.pixel_width = 1920
    config.frame_rate = 60

    base_name = os.path.basename(storyboard_path).split('.')[0]
    file_ext = "mp4" if output_format == "mp4" else "gif"
    target_file_name = f"{base_name}.{file_ext}"

    temp_media_dir = "./temp_render_output"
    os.makedirs(temp_media_dir, exist_ok=True)

    temp_scene_file = "./temp_scene.py"
    scene_code = f'''
from animation_scene import AnimationScene
class CodeAnimatorScene(AnimationScene):
    def __init__(self):
        super().__init__(storyboard_path="{storyboard_path}")
'''
    with open(temp_scene_file, 'w') as f:
        f.write(scene_code)

    try:
        cmd = ["manim", "-o", target_file_name, "-v", "WARNING", "--media_dir", temp_media_dir, temp_scene_file,
               "CodeAnimatorScene"]
        if output_format == "gif": cmd.append("-i")
        subprocess.run(cmd, check=True)

        rendered_local_path = None
        for root, dirs, files in os.walk(temp_media_dir):
            if target_file_name in files:
                rendered_local_path = os.path.join(root, target_file_name)
                break

        if rendered_local_path:
            upload_to_s3(rendered_local_path, target_file_name)
    finally:
        if os.path.exists(temp_scene_file): os.remove(temp_scene_file)


def main():
    # 1. Check for SCRIPT_DATA from Step Functions
    script_data_env = os.getenv("SCRIPT_DATA")

    if script_data_env:
        print("Running in AWS Mode (Fargate)")
        try:
            # Parse the JSON string from the environment variable
            input_params = json.loads(script_data_env)
            s3_key = input_params.get("script_s3_key")

            if not s3_key:
                print("Error: script_s3_key not found in SCRIPT_DATA")
                sys.exit(1)

            # Local path to save the downloaded JSON
            local_json_path = "/tmp/storyboard.json"

            # 2. Download the file
            if download_from_s3(s3_key, local_json_path):
                render_animation(local_json_path, "mp4")
                # Cleanup downloaded JSON
                if os.path.exists(local_json_path):
                    os.remove(local_json_path)
            else:
                sys.exit(1)

        except json.JSONDecodeError as e:
            print(f"Error parsing SCRIPT_DATA JSON: {e}")
            sys.exit(1)

    # 3. Fallback to Local CLI Mode
    elif len(sys.argv) >= 2:
        print("Running in Local Mode")
        path = sys.argv[1]
        fmt = sys.argv[2] if len(sys.argv) > 2 else "mp4"
        render_animation(path, fmt)
    else:
        print("Usage: SCRIPT_DATA env var must be set OR python main.py <path> [fmt]")
        sys.exit(1)


if __name__ == "__main__":
    main()