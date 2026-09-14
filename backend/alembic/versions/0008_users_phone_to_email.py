"""EMAIL-1: 登录身份 phone → email（users 列重命名 + 类型放宽 + 约束更名）

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users RENAME COLUMN phone TO email")
    op.execute("ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(255)")
    op.execute("ALTER INDEX ux_users_phone RENAME TO ux_users_email")


def downgrade() -> None:
    op.execute("ALTER INDEX ux_users_email RENAME TO ux_users_phone")
    op.execute("ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(32)")
    op.execute("ALTER TABLE users RENAME COLUMN email TO phone")
