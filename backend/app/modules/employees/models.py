from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Employee(Base):
    """员工（B-specs §4.1）：五值 job_type（Locked）；resigned_on ⇔ status（CHECK）；
    user_id 预留恒 NULL，无绑定流（Locked，[Open O-13]）。
    """

    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('long_term','summer','winter','weekend','temporary')",
            name="ck_employees_job_type",
        ),
        CheckConstraint(
            "(status = 'resigned') = (resigned_on IS NOT NULL)",
            name="ck_employees_resigned_pair",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    name: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    contact: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resigned_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)


class EmployeeLeave(Base):
    """请假（[Open O-25]：不影响工时汇总）；当日落在区间内 → 展示态「请假」。"""

    __tablename__ = "employee_leaves"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_employee_leaves_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
