from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.enums import ClaimStatus, Direction
from app.modules.claims.models import ExpenseClaim
from app.modules.ledger.models import LedgerEntry
from app.modules.overview.schemas import OverviewOut, PendingClaimsOut, StoreBriefOut
from app.modules.stores.models import PublicAccount


def _month_bounds(month: str):
    year, mon = (int(p) for p in month.split("-"))
    start = date(year, mon, 1)
    if mon == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, mon + 1, 1)
    return start, end


def get_overview(db: Session, ctx: StoreContext, month: str) -> OverviewOut:
    """概览（B-specs §5.1，Locked）：仅 ctx.store_id；无任何跨店聚合。"""
    start, end = _month_bounds(month)
    sums = dict(
        db.query(LedgerEntry.direction, func.coalesce(func.sum(LedgerEntry.amount), Decimal("0.00")))
        .filter(
            LedgerEntry.store_id == ctx.store.id,
            LedgerEntry.entry_date >= start,
            LedgerEntry.entry_date < end,
        )
        .group_by(LedgerEntry.direction)
        .all()
    )
    pending_count, pending_amount = (
        db.query(func.count(ExpenseClaim.id), func.coalesce(func.sum(ExpenseClaim.amount), Decimal("0")))
        .filter(
            ExpenseClaim.store_id == ctx.store.id,
            ExpenseClaim.status == ClaimStatus.pending.value,
        )
        .one()
    )
    acct = db.query(PublicAccount).filter_by(store_id=ctx.store.id).one()
    return OverviewOut(
        store=StoreBriefOut(id=ctx.store.id, name=ctx.store.name),
        month=month,
        income=sums.get(Direction.income.value, Decimal("0.00")),
        expense=sums.get(Direction.expense.value, Decimal("0.00")),
        public_balance=acct.balance,
        pending_claims=PendingClaimsOut(
            count=int(pending_count or 0), amount=pending_amount
        ),
    )
