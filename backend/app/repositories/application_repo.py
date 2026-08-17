"""
投递记录 Repository
"""

from sqlalchemy.orm import Session
from backend.app.models.application import Application


class ApplicationRepository:
    """投递记录数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        company: str,
        position: str,
        jd_text: str = None,
        match_score: str = None,
        match_summary: str = None,
        applied_at: str = None,
        notes: str = None,
    ) -> Application:
        app = Application(
            user_id=user_id,
            company=company,
            position=position,
            jd_text=jd_text,
            match_score=match_score,
            match_summary=match_summary,
            applied_at=applied_at,
            notes=notes,
            status="applied",
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app

    def list_by_user(self, user_id: int, status: str = None) -> list[Application]:
        """获取用户的所有投递记录，可选按状态筛选"""
        q = self.db.query(Application).filter(Application.user_id == user_id)
        if status:
            q = q.filter(Application.status == status)
        return q.order_by(Application.created_at.desc()).all()

    def get_by_id(self, app_id: int, user_id: int) -> Application | None:
        """按 ID 获取，同时校验归属（防止越权）"""
        return (
            self.db.query(Application)
            .filter(Application.id == app_id, Application.user_id == user_id)
            .first()
        )

    def update(self, app_id: int, user_id: int, **kwargs) -> Application | None:
        """更新字段（status、notes 等），返回更新后的对象"""
        app = self.get_by_id(app_id, user_id)
        if not app:
            return None
        for key, value in kwargs.items():
            if hasattr(app, key) and value is not None:
                setattr(app, key, value)
        self.db.commit()
        self.db.refresh(app)
        return app

    def delete(self, app_id: int, user_id: int) -> bool:
        """删除记录，返回是否成功"""
        app = self.get_by_id(app_id, user_id)
        if not app:
            return False
        self.db.delete(app)
        self.db.commit()
        return True
