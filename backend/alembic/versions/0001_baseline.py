"""baseline: 标记现有 users/applications 表

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-15

这是基线迁移——users 和 applications 表已通过 Base.metadata.create_all 存在。
后续新表（Resume/UserProfile）的迁移从这个基线开始。
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0001_baseline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 基线：不创建任何表，只是标记现有状态。
    # 如果数据库中还没有表（全新环境），则由 create_all 或后续迁移负责。
    pass


def downgrade() -> None:
    pass
