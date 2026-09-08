from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import JobType


class ShiftCreateIn(BaseModel):
    employee_id: int
    start_at: datetime
    end_at: datetime


class ShiftUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    start_at: datetime
    end_at: datetime


class ShiftDeleteIn(BaseModel):
    version: int


class ShiftOut(BaseModel):
    id: int
    employee_id: int
    start_at: datetime
    end_at: datetime
    minutes: int
    version: int


class ShiftEmployeeOut(BaseModel):
    id: int
    name: str
    status: str
    display_status: str
    job_type: JobType
    version: int


class ShiftListOut(BaseModel):
    items: list[ShiftOut]
    employees: list[ShiftEmployeeOut]
