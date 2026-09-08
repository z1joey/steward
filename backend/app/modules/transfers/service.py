from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import (
    AlreadyProcessed,
    BusinessError,
    Conflict,
    Forbidden,
    NotFound,
    SeatConflict,
    VersionConflict,
)
from app.modules.auth.models import User
from app.modules.memberships.models import Membership
from app.modules.stores.models import Store
from app.modules.transfers.models import Transfer
from app.modules.transfers.schemas import AcceptTransferOut, TransferOut


def create_transfer(db: Session, ctx: StoreContext, phone: str) -> TransferOut:
    """发起转让管理者（仅管理者；本店同时只允许一笔待接受）。"""
    phone = phone.strip()
    target = db.query(User).filter(User.phone == phone).one_or_none()
    if target is None:
        raise NotFound("phone_not_registered")   # 必须已注册 [C]
    if target.id == ctx.user.id:
        raise BusinessError("self_transfer")      # 422 [C]
    pending = (
        db.query(Transfer)
        .filter(Transfer.store_id == ctx.store.id, Transfer.status == "pending")
        .one_or_none()
    )
    if pending is not None:
        raise Conflict("pending_exists")          # ux_transfers_one_pending_per_store [C]
    transfer = Transfer(
        store_id=ctx.store.id,
        from_user_id=ctx.user.id,
        to_user_id=target.id,
        status="pending",
        version=1,
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return TransferOut(id=transfer.id, to={"id": target.id, "phone": target.phone}, status=transfer.status)


def _resolve_one_shot_failure(db: Session, transfer_id: int, user: User) -> None:
    """rowcount=0 判定：不存在/非被转让方 403 · 已处理 409 · 版本 409。"""
    transfer = db.get(Transfer, transfer_id)
    if transfer is None or transfer.to_user_id != user.id:
        raise Forbidden("not_transfer_target")
    if transfer.status != "pending":
        raise AlreadyProcessed()
    raise VersionConflict()


def accept_transfer(db: Session, user: User, transfer_id: int, version: int) -> AcceptTransferOut:
    """接受转让（Locked 事务，B-specs §1.5）：

    one-shot 标记 accepted → FOR UPDATE 锁管理者行 → 过期校验 → 先降后升；
    目标已是本店店长则升格其行；其余店长不动；恰 1 管理者由 partial unique 兜底。
    """
    updated = db.scalars(
        update(Transfer)
        .where(
            Transfer.id == transfer_id,
            Transfer.to_user_id == user.id,
            Transfer.status == "pending",
            Transfer.version == version,
        )
        .values(status="accepted", responded_at=func.now(), version=Transfer.version + 1)
        .returning(Transfer.store_id)
    ).first()
    if updated is None:
        _resolve_one_shot_failure(db, transfer_id, user)
    store_id = int(updated)

    mgr = (
        db.query(Membership)
        .filter(Membership.store_id == store_id, Membership.role == "manager")
        .with_for_update()
        .one_or_none()
    )
    if mgr is None or mgr.user_id != _from_user_id(db, transfer_id):
        db.rollback()
        raise SeatConflict()   # 转让过期：发起人已非管理者（Locked → 409 seat_conflict）

    # 先降：原管理者 → 店长
    mgr.role = "store_manager"
    mgr.version += 1

    target_membership = (
        db.query(Membership)
        .filter(Membership.store_id == store_id, Membership.user_id == user.id)
        .one_or_none()
    )
    if target_membership is not None:
        # 目标已是本店店长：升格其行（店长总数不变，AC-TR-01 变体）
        target_membership.role = "manager"
        target_membership.version += 1
    else:
        # 目标为店外用户：新建 manager 行（店长总数 +1；无店长席位校验）
        db.add(Membership(user_id=user.id, store_id=store_id, role="manager", version=1))

    try:
        db.commit()
    except IntegrityError:
        # ux_memberships_one_manager 兜底 → 409 seat_conflict（B-specs §1.5）
        db.rollback()
        raise SeatConflict() from None

    store = db.get(Store, store_id)
    return AcceptTransferOut(store={"id": store.id, "name": store.name})


def _from_user_id(db: Session, transfer_id: int) -> int:
    transfer = db.get(Transfer, transfer_id)
    if transfer is None:
        raise NotFound()
    return transfer.from_user_id
