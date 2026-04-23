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

# --- НАЧАЛО: Предзагрузка моделей в слой билдера ---
# Важно: Мы скачиваем модели от root, но сохраняем их в фиксированную папку /models_cache,
# чтобы потом легко скопировать их в runtime stage.
ENV TRANSFORMERS_CACHE=/models_cache \
    TORCH_HOME=/models_cache/torch \
    HF_HOME=/models_cache/huggingface

# Создаем директорию для кеша и даем права 777 (чтобы потом appuser мог читать)
RUN mkdir -p /models_cache && chmod 777 /models_cache

# Скрипт предзагрузки.
# Используем python -c для скачивания конкретных моделей.
# Если список моделей большой, лучше вынести в отдельный файл preload.py и скопировать его.
RUN python -c "\
from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
AutoTokenizer.from_pretrained('cointegrated/rubert-tiny-toxicity'); \
AutoModelForSequenceClassification.from_pretrained('cointegrated/rubert-tiny-toxicity'); \
print('✅ RuBERT loaded'); \
\
import torch; \
torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v3_1_ru.pt', '/tmp/silero_model.pt'); \
torch.package.PackageImporter('/tmp/silero_model.pt'); \
print('✅ Silero loaded'); \
"
# --- КОНЕЦ: Предзагрузка моделей ---
# -----------------------------------------------------------------------------
# Stage 2: Runtime - минимальный образ для запуска
# -----------------------------------------------------------------------------
FROM python:3.12.8-slim-bookworm AS runtime

LABEL maintainer="qu1nqqy" \
      description="ML TTS Service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"
# --- НАЧАЛО: Копирование кеша моделей ---
# Указываем приложению, где лежат скачанные модели.
# Важно: переменные должны совпадать с путями из stage builder.
ENV TRANSFORMERS_CACHE=/models_cache \
    TORCH_HOME=/models_cache/torch \
    HF_HOME=/models_cache/huggingface
# --- КОНЕЦ: Копирование кеша моделей ---

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
