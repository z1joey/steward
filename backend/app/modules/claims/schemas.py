from decimal import Decimal

from pydantic import BaseModel

from app.modules.ledger.schemas import ClaimView, EntryView


class VersionIn(BaseModel):
    version: int


class PublicTxnBrief(BaseModel):
    id: int
    balance_after: Decimal | None = None


class ApproveClaimOut(BaseModel):
    claim: ClaimView
    entry: EntryView
    public_txn: PublicTxnBrief


class RejectClaimOut(BaseModel):
    claim: ClaimView


class ClaimListOut(BaseModel):
    items: list[ClaimView]
