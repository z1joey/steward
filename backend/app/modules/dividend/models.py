from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DividendRun(Base):
    """分红记录（B-specs §3.1）：dividend_plans [Open O-02]，MVP 只落 runs。"""

    __tablename__ = "dividend_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    memo: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    confirmed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ledger_entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entries.id"))
    public_txn_id: Mapped[int] = mapped_column(ForeignKey("public_account_txns.id"))
