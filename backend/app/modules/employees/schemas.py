from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import EmployeeStatus, JobType


class EmployeeCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    contact: str = Field(default="", max_length=100)
    job_type: JobType
    notes: str = ""


class EmployeeUpdateIn(BaseModel):
    """不接受 status / resigned_on / user_id（extra="forbid" → 422）。"""

    model_config = ConfigDict(extra="forbid")

    version: int
    name: str | None = Field(default=None, min_length=1, max_length=50)
    contact: str | None = Field(default=None, max_length=100)
    job_type: JobType | None = None
    notes: str | None = None


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
    resigned_on: date | None
    version: int


class EmployeeDetailOut(EmployeeOut):
    leaves: list[LeaveOut]


class EmployeeListOut(BaseModel):
    items: list[EmployeeOut]


class ResignOut(BaseModel):
    status: str
    resigned_on: date
