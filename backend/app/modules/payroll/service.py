import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import extract, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import BusinessError, Conflict
from app.enums import Direction, SourceType
from app.modules.employees.models import Employee
from app.modules.payroll.models import PayrollLine, PayrollRun
from app.modules.payroll import rate_rule
from app.modules.payroll.schemas import (
    PayrollLineView,
    PayrollOut,
    PayrollPreviewRow,
    PayrollRunView,
    PayrollSettleIn,
    SettleOut,
)
from app.modules.shifts.models import ShiftSegment
from app.posting.service import EntryDraft, post

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass
class _Preview:
    """内部聚合行：含 rate_snapshot 明细（不进 GET 响应，结算时落 payroll_lines）。"""

    employee_id: int
    name: str
    hours: Decimal
    worked_days: int
    segments_count: int
    pay_type: str | None
    amount: Decimal | None
    snapshot: dict | None


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    year, mon = (int(p) for p in month.split("-"))
    start = datetime(year, mon, 1).astimezone()
    if mon == 12:
        end = datetime(year + 1, 1, 1).astimezone()
    else:
        end = datetime(year, mon + 1, 1).astimezone()
    return start, end


def _last_day(month: str) -> date:
    _, end = _month_bounds(month)
    return (end - timedelta(days=1)).date()


def _aggregate_preview(
    db: Session, ctx: StoreContext, month: str
) -> list[_Preview]:
    """compute-on-read [C · O-16]：按 start_at 归月求工时；请假不扣减 [Open O-25]。

    [O-07] 按日算法需要自然日出勤天数 → 单条 SQL 按 (employee_id, 出勤日) 分组，
    派生 hours（Σ 段时长）与 worked_days（distinct 天数，同日多段计 1 天）。
    """
    start, end = _month_bounds(month)
    # (end_at − start_at) 求和后 / 3600 → 小时数（epoch 为秒；段时长以分钟粒度）
    day_seconds = func.sum(
        extract("epoch", ShiftSegment.end_at - ShiftSegment.start_at)
    )
    day = func.date(ShiftSegment.start_at)   # 服务端单一时区口径（O-21，与 _month_bounds 一致）
    rows = (
        db.query(
            ShiftSegment.employee_id,
            func.count(ShiftSegment.id),
            day_seconds / 3600.0,
            day,
        )
        .filter(
            ShiftSegment.store_id == ctx.store.id,
            ShiftSegment.start_at >= start,
            ShiftSegment.start_at < end,
        )
        .group_by(ShiftSegment.employee_id, day)
        .all()
    )
    if not rows:
        return []
    employees = {
        e.id: e
        for e in db.query(Employee)
        .filter(Employee.store_id == ctx.store.id)
        .all()
    }

    agg: dict[int, dict] = {}
    for employee_id, segments_count, day_hours, _worked_day in rows:
        employee = employees.get(employee_id)
        if employee is None:
            continue
        slot = agg.setdefault(
            employee_id,
            {"employee": employee, "hours": Decimal("0"), "days": 0, "segments": 0},
        )
        slot["hours"] += Decimal(str(day_hours or 0))
        slot["days"] += 1          # 每个 distinct 出勤日 +1（同日多段合并在同一分组行）
        slot["segments"] += int(segments_count)

    preview: list[_Preview] = []
    for employee_id in sorted(agg):
        slot = agg[employee_id]
        employee = slot["employee"]
        hours = slot["hours"].quantize(Decimal("0.01"))
        outcome = rate_rule.compute(
            employee, hours, month, worked_days=slot["days"]
        )   # DI：测试可 monkeypatch
        preview.append(
            _Preview(
                employee_id=employee_id,
                name=employee.name,
                hours=hours,
                worked_days=slot["days"],
                segments_count=slot["segments"],
                pay_type=employee.pay_type,
                amount=outcome.amount if outcome is not None else None,
                snapshot=outcome.snapshot if outcome is not None else None,
            )
        )
    return preview


