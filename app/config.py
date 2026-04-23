from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    INTERNAL_SECRET: str = "ml_secret_key"

    LOG_LEVEL: str = "INFO"

    DEVICE: str = "cpu"

    TOXIC_THRESHOLD: float = 0.65

    MAX_TEXT_LENGTH: int = 300

    TTS_SAMPLE_RATE: int = 48000

    TTS_SPEAKER: str = "aidar"

<<<<<<< Updated upstream
    # MinIO / S3
    S3_HOST: str = "http://localhost:9000"
=======
    S3_ENDPOINT: str = "http://localhost:9000"
>>>>>>> Stashed changes
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "audio"

    IMAGE_PROVIDER: str = "stable_diffusion"
    IMAGE_WIDTH: int = 1024
    IMAGE_HEIGHT: int = 1024
    IMAGE_NUM_IMAGES: int = 1
    IMAGE_TIMEOUT_SEC: float = 120.0
    IMAGE_NSFW_CHECK_ENABLED: bool = True
    IMAGE_NSFW_THRESHOLD: float = 0.5

    AIRFAIL_API_KEY: str = ""
    AIRFAIL_API_URL: str = "https://app.air.fail/images/flux"
    AIRFAIL_MODEL_ID: str = "flux"

    class Config:
        env_file = ".env"


settings = Settings()
