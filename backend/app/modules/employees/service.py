from datetime import date

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.deps import StoreContext
from app.core.errors import BusinessError, Conflict, NotFound, VersionConflict
from app.enums import EmployeeStatus
from app.modules.employees.models import Employee, EmployeeLeave
from app.modules.employees.schemas import (
    EmployeeCreateIn,
    EmployeeDetailOut,
    EmployeeListOut,
    EmployeeOut,
    EmployeeUpdateIn,
    LeaveCreateIn,
    LeaveOut,
    ResignIn,
    ResignOut,
)


def _display_status(
    db: Session, employee: Employee, today: date | None = None
) -> str:
    """[C]：resigned / 当日在假 on_leave / active。"""
    if employee.status == EmployeeStatus.resigned.value:
        return "resigned"
    today = today or date.today()
    on_leave = (
        db.query(EmployeeLeave)
        .filter(
            EmployeeLeave.employee_id == employee.id,
            EmployeeLeave.start_date <= today,
            EmployeeLeave.end_date >= today,
        )
        .first()
    )
    return "on_leave" if on_leave else "active"


def employee_out(db: Session, employee: Employee) -> EmployeeOut:
    return EmployeeOut(
        id=employee.id,
        name=employee.name,
        status=EmployeeStatus(employee.status),
        display_status=_display_status(db, employee),
        contact=employee.contact,
        job_type=employee.job_type,
        notes=employee.notes,
        resigned_on=employee.resigned_on,
        version=employee.version,
    )


def _get_or_404(db: Session, ctx: StoreContext, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None or employee.store_id != ctx.store.id:
        raise NotFound()   # 员工跨店 404
    return employee


def list_employees(
    db: Session, ctx: StoreContext, include_resigned: bool = False
) -> EmployeeListOut:
    """花名册：默认不含 resigned（Locked 排班可见性）。"""
    q = db.query(Employee).filter(Employee.store_id == ctx.store.id)
    if not include_resigned:
        q = q.filter(Employee.status != EmployeeStatus.resigned.value)
    rows = q.order_by(Employee.id).all()
    return EmployeeListOut(items=[employee_out(db, e) for e in rows])


def create_employee(
    db: Session, ctx: StoreContext, payload: EmployeeCreateIn
) -> EmployeeOut:
    employee = Employee(
        store_id=ctx.store.id,
        name=payload.name.strip(),
        status=EmployeeStatus.active.value,
        contact=payload.contact,
        job_type=payload.job_type.value,
        notes=payload.notes,
        version=1,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee_out(db, employee)


def get_employee(
    db: Session, ctx: StoreContext, employee_id: int
) -> EmployeeDetailOut:
    employee = _get_or_404(db, ctx, employee_id)
    leaves = (
        db.query(EmployeeLeave)
        .filter(EmployeeLeave.employee_id == employee.id)
        .order_by(EmployeeLeave.start_date.desc(), EmployeeLeave.id.desc())
        .all()
    )
    base = employee_out(db, employee)
    return EmployeeDetailOut(
        **base.model_dump(),
        leaves=[
            LeaveOut(
                id=l.id,
                employee_id=l.employee_id,
                start_date=l.start_date,
                end_date=l.end_date,
                note=l.note,
                version=l.version,
            )
            for l in leaves
        ],
    )


def update_employee(
    db: Session, ctx: StoreContext, employee_id: int, payload: EmployeeUpdateIn
) -> EmployeeOut:
    employee = _get_or_404(db, ctx, employee_id)
    fields: dict[str, object] = {"version": Employee.version + 1}
    if payload.name is not None:
        fields["name"] = payload.name.strip()
    if payload.contact is not None:
        fields["contact"] = payload.contact
    if payload.job_type is not None:
        fields["job_type"] = payload.job_type.value
    if payload.notes is not None:
        fields["notes"] = payload.notes
    updated = db.execute(
        update(Employee)
        .where(
            Employee.id == employee_id,
            Employee.store_id == ctx.store.id,
            Employee.version == payload.version,
        )
        .values(**fields)
    )
    if updated.rowcount != 1:
        raise VersionConflict()
    db.commit()
    db.refresh(employee)
    return employee_out(db, employee)


def create_leave(
    db: Session, ctx: StoreContext, employee_id: int, payload: LeaveCreateIn
) -> LeaveOut:
    employee = _get_or_404(db, ctx, employee_id)
    if payload.end_date < payload.start_date:
        raise BusinessError("invalid_date_range")
    leave = EmployeeLeave(
        store_id=employee.store_id,
        employee_id=employee.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        note=payload.note,
        version=1,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return LeaveOut(
        id=leave.id,
        employee_id=leave.employee_id,
        start_date=leave.start_date,
        end_date=leave.end_date,
        note=leave.note,
        version=leave.version,
    )


def delete_leave(
    db: Session, ctx: StoreContext, employee_id: int, leave_id: int, version: int
) -> None:
    _get_or_404(db, ctx, employee_id)
    leave = db.get(EmployeeLeave, leave_id)
    if leave is None or leave.employee_id != employee_id or leave.store_id != ctx.store.id:
        raise NotFound()
    updated = db.execute(
        update(EmployeeLeave)
        .where(
            EmployeeLeave.id == leave_id,
            EmployeeLeave.version == version,
        )
        .values(version=EmployeeLeave.version + 1)
    )
    if updated.rowcount != 1:
        raise VersionConflict()
    db.delete(leave)
    db.commit()


def resign_employee(
    db: Session, ctx: StoreContext, employee_id: int, payload: ResignIn
) -> ResignOut:
    """离职（B-specs §4.5）：不删班次、不改历史工资。"""
    employee = _get_or_404(db, ctx, employee_id)
    if employee.status == EmployeeStatus.resigned.value:
        raise Conflict("already_resigned")
    updated = db.execute(
        update(Employee)
        .where(
            Employee.id == employee_id,
            Employee.store_id == ctx.store.id,
            Employee.version == payload.version,
        )
        .values(
            status=EmployeeStatus.resigned.value,
            resigned_on=payload.effective_on,
            version=Employee.version + 1,
        )
    )
    if updated.rowcount != 1:
        raise VersionConflict()
    db.commit()
    db.refresh(employee)
    return ResignOut(status=employee.status, resigned_on=employee.resigned_on)
