from sqlalchemy.orm import Session

from app.core.errors import Conflict, Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import TokenOut, UserOut


def register(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    if not email:
        raise Conflict("email_required", 422)
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing is not None:
        raise Conflict("email_taken")   # 重复邮箱拒绝（AC-AUTH-01）
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, email: str, password: str) -> TokenOut:
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None or not verify_password(user.password_hash, password):
        raise Unauthorized("invalid_credentials")   # 401（AC-AUTH-02）
    return TokenOut(
        access_token=create_access_token(user.id), token_type="bearer", user=UserOut.model_validate(user)
    )
