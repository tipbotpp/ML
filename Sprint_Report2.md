## Sprint 3

### 1. ML Провайдер модерации текста (ruBERT)

#### Реализовано

-   Интеграция ruBERT модели токсичности
-   FastAPI endpoint `/moderation/check`
-   Проверка стоп-слов
-   Проверка длины сообщения
-   API key защита

#### Используемая модель

-   cointegrated/rubert-tiny-toxicity

#### Endpoint

POST /moderation/check

Request:

``` json
{
  "text": "Ты тупой стример"
}
```

Response:

``` json
{
  "is_toxic": true,
  "toxicity_score": 0.91,
  "blocked": true
}
```

------------------------------------------------------------------------

### 2. Настройка возврата ошибок JSON



#### Реализовано

Единый формат ошибок:

``` json
{
  "error": true,
  "code": "TOXIC_MESSAGE",
  "message": "Сообщение содержит токсичность"
}
```

Добавлены ошибки:

-   TOXIC_MESSAGE
-   STOP_WORD
-   TEXT_TOO_LONG
-   TTS_ERROR
-   INTERNAL_ERROR

Глобальный exception handler

------------------------------------------------------------------------

### 3. Тестирование на реальных донатах



#### Реализовано

Создан dataset:

-   токсичные сообщения
-   нормальные сообщения

Добавлены тесты:

tests/moderation_test.py\

#### Метрики

  Метрика           Значение
  ----------------- ----------
  Accuracy          \~90%
  Avg Latency CPU   80ms
  Throughput        \~10 rps

------------------------------------------------------------------------




## Используемые технологии

-   Python 3.11
-   FastAPI
-   PyTorch
-   ruBERT
-   Silero TTS
-   Transformers

------------------------------------------------------------------------

## Переменные окружения

    API_KEY=ml_secret_key
    DEVICE=cpu
    TOXIC_THRESHOLD=0.65
    MAX_TEXT_LENGTH=300
    TTS_SAMPLE_RATE=48000
    TTS_SPEAKER=aidar

------------------------------------------------------------------------

## Запуск сервиса

``` bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

------------------------------------------------------------------------

## Swagger

http://localhost:8000/docs

------------------------------------------------------------------------

