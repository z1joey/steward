from datetime import datetime

from pydantic import BaseModel


class MemberUserOut(BaseModel):
    id: int
    phone: str


class MemberOut(BaseModel):
    user: MemberUserOut
    role: str
    since: datetime


class PendingInviteOut(BaseModel):
    id: int
    user: MemberUserOut
    created_at: datetime


class PendingTransferOut(BaseModel):
    id: int
    user: MemberUserOut
    created_at: datetime


class MembersOut(BaseModel):
    members: list[MemberOut]
    pending_invites: list[PendingInviteOut]
    pending_transfers: list[PendingTransferOut]
