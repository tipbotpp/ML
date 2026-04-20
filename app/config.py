from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    INTERNAL_SECRET: str = "ml_secret_key"

    LOG_LEVEL: str = "INFO"

    DEVICE: str = "cpu"

    TOXIC_THRESHOLD: float = 0.65

    MAX_TEXT_LENGTH: int = 300

    TTS_SAMPLE_RATE: int = 48000

    TTS_SPEAKER: str = "aidar"

    # MinIO / S3
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_AUDIO: str = "audio"
    S3_BUCKET_IMAGE: str = "images"

    IMAGE_PROVIDER: str = "kandinsky"
    IMAGE_DEFAULT_STYLE: str = "DEFAULT"
    IMAGE_WIDTH: int = 1024
    IMAGE_HEIGHT: int = 1024
    IMAGE_NUM_IMAGES: int = 1
    IMAGE_TIMEOUT_SEC: float = 120.0
    IMAGE_NSFW_CHECK_ENABLED: bool = True
    IMAGE_NSFW_THRESHOLD: float = 0.5
    
    # Performance optimization settings
    IMAGE_POLL_INTERVAL_INITIAL: float = 1.0
    IMAGE_POLL_INTERVAL_MAX: float = 3.0
    IMAGE_POLL_BACKOFF_FACTOR: float = 1.2

    KANDINSKY_API_URL: str = "https://api-key.fusionbrain.ai"
    KANDINSKY_API_KEY: str = ""
    KANDINSKY_SECRET_KEY: str = ""
    KANDINSKY_MODEL_ID: int | None = None

    class Config:
        env_file = ".env"


settings = Settings()
