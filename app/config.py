from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: str
    DEVICE: str = "cpu"

    class Config:
        env_file = ".env"


settings = Settings()