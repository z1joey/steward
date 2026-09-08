import re
from datetime import date, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import BusinessError, NotFound, VersionConflict
from app.enums import EmployeeStatus
from app.modules.employees.models import Employee
from app.modules.employees.service import _display_status
from app.modules.shifts.models import ShiftSegment
from app.modules.shifts.schemas import (
    ShiftCreateIn,
    ShiftDeleteIn,
    ShiftEmployeeOut,
    ShiftListOut,
    ShiftOut,
    ShiftUpdateIn,
)

_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")


def _parse_week(week: str) -> tuple[datetime, datetime]:
    """'YYYY-Www' → [周一 00:00, 下周一 00:00)（服务端单一时区 [O-21]）。"""
    m = _WEEK_RE.match(week)
    if not m:
        raise BusinessError("invalid_week")
    monday = date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
    start = datetime(monday.year, monday.month, monday.day).astimezone()
    return start, start + timedelta(days=7)


def _range_from_params(
    week: str | None, from_str: str | None, to_str: str | None
) -> tuple[datetime, datetime]:
    if week is not None:
        return _parse_week(week)
    if from_str is not None and to_str is not None:
        try:
            start = date.fromisoformat(from_str)
            end = date.fromisoformat(to_str)
        except ValueError:
            raise BusinessError("invalid_range") from None
        if end < start:
            raise BusinessError("invalid_range")
        s = datetime(start.year, start.month, start.day).astimezone()
        e = datetime(end.year, end.month, end.day).astimezone() + timedelta(days=1)
        return s, e
    # 缺省当前周
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    start = datetime(monday.year, monday.month, monday.day).astimezone()
    return start, start + timedelta(days=7)


def _truncate_minute(dt: datetime) -> datetime:
    """分钟精度：秒与微秒截 0。"""
    return dt.replace(second=0, microsecond=0)


def _minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _shift_out(s: ShiftSegment) -> ShiftOut:
    return ShiftOut(
        id=s.id,
        employee_id=s.employee_id,
        start_at=s.start_at,
        end_at=s.end_at,
        minutes=_minutes(s.start_at, s.end_at),
        version=s.version,
    )


def _get_employee_or_404(db: Session, ctx: StoreContext, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None or employee.store_id != ctx.store.id:
        raise NotFound()   # 员工跨店 404
    return employee


def _ensure_no_overlap(
    db: Session, employee_id: int, start: datetime, end: datetime, exclude_id: int | None = None
) -> None:
    q = db.query(ShiftSegment).filter(
        ShiftSegment.employee_id == employee_id,
        ShiftSegment.start_at < end,
        ShiftSegment.end_at > start,
    )
    if exclude_id is not None:
        q = q.filter(ShiftSegment.id != exclude_id)
    if db.query(q.exists()).scalar():
        raise BusinessError("overlap")   # 同人重叠拒绝 [C · O-24]


def list_segments(
    db: Session,
    ctx: StoreContext,
    week: str | None,
    from_str: str | None,
    to_str: str | None,
) -> ShiftListOut:
    """周视图数据（Locked 可见性）：employees = active ∪ 本周有段的 resigned。"""
    range_start, range_end = _range_from_params(week, from_str, to_str)
    segments = (
        db.query(ShiftSegment)
        .filter(
            ShiftSegment.store_id == ctx.store.id,
            ShiftSegment.start_at >= range_start,
            ShiftSegment.start_at < range_end,
        )
        .order_by(ShiftSegment.employee_id, ShiftSegment.start_at)
        .all()
    )
    employees = (
        db.query(Employee)
        .filter(Employee.store_id == ctx.store.id)
        .order_by(Employee.id)
        .all()
    )
    with_segment_ids = {s.employee_id for s in segments}
    visible = [
        e
        for e in employees
        if e.status == EmployeeStatus.active.value or e.id in with_segment_ids
    ]
    return ShiftListOut(
        items=[_shift_out(s) for s in segments],
        employees=[
            ShiftEmployeeOut(
                id=e.id,
                name=e.name,
                status=e.status,
                display_status=_display_status(db, e),
                job_type=e.job_type,
                version=e.version,
            )
            for e in visible
        ],
    )


def create_segment(db: Session, ctx: StoreContext, payload: ShiftCreateIn) -> ShiftOut:
    employee = _get_employee_or_404(db, ctx, payload.employee_id)
    start = _truncate_minute(payload.start_at)
    end = _truncate_minute(payload.end_at)
    if end <= start:
        raise BusinessError("end_before_start")
    _ensure_no_overlap(db, employee.id, start, end)
    segment = ShiftSegment(
        store_id=ctx.store.id,
        employee_id=employee.id,
        start_at=start,
        end_at=end,
        version=1,
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return _shift_out(segment)


def _get_segment_or_404(db: Session, ctx: StoreContext, segment_id: int) -> ShiftSegment:
    segment = db.get(ShiftSegment, segment_id)
    if segment is None or segment.store_id != ctx.store.id:
        raise NotFound()   # segment 跨店 404
    return segment


def update_segment(
    db: Session, ctx: StoreContext, segment_id: int, payload: ShiftUpdateIn
) -> ShiftOut:
    segment = _get_segment_or_404(db, ctx, segment_id)
    start = _truncate_minute(payload.start_at)
    end = _truncate_minute(payload.end_at)
    if end <= start:
        raise BusinessError("end_before_start")
    _ensure_no_overlap(db, segment.employee_id, start, end, exclude_id=segment.id)
    updated = db.execute(
        update(ShiftSegment)
        .where(
            ShiftSegment.id == segment_id,
            ShiftSegment.store_id == ctx.store.id,
            ShiftSegment.version == payload.version,
        )
        .values(start_at=start, end_at=end, version=ShiftSegment.version + 1)
    )
    if updated.rowcount != 1:
        raise VersionConflict()
    db.commit()
    db.refresh(segment)
    return _shift_out(segment)


def delete_segment(
    db: Session, ctx: StoreContext, segment_id: int, payload: ShiftDeleteIn
) -> None:
    _get_segment_or_404(db, ctx, segment_id)
    updated = db.execute(
        update(ShiftSegment)
        .where(
            ShiftSegment.id == segment_id,
            ShiftSegment.store_id == ctx.store.id,
            ShiftSegment.version == payload.version,
        )
        .values(version=ShiftSegment.version + 1)
    )
    if updated.rowcount != 1:
        raise VersionConflict()
    db.query(ShiftSegment).filter(ShiftSegment.id == segment_id).delete()
    db.commit()
