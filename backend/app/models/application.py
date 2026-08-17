"""
投递记录 ORM 模型

字段设计：
- id: 自增主键
- user_id: 外键关联 users 表，每个用户有自己的投递列表
- company: 公司名（从 JD 提取，或用户手动输入）
- position: 岗位名
- jd_text: JD 原文备份（可选，后续回顾用）
- match_score: 匹配度分数（从 match_result 中提取）
- match_summary: 匹配分析摘要（LLM 输出中截取的关键结论）
- status: 当前状态（枚举：applied / screening / interviewing / offered / rejected）
- applied_at: 投递日期
- notes: 用户备注
- created_at / updated_at: 记录时间戳
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from backend.app.core.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    company = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)
    jd_text = Column(Text, nullable=True)
    match_score = Column(String(20), nullable=True)
    match_summary = Column(Text, nullable=True)

    # 状态：applied / screening / interviewing / offered / rejected
    status = Column(String(20), nullable=False, default="applied")

    applied_at = Column(String(20), nullable=True)  # "2026-07-24"
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Application(id={self.id}, {self.company} - {self.position}, status={self.status})>"
