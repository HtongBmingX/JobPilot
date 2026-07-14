from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend 目录
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):

    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    MODEL_NAME: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()