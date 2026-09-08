from datetime import datetime

from pydantic import BaseModel, Field


class TransferCreateIn(BaseModel):
    phone: str = Field(min_length=1, max_length=32)


class VersionIn(BaseModel):
    version: int


class TransferTargetOut(BaseModel):
    id: int
    phone: str


class TransferOut(BaseModel):
    id: int
    to: TransferTargetOut
    status: str


class StoreRoleOut(BaseModel):
    id: int
    name: str


class AcceptTransferOut(BaseModel):
    store: StoreRoleOut
    role: str = "manager"
