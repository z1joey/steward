import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(v: str) -> str:
    """邮箱归一化 [C]：去空格 + 转小写；简单格式校验（不引依赖，[O-26]）。"""
    v = v.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("邮箱格式不正确")
    return v


class RegisterIn(BaseModel):
    email: str   # 归一化 + 格式校验（见下）
    password: str = Field(min_length=1, max_length=128)  # 弱口令规则 [Open]

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return normalize_email(v)


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email_ok(cls, v: str) -> str:
        return normalize_email(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
