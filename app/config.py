from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    API_KEY: str = "ml_secret_key"

    DEVICE: str = "cpu"

    TOXIC_THRESHOLD: float = 0.65

    MAX_TEXT_LENGTH: int = 300

    TTS_SAMPLE_RATE: int = 48000

    TTS_SPEAKER: str = "aidar"


    class Config:
        env_file = ".env"


settings = Settings()