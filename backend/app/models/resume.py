"""
简历库 ORM 模型

支持用户保存多份简历（针对不同岗位定制不同版本）。

字段设计：
- id: 自增主键
- user_id: 外键关联 users 表，每个用户有多份简历
- name: 简历名称（如"后端开发版"、"算法版"，用户自定义）
- content: 简历全文
- is_default: 是否默认简历（切换时优先使用）
- created_at / updated_at: 时间戳
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from backend.app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(100), nullable=False, default="我的简历")
    content = Column(Text, nullable=False, default="")
    is_default = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Resume(id={self.id}, name='{self.name}')>"
