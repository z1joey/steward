"""公账 schemas（余额调整 [管理者]，B-specs §2.2 钱管道约束下的受控修改）。"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.claims.schemas import PublicTxnBrief
from app.modules.ledger.schemas import EntryView


class BalanceAdjustIn(BaseModel):
    """公账余额调整：输入盘点后的正确余额，服务端计算差额入账。

    reason 必填（审计要求，strip 后不得为空），原样落入分录 memo
    （「公账调整：<原因>」）；public_account_version 为乐观锁
    （GET /ledger/stats 返回值）。
    """

    new_balance: Decimal = Field(max_digits=14, decimal_places=2)
    reason: str = Field(min_length=1, max_length=500)
    public_account_version: int

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("原因不能为空")
        return v


class BalanceAdjustOut(BaseModel):
    entry: EntryView
    public_txn: PublicTxnBrief
    balance: Decimal
