FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    zlib1g-dev \
    texlive-latex-base \
    texlive-fonts-recommended \
    cm-super \
    dvipng \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
ENV MANIM_RENDERER=cairo

WORKDIR /app

RUN pip install --no-cache-dir "setuptools>=65,<80"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
