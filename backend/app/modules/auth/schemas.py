from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    phone: str = Field(min_length=1, max_length=32)   # 格式规则 [C · O-26]：非空、去空格、≤32
    password: str = Field(min_length=1, max_length=128)  # 弱口令规则 [Open]


class LoginIn(BaseModel):
    phone: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
