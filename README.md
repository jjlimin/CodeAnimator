# CodeAnimator

Transform Python code into animated educational videos — automatically.

CodeAnimator takes Python code as input and generates a narrated, step-by-step
Manim animation explaining how the code works. An AI agent with a
self-correction loop generates the scenes, AWS Fargate renders them in
parallel, and the final video (with TTS voiceover) lands in S3.

---

## How It Works

```
user_code
    ↓
createJobLambda        — creates job_id, writes PENDING to DynamoDB,
    ↓                    starts the Step Function
Step Function: ai-code-animator-state-machine
    │
    ├─ 1. AIAgentLambda            — AI agent generates the scenes
    │       generate → validate → self-correct loop (see below)
    │       returns {job_id, scenes: [{scene_id, narration, manim_code}]}
    │
    ├─ 2. RenderScenesMap          — Map over scenes, MaxConcurrency 4
    │       each scene → ECS Fargate task (manim-container):
    │       OpenAI TTS (gpt-4o-mini-tts) → Manim render → ffmpeg mux
    │       (narration merged into the video) → S3 jobs/{job_id}/scenes/
    │
    └─ 3. concatVideosLambda       — ffmpeg concat (stream copy) →
            jobs/{job_id}/final_output.mp4, DynamoDB status = COMPLETED

CheckStatusLambda      — GET status/video_url by job_id
```

## The AI Agent (AIAgentLambda)

The core of the pipeline is an agentic loop that guarantees the generated
Manim code actually runs before it ever reaches the renderer:

1. **Generate** — one OpenAI **Responses API** call (structured JSON output).
   The model decides the number of scenes dynamically: total narration is
   budgeted at 60–120 seconds (~150 words/min), fewer/shorter scenes for
   simpler input.
2. **Validate** every scene without rendering video, in tiers:
   - `ast.parse` syntax check;
   - static Manim lint — structure checks plus a table of APIs/kwargs that
     LLMs hallucinate from old Manim versions (`ShowCreation`, `Code(code=...)`,
     `Code(font_size=...)`, …) with the correct replacement in the error text;
   - full dry-run execution in a subprocess (`config.dry_run = True`) — only
     where the `manim` package is importable (local dev / container), skipped
     automatically in the zip-packaged Lambda.
3. **Self-correct** — failed scenes go back to the model with their exact
   error/traceback; validated scenes are frozen. Up to `MAX_RETRIES` rounds
   (default 3), also bounded by the Lambda's remaining execution time.
4. On success: raw code strings out. If a scene still fails after all
   retries, the job fails loudly (no broken code reaches the renderer).

Test it locally without any AWS (mocks the Lambda event/context):

```bash
cd backend/lambdas/AIAgentLambda
pip install openai manim          # manim optional but enables full dry-run validation
echo "OPENAI_API_KEY=sk-..." > .env
python local_test.py              # built-in sample
python local_test.py --file my_code.py
python local_test.py --self-test  # validator smoke test, no API calls
```

---

## Project Structure

```
CodeAnimator/
├── frontend/                          # React SPA (NOTE: targets the previous
│                                      #  API contract — pending update)
├── backend/
│   ├── lambdas/
│   │   ├── AIAgentLambda/             # the AI agent (see above)
│   │   │   ├── lambda_function.py     # handler + self-correction loop
│   │   │   ├── prompts.py             # system prompts + JSON schemas
│   │   │   ├── validator.py           # tiered Manim validation
│   │   │   ├── local_test.py          # local harness (no AWS needed)
│   │   │   └── requirements.txt
│   │   ├── concatVideosLambda/        # ffmpeg concat of rendered scenes
│   │   ├── createJobLambda/           # job creation + state machine start
│   │   ├── CheckStatusLambda/         # job status lookup
│   │   └── ApiTriggerLambda/          # (stub)
│   ├── fargate-worker/                # ECS render container
│   │   ├── Dockerfile                 # extends the worker image, adds ffmpeg
│   │   └── render_worker.py           # TTS → Manim render → audio mux → S3
│   ├── layers/                        # Lambda layer build docs + scripts
│   ├── step-functions/ai-code-animator-state-machine.json
│   ├── ecs/ManimRenderTask.json       # task definition (family revision 4+)
│   └── dynamodb/CodeAnimatorJobs.json
├── poc/                               # early proof-of-concept code
└── docs/
```

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Scene generation | OpenAI Responses API, `gpt-4.1-mini`, structured outputs |
| Narration (TTS) | OpenAI `gpt-4o-mini-tts` (voice: alloy) |
| Animation engine | Manim Community v0.20 (in the Fargate container) |
| Rendering | ECS Fargate (2 vCPU / 4 GB), up to 4 scenes in parallel |
| Video assembly | ffmpeg (mux in container; concat via `ffmpeg-layer` in Lambda) |
| Orchestration | AWS Step Functions |
| State / storage | DynamoDB `CodeAnimatorJobs`, S3 `code-animator-media-bucket-2026` |
| Compute | AWS Lambda python3.12 (zip + layers — no container Lambdas needed) |

---

## Deployment Notes (AWS Academy Learner Lab)

- All Lambdas run with `LabRole`, region `us-east-1`.
- `AIAgentLambda`: timeout 300s, 512MB, layer `openai-linux-layer`,
  env `OPENAI_API_KEY` + `OPENAI_MODEL` (default `gpt-4o-mini`; deployed with
  `gpt-4.1-mini`).
- `concatVideosLambda`: timeout 300s, 1024MB, 2GB `/tmp`, layer `ffmpeg-layer`.
- Render image: ECR `code-animator-manim-worker:v4` — build from
  `backend/fargate-worker/`, push, then register a new `ManimRenderTask`
  revision pointing at the new tag (the state machine picks up the latest
  revision automatically).
- The state machine JSON in this repo has the OpenAI key replaced with
  `REPLACE_WITH_OPENAI_API_KEY` — set the real key when creating/updating it.
- Update Lambda code with:
  ```bash
  cd backend/lambdas/AIAgentLambda
  zip -j deploy.zip lambda_function.py prompts.py validator.py
  aws lambda update-function-code --function-name AIAgentLambda --zip-file fileb://deploy.zip
  ```

---

## API Reference

### `POST createJobLambda` — body:
```json
{ "user_code": "# Python code here" }
```
Returns `{ "job_id": "...", "message": "Job started" }`.

### `CheckStatusLambda` — `?job_id=...`
Returns `{ "job_id", "status": "PENDING" | "COMPLETED", "video_url" }`.

---

## License

MIT
