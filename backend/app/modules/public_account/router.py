"""公账路由：余额调整（管理者）+ 调整记录公示（两角色）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_role, require_store_membership
from app.enums import Role
from app.modules.public_account.schemas import (
    AdjustmentListOut,
    BalanceAdjustIn,
    BalanceAdjustOut,
)
from app.modules.public_account.service import adjust_balance, list_adjustments

router = APIRouter()


@router.post("/public-account/adjust", response_model=BalanceAdjustOut, status_code=201)
def adjust_balance_route(
    payload: BalanceAdjustIn,
    ctx: StoreContext = Depends(require_role(Role.manager)),
    db: Session = Depends(get_db),
) -> BalanceAdjustOut:
    return adjust_balance(db, ctx, payload)


@router.get("/public-account/adjustments", response_model=AdjustmentListOut)
def list_adjustments_route(
    limit: Annotated[int, Query(ge=1, le=100)] = 3,
    offset: Annotated[int, Query(ge=0)] = 0,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> AdjustmentListOut:
    return list_adjustments(db, ctx, limit=limit, offset=offset)
