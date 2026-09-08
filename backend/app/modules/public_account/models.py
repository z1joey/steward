from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PublicAccountTxn(Base):
    """公账流水（B-specs §2.1，Locked：必与分录配对）。

    仅由 posting service 写入；balance_after 便于「最近变动」与一致性校验 [C]。
    """

    __tablename__ = "public_account_txns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    public_account_id: Mapped[int] = mapped_column(ForeignKey("public_accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(5), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ledger_entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entries.id"))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
