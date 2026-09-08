from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RecentTxnOut(BaseModel):
    id: int
    amount: Decimal
    direction: str
    source_type: str
    balance_after: Decimal
    created_at: datetime
    memo: str


class PublicOut(BaseModel):
    balance: Decimal
    version: int
    recent_txns: list[RecentTxnOut]


class StatsOut(BaseModel):
    month: str
    income: Decimal
    expense: Decimal
    profit_rate: float | None
    public: PublicOut
