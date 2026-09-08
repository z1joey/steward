from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LedgerEntry(Base):
    """流水分录（B-specs §2.1）。

    reverses_entry_id 非空 = 冲正分录（继承原 source_type [C]）；
    reversed_by_id 为原分录被冲正后的唯一允许回填（不改金额/内容）[C]。
    """

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    ledger_id: Mapped[int] = mapped_column(ForeignKey("ledgers.id"))
    entry_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    memo: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reverses_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("ledger_entries.id"), nullable=True
    )
    reversed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("ledger_entries.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
