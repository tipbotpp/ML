#!/bin/bash
set -e

MARKER=/app/models_cache/.downloaded

if [ ! -f "$MARKER" ]; then
    echo "📦 Downloading models for the first time..."
    python -c "
from transformers import AutoTokenizer, AutoModelForSequenceClassification
AutoTokenizer.from_pretrained('cointegrated/rubert-tiny-toxicity')
AutoModelForSequenceClassification.from_pretrained('cointegrated/rubert-tiny-toxicity')
print('✅ RuBERT loaded')

import torch
torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v3_1_ru.pt', '/tmp/silero_model.pt')
torch.package.PackageImporter('/tmp/silero_model.pt')
print('✅ Silero loaded')
"
    touch "$MARKER"
    echo "✅ Models downloaded"
else
    echo "✅ Models already cached, skipping download"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000