from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RecurringExpense(Base):
    """周期项（B-specs §3.1）：period 仅 month（Locked）；wages 禁手填金额（Locked）。"""

    __tablename__ = "recurring_expenses"
    __table_args__ = (
        CheckConstraint("period = 'month'", name="ck_recurring_period_month"),
        CheckConstraint("kind <> 'wages' OR fixed_amount IS NULL", name="ck_recurring_wages_no_amount"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    period: Mapped[str] = mapped_column(String(10), default="month", nullable=False)
    is_fixed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)


class RecurringOccurrence(Base):
    """浮动项每期录入最小闭环 [C · O-10]：每期一次（UNIQUE），one-shot。"""

    __tablename__ = "recurring_occurrences"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    recurring_expense_id: Mapped[int] = mapped_column(ForeignKey("recurring_expenses.id"))
    period_month: Mapped[str] = mapped_column(String(7))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    ledger_entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entries.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
