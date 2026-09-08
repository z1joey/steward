from dataclasses import dataclass

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.enums import Role
from app.modules.auth.models import User
from app.modules.memberships.models import Membership
from app.modules.stores.models import Store

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise Unauthorized()
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None:
        raise Unauthorized()
    return user


@dataclass
class StoreContext:
    """当前请求的店上下文：已接受 membership 校验后的聚合。"""

    user: User
    store: Store
    membership: Membership
    role: Role


def require_store_membership(
    x_store_id: str | None = Header(default=None, alias="X-Store-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StoreContext:
    """X-Store-Id → 已接受 membership → StoreContext（AC-ISO-01）。

    缺头 / 非整数 / 无 membership → 403（B-specs §0.4）。
    """
    if x_store_id is None:
        raise Forbidden("no_membership")
    try:
        store_id = int(x_store_id)
    except ValueError:
        raise Forbidden("no_membership") from None
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.store_id == store_id)
        .one_or_none()
    )
    if membership is None:
        raise Forbidden("no_membership")
    store = db.get(Store, store_id)
    if store is None:
        raise Forbidden("no_membership")
    return StoreContext(
        user=user, store=store, membership=membership, role=Role(membership.role)
    )


def require_role(role: Role):
    """角色守卫：ctx.role 不符 → 403 {"detail":"forbidden_role"}（api.md §5 Deny 清单）。"""

    def dependency(
        ctx: StoreContext = Depends(require_store_membership),
    ) -> StoreContext:
        if ctx.role != role:
            raise Forbidden("forbidden_role")
        return ctx

    return dependency
