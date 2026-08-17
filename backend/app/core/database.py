"""
SQLAlchemy 数据库引擎配置

设计决策：
- SQLite 零配置，适合开发/演示阶段
- 同步 Session（不是 async）——FastAPI 的 def 端点在线程池中执行，
  同步 Session 不会阻塞事件循环。当前规模不需要 async SQLAlchemy。
- Repository 模式封装所有数据库操作——后续切 PostgreSQL 只改连接字符串
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# 数据库文件路径：backend/data/jobpilot.db
# Path(__file__).resolve().parents[2] = backend/
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)  # 不存在则创建

DATABASE_URL = f"sqlite:///{DATA_DIR / 'jobpilot.db'}"

# engine — 进程级单例
# connect_args 的 check_same_thread 是 SQLite 特有的：
# SQLite 默认禁止多线程访问同一个连接，FastAPI 的线程池模式需要关掉
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # 设 True 可以看 SQL 日志（debug 用）
)

# SessionLocal — 每次请求创建一个新 session 的工厂函数
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base — 所有 ORM 模型的基类
Base = declarative_base()


def get_db() -> Session:
    """
    FastAPI Depends 用的数据库会话生成器。

    用法：
        @app.get("/users/me")
        def get_me(db: Session = Depends(get_db)):
            ...

    请求进入时创建 session → 业务代码使用 → 请求结束时自动 close。
    如果中间抛异常，FastAPI 的异常处理也会触发 finally 清理。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
