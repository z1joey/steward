from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_role
from app.enums import Role
from app.modules.auth.models import User
from app.modules.invites.models import Invite
from app.modules.memberships.models import Membership
from app.modules.memberships.schemas import (
    MemberOut,
    MembersOut,
    PendingInviteOut,
    PendingTransferOut,
)
from app.modules.transfers.models import Transfer

router = APIRouter()


@router.get("/settings/members", response_model=MembersOut)
def list_members(
    ctx: StoreContext = Depends(require_role(Role.manager)),   # manager only（US-F1 / AC-INV-05）
    db: Session = Depends(get_db),
) -> MembersOut:
    """成员 + pending 邀请 / 转让（仅本店，TA-08）。"""
    member_rows = (
        db.query(Membership, User)
        .join(User, User.id == Membership.user_id)
        .filter(Membership.store_id == ctx.store.id)
        .order_by(Membership.created_at.asc(), Membership.id.asc())
        .all()
    )
    invite_rows = (
        db.query(Invite, User)
        .join(User, User.id == Invite.invitee_user_id)
        .filter(Invite.store_id == ctx.store.id, Invite.status == "pending")
        .order_by(Invite.created_at.asc(), Invite.id.asc())
        .all()
    )
    transfer_rows = (
        db.query(Transfer, User)
        .join(User, User.id == Transfer.to_user_id)
        .filter(Transfer.store_id == ctx.store.id, Transfer.status == "pending")
        .order_by(Transfer.created_at.asc(), Transfer.id.asc())
        .all()
    )
    return MembersOut(
        members=[
            MemberOut(user={"id": u.id, "phone": u.phone}, role=m.role, since=m.created_at)
            for m, u in member_rows
        ],
        pending_invites=[
            PendingInviteOut(id=i.id, user={"id": u.id, "phone": u.phone}, created_at=i.created_at)
            for i, u in invite_rows
        ],
        pending_transfers=[
            PendingTransferOut(id=t.id, user={"id": u.id, "phone": u.phone}, created_at=t.created_at)
            for t, u in transfer_rows
        ],
    )
