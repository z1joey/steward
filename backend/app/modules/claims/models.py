from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ExpenseClaim(Base):
    """报销单（B-specs §2.1）。

    status: pending / posted / rejected [C · O-04]（无 approved-not-posted）；
    ledger_entry_id 在 approve post() 后回填。
    """

    __tablename__ = "expense_claims"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    entry_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    memo: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ledger_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("ledger_entries.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
