from pydantic import BaseModel, ConfigDict, Field


class StoreCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str
    version: int


class StoresOut(BaseModel):
    items: list[StoreOut]
