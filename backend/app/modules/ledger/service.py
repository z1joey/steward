from datetime import date

from sqlalchemy import exists, update
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import BusinessError, Conflict, NotFound, VersionConflict
from app.enums import ClaimStatus, Direction, SourceType, TxnDirection
from app.modules.claims.models import ExpenseClaim
from app.modules.auth.models import User
from app.modules.ledger.models import LedgerEntry
from app.modules.ledger.schemas import (
    ClaimView,
    EntryCreateIn,
    EntryCreateOut,
    EntryView,
    LedgerListOut,
    LedgerRowOut,
    RequestedByOut,
    ReversalPublicTxnOut,
    ReverseEntryIn,
    ReverseEntryOut,
)
from app.modules.public_account.models import PublicAccountTxn
from app.posting.service import EntryDraft, PublicTxnDraft, post


def entry_view(db: Session, entry: LedgerEntry) -> EntryView:
    claim_status: str | None = None
    if entry.source_type == SourceType.claim.value and entry.source_id is not None:
        claim = db.get(ExpenseClaim, entry.source_id)
        if claim is not None:
            claim_status = claim.status
    return EntryView(
        id=entry.id,
        date=entry.entry_date,
        amount=entry.amount,
        direction=entry.direction,
        memo=entry.memo,
        source_type=entry.source_type,
        source_id=entry.source_id,
        is_reversal=entry.reverses_entry_id is not None,
        reversed_by_id=entry.reversed_by_id,
        claim_status=claim_status,
        version=entry.version,
        created_at=entry.created_at,
    )


def claim_view(db: Session, claim: ExpenseClaim) -> ClaimView:
    requester = db.get(User, claim.requested_by)
    return ClaimView(
        id=claim.id,
        date=claim.entry_date,
        amount=claim.amount,
        memo=claim.memo,
        status=claim.status,
        requested_by=RequestedByOut(id=requester.id, phone=requester.phone),
        decided_at=claim.decided_at,
        ledger_entry_id=claim.ledger_entry_id,
        version=claim.version,
    )


def create_entry(db: Session, ctx: StoreContext, payload: EntryCreateIn) -> EntryCreateOut:
    """记一笔（B-specs §2.6）：

    勾报销 → INSERT expense_claims(pending)，不触公账（Locked，AC-LED-03）；
    不勾 → post(manual, public_txn=None)（公账关系 [Open O-05]，测试勿假设）。
    """
    if payload.needs_reimbursement:
        claim = ExpenseClaim(
            store_id=ctx.store.id,
            entry_date=payload.date,
            amount=payload.amount,
            memo=payload.memo,
            status=ClaimStatus.pending.value,
            requested_by=ctx.user.id,
            version=1,
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)
        return EntryCreateOut(kind="claim", claim=claim_view(db, claim))

    result = post(
        db,
        ctx,
        EntryDraft(
            entry_date=payload.date,
            amount=payload.amount,
            direction=Direction(payload.direction),
            memo=payload.memo,
            source_type=SourceType.manual,
            source_id=None,
        ),
        public_txn=None,
    )
    db.commit()
    entry = db.get(LedgerEntry, result.entry_id)
    return EntryCreateOut(kind="entry", entry=entry_view(db, entry))


def _month_range(month: str) -> tuple[date, date]:
    year, mon = (int(p) for p in month.split("-"))
    start = date(year, mon, 1)
    if mon == 12:
        next_start = date(year + 1, 1, 1)
    else:
        next_start = date(year, mon + 1, 1)
    return start, next_start


