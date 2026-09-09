from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import EmployeeStatus, JobType

PayType = Literal["hourly", "daily"]


class _PayPairValidatorMixin(BaseModel):
    """[O-07] pay_type 与 unit_price 必须同设或同空（DB ck_employees_pay_pair 前置校验）。"""

    @model_validator(mode="after")
    def _pay_pair(self):  # noqa: ANN001, ANN202
        if (self.pay_type is None) != (self.unit_price is None):
            raise ValueError("pay_type 与 unit_price 必须同时设置")
        return self


class EmployeeCreateIn(_PayPairValidatorMixin):
    name: str = Field(min_length=1, max_length=50)
    contact: str = Field(default="", max_length=100)
    job_type: JobType
    notes: str = ""
    pay_type: PayType | None = None
    unit_price: Decimal | None = Field(default=None, gt=0)


class EmployeeUpdateIn(_PayPairValidatorMixin):
    """不接受 status / resigned_on / user_id（extra="forbid" → 422）。

    计薪字段（[O-07]）一旦设置不支持清除，只能改方式或改价。
    """

    model_config = ConfigDict(extra="forbid")

    version: int
    name: str | None = Field(default=None, min_length=1, max_length=50)
    contact: str | None = Field(default=None, max_length=100)
    job_type: JobType | None = None
    notes: str | None = None
    pay_type: PayType | None = None
    unit_price: Decimal | None = Field(default=None, gt=0)


class LeaveCreateIn(BaseModel):
    start_date: date
    end_date: date
    note: str = Field(default="", max_length=200)


class LeaveDeleteIn(BaseModel):
    version: int


class ResignIn(BaseModel):
    effective_on: date
    version: int


class LeaveOut(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    note: str
    version: int


class EmployeeOut(BaseModel):
    id: int
    name: str
    status: EmployeeStatus
    display_status: str   # resigned / on_leave / active [C]
    contact: str
    job_type: JobType
    notes: str
    pay_type: str | None = None      # [O-07]
    unit_price: Decimal | None = None
    resigned_on: date | None
    version: int


class EmployeeDetailOut(EmployeeOut):
    leaves: list[LeaveOut]


class EmployeeListOut(BaseModel):
    items: list[EmployeeOut]


class ResignOut(BaseModel):
    status: str
    resigned_on: date
