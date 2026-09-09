"""公账余额调整（管理者；[O-22/O-05] 演进：受控的盘点纠错入口）。

Locked 约束不破例：调整仍走 posting service——生成一笔 adjustment 分录
（memo =「公账调整：<原因>」，原因必填）+ 配对公账流水，余额一次到位；
FOR UPDATE + version 乐观锁防并发（与 dividends/confirm 同模式）。
调整记录经 GET /public-account/adjustments 公示（两角色可查）。
"""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import BusinessError, VersionConflict
from app.enums import Direction, SourceType, TxnDirection
from app.modules.claims.schemas import PublicTxnBrief
from app.modules.ledger.models import LedgerEntry
from app.modules.ledger.service import entry_view
from app.modules.public_account.models import PublicAccountTxn
from app.modules.public_account.schemas import (
    AdjustmentItem,
    AdjustmentListOut,
    BalanceAdjustIn,
    BalanceAdjustOut,
)
from app.modules.stores.models import PublicAccount
from app.posting.service import EntryDraft, PublicTxnDraft, post

_MEMO_PREFIX = "公账调整："


def adjust_balance(
    db: Session, ctx: StoreContext, payload: BalanceAdjustIn
) -> BalanceAdjustOut:
    # 先锁行再校验 version（防 TOCTOU，与 confirm_dividend 同模式）
    acct = (
        db.query(PublicAccount)
        .filter_by(store_id=ctx.store.id)
        .with_for_update()
        .one()
    )
    if acct.version != payload.public_account_version:
        raise VersionConflict()

    new_balance = payload.new_balance.quantize(Decimal("0.01"))
    delta = (new_balance - acct.balance).quantize(Decimal("0.01"))
    if delta == 0:
        raise BusinessError("no_change")

    direction = Direction.income if delta > 0 else Direction.expense
    result = post(
        db,
        ctx,
        EntryDraft(
            entry_date=date.today(),
            amount=abs(delta),
            direction=direction,
            memo=f"公账调整：{payload.reason.strip()}",
            source_type=SourceType.adjustment,
            source_id=None,
        ),
        PublicTxnDraft(
            direction=TxnDirection.inn if delta > 0 else TxnDirection.out,
            require_sufficient_balance=False,   # 盘点纠错如实反映，可为负
        ),
    )
    db.commit()
    entry = db.get(LedgerEntry, result.entry_id)
    txn = db.get(PublicAccountTxn, result.txn_id)
    return BalanceAdjustOut(
        entry=entry_view(db, entry),
        public_txn=PublicTxnBrief(id=txn.id, balance_after=txn.balance_after),
        balance=result.new_balance,
    )


def list_adjustments(
    db: Session, ctx: StoreContext, limit: int = 3, offset: int = 0
) -> AdjustmentListOut:
    """调整记录公示（两角色可查）：按时间倒序，最新在前。"""
    base = (
        db.query(LedgerEntry, PublicAccountTxn)
        .join(PublicAccountTxn, PublicAccountTxn.ledger_entry_id == LedgerEntry.id)
        .filter(
            LedgerEntry.store_id == ctx.store.id,
            LedgerEntry.source_type == SourceType.adjustment.value,
        )
    )
    total = base.count()
    rows = base.order_by(LedgerEntry.id.desc()).offset(offset).limit(limit).all()
    items = []
    for entry, txn in rows:
        memo = entry.memo
        reason = memo[len(_MEMO_PREFIX):] if memo.startswith(_MEMO_PREFIX) else memo
        items.append(
            AdjustmentItem(
                id=entry.id,
                date=entry.entry_date,
                direction=Direction(entry.direction),
                amount=entry.amount,
                reason=reason,
                balance_after=txn.balance_after,
                created_at=entry.created_at,
            )
        )
    return AdjustmentListOut(items=items, total=total)
