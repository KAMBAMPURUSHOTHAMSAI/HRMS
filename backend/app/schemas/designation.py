
from pydantic import BaseModel, ConfigDict, Field


class DesignationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    department_id: int = Field(gt=0)
    level: str | None = Field(default=None, max_length=50)


class DesignationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    department_id: int | None = Field(default=None, gt=0)
    level: str | None = Field(default=None, max_length=50)


class DesignationRead(BaseModel):
    id: int
    name: str
    department_id: int
    level: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
