"""
用户 ORM 模型

字段设计说明：
- username: 唯一索引，用于登录
- hashed_password: bcrypt 哈希后的密码，不存明文
- created_at: 注册时间，用于后续做"试用期"功能
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
