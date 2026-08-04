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

import ast
import json
import logging
import os

import boto3
from openai import OpenAI

from prompts import (
    CORRECTION_SCHEMA,
    CORRECTION_SYSTEM_PROMPT,
    GENERATION_SCHEMA,
    GENERATION_SYSTEM_PROMPT,
    build_correction_user_message,
    build_generation_user_message,
    build_buggy_generation_user_message,
    inject_code_panel,
)
from validator import MANIM_AVAILABLE, validate_scene

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
VALIDATION_TIMEOUT = int(os.environ.get("VALIDATION_TIMEOUT", "30"))
TIME_BUFFER_MS = int(os.environ.get("TIME_BUFFER_MS", "20000"))
TABLE_NAME = "CodeAnimatorJobs"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
dynamodb = boto3.client("dynamodb")


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


def _generate_scenes(user_code: str, complexity: str, mode=None, code_error=None) -> tuple:
    # explain_bug: keep the broken code on screen and explain how to fix it.
    if mode == "explain_bug":
        user_message = build_buggy_generation_user_message(user_code, code_error or "", complexity)
    else:
        user_message = build_generation_user_message(user_code, complexity)
    result = _call_openai(GENERATION_SYSTEM_PROMPT, user_message, GENERATION_SCHEMA)
    scenes = result["scenes"]
    if not scenes:
        raise ValueError("Model returned zero scenes")
    # Generous safety cap only — the prompt asks for ~10-15 chars, this just
    # guards against a runaway response, not the intended length.
    title = (result.get("title") or "").strip()[:40]
    return title, scenes


def _save_title(job_id: str, title: str) -> None:
    """Best-effort: persist the AI-generated title as soon as it's known, so
    the frontend can show it while validation/rendering are still running —
    replacing createJobLambda's placeholder date/time title. Must never fail
    the job over a cosmetic write."""
    if not title:
        return
    try:
        dynamodb.update_item(
            TableName=TABLE_NAME,
            Key={"job_id": {"S": job_id}},
            UpdateExpression="SET title = :t",
            ExpressionAttributeValues={":t": {"S": title}},
        )
    except Exception:
        logger.exception("Job %s: failed to save AI-generated title", job_id)


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
    complexity = event.get("complexity") or "balanced"
    mode = event.get("mode")            # None | 'explain_bug'
    code_error = event.get("code_error")

    if not user_code:
        raise ValueError("Missing user_code in event")

    logger.info(
        "Job %s: generating scenes (model=%s, complexity=%s, mode=%s, manim_available=%s, max_retries=%s)",
        job_id, MODEL, complexity, mode, MANIM_AVAILABLE, MAX_RETRIES,
    )

    title, scenes = _generate_scenes(user_code, complexity, mode, code_error)
    scenes.sort(key=lambda s: s["scene_id"])
    logger.info("Job %s: model produced %d scenes, title=%r", job_id, len(scenes), title)
    _save_title(job_id, title)

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

    # Deterministic post-processing: splice in the code sidebar now that every
    # scene's own content has passed validation — the self-correction loop
    # never has to see or reason about this boilerplate. Sanity-checked with
    # ast.parse since this step is not itself covered by the validator.
    for scene in scenes:
        scene["manim_code"] = inject_code_panel(
            scene["manim_code"], user_code, scene.get("active_lines", [])
        )
        try:
            ast.parse(scene["manim_code"])
        except SyntaxError as e:
            raise RuntimeError(
                f"Job {job_id}: code-panel injection produced invalid syntax "
                f"for scene {scene['scene_id']}: {e}"
            ) from e

    return {"scenes": scenes, "job_id": job_id, "title": title}
