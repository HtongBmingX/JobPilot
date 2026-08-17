"""
用户画像 ORM 模型

跨会话沉淀用户的关键求职信息——即使换了 session、过了 24h TTL，
这些信息也持久化在 SQLite 里，Agent 可以持续引用。

字段设计（都是可选，用户逐步填写）：
- user_id: 一对一关联 users 表
- tech_stack: 技术栈（如 "Python, FastAPI, Redis"）
- target_role: 目标岗位（如 "后端开发工程师"）
- target_companies: 目标公司（如 "字节跳动, 腾讯"）
- education: 学历背景
- experience_summary: 工作/项目经历摘要
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from backend.app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    tech_stack = Column(Text, nullable=True)
    target_role = Column(String(100), nullable=True)
    target_companies = Column(Text, nullable=True)
    education = Column(String(200), nullable=True)
    experience_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, role='{self.target_role}')>"
