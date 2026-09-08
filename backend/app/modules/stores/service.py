from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.memberships.models import Membership
from app.modules.stores.models import Ledger, PublicAccount, Store
from app.modules.stores.schemas import StoreOut


def create_store(db: Session, user: User, name: str) -> Store:
    """建店事务（Locked，database.md §3-2）：

    stores + membership(管理者) + ledgers + public_accounts(balance=0) 同一事务。
    """
    store = Store(name=name.strip(), created_by=user.id, version=1)
    db.add(store)
    db.flush()
    db.add(Membership(user_id=user.id, store_id=store.id, role="manager", version=1))
    db.add(Ledger(store_id=store.id))
    db.add(PublicAccount(store_id=store.id, balance=Decimal("0"), version=1))
    db.commit()
    db.refresh(store)
    return store


def list_stores_for_user(db: Session, user: User) -> list[StoreOut]:
    """我的门店：仅已接受 membership（AC-AUTH-05）。

    Phase A 中 membership 行即已接受（pending 状态只存在于 invites）。
    """
    rows = (
        db.query(Store, Membership.role)
        .join(Membership, Membership.store_id == Store.id)
        .filter(Membership.user_id == user.id)
        .order_by(Store.id)
        .all()
    )
    return [
        StoreOut(id=store.id, name=store.name, role=role, version=store.version)
        for store, role in rows
    ]
