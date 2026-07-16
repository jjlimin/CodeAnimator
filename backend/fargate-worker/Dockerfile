# v4: extends the exact deployed worker image (v3) — same manim/texlive env —
# adding ffmpeg (for narration muxing) and the fixed render_worker.py.
FROM 719246278807.dkr.ecr.us-east-1.amazonaws.com/code-animator-manim-worker@sha256:da41e595183810e2cf60c82dfe5b89f2125ccdff4c4319b97e7ce33437bebbac

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY render_worker.py /app/render_worker.py
WORKDIR /app
CMD ["python", "render_worker.py"]
