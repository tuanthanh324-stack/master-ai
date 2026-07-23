# ============================================
# DOCKERFILE - Deploy lên cloud (Render / HuggingFace)
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install system deps + ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only lightweight binary
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create dirs
RUN mkdir -p temp logs assets/bgm

# Env vars
ENV PORT=7860
ENV MASTERAI_PORT=7860
ENV MASTERAI_WHISPER_MODEL=tiny
ENV MASTERAI_LOG_LEVEL=INFO

EXPOSE 7860

CMD ["python", "-u", "server.py"]