def get_payroll(db: Session, ctx: StoreContext, month: str) -> PayrollOut:
    """GET /payroll（只读自动汇总，无「计算」端点；AC-PAY-01/04）。"""
    preview = _aggregate_preview(db, ctx, month)
    run = (
        db.query(PayrollRun)
        .filter(PayrollRun.store_id == ctx.store.id, PayrollRun.period_month == month)
        .one_or_none()
    )
    settled: PayrollRunView | None = None
    if run is not None:
        lines = (
            db.query(PayrollLine).filter(PayrollLine.run_id == run.id).order_by(PayrollLine.id)
            .all()
        )
        settled = PayrollRunView(
            id=run.id,
            period_month=run.period_month,
            total_amount=run.total_amount,
            lines=[
                PayrollLineView(
                    employee_id=l.employee_id,
                    hours=l.hours,
                    amount=l.amount,
                    ledger_entry_id=l.ledger_entry_id,
                )
                for l in lines
            ],
        )
    total_hours = sum((p.hours for p in preview), Decimal("0"))
    amounts = [p.amount for p in preview]
    total_amount = (
        sum((a for a in amounts if a is not None), Decimal("0"))
        if all(a is not None for a in amounts)
        else None
    )
    return PayrollOut(
        month=month,
        settled=settled,
        preview=[
            PayrollPreviewRow(
                employee_id=p.employee_id,
                name=p.name,
                hours=p.hours,
                worked_days=p.worked_days,
                segments_count=p.segments_count,
                pay_type=p.pay_type,
                amount=p.amount,
            )
            for p in preview
        ],
        total_hours=total_hours,
        total_amount=total_amount,
    )


def settle_payroll(
    db: Session, ctx: StoreContext, payload: PayrollSettleIn
) -> SettleOut:
    """结算（B-specs §4.5，manager only，AC-PAY-02/03/04 · AC-REC-03）：

    UNIQUE(store, month) one-shot 兜底；rate_rule 不可得 → 422 rate_rule_missing；
    无可结算行 → 422 nothing_to_settle；每行 post(payroll, None)（O-05）。
    """
    if not _MONTH_RE.match(payload.month):
        raise BusinessError("period_month_invalid")
    existing = (
        db.query(PayrollRun)
        .filter(
            PayrollRun.store_id == ctx.store.id,
            PayrollRun.period_month == payload.month,
        )
        .one_or_none()
    )
    if existing is not None:
        raise Conflict("period_already_settled")

    preview = _aggregate_preview(db, ctx, payload.month)
    if not preview or all(p.hours <= 0 for p in preview):
        raise BusinessError("nothing_to_settle")   # AC-PAY-04：无班次无应发
    rows = [p for p in preview if p.hours > 0]
    if any(p.amount is None for p in rows):
        raise BusinessError("rate_rule_missing")   # 员工未设置计薪方式/单价

    total = Decimal("0")
    run = PayrollRun(
        store_id=ctx.store.id,
        period_month=payload.month,
        settled_by=ctx.user.id,
        total_amount=Decimal("0"),
    )
    db.add(run)
    db.flush()

    entry_date = _last_day(payload.month)
    for p in rows:
        amount: Decimal = p.amount  # type: ignore[assignment]
        line = PayrollLine(
            run_id=run.id,
            store_id=ctx.store.id,
            employee_id=p.employee_id,
            hours=p.hours,
            amount=amount,
            rate_snapshot=p.snapshot or {"rate_rule": "settled"},   # [O-07] 真实算薪明细
        )
        db.add(line)
        db.flush()   # 取 line.id 作 source_id
        result = post(
            db,
            ctx,
            EntryDraft(
                entry_date=entry_date,
                amount=amount,
                direction=Direction.expense,
                memo=f"工资 {p.name} {payload.month}",
                source_type=SourceType.payroll,
                source_id=line.id,
            ),
            public_txn=None,   # 工资是否动公账 [Open O-05]
        )
        line.ledger_entry_id = result.entry_id
        total += amount

    run.total_amount = total
    try:
        db.commit()
    except IntegrityError:
        # UNIQUE(store, month) 兜底（并发第二次结算）→ 409
        db.rollback()
        raise Conflict("period_already_settled") from None
    db.refresh(run)

    lines = (
        db.query(PayrollLine).filter(PayrollLine.run_id == run.id).order_by(PayrollLine.id).all()
    )
    return SettleOut(
        run=PayrollRunView(
            id=run.id,
            period_month=run.period_month,
            total_amount=run.total_amount,
            lines=[
                PayrollLineView(
                    employee_id=l.employee_id,
                    hours=l.hours,
                    amount=l.amount,
                    ledger_entry_id=l.ledger_entry_id,
                )
                for l in lines
            ],
        )
    )
