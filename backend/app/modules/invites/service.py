from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AlreadyProcessed, Conflict, Forbidden, NotFound, VersionConflict
from app.core.deps import StoreContext
from app.modules.auth.models import User
from app.modules.invites.models import Invite
from app.modules.invites.schemas import (
    AcceptInviteOut,
    InviteOut,
    PendingInviteItem,
    PendingListOut,
    PendingTransferItem,
)
from app.modules.memberships.models import Membership
from app.modules.stores.models import Store
from app.modules.transfers.models import Transfer


def create_invite(db: Session, ctx: StoreContext, phone: str) -> Invite:
    """邀请店长（Locked：不限店长人数；两次校验「对方尚非本店成员」）。"""
    phone = phone.strip()
    invitee = db.query(User).filter(User.phone == phone).one_or_none()
    if invitee is None:
        raise NotFound("phone_not_registered")   # 必须已注册（Locked）
    already_member = (
        db.query(Membership)
        .filter(Membership.store_id == ctx.store.id, Membership.user_id == invitee.id)
        .one_or_none()
    )
    if already_member is not None:
        raise Conflict("already_member")          # 对方已是本店成员（AC-INV-04）
    pending = (
        db.query(Invite)
        .filter(
            Invite.store_id == ctx.store.id,
            Invite.invitee_user_id == invitee.id,
            Invite.status == "pending",
        )
        .one_or_none()
    )
    if pending is not None:
        raise Conflict("pending_exists")          # 同一人同店重复待接受（AC-INV-04）
    invite = Invite(
        store_id=ctx.store.id,
        inviter_user_id=ctx.user.id,
        invitee_user_id=invitee.id,
        role="store_manager",
        status="pending",
        version=1,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def invite_to_out(db: Session, invite: Invite) -> InviteOut:
    invitee = db.get(User, invite.invitee_user_id)
    return InviteOut(
        id=invite.id,
        store_id=invite.store_id,
        invitee={"id": invitee.id, "phone": invitee.phone},
        status=invite.status,
        created_at=invite.created_at,
    )


def _resolve_one_shot_failure(db: Session, invite_id: int, user: User) -> None:
    """rowcount=0 判定（B-specs §1.5）：不存在/非本人 403 · 已处理 409 · 版本 409。"""
    invite = db.get(Invite, invite_id)
    if invite is None or invite.invitee_user_id != user.id:
        raise Forbidden("not_invitee")
    if invite.status != "pending":
        raise AlreadyProcessed()
    raise VersionConflict()


def accept_invite(db: Session, user: User, invite_id: int, version: int) -> AcceptInviteOut:
    """one-shot 条件更新 + 插入店长 membership（B-specs §1.5）。"""
    updated = db.scalars(
        update(Invite)
        .where(
            Invite.id == invite_id,
            Invite.invitee_user_id == user.id,
            Invite.status == "pending",
            Invite.version == version,
        )
        .values(status="accepted", responded_at=func.now(), version=Invite.version + 1)
        .returning(Invite.store_id)
    ).first()
    if updated is None:
        _resolve_one_shot_failure(db, invite_id, user)
    store_id = int(updated)
    db.add(
        Membership(user_id=user.id, store_id=store_id, role="store_manager", version=1)
    )
    try:
        db.commit()
    except IntegrityError:
        # UNIQUE(user_id, store_id) 兜底 → ROLLBACK，409 already_member（B-specs §1.5）
        db.rollback()
        raise Conflict("already_member") from None
    store = db.get(Store, store_id)
    return AcceptInviteOut(store={"id": store.id, "name": store.name})


def reject_invite(db: Session, user: User, invite_id: int, version: int) -> None:
    """拒绝：不建 membership（不实现取消流 [Open O-08]）。"""
    updated = db.scalars(
        update(Invite)
        .where(
            Invite.id == invite_id,
            Invite.invitee_user_id == user.id,
            Invite.status == "pending",
            Invite.version == version,
        )
        .values(status="rejected", responded_at=func.now(), version=Invite.version + 1)
        .returning(Invite.id)
    ).first()
    if updated is None:
        _resolve_one_shot_failure(db, invite_id, user)
    db.commit()


def list_pending_for_user(db: Session, user: User) -> PendingListOut:
    """当前用户为受邀方 / 被转让方且 pending 的列表（GET /invites）。"""
    invite_rows = (
        db.query(Invite, Store, User)
        .join(Store, Store.id == Invite.store_id)
        .join(User, User.id == Invite.inviter_user_id)
        .filter(Invite.invitee_user_id == user.id, Invite.status == "pending")
        .order_by(Invite.created_at.desc(), Invite.id.desc())
        .all()
    )
    transfer_rows = (
        db.query(Transfer, Store, User)
        .join(Store, Store.id == Transfer.store_id)
        .join(User, User.id == Transfer.from_user_id)
        .filter(Transfer.to_user_id == user.id, Transfer.status == "pending")
        .order_by(Transfer.created_at.desc(), Transfer.id.desc())
        .all()
    )
    return PendingListOut(
        invites=[
            PendingInviteItem(
                id=invite.id,
                store={"id": store.id, "name": store.name},
                inviter_phone=inviter.phone,
                created_at=invite.created_at,
            )
            for invite, store, inviter in invite_rows
        ],
        transfers=[
            PendingTransferItem(
                id=transfer.id,
                store={"id": store.id, "name": store.name},
                from_phone=sender.phone,
                created_at=transfer.created_at,
            )
            for transfer, store, sender in transfer_rows
        ],
    )
