"""Lambda handler: agentic Manim scene generation with a self-correction loop.

Flow:
  1. Ask the model (OpenAI Responses API, structured output) for a dynamic
     number of scenes totalling ~60-120s of narration.
  2. Validate every scene's manim_code WITHOUT rendering video (see validator.py).
  3. Feed the errors of failed scenes back to the model for targeted fixes;
     scenes that already passed are frozen and never regenerated.
  4. Repeat up to MAX_RETRIES correction rounds, also bounded by the Lambda's
     remaining execution time.
  5. If any scene still fails, raise SceneValidationError (fails the job).
     Otherwise return {"scenes": [...], "job_id": ...} — raw code strings only;
     actual rendering happens later in ECS.

Environment variables:
  OPENAI_API_KEY       required
  OPENAI_MODEL         default "gpt-4o-mini"
  MAX_RETRIES          correction rounds, default 3
  VALIDATION_TIMEOUT   seconds per scene dry-run subprocess, default 30
  TIME_BUFFER_MS       min remaining Lambda time to start another round, default 20000
"""

import json
import logging
import os

from openai import OpenAI

from prompts import (
    CORRECTION_SCHEMA,
    CORRECTION_SYSTEM_PROMPT,
    GENERATION_SCHEMA,
    GENERATION_SYSTEM_PROMPT,
    build_correction_user_message,
    build_generation_user_message,
)
from validator import MANIM_AVAILABLE, validate_scene

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
VALIDATION_TIMEOUT = int(os.environ.get("VALIDATION_TIMEOUT", "30"))
TIME_BUFFER_MS = int(os.environ.get("TIME_BUFFER_MS", "20000"))

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


class SceneValidationError(Exception):
    """Raised when scenes still fail validation after all correction rounds."""

    def __init__(self, failed_scenes):
        self.failed_scenes = failed_scenes
        ids = sorted(s["scene_id"] for s in failed_scenes)
        details = "\n\n".join(
            f"Scene {s['scene_id']} ({s['tier']}):\n{s['error']}" for s in failed_scenes
        )
        super().__init__(
            f"Scenes {ids} failed validation after all correction attempts.\n{details}"
        )


def _call_openai(system_prompt: str, user_message: str, schema: dict) -> dict:
    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        text={"format": schema},
        temperature=0.2,
    )
    return json.loads(response.output_text)


def _generate_scenes(user_code: str) -> list:
    result = _call_openai(
        GENERATION_SYSTEM_PROMPT,
        build_generation_user_message(user_code),
        GENERATION_SCHEMA,
    )
    scenes = result["scenes"]
    if not scenes:
        raise ValueError("Model returned zero scenes")
    return scenes


def _validate_scenes(scenes: list) -> list:
    """Validate the given scenes in place. Returns the scenes that failed,
    each annotated with 'error' and 'tier'."""
    failed = []
    for scene in scenes:
        result = validate_scene(scene["manim_code"], timeout=VALIDATION_TIMEOUT)
        if result.passed:
            scene.pop("error", None)
            scene.pop("tier", None)
        else:
            scene["error"] = result.error
            scene["tier"] = result.tier
            failed.append(scene)
        logger.info(
            "Scene %s validation: %s (tier=%s)",
            scene["scene_id"],
            "PASS" if result.passed else "FAIL",
            result.tier,
        )
    return failed


def _remaining_ms(context) -> int:
    """Remaining execution time; effectively unlimited outside real Lambda."""
    if context is not None and hasattr(context, "get_remaining_time_in_millis"):
        return context.get_remaining_time_in_millis()
    return 10**9


def lambda_handler(event, context):
    job_id = event.get("job_id")
    user_code = event.get("user_code")

    if not user_code:
        raise ValueError("Missing user_code in event")

    logger.info(
        "Job %s: generating scenes (model=%s, manim_available=%s, max_retries=%s)",
        job_id, MODEL, MANIM_AVAILABLE, MAX_RETRIES,
    )

    scenes = _generate_scenes(user_code)
    scenes.sort(key=lambda s: s["scene_id"])
    logger.info("Job %s: model produced %d scenes", job_id, len(scenes))

    scenes_by_id = {s["scene_id"]: s for s in scenes}
    failed = _validate_scenes(scenes)

    rounds = 0
    while failed and rounds < MAX_RETRIES:
        if _remaining_ms(context) < TIME_BUFFER_MS:
            logger.warning(
                "Job %s: time budget exhausted after %d correction rounds", job_id, rounds
            )
            break
        rounds += 1
        logger.info(
            "Job %s: correction round %d/%d for scenes %s",
            job_id, rounds, MAX_RETRIES, sorted(s["scene_id"] for s in failed),
        )

        result = _call_openai(
            CORRECTION_SYSTEM_PROMPT,
            build_correction_user_message(user_code, failed),
            CORRECTION_SCHEMA,
        )

        failed_ids = {s["scene_id"] for s in failed}
        for fix in result["fixes"]:
            # Only accept fixes for scenes that actually failed — a stray fix
            # must never overwrite a scene that already validated.
            if fix["scene_id"] in failed_ids:
                scenes_by_id[fix["scene_id"]]["manim_code"] = fix["manim_code"]

        failed = _validate_scenes(failed)

    if failed:
        raise SceneValidationError(failed)

    for scene in scenes:
        scene.pop("error", None)
        scene.pop("tier", None)

    logger.info(
        "Job %s: all %d scenes validated after %d correction rounds",
        job_id, len(scenes), rounds,
    )
    return {"scenes": scenes, "job_id": job_id}
