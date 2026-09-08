from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.modules.auth.service import login, register

router = APIRouter()


@router.post("/auth/register", status_code=201, response_model=UserOut)
def register_user(payload: RegisterIn, db: Session = Depends(get_db)) -> User:
    return register(db, payload.phone, payload.password)


@router.post("/auth/login", response_model=TokenOut)
def login_user(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    return login(db, payload.phone, payload.password)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
