"""invites DDL 为 [Open O-08] 的最小 Convention（B-specs §1.1）。"""

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


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        CheckConstraint("role = 'store_manager'", name="ck_invites_role"),
        CheckConstraint(
            "status IN ('pending','accepted','rejected')", name="ck_invites_status"
        ),
        Index(
            "ux_invites_one_pending_per_invitee",
            "store_id",
            "invitee_user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_invites_invitee", "invitee_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    inviter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invitee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 创建时由手机号解析；必须已注册（Locked）
    role: Mapped[str] = mapped_column(String(20), default="store_manager", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
