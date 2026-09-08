from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_store_membership
from app.modules.recurring.schemas import (
    OccurrenceCreateIn,
    OccurrenceCreateOut,
    RecurringCreateIn,
    RecurringListOut,
    RecurringOut,
    RecurringUpdateIn,
)
from app.modules.recurring.service import (
    create_recurring,
    list_recurring,
    record_occurrence,
    update_recurring,
)

router = APIRouter()


@router.get("/ledger/recurring", response_model=RecurringListOut)
def list_recurring_route(
    ctx: StoreContext = Depends(require_store_membership),   # 两角色（B-specs §3.4）
    db: Session = Depends(get_db),
) -> RecurringListOut:
    return list_recurring(db, ctx)


@router.post("/ledger/recurring", status_code=201, response_model=RecurringOut)
def create_recurring_route(
    payload: RecurringCreateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> RecurringOut:
    return create_recurring(db, ctx, payload)


@router.put("/ledger/recurring/{rec_id}", response_model=RecurringOut)
def update_recurring_route(
    rec_id: int,
    payload: RecurringUpdateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> RecurringOut:
    return update_recurring(db, ctx, rec_id, payload)


@router.post(
    "/ledger/recurring/{rec_id}/occurrences", status_code=201, response_model=OccurrenceCreateOut
)
def record_occurrence_route(
    rec_id: int,
    payload: OccurrenceCreateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> OccurrenceCreateOut:
    return record_occurrence(db, ctx, rec_id, payload)
