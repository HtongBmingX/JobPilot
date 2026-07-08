from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    MODEL_NAME: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

settings = Settings()