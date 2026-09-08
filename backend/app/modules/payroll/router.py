from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_role, require_store_membership
from app.core.errors import BusinessError
from app.enums import Role
from app.modules.payroll.schemas import PayrollOut, PayrollSettleIn, SettleOut
from app.modules.payroll.service import get_payroll, settle_payroll

router = APIRouter()

# Locked（AC-REC-03 / 架构 §7）：客户端提交的任何金额字段 → 422 client_amount_forbidden
_FORBIDDEN_FIELDS = {"amount", "lines", "hours", "total_amount"}


async def settle_payload(request: Request) -> PayrollSettleIn:
    body = await request.json()
    if not isinstance(body, dict):
        raise BusinessError("client_amount_forbidden")
    if _FORBIDDEN_FIELDS & set(body.keys()):
        raise BusinessError("client_amount_forbidden")
    return PayrollSettleIn.model_validate(body)


@router.get("/payroll", response_model=PayrollOut)
def get_payroll_route(
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    ctx: StoreContext = Depends(require_store_membership),   # 两角色可查
    db: Session = Depends(get_db),
) -> PayrollOut:
    if month is None:
        month = date.today().strftime("%Y-%m")
    return get_payroll(db, ctx, month)


@router.post("/payroll/settle", status_code=201, response_model=SettleOut)
def settle_route(
    payload: PayrollSettleIn = Depends(settle_payload),
    ctx: StoreContext = Depends(require_role(Role.manager)),   # Deny：payroll.settle（AC-PAY-03）
    db: Session = Depends(get_db),
) -> SettleOut:
    return settle_payroll(db, ctx, payload)
