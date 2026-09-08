from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_role
from app.enums import Role
from app.modules.dividend.schemas import DividendConfirmIn, DividendConfirmOut
from app.modules.dividend.service import confirm_dividend

router = APIRouter()


@router.post("/dividends/confirm", status_code=201, response_model=DividendConfirmOut)
def confirm_dividend_route(
    payload: DividendConfirmIn,
    ctx: StoreContext = Depends(require_role(Role.manager)),   # Deny：dividend.confirm（AC-DIV-03）
    db: Session = Depends(get_db),
) -> DividendConfirmOut:
    return confirm_dividend(db, ctx, payload)
