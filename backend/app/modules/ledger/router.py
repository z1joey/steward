from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_store_membership
from app.modules.ledger.schemas import EntryCreateIn, EntryCreateOut, LedgerListOut
from app.modules.ledger.service import create_entry, list_entries

router = APIRouter()


@router.get("/ledger/entries", response_model=LedgerListOut)
def list_entries_route(
    filter: str = Query(default="all"),
    month: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: StoreContext = Depends(require_store_membership),
    db: Session = Depends(get_db),
) -> LedgerListOut:
    return list_entries(db, ctx, filter=filter, month=month, limit=limit, offset=offset)


@router.post("/ledger/entries", status_code=201, response_model=EntryCreateOut)
def create_entry_route(
    payload: EntryCreateIn,
    ctx: StoreContext = Depends(require_store_membership),   # 两角色可记（B-specs §2.5）
    db: Session = Depends(get_db),
) -> EntryCreateOut:
    return create_entry(db, ctx, payload)
