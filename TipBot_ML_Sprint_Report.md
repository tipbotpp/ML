## 1. Обертка Silero TTS в FastAPI провайдер

### Endpoint

POST /generate/audio

Request:
{
  "text": "Спасибо за донат"
}

Response:
{
  "file": "uuid.wav",
  "latency": 0.82
}

### Используемая модель

Silero TTS

Параметры:

- language: ru
- speaker: v4_ru
- voice: baya
- sample rate: 48000



## 2. Настройка API ключей


### Реализация

Header авторизация:

x-api-key: ml_secret_key

Middleware проверяет:

- валидность ключа
- возврат 401 при ошибке


## 3. Тестирование latency

### Dataset

100 запросов

Примеры:

- Спасибо за донат
- Ты топ
- Привет чат
- Спасибо за стрим

### Метрики

- avg
- min
- max
- p95

### Результаты (CPU)

avg: 0.8s
p95: 1.1s
min: 0.6s
max: 1.3s



# Endpoints

POST /generate/audio
GET /health


# Стек

- Python
- FastAPI
- Torch
- Silero TTS
- httpx

---

# Результат

Выполнено:

 Silero FastAPI Provider  
 API Keys  
 Latency Tests  

