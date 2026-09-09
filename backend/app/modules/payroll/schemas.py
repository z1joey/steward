from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PayrollSettleIn(BaseModel):
    """仅接受 month；金额字段 → 422 client_amount_forbidden（Locked，AC-REC-03）。

    extra="forbid"：month 之外的任何字段都被拒绝。
    """

    model_config = ConfigDict(extra="forbid")

    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class PayrollPreviewRow(BaseModel):
    employee_id: int
    name: str
    hours: Decimal
    worked_days: int = 0   # [O-07] 自然日出勤天数（按日算法依据）
    amount: Decimal | None
    segments_count: int
    pay_type: str | None = None   # hourly / daily；null = 未设置计薪


class PayrollLineView(BaseModel):
    employee_id: int
    hours: Decimal
    amount: Decimal
    ledger_entry_id: int | None


class PayrollRunView(BaseModel):
    id: int
    period_month: str
    total_amount: Decimal
    lines: list[PayrollLineView]


class PayrollOut(BaseModel):
    month: str
    settled: PayrollRunView | None
    preview: list[PayrollPreviewRow]
    total_hours: Decimal
    total_amount: Decimal | None


class SettleOut(BaseModel):
    run: PayrollRunView
