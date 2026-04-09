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

    class Config:
        env_file = ".env"


settings = Settings()
