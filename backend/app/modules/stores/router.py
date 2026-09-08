from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import User
from app.modules.stores.schemas import StoreCreateIn, StoreOut, StoresOut
from app.modules.stores.service import create_store, list_stores_for_user

router = APIRouter()


@router.post("/stores", status_code=201, response_model=StoreOut)
def create_store_route(
    payload: StoreCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StoreOut:
    store = create_store(db, user, payload.name)
    return StoreOut(id=store.id, name=store.name, role="manager", version=store.version)


@router.get("/stores", response_model=StoresOut)
def list_stores_route(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StoresOut:
    return StoresOut(items=list_stores_for_user(db, user))
