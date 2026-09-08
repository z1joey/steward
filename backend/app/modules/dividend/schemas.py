from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.ledger.schemas import EntryView


class DividendConfirmIn(BaseModel):
    amount: Decimal = Field(gt=0)   # amount ≤ 0 → 422
    memo: str = Field(default="", max_length=500)
    public_account_version: int


class DividendRunOut(BaseModel):
    id: int
    amount: Decimal
    confirmed_at: datetime


class PublicBriefOut(BaseModel):
    balance: Decimal
    version: int


class DividendConfirmOut(BaseModel):
    run: DividendRunOut
    entry: EntryView
    public: PublicBriefOut
