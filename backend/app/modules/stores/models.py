from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)


class Ledger(Base):
    """一店一账本（UNIQUE store），建店事务内创建。"""

    __tablename__ = "ledgers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), unique=True)


class PublicAccount(Base):
    """公账：余额唯一真相在 Postgres；余额变动仅经 posting service（Phase B）。"""

    __tablename__ = "public_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), unique=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
