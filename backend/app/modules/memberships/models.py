from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Membership(Base):
    """席位（Locked）：一店恰 1 管理者（partial unique）；店长 ≥ 0 不限。"""

    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint("role IN ('manager','store_manager')", name="ck_memberships_role"),
        Index(
            "ux_memberships_one_manager",
            "store_id",
            unique=True,
            postgresql_where=text("role = 'manager'"),
        ),
        Index("ix_memberships_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
