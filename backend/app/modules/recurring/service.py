import re
from datetime import date
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import BusinessError, Conflict, NotFound, VersionConflict
from app.enums import Direction, RecurringKind, SourceType
from app.modules.recurring.models import RecurringExpense, RecurringOccurrence
from app.modules.recurring.schemas import (
    OccurrenceCreateIn,
    OccurrenceCreateOut,
    OccurrenceOut,
    RecurringCreateIn,
    RecurringListOut,
    RecurringOut,
    RecurringUpdateIn,
)
from app.posting.service import EntryDraft, post

_PERIOD_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validate_kind_amounts(
    kind: RecurringKind, is_fixed: bool, fixed_amount: Decimal | None
) -> None:
    """Locked（AC-REC-02/03）：wages 一律无金额；固定项必须带金额。"""
    if kind == RecurringKind.wages:
        if fixed_amount is not None or is_fixed:
            raise BusinessError("wages_not_hand_filled")
    elif is_fixed and fixed_amount is None:
        raise BusinessError("fixed_amount_required")


def _to_out(
    db: Session, rec: RecurringExpense, current_month: str
) -> RecurringOut:
    occurrence = (
        db.query(RecurringOccurrence)
        .filter(
            RecurringOccurrence.recurring_expense_id == rec.id,
            RecurringOccurrence.period_month == current_month,
        )
        .one_or_none()
    )
    return RecurringOut(
        id=rec.id,
        name=rec.name,
        kind=RecurringKind(rec.kind),
        period=rec.period,
        is_fixed=rec.is_fixed,
        fixed_amount=rec.fixed_amount,
        active=rec.active,
        version=rec.version,
        created_at=rec.created_at,
        current_month_occurrence=(
            OccurrenceOut(
                id=occurrence.id,
                period_month=occurrence.period_month,
                amount=occurrence.amount,
                recurring_expense_id=occurrence.recurring_expense_id,
            )
            if occurrence
            else None
        ),
    )


def create_recurring(
    db: Session, ctx: StoreContext, payload: RecurringCreateIn
) -> RecurringOut:
    if payload.period != "month":
        raise BusinessError("period_must_be_month")   # Locked：仅 month（AC-REC-01）
    _validate_kind_amounts(payload.kind, payload.is_fixed, payload.fixed_amount)
    rec = RecurringExpense(
        store_id=ctx.store.id,
        name=payload.name.strip(),
        kind=payload.kind.value,
        period="month",
        is_fixed=payload.is_fixed,
        fixed_amount=payload.fixed_amount if payload.is_fixed else None,
        active=True,
        version=1,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _to_out(db, rec, date.today().strftime("%Y-%m"))


def list_recurring(db: Session, ctx: StoreContext) -> RecurringListOut:
    rows = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.store_id == ctx.store.id)
        .order_by(RecurringExpense.id.desc())
        .all()
    )
    current_month = date.today().strftime("%Y-%m")
    return RecurringListOut(items=[_to_out(db, r, current_month) for r in rows])


def _get_or_404(db: Session, ctx: StoreContext, rec_id: int) -> RecurringExpense:
    rec = db.get(RecurringExpense, rec_id)
    if rec is None or rec.store_id != ctx.store.id:
        raise NotFound()   # 不存在 / 跨店 404
    return rec


def update_recurring(
    db: Session, ctx: StoreContext, rec_id: int, payload: RecurringUpdateIn
) -> RecurringOut:
    """PUT（乐观锁，B-specs §3.2）：version 条件更新；wages 规则同新建。"""
    rec = _get_or_404(db, ctx, rec_id)
    kind = RecurringKind(rec.kind)
    is_fixed = payload.is_fixed if payload.is_fixed is not None else rec.is_fixed
    fixed_amount = (
        payload.fixed_amount
        if payload.fixed_amount is not None
        else rec.fixed_amount
    )
    if not is_fixed:
        fixed_amount = None
    _validate_kind_amounts(kind, is_fixed, fixed_amount)

    fields: dict[str, object] = {"version": RecurringExpense.version + 1}
    if payload.name is not None:
        fields["name"] = payload.name.strip()
    if payload.is_fixed is not None:
        fields["is_fixed"] = payload.is_fixed
    if payload.fixed_amount is not None or not is_fixed:
        fields["fixed_amount"] = fixed_amount
    if payload.active is not None:
        fields["active"] = payload.active

    updated = db.execute(
        update(RecurringExpense)
        .where(
            RecurringExpense.id == rec_id,
            RecurringExpense.store_id == ctx.store.id,
            RecurringExpense.version == payload.version,
        )
        .values(**fields)
    )
    if updated.rowcount != 1:
        raise VersionConflict()
    db.commit()
    db.refresh(rec)
    return _to_out(db, rec, date.today().strftime("%Y-%m"))


def record_occurrence(
    db: Session, ctx: StoreContext, rec_id: int, payload: OccurrenceCreateIn
) -> OccurrenceCreateOut:
    """记本月 [C · O-10]（B-specs §3.5）：wages 一律 422；post(recurring, None)（O-05）。

    version 条件更新周期项行（乐观锁）+ UNIQUE(rec, month) 兜底 → 409。
    """
    rec = _get_or_404(db, ctx, rec_id)
    if rec.kind == RecurringKind.wages.value:
        raise BusinessError("wages_not_hand_filled")   # 工资只能源于结算（AC-REC-03）
    if not _PERIOD_MONTH_RE.match(payload.period_month):
        raise BusinessError("period_month_invalid")
    if rec.is_fixed:
        amount = rec.fixed_amount
    else:
        if payload.amount is None:
            raise BusinessError("amount_required")     # 浮动项必填
        amount = payload.amount

    locked = db.execute(
        update(RecurringExpense)
        .where(
            RecurringExpense.id == rec_id,
            RecurringExpense.store_id == ctx.store.id,
            RecurringExpense.version == payload.version,
        )
        .values(version=RecurringExpense.version + 1)
    )
    if locked.rowcount != 1:
        raise VersionConflict()

    result = post(
        db,
        ctx,
        EntryDraft(
            entry_date=_first_day(payload.period_month),
            amount=amount,
            direction=Direction.expense,
            memo=rec.name,
            source_type=SourceType.recurring,
            source_id=rec.id,
        ),
        public_txn=None,   # 是否动公账 [Open O-05]
    )
    occurrence = RecurringOccurrence(
        store_id=ctx.store.id,
        recurring_expense_id=rec.id,
        period_month=payload.period_month,
        amount=amount,
        ledger_entry_id=result.entry_id,
    )
    db.add(occurrence)
    try:
        db.commit()
    except IntegrityError:
        # UNIQUE(rec, month) 兜底 → 409（并发第二请求）
        db.rollback()
        raise Conflict("period_already_recorded") from None
    db.refresh(occurrence)
    return OccurrenceCreateOut(
        occurrence=OccurrenceOut(
            id=occurrence.id,
            period_month=occurrence.period_month,
            amount=occurrence.amount,
            recurring_expense_id=occurrence.recurring_expense_id,
        ),
        entry_id=result.entry_id,
    )


def _first_day(period_month: str) -> date:
    year, mon = (int(p) for p in period_month.split("-"))
    return date(year, mon, 1)
