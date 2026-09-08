from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PayrollRun(Base):
    """工资结算批次：一期一次（UNIQUE store+month）= one-shot 兜底 [C]。"""

    __tablename__ = "payroll_runs"
    __table_args__ = ()  # UNIQUE(store_id, period_month) 见迁移 0005

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    period_month: Mapped[str] = mapped_column(String(7))
    settled_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


class PayrollLine(Base):
    """结算行：hours 服务端汇总；amount 由费率规则 [Open O-07]；rate_snapshot JSONB。"""

    __tablename__ = "payroll_lines"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rate_snapshot: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    ledger_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("ledger_entries.id"), nullable=True
    )
