"""transfers DDL 为 [Open O-08] 的最小 Convention（B-specs §1.1）。

拒绝 / 取消流不实现（O-08）：status 仅 pending / accepted。
"""

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


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted')", name="ck_transfers_status"
        ),
        Index(
            "ux_transfers_one_pending_per_store",
            "store_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_transfers_to", "to_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 发起时的管理者
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))    # 必须已注册 [C]
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
