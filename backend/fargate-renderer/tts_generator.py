"""
TTS Generator - OpenAI Text-to-Speech for voiceovers.

Generates MP3 audio files from narration text using OpenAI tts-1 / alloy voice,
calculates their durations, and handles cleanup of temporary files.
"""

import os
from mutagen.mp3 import MP3


def generate_step_audio(step_id: int, text: str, audio_dir: str) -> str:
    """
    Generate TTS audio for a single step using OpenAI tts-1 (alloy voice).

    Args:
        step_id: Step identifier, used for the output filename.
        text: Narration text to synthesize.
        audio_dir: Directory to write the MP3 file into.

    Returns:
        Absolute path to the generated MP3 file.

    Raises:
        RuntimeError: If OPENAI_API_KEY is not set.
        openai.OpenAIError: On API failure.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)

    audio_path = os.path.abspath(os.path.join(audio_dir, f"step_{step_id}.mp3"))

    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )
    with open(audio_path, "wb") as f:
        f.write(response.content)

    return audio_path


def get_audio_duration(audio_path: str) -> float:
    """
    Return the duration of an MP3 file in seconds.

    Args:
        audio_path: Path to the MP3 file.

    Returns:
        Duration in seconds (float).
    """
    audio = MP3(audio_path)
    return audio.info.length


def cleanup_audio_files(audio_paths: list) -> None:
    """
    Delete a list of temporary audio files, ignoring missing files.

    Args:
        audio_paths: List of file paths to remove.
    """
    for path in audio_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            print(f"Warning: could not remove temp audio file {path}: {e}")
