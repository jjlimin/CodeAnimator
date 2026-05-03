# CodeAnimator

Transform Python code into animated educational videos — automatically.

CodeAnimator takes Python code as input and generates a step-by-step visual animation with narration that explains how the code executes. Built on AWS serverless infrastructure, it uses AI to produce Manim-rendered MP4 videos walkthrough through program execution, variable changes, and data structures.

---

## Demo

1. Paste Python code into the editor
2. Click **Generate**
3. Wait ~2–3 minutes while the pipeline runs
4. Watch and download your animation

---

## How It Works

```
Python Code (user input)
    ↓
Parser Lambda        — converts code to an AST JSON via Python's ast module
    ↓
ScriptGenerator Lambda — uses OpenAI to turn the AST into a Manim animation script
    ↓
Fargate Renderer     — runs Manim + FFmpeg inside a container to render the MP4
    ↓
S3                   — stores the finished video; returns a presigned URL
    ↓
Frontend             — polls for status every 15 s, then plays/downloads the video
```

All steps are orchestrated by AWS Step Functions.

---

## Tech Stack

### Frontend
| Tool | Purpose |
|------|---------|
| React 19 + Vite | UI framework and build tool |
| Monaco Editor | Code editor with syntax highlighting |
| Tailwind CSS 4 | Styling |
| Axios | HTTP client |

### Backend
| Tool | Purpose |
|------|---------|
| AWS Lambda (Python 3.12) | Parser & ScriptGenerator |
| AWS ECS Fargate | Containerised Manim renderer |
| AWS Step Functions | Pipeline orchestration |
| DynamoDB | Job status tracking |
| S3 | Asset + video storage |
| OpenAI API | Animation script generation + TTS narration |
| Manim 0.18 | Mathematical animation engine |
| FFmpeg | Video encoding |

---

## Project Structure

```
CodeAnimator/
├── frontend/                     # React SPA
│   └── src/
│       ├── api/videoApi.js       # generate & status calls
│       ├── components/           # Sidebar, CodeInput, Processing, Done views
│       ├── hooks/useVideoPoll.jsx # 15-second status poller
│       └── pages/GeneratorPage.jsx
│
├── backend/
│   ├── lambdas/
│   │   ├── CodeAnimator-Parser/          # Python → AST JSON
│   │   ├── CodeAnimator-ScriptGenerator/ # AST → Manim script via OpenAI
│   │   ├── CodeAnimator-StatusChecker/   # Job status lookup
│   │   └── CodeAnimator-Notifier/        # Writes video URL to DynamoDB
│   ├── fargate-renderer/                 # Manim rendering service
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── animation_scene.py
│   │   └── renderer.py
│   ├── dynamodb/CodeAnimatorTable.json
│   └── step-functions/CodeAnimator-StepFunction.json
│
└── poc/                          # Early proof-of-concept code
```

---

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.12+
- Docker (for local Fargate renderer testing)
- AWS account with the following set up:
  - DynamoDB table `CodeAnimatorTable`
  - S3 bucket `code-animator-assets`
  - Step Functions state machine deployed
  - Lambda functions deployed
  - ECS Fargate cluster with ECR image `code-animator-engine:latest`

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Fargate Renderer (local testing)

```bash
cd backend/fargate-renderer
pip install -r requirements.txt
python main.py
```

```bash
# Build and push Docker image
docker build -t code-animator-engine:latest .
# Tag and push to your ECR repository
```

---

## Environment Variables

### Frontend

Create a `.env` file inside `frontend/`:

```env
VITE_API_URL=https://<your-api-gateway-url>
```

### Backend Lambdas

Set these in the Lambda console or via IaC:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for script generation and TTS |

### Fargate Renderer

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for TTS narration |
| `AWS_S3_BUCKET` | S3 bucket name (default: `code-animator-assets`) |
| `SCRIPT_DATA` | Injected at runtime by Step Functions |

---

## API Reference

### `POST /generate`

Start a new animation job.

**Request body:**
```json
{
  "UserID": "string",
  "ProjectID": "string",
  "code": "# Python code here"
}
```

**Response:** Returns the `ProjectID` used to poll status.

---

### `GET /status?userId=&projectId=`

Poll job progress.

**Response:**
```json
{
  "Status": "Done",
  "S3_VideoUrl": "https://..."
}
```

**Status values:** `Parsing` → `GeneratingContent` → `ScriptGenerated` → `Done` | `Error` | `SyntaxError`

---

## DynamoDB Schema

**Table:** `CodeAnimatorTable`  
**Primary key:** `UserID` (partition) + `ProjectID` (sort, format `PROJ#{job_id}`)

Key attributes: `Status`, `startTime`, `VideoS3Key`, `VideoURL`, `FinishedAt`, `errorMessage`

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Open a pull request against `main`

---

## License

MIT
