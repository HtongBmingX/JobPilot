"""简历库 Repository"""

from sqlalchemy.orm import Session
from backend.app.models.resume import Resume


class ResumeRepository:
    """简历库数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, name: str, content: str = "", is_default: bool = False) -> Resume:
        resume = Resume(
            user_id=user_id,
            name=name,
            content=content,
            is_default=is_default,
        )
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return resume

    def list_by_user(self, user_id: int) -> list[Resume]:
        """获取用户的所有简历，默认简历排前面"""
        return (
            self.db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.is_default.desc(), Resume.created_at.desc())
            .all()
        )

    def get_by_id(self, resume_id: int, user_id: int) -> Resume | None:
        """按 ID 获取，同时校验归属（防止越权）"""
        return (
            self.db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == user_id)
            .first()
        )

    def get_default(self, user_id: int) -> Resume | None:
        """获取用户的默认简历"""
        return (
            self.db.query(Resume)
            .filter(Resume.user_id == user_id, Resume.is_default == True)  # noqa: E712
            .first()
        )

    def clear_default(self, user_id: int) -> None:
        """清除用户所有简历的默认标记"""
        self.db.query(Resume).filter(Resume.user_id == user_id).update(
            {Resume.is_default: False}
        )

    def update(self, resume_id: int, user_id: int, **kwargs) -> Resume | None:
        """更新简历字段"""
        resume = self.get_by_id(resume_id, user_id)
        if not resume:
            return None
        for key, value in kwargs.items():
            if hasattr(resume, key) and value is not None:
                setattr(resume, key, value)
        self.db.commit()
        self.db.refresh(resume)
        return resume

    def delete(self, resume_id: int, user_id: int) -> bool:
        """删除简历"""
        resume = self.get_by_id(resume_id, user_id)
        if not resume:
            return False
        self.db.delete(resume)
        self.db.commit()
        return True
