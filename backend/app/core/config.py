from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend 目录
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):

    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    MODEL_NAME: str

    # DashScope（通义千问）embedding 配置——RAG 向量化用
    DASHSCOPE_API_KEY: str = ""              # 为空时 RAG 不可用（优雅降级）
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_DIMENSIONS: int = 1024

    # ↓ Stage 3 新增：LLM 调用健壮性配置（带默认值）
    LLM_TIMEOUT: float = 60.0      # 单次调用超时（秒）
    LLM_MAX_RETRIES: int = 3       # 失败重试次数

    # Redis 配置（带默认值，可被环境变量覆盖）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_MAX_CONNECTIONS: int = 20

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()