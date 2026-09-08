from decimal import Decimal

from pydantic import BaseModel


class PendingClaimsOut(BaseModel):
    count: int
    amount: Decimal


class StoreBriefOut(BaseModel):
    id: int
    name: str


class OverviewOut(BaseModel):
    store: StoreBriefOut
    month: str
    income: Decimal
    expense: Decimal
    public_balance: Decimal
    pending_claims: PendingClaimsOut
