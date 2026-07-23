# ============================================
# DOCKERFILE - Deploy lên cloud
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install system deps + ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create dirs
RUN mkdir -p temp logs assets/bgm

# Env vars
ENV MASTERAI_WHISPER_MODEL=tiny
ENV MASTERAI_LOG_LEVEL=INFO
ENV MASTERAI_PORT=7860

EXPOSE 7860

CMD ["python", "server.py"]
