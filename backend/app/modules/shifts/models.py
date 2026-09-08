from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ShiftSegment(Base):
    """班次段（B-specs §4.1）：分钟精度（秒截 0）；同人重叠 → 422 [C · O-24]。"""

    __tablename__ = "shift_segments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
