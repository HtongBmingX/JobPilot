"""用户画像 Repository"""

from sqlalchemy.orm import Session
from backend.app.models.user_profile import UserProfile


class UserProfileRepository:
    """用户画像数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> UserProfile | None:
        return (
            self.db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )

    def get_or_create(self, user_id: int) -> UserProfile:
        """获取画像，不存在则创建空画像"""
        profile = self.get_by_user(user_id)
        if profile:
            return profile
        profile = UserProfile(user_id=user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(self, user_id: int, **kwargs) -> UserProfile:
        """更新画像字段（不存在则创建）"""
        profile = self.get_or_create(user_id)
        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile
