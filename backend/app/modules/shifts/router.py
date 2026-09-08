from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_store_membership
from app.modules.shifts.schemas import (
    ShiftCreateIn,
    ShiftDeleteIn,
    ShiftListOut,
    ShiftOut,
    ShiftUpdateIn,
)
from app.modules.shifts.service import (
    create_segment,
    delete_segment,
    list_segments,
    update_segment,
)

router = APIRouter()


@router.get("/shift_segments", response_model=ShiftListOut)
def list_segments_route(
    week: str | None = Query(default=None),                  # YYYY-Www
    from_: str | None = Query(default=None, alias="from"),   # YYYY-MM-DD
    to: str | None = Query(default=None),                    # YYYY-MM-DD
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> ShiftListOut:
    return list_segments(db, ctx, week, from_, to)


@router.post("/shift_segments", status_code=201, response_model=ShiftOut)
def create_segment_route(
    payload: ShiftCreateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> ShiftOut:
    return create_segment(db, ctx, payload)


@router.put("/shift_segments/{segment_id}", response_model=ShiftOut)
def update_segment_route(
    segment_id: int,
    payload: ShiftUpdateIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> ShiftOut:
    return update_segment(db, ctx, segment_id, payload)


@router.delete("/shift_segments/{segment_id}", status_code=204)
def delete_segment_route(
    segment_id: int,
    payload: ShiftDeleteIn,
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> None:
    delete_segment(db, ctx, segment_id, payload)
