from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_store_membership
from app.modules.employees.schemas import (
    EmployeeCreateIn,
    EmployeeDetailOut,
    EmployeeListOut,
    EmployeeOut,
    EmployeeUpdateIn,
    LeaveCreateIn,
    LeaveDeleteIn,
    LeaveOut,
    ResignIn,
    ResignOut,
)
from app.modules.employees.service import (
    create_employee,
    create_leave,
    delete_leave,
    get_employee,
    list_employees,
    resign_employee,
    update_employee,
)

router = APIRouter()


@router.get("/employees", response_model=EmployeeListOut)
def list_employees_route(
    include_resigned: bool = Query(default=False),
    ctx: StoreContext = Depends(require_store_membership),   # 两角色（B-specs §4.4）
    db: Session = Depends(get_db),
) -> EmployeeListOut:
    return list_employees(db, ctx, include_resigned=include_resigned)


@router.post("/employees", status_code=201, response_model=EmployeeOut)
def create_employee_route(
    payload: EmployeeCreateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    return create_employee(db, ctx, payload)


@router.get("/employees/{employee_id}", response_model=EmployeeDetailOut)
def get_employee_route(
    employee_id: int,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> EmployeeDetailOut:
    return get_employee(db, ctx, employee_id)


@router.put("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee_route(
    employee_id: int,
    payload: EmployeeUpdateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> EmployeeOut:
    return update_employee(db, ctx, employee_id, payload)


@router.post("/employees/{employee_id}/leaves", status_code=201, response_model=LeaveOut)
def create_leave_route(
    employee_id: int,
    payload: LeaveCreateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> LeaveOut:
    return create_leave(db, ctx, employee_id, payload)


@router.delete("/employees/{employee_id}/leaves/{leave_id}", status_code=204)
def delete_leave_route(
    employee_id: int,
    leave_id: int,
    payload: LeaveDeleteIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> None:
    delete_leave(db, ctx, employee_id, leave_id, payload.version)


@router.post("/employees/{employee_id}/resign", response_model=ResignOut)
def resign_employee_route(
    employee_id: int,
    payload: ResignIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> ResignOut:
    return resign_employee(db, ctx, employee_id, payload)
