# =============================================================================
# Dockerfile для ML TTS сервиса
# Multi-stage build для минимизации размера итогового образа
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - установка зависимостей
# -----------------------------------------------------------------------------
FROM python:3.12.8-slim-bookworm AS builder

WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt ./

# Устанавливаем зависимости в отдельную директорию
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - минимальный образ для запуска
# -----------------------------------------------------------------------------
FROM python:3.12.8-slim-bookworm AS runtime

LABEL maintainer="qu1nqqy" \
      description="ML TTS Service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

# Создаём непривилегированного пользователя
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Копируем установленные зависимости из builder stage
COPY --from=builder /install /usr/local

# Копируем исходный код приложения
COPY app ./app

# Копируем конфигурацию окружения
COPY .env ./

# Устанавливаем владельца файлов
RUN chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
