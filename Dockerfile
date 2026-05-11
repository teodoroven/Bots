FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        flac \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

RUN mkdir -p \
        attachments \
        cache \
        files \
        logs \
        voice \
    && useradd --uid 1000 --create-home --shell /usr/sbin/nologin botuser \
    && chown -R botuser:botuser /app

USER botuser

VOLUME ["/app/logs", "/app/attachments", "/app/cache", "/app/files", "/app/voice"]

CMD ["python", "main.py"]
