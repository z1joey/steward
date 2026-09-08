from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InviteCreateIn(BaseModel):
    phone: str = Field(min_length=1, max_length=32)


class VersionIn(BaseModel):
    version: int


class InviteeOut(BaseModel):
    id: int
    phone: str


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    invitee: InviteeOut
    status: str
    created_at: datetime


class StoreRefOut(BaseModel):
    id: int
    name: str


class AcceptInviteOut(BaseModel):
    store: StoreRefOut
    role: str = "store_manager"


class RejectInviteOut(BaseModel):
    status: str = "rejected"


class PendingInviteItem(BaseModel):
    id: int
    store: StoreRefOut
    inviter_phone: str
    created_at: datetime


class PendingTransferItem(BaseModel):
    id: int
    store: StoreRefOut
    from_phone: str
    created_at: datetime


class PendingListOut(BaseModel):
    invites: list[PendingInviteItem]
    transfers: list[PendingTransferItem]
