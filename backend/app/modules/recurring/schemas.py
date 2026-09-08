from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.enums import RecurringKind


class RecurringCreateIn(BaseModel):
    """period 不接受输入（固定 month）；误传非 month → 422 period_must_be_month。"""

    name: str = Field(min_length=1, max_length=100)
    kind: RecurringKind
    is_fixed: bool
    fixed_amount: Decimal | None = Field(default=None, gt=0)
    period: str = "month"


class RecurringUpdateIn(BaseModel):
    version: int
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_fixed: bool | None = None
    fixed_amount: Decimal | None = Field(default=None, gt=0)
    active: bool | None = None


class OccurrenceCreateIn(BaseModel):
    """固定项忽略 amount 取 fixed_amount；浮动项必填（TC-02 / [Open O-10]）。"""

    period_month: str
    amount: Decimal | None = Field(default=None, gt=0)
    version: int


class OccurrenceOut(BaseModel):
    id: int
    period_month: str
    amount: Decimal
    recurring_expense_id: int


class RecurringOut(BaseModel):
    id: int
    name: str
    kind: RecurringKind
    period: str
    is_fixed: bool
    fixed_amount: Decimal | None
    active: bool
    version: int
    created_at: datetime
    current_month_occurrence: OccurrenceOut | None = None


class RecurringListOut(BaseModel):
    items: list[RecurringOut]


class OccurrenceCreateOut(BaseModel):
    occurrence: OccurrenceOut
    entry_id: int
