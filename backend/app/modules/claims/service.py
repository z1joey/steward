from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import AlreadyProcessed, NotFound, VersionConflict
from app.enums import ClaimStatus, Direction, SourceType, TxnDirection
from app.modules.claims.models import ExpenseClaim
from app.modules.claims.schemas import (
    ApproveClaimOut,
    ClaimListOut,
    PublicTxnBrief,
    RejectClaimOut,
)
from app.modules.ledger.models import LedgerEntry
from app.modules.ledger.service import claim_view, entry_view
from app.posting.service import EntryDraft, PublicTxnDraft, post


def _resolve_one_shot_failure(db: Session, claim_id: int, store_id: int) -> None:
    """rowcount=0 判定（B-specs §2.6）：跨店/不存在 404 · 非 pending 409 · 版本 409。"""
    claim = db.get(ExpenseClaim, claim_id)
    if claim is None or claim.store_id != store_id:
        raise NotFound()
    if claim.status != ClaimStatus.pending.value:
        raise AlreadyProcessed()
    raise VersionConflict()


def approve_claim(
    db: Session, ctx: StoreContext, claim_id: int, version: int
) -> ApproveClaimOut:
    """报销（Locked，AC-LED-04）：one-shot → post(claim, out) → 回填 ledger_entry_id。

    同一事务：entry + txn + 扣余额 + claim→posted；任何一步失败整体 ROLLBACK。
    """
    updated = db.execute(
        update(ExpenseClaim)
        .where(
            ExpenseClaim.id == claim_id,
            ExpenseClaim.store_id == ctx.store.id,
            ExpenseClaim.status == ClaimStatus.pending.value,
            ExpenseClaim.version == version,
        )
        .values(
            status=ClaimStatus.posted.value,
            decided_by=ctx.user.id,
            decided_at=func.now(),
            version=ExpenseClaim.version + 1,
        )
    )
    if updated.rowcount != 1:
        _resolve_one_shot_failure(db, claim_id, ctx.store.id)

    claim = db.get(ExpenseClaim, claim_id)
    result = post(
        db,
        ctx,
        EntryDraft(
            entry_date=claim.entry_date,
            amount=claim.amount,
            direction=Direction.expense,
            memo=claim.memo,
            source_type=SourceType.claim,
            source_id=claim.id,
        ),
        PublicTxnDraft(direction=TxnDirection.out, require_sufficient_balance=False),
    )
    claim.ledger_entry_id = result.entry_id
    db.commit()

    entry = db.get(LedgerEntry, result.entry_id)
    return ApproveClaimOut(
        claim=claim_view(db, claim),
        entry=entry_view(db, entry),
        public_txn=PublicTxnBrief(id=result.txn_id, balance_after=result.new_balance),
    )


def reject_claim(
    db: Session, ctx: StoreContext, claim_id: int, version: int
) -> RejectClaimOut:
    """驳回（Locked，AC-LED-05）：不 post、不入账、不扣公账。"""
    updated = db.execute(
        update(ExpenseClaim)
        .where(
            ExpenseClaim.id == claim_id,
            ExpenseClaim.store_id == ctx.store.id,
            ExpenseClaim.status == ClaimStatus.pending.value,
            ExpenseClaim.version == version,
        )
        .values(
            status=ClaimStatus.rejected.value,
            decided_by=ctx.user.id,
            decided_at=func.now(),
            version=ExpenseClaim.version + 1,
        )
    )
    if updated.rowcount != 1:
        _resolve_one_shot_failure(db, claim_id, ctx.store.id)
    db.commit()
    claim = db.get(ExpenseClaim, claim_id)
    return RejectClaimOut(claim=claim_view(db, claim))


def list_claims(
    db: Session, ctx: StoreContext, status: str | None = None
) -> ClaimListOut:
    """GET /claims?status=（流水页待审行数据源 [C]，亦可走合并的 /ledger/entries）。"""
    q = db.query(ExpenseClaim).filter(ExpenseClaim.store_id == ctx.store.id)
    if status is not None:
        q = q.filter(ExpenseClaim.status == status)
    claims = q.order_by(ExpenseClaim.entry_date.desc(), ExpenseClaim.id.desc()).all()
    return ClaimListOut(items=[claim_view(db, c) for c in claims])
