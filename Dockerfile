FROM python:3.12.8-slim-bookworm AS builder

WORKDIR /app

COPY requirements.txt ./

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

FROM python:3.12.8-slim-bookworm AS runtime

LABEL maintainer="qu1nqqy" \
      description="ML TTS Service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    TRANSFORMERS_CACHE=/app/models_cache \
    TORCH_HOME=/app/models_cache/torch \
    HF_HOME=/app/models_cache/huggingface

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app ./app
COPY .env ./
COPY entrypoint.sh ./

RUN mkdir -p /app/models_cache && \
    chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["./entrypoint.sh"]