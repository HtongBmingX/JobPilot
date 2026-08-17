"""
用户 Repository 层

Repository 模式的价值：
- 业务代码通过 UserRepository 操作数据库，不直接依赖 SQLAlchemy Session
- 后续切数据库（SQLite → PostgreSQL）只改 repository 内部实现
- 可测试——单元测试时 mock UserRepository 即可，不需要真实数据库
"""

from sqlalchemy.orm import Session
from backend.app.models.user import User


class UserRepository:
    """用户数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, username: str, hashed_password: str) -> User:
        """创建新用户，返回 ORM 对象"""
        user = User(username=username, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)  # 获取数据库生成的 id 和 created_at
        return user

    def get_by_username(self, username: str) -> User | None:
        """按用户名查找用户。用户名是唯一索引，最多返回一条"""
        return self.db.query(User).filter(User.username == username).first()

    def get_by_id(self, user_id: int) -> User | None:
        """按 ID 查找用户"""
        return self.db.query(User).filter(User.id == user_id).first()
