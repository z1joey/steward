from sqlalchemy.orm import Session

from app.core.errors import Conflict, Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import TokenOut, UserOut


def register(db: Session, phone: str, password: str) -> User:
    phone = phone.strip()
    if not phone:
        raise Conflict("phone_required", 422)
    existing = db.query(User).filter(User.phone == phone).one_or_none()
    if existing is not None:
        raise Conflict("phone_taken")   # 重复手机号拒绝（AC-AUTH-01）
    user = User(phone=phone, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, phone: str, password: str) -> TokenOut:
    phone = phone.strip()
    user = db.query(User).filter(User.phone == phone).one_or_none()
    if user is None or not verify_password(user.password_hash, password):
        raise Unauthorized("invalid_credentials")   # 401（AC-AUTH-02）
    return TokenOut(
        access_token=create_access_token(user.id), token_type="bearer", user=UserOut.model_validate(user)
    )