def list_entries(
    db: Session,
    ctx: StoreContext,
    filter: str = "all",
    month: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> LedgerListOut:
    """流水列表 [C]：filter=all/claim 合并 pending claims 待审行置顶；rejected 不出现（O-04）。

    分页 [Open O-15]：pending 行量少不参与分页；entries 按 limit/offset 截取，
    total = entries + pending 合计。
    """
    q = db.query(LedgerEntry).filter(LedgerEntry.store_id == ctx.store.id)
    pending_q = db.query(ExpenseClaim).filter(
        ExpenseClaim.store_id == ctx.store.id,
        ExpenseClaim.status == ClaimStatus.pending.value,
    )
    if filter == SourceType.claim.value:
        q = q.filter(LedgerEntry.source_type == SourceType.claim.value)
    elif filter != "all":
        q = q.filter(LedgerEntry.source_type == filter)

    if month is not None:
        start, end = _month_range(month)
        q = q.filter(LedgerEntry.entry_date >= start, LedgerEntry.entry_date < end)
        pending_q = pending_q.filter(
            ExpenseClaim.entry_date >= start, ExpenseClaim.entry_date < end
        )

    total_entries = q.count()
    total_pending = 0
    rows: list[LedgerRowOut] = []
    if filter in ("all", SourceType.claim.value):
        pending = pending_q.order_by(ExpenseClaim.entry_date.desc(), ExpenseClaim.id.desc()).all()
        total_pending = len(pending)
        rows = [
            LedgerRowOut(
                row_type="claim_pending",
                id=c.id,
                date=c.entry_date,
                amount=c.amount,
                memo=c.memo,
                version=c.version,
                requested_by=RequestedByOut(
                    id=(db.get(User, c.requested_by)).id,
                    phone=(db.get(User, c.requested_by)).phone,
                ),
            )
            for c in pending
        ]

    entry_offset = max(0, offset - total_pending)
    entry_limit = max(0, limit - len(rows)) if offset < total_pending else limit
    entries = (
        q.order_by(LedgerEntry.entry_date.desc(), LedgerEntry.id.desc())
        .offset(entry_offset)
        .limit(entry_limit)
        .all()
    )
    rows.extend(
        LedgerRowOut(
            row_type="entry",
            id=e.id,
            date=e.entry_date,
            amount=e.amount,
            direction=e.direction,
            memo=e.memo,
            source_type=e.source_type,
            source_id=e.source_id,
            is_reversal=e.reverses_entry_id is not None,
            reversed_by_id=e.reversed_by_id,
            claim_status=(
                db.get(ExpenseClaim, e.source_id).status
                if e.source_type == SourceType.claim.value
                and e.source_id is not None
                and db.get(ExpenseClaim, e.source_id) is not None
                else None
            ),
            version=e.version,
            created_at=e.created_at,
        )
        for e in entries
    )
    return LedgerListOut(items=rows, total=total_entries + total_pending)


def _opposite(direction: str) -> Direction:
    return Direction.income if direction == Direction.expense.value else Direction.expense


def _txn_opposite(entry_direction: str) -> TxnDirection:
    # 原分录 expense→配对 out；反向 income→配对 in（反之亦然）
    return TxnDirection.inn if entry_direction == Direction.expense.value else TxnDirection.out


def reverse_entry(
    db: Session, ctx: StoreContext, entry_id: int, payload: ReverseEntryIn
) -> ReverseEntryOut:
    """冲正（B-specs §2.6，AC-LED-08）：

    FOR UPDATE 原行 → one-shot 占位（不改金额/内容）→ post(反向, 配对 txn if 原有)
    → 回填 reversed_by_id；被冲正行拒冲正（422）[C]；manager only。
    """
    orig = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.id == entry_id, LedgerEntry.store_id == ctx.store.id)
        .with_for_update()
        .one_or_none()
    )
    if orig is None:
        raise NotFound()          # 不存在 / 跨店 404
    if orig.reverses_entry_id is not None:
        raise BusinessError("cannot_reverse_reversal")   # 反向行不可再冲正 [C]

    placeholder = db.execute(
        update(LedgerEntry)
        .where(
            LedgerEntry.id == orig.id,
            LedgerEntry.reversed_by_id.is_(None),   # one-shot 占位
            LedgerEntry.version == payload.version,
        )
        .values(version=LedgerEntry.version + 1)
    )
    if placeholder.rowcount != 1:
        if orig.reversed_by_id is not None:
            raise Conflict("already_reversed")
        raise VersionConflict()

    had_txn = db.query(
        exists().where(
            PublicAccountTxn.ledger_entry_id == orig.id,
            PublicAccountTxn.store_id == ctx.store.id,
        )
    ).scalar()

    memo = f"冲正：{orig.memo}"
    if payload.reason:
        memo = f"{memo}（{payload.reason}）"
    memo = memo[:500]

    result = post(
        db,
        ctx,
        EntryDraft(
            entry_date=date.today(),   # [C]
            amount=orig.amount,
            direction=_opposite(orig.direction),
            memo=memo,
            source_type=SourceType(orig.source_type),   # 继承原 source_type [C]
            source_id=orig.source_id,
            reverses_entry_id=orig.id,
        ),
        PublicTxnDraft(
            direction=_txn_opposite(orig.direction),
            require_sufficient_balance=False,
        )
        if had_txn
        else None,   # 配对公账（Locked：原有公账流水才配对反向）
    )
    orig.reversed_by_id = result.entry_id
    db.commit()

    reversal = db.get(LedgerEntry, result.entry_id)
    txn_out = (
        ReversalPublicTxnOut(id=result.txn_id, balance_after=result.new_balance)
        if result.txn_id is not None
        else None
    )
    return ReverseEntryOut(
        entry=entry_view(db, reversal),
        original=entry_view(db, db.get(LedgerEntry, orig.id)),
        public_txn=txn_out,
    )
