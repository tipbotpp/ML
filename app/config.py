from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    INTERNAL_SECRET: str

    LOG_LEVEL: str = "INFO"

    DEVICE: str = "cpu"

    TOXIC_THRESHOLD: float = 0.65

    MAX_TEXT_LENGTH: int = 300

    TTS_SAMPLE_RATE: int = 48000

    TTS_SPEAKER: str = "aidar"

    # MinIO / S3
    S3_HOST: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "tipbot-dev"

    IMAGE_PROVIDER: str = "stable_diffusion"
    IMAGE_WIDTH: int = 1024
    IMAGE_HEIGHT: int = 1024
    IMAGE_NUM_IMAGES: int = 1
    IMAGE_TIMEOUT_SEC: float = 120.0
    IMAGE_NSFW_CHECK_ENABLED: bool = False
    IMAGE_NSFW_THRESHOLD: float = 0.5

    AIRFAIL_API_KEY: str = ""
    AIRFAIL_API_URL: str = "https://app.air.fail/images/flux"
    AIRFAIL_MODEL_ID: str = "flux"

    CACHE_ENABLED: bool = True
    CACHE_MODERATION_TTL_SECONDS: int = 1800
    CACHE_TTS_TTL_SECONDS: int = 86400
    CACHE_IMAGE_TTL_SECONDS: int = 3600
    CACHE_MAX_ENTRIES: int = 1000
    CACHE_MAX_MEMORY_MB: float = 500.0
    CACHE_CLEANUP_INTERVAL_SECONDS: int = 300

    class Config:
        env_file = ".env"


settings = Settings()