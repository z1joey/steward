from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.enums import Direction
from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import PublicAccount
from app.modules.stats.profit_rate import compute
from app.modules.stats.schemas import PublicOut, RecentTxnOut, StatsOut


def month_stats(db: Session, ctx: StoreContext, month: str) -> StatsOut:
    """统计页（B-specs §3.2 / [Open O-01/O-23]）：

    income / expense = SUM(amount) by direction（含冲正反向分录，自然抵消）；
    profit_rate 拍板前为 null。
    """
    year, mon = (int(p) for p in month.split("-"))
    start = date(year, mon, 1)
    if mon == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, mon + 1, 1)

    sums = dict(
        db.query(LedgerEntry.direction, func.coalesce(func.sum(LedgerEntry.amount), Decimal("0")))
        .filter(
            LedgerEntry.store_id == ctx.store.id,
            LedgerEntry.entry_date >= start,
            LedgerEntry.entry_date < end,
        )
        .group_by(LedgerEntry.direction)
        .all()
    )
    income = sums.get(Direction.income.value, Decimal("0"))
    expense = sums.get(Direction.expense.value, Decimal("0"))

    acct = (
        db.query(PublicAccount).filter_by(store_id=ctx.store.id).one()
    )
    txns = (
        db.query(PublicAccountTxn, LedgerEntry.memo)
        .join(LedgerEntry, LedgerEntry.id == PublicAccountTxn.ledger_entry_id)
        .filter(PublicAccountTxn.store_id == ctx.store.id)
        .order_by(PublicAccountTxn.created_at.desc(), PublicAccountTxn.id.desc())
        .limit(10)
        .all()
    )

    return StatsOut(
        month=month,
        income=income,
        expense=expense,
        profit_rate=compute(income, expense),
        public=PublicOut(
            balance=acct.balance,
            version=acct.version,
            recent_txns=[
                RecentTxnOut(
                    id=txn.id,
                    amount=txn.amount,
                    direction=txn.direction,
                    source_type=txn.source_type,
                    balance_after=txn.balance_after,
                    created_at=txn.created_at,
                    memo=memo,
                )
                for txn, memo in txns
            ],
        ),
    )
