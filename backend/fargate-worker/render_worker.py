import os
import boto3
import shutil
import subprocess
import sys
from openai import OpenAI

# Initialize AWS clients
s3 = boto3.client('s3')
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Your globally unique bucket name
BUCKET_NAME = 'code-animator-media-bucket-2026'

TTS_MODEL = os.environ.get('TTS_MODEL', 'gpt-4o-mini-tts')
TTS_VOICE = os.environ.get('TTS_VOICE', 'alloy')

FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')


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

    print("Render task completed successfully!")


if __name__ == "__main__":
    main()
