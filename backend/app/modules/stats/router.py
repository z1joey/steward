import re
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_store_membership
from app.core.errors import BusinessError
from app.modules.stats.schemas import StatsOut
from app.modules.stats.service import month_stats

router = APIRouter()

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@router.get("/ledger/stats", response_model=StatsOut)
def stats_route(
    month: str = Query(default=None),   # 缺省当月（服务端时区 [C · O-21]）
    ctx: StoreContext = Depends(require_store_membership),   # 两角色（B-specs §3.4）
    db: Session = Depends(get_db),
) -> StatsOut:
    if month is None:
        month = date.today().strftime("%Y-%m")
    if not _MONTH_RE.match(month):
        raise BusinessError("period_month_invalid")
    return month_stats(db, ctx, month)
