from datetime import date

from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import VersionConflict
from app.enums import Direction, SourceType, TxnDirection
from app.modules.dividend.models import DividendRun
from app.modules.dividend.schemas import (
    DividendConfirmIn,
    DividendConfirmOut,
    DividendRunOut,
    PublicBriefOut,
)
from app.modules.ledger.models import LedgerEntry
from app.modules.ledger.service import entry_view
from app.modules.stores.models import PublicAccount
from app.posting.service import EntryDraft, PublicTxnDraft, post


def confirm_dividend(
    db: Session, ctx: StoreContext, payload: DividendConfirmIn
) -> DividendConfirmOut:
    """确认发放（B-specs §3.5，Locked AC-DIV-01/02）：

    FOR UPDATE 公账 → version 校验 → post(dividend, out, require_sufficient_balance=True)
    → 落 runs → 回填 source_id；超额 422 insufficient_balance 零副作用；manager only。
    """
    acct = (
        db.query(PublicAccount)
        .filter_by(store_id=ctx.store.id)
        .with_for_update()
        .one()
    )
    if acct.version != payload.public_account_version:
        raise VersionConflict()   # 页面余额过期先刷新 [C]

    result = post(
        db,
        ctx,
        EntryDraft(
            entry_date=date.today(),
            amount=payload.amount,
            direction=Direction.expense,
            memo=payload.memo or "分红",
            source_type=SourceType.dividend,
            source_id=None,   # runs 落库后回填
        ),
        PublicTxnDraft(direction=TxnDirection.out, require_sufficient_balance=True),
        # post 内 new_balance < 0 → InsufficientBalance → 422 零副作用（AC-DIV-02）
    )

    run = DividendRun(
        store_id=ctx.store.id,
        amount=payload.amount,
        memo=payload.memo,
        confirmed_by=ctx.user.id,
        ledger_entry_id=result.entry_id,
        public_txn_id=result.txn_id,
    )
    db.add(run)
    db.flush()
    entry = db.get(LedgerEntry, result.entry_id)
    entry.source_id = run.id   # 回填 source_id（B-specs §3.5）
    db.commit()

    return DividendConfirmOut(
        run=DividendRunOut(
            id=run.id, amount=run.amount, confirmed_at=run.confirmed_at
        ),
        entry=entry_view(db, db.get(LedgerEntry, result.entry_id)),
        public=PublicBriefOut(balance=acct.balance, version=acct.version),
    )
