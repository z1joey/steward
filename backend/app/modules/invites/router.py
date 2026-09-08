from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, get_current_user, require_role
from app.core.errors import NotFound
from app.enums import Role
from app.modules.auth.models import User
from app.modules.invites.schemas import (
    AcceptInviteOut,
    InviteCreateIn,
    InviteOut,
    PendingListOut,
    RejectInviteOut,
    VersionIn,
)
from app.modules.invites.service import (
    accept_invite,
    create_invite,
    invite_to_out,
    list_pending_for_user,
    reject_invite,
)

router = APIRouter()


@router.post("/stores/{store_id}/invites", status_code=201, response_model=InviteOut)
def create_invite_route(
    store_id: int,
    payload: InviteCreateIn,
    ctx: StoreContext = Depends(require_role(Role.manager)),   # Deny：invites.create（AC-INV-05）
    db: Session = Depends(get_db),
) -> InviteOut:
    if store_id != ctx.store.id:
        # `:id` 与 X-Store-Id 必须一致 [C]；不一致按跨店资源 → 404
        raise NotFound()
    return invite_to_out(db, create_invite(db, ctx, payload.phone))


@router.get("/invites", response_model=PendingListOut)
def list_pending_route(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PendingListOut:
    return list_pending_for_user(db, user)


@router.post("/invites/{invite_id}/accept", response_model=AcceptInviteOut)
def accept_invite_route(
    invite_id: int,
    payload: VersionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcceptInviteOut:
    return accept_invite(db, user, invite_id, payload.version)


@router.post("/invites/{invite_id}/reject", response_model=RejectInviteOut)
def reject_invite_route(
    invite_id: int,
    payload: VersionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RejectInviteOut:
    reject_invite(db, user, invite_id, payload.version)
    return RejectInviteOut()
