"""Posting service — 唯一钱管道（B-specs §2.2，Locked 行为）。

允许的调用方：claims.approve · ledger.reverse · dividend.confirm · payroll.settle；
manual 直接分录调用 post(entry, public_txn=None)（是否动公账 [Open O-05]）。
recurring 同 manual（[Open O-05/O-10]）。

调用约定：调用方必须已在同一 db 事务内完成自己的 one-shot 条件更新；
本函数不开新事务、不 commit；任何异常向上抛 → 调用方整体 ROLLBACK。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import InsufficientBalance
from app.enums import Direction, SourceType, TxnDirection
from app.modules.ledger.models import LedgerEntry
from app.modules.public_account.models import PublicAccountTxn
from app.modules.stores.models import Ledger, PublicAccount


@dataclass
class EntryDraft:
    entry_date: date
    amount: Decimal
    direction: Direction
    memo: str
    source_type: SourceType
    source_id: int | None
    reverses_entry_id: int | None = None


@dataclass
class PublicTxnDraft:
    direction: TxnDirection  # 与 entry.direction 对应：expense→out，income→in
    require_sufficient_balance: bool  # 分红为 True；其他为 False


@dataclass
class PostResult:
    entry_id: int
    txn_id: int | None
    new_balance: Decimal | None


def post(
    db: Session,
    ctx: StoreContext,
    entry: EntryDraft,
    public_txn: PublicTxnDraft | None,
) -> PostResult:
    """插分录 + 可选配对公账流水并更新余额（同一事务，串行化于公账行锁）。"""
    acct = (
        db.query(PublicAccount)
        .filter(PublicAccount.store_id == ctx.store.id)
        .with_for_update()
        .one()
    )
    ledger = db.query(Ledger).filter(Ledger.store_id == ctx.store.id).one()
    entry_row = LedgerEntry(
        store_id=ctx.store.id,
        ledger_id=ledger.id,
        entry_date=entry.entry_date,
        amount=entry.amount,
        direction=entry.direction.value,
        memo=entry.memo,
        source_type=entry.source_type.value,
        source_id=entry.source_id,
        reverses_entry_id=entry.reverses_entry_id,
        created_by=ctx.user.id,
        version=1,
    )
    db.add(entry_row)
    db.flush()  # 取 entry_row.id 供流水外键

    txn_id: int | None = None
    new_balance: Decimal | None = None
    if public_txn is not None:
        amount = entry.amount
        if public_txn.direction == TxnDirection.inn:
            new_balance = acct.balance + amount
        else:
            new_balance = acct.balance - amount
        if public_txn.require_sufficient_balance and new_balance < 0:
            raise InsufficientBalance()  # → 422，调用方整体 ROLLBACK（AC-DIV-02）
        txn = PublicAccountTxn(
            store_id=ctx.store.id,
            public_account_id=acct.id,
            amount=amount,
            direction=public_txn.direction.value,
            source_type=entry.source_type.value,
            source_id=entry.source_id,
            ledger_entry_id=entry_row.id,
            balance_after=new_balance,
        )
        db.add(txn)
        db.flush()
        txn_id = txn.id
        acct.balance = new_balance
        acct.version += 1

    return PostResult(entry_id=entry_row.id, txn_id=txn_id, new_balance=new_balance)
