import re
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_store_membership
from app.core.errors import BusinessError
from app.modules.overview.schemas import OverviewOut
from app.modules.overview.service import get_overview

router = APIRouter()

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@router.get("/overview", response_model=OverviewOut)
def overview_route(
    month: str | None = Query(default=None),
    ctx: StoreContext = Depends(require_store_membership),   # 两角色（B-specs §5.3）
    db: Session = Depends(get_db),
) -> OverviewOut:
    if month is None:
        month = date.today().strftime("%Y-%m")
    if not _MONTH_RE.match(month):
        raise BusinessError("period_month_invalid")
    return get_overview(db, ctx, month)
