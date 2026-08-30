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

    # RAG 拒答阈值：检索结果 top-1 的向量余弦相似度低于此值时，视为「知识库外问题」，
    # 返回「无相关内容」而非强行召回低相关文档。0.0 = 不启用（保持原行为）。
    # 注意：阈值必须基于向量余弦相似度（0~1），不能基于 RRF 排名分数（量纲不同）。
    # 校准方法：跑 python -m backend.app.rag.eval.runner --real，对比
    # 「命中题 top1 相似度」和「负例 top1 相似度」（报告里的 negative_avg_top1_sim），
    # 取两者之间的值。实测负例约 0.374，命中题远高于此。
    RAG_SIMILARITY_THRESHOLD: float = 0.0

    # ↓ Stage 3 新增：LLM 调用健壮性配置（带默认值）
    LLM_TIMEOUT: float = 60.0      # 单次调用超时（秒）
    LLM_MAX_RETRIES: int = 3       # 失败重试次数

    # MCP（Model Context Protocol）配置——GitHub Server 用（只读 PAT 即可）
    # 为空时 MCP 不可用，Agent 正常降级（和 RAG 未配置 DashScope key 一致）
    GITHUB_PAT: str = ""

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