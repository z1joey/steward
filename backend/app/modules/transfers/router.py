from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, get_current_user, require_role
from app.core.errors import NotFound
from app.enums import Role
from app.modules.auth.models import User
from app.modules.transfers.schemas import (
    AcceptTransferOut,
    TransferCreateIn,
    TransferOut,
    VersionIn,
)
from app.modules.transfers.service import accept_transfer, create_transfer

router = APIRouter()


@router.post("/stores/{store_id}/transfers", status_code=201, response_model=TransferOut)
def create_transfer_route(
    store_id: int,
    payload: TransferCreateIn,
    ctx: StoreContext = Depends(require_role(Role.manager)),   # Deny：transfers.create
    db: Session = Depends(get_db),
) -> TransferOut:
    if store_id != ctx.store.id:
        raise NotFound()   # 与 X-Store-Id 不一致 → 跨店 404
    return create_transfer(db, ctx, payload.phone)


@router.post("/transfers/{transfer_id}/accept", response_model=AcceptTransferOut)
def accept_transfer_route(
    transfer_id: int,
    payload: VersionIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcceptTransferOut:
    return accept_transfer(db, user, transfer_id, payload.version)
