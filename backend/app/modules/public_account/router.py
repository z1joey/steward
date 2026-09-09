"""公账路由：余额调整（管理者，Deny 清单语义——店长 403）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_role
from app.enums import Role
from app.modules.public_account.schemas import BalanceAdjustIn, BalanceAdjustOut
from app.modules.public_account.service import adjust_balance

router = APIRouter()


@router.post("/public-account/adjust", response_model=BalanceAdjustOut, status_code=201)
def adjust_balance_route(
    payload: BalanceAdjustIn,
    ctx: StoreContext = Depends(require_role(Role.manager)),
    db: Session = Depends(get_db),
) -> BalanceAdjustOut:
    return adjust_balance(db, ctx, payload)
