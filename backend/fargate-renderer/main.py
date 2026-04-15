import sys
import os
import subprocess
import boto3
from botocore.exceptions import NoCredentialsError
from manim import config

# S3 Configuration
S3_BUCKET = os.getenv("AWS_S3_BUCKET", "code-animator-assets")
S3_PREFIX = os.getenv("AWS_S3_PREFIX", "projects/")

# AWS Credentials from environment variables (secure!)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_TOKEN = os.getenv("AWS_SESSION_TOKEN")


def upload_to_s3(local_file_path, s3_file_name):
    """
    Uploads a local file to the specified S3 bucket and prefix using
    credentials from environment variables.
    """
    # Validate credentials exist
    if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_TOKEN]):
        print("⚠️  Warning: AWS credentials not found in environment variables.")
        print("   To upload to S3, set: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN")
        print("   Skipping S3 upload...")
        return
    
    # Initialize the S3 client with environment credentials
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_session_token=AWS_TOKEN
    )

    try:
        print(f"Uploading {local_file_path} to S3...")

        # Upload the file
        s3.upload_file(local_file_path, S3_BUCKET, S3_PREFIX + s3_file_name)

        print(f"Successfully uploaded to: s3://{S3_BUCKET}/{S3_PREFIX}{s3_file_name}")

        # Clean up: Remove the local file after a successful upload
        os.remove(local_file_path)
        print(f"Local file {local_file_path} removed.")

    except FileNotFoundError:
        print(f"Error: The local file {local_file_path} was not found.")
    except NoCredentialsError:
        print("Error: AWS credentials invalid or expired.")
    except Exception as e:
        print(f"An unexpected error occurred during S3 upload: {e}")


def render_animation(storyboard_path: str, output_format: str = "mp4") -> None:
    """
    Renders a Manim animation based on a JSON storyboard and uploads it to S3.
    """
    if not os.path.exists(storyboard_path):
        raise FileNotFoundError(f"Storyboard file not found: {storyboard_path}")

    # Manim Global Configuration
    config.pixel_height = 1080
    config.pixel_width = 1920
    config.frame_rate = 60

    # Define output file names
    base_name = os.path.basename(storyboard_path).split('.')[0]
    file_ext = "mp4" if output_format == "mp4" else "gif"
    target_file_name = f"{base_name}.{file_ext}"

    # Temporary directory for Manim rendering process
    temp_media_dir = "./temp_render_output"
    os.makedirs(temp_media_dir, exist_ok=True)

    # Generate the temporary python scene file
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
        print(f"Starting Manim render for: {target_file_name}")

        # Build the Manim CLI command
        cmd = [
            "manim",
            "-o", target_file_name,
            "-v", "WARNING",
            "--media_dir", temp_media_dir,
            # "--video_dir", temp_media_dir,
            temp_scene_file,
            "CodeAnimatorScene"
        ]

        if output_format == "gif":
            cmd.append("-i")

        # Execute Manim
        subprocess.run(cmd, check=True)

        # Search for the rendered file in the temp directory
        rendered_local_path = None
        for root, dirs, files in os.walk(temp_media_dir):
            if target_file_name in files:
                rendered_local_path = os.path.join(root, target_file_name)
                break

        if rendered_local_path:
            # Upload the result to AWS S3
            upload_to_s3(rendered_local_path, target_file_name)
        else:
            print("Error: Render finished but the output file could not be located.")

    except subprocess.CalledProcessError as e:
        print(f"Manim Rendering Failed: {e}")
    finally:
        # Cleanup the temporary scene script
        if os.path.exists(temp_scene_file):
            os.remove(temp_scene_file)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_storyboard.json> [mp4|gif]")
        sys.exit(1)

    path = sys.argv[1]
    fmt = sys.argv[2] if len(sys.argv) > 2 else "mp4"

    render_animation(path, fmt)


if __name__ == "__main__":
    main()