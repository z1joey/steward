from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.enums import Direction


class EntryCreateIn(BaseModel):
    """记一笔（O-23 拍板前：direction 可选，默认 expense，弹窗不暴露控件）。"""

    date: date_type
    amount: Decimal = Field(gt=0)
    memo: str = Field(default="", max_length=500)
    needs_reimbursement: bool
    direction: Direction = Direction.expense


class RequestedByOut(BaseModel):
    id: int
    phone: str


class ClaimView(BaseModel):
    id: int
    date: date_type
    amount: Decimal
    memo: str
    status: str
    requested_by: RequestedByOut
    decided_at: datetime | None = None
    ledger_entry_id: int | None = None
    version: int


class EntryView(BaseModel):
    id: int
    date: date_type
    amount: Decimal
    direction: str
    memo: str
    source_type: str
    source_id: int | None = None
    is_reversal: bool
    reversed_by_id: int | None = None
    claim_status: str | None = None
    version: int
    created_at: datetime


class EntryCreateOut(BaseModel):
    kind: str  # "entry" | "claim"
    entry: EntryView | None = None
    claim: ClaimView | None = None


class LedgerRowOut(BaseModel):
    """流水行：普通分录（row_type=entry）或待审报销行（row_type=claim_pending）[C]。"""

    row_type: str = "entry"
    id: int
    date: date_type
    amount: Decimal
    direction: str | None = None
    memo: str = ""
    source_type: str | None = None
    source_id: int | None = None
    is_reversal: bool = False
    reversed_by_id: int | None = None
    claim_status: str | None = None
    version: int = 1
    created_at: datetime | None = None
    requested_by: RequestedByOut | None = None


class LedgerListOut(BaseModel):
    items: list[LedgerRowOut]
    total: int


class ReverseEntryIn(BaseModel):
    """冲正（reason 是否必填 [Open O-09]，Convention 可选）。"""

    version: int
    reason: str = Field(default="", max_length=500)


class ReversalPublicTxnOut(BaseModel):
    id: int
    balance_after: Decimal | None = None


class ReverseEntryOut(BaseModel):
    entry: EntryView          # 反向分录
    original: EntryView       # 原分录（reversed_by_id 已回填）
    public_txn: ReversalPublicTxnOut | None = None
