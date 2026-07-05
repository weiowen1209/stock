from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class ResponseMeta(BaseModel):
    source: str = "sqlite"
    updated_at: datetime | None = None
    stale: bool = False


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: Any = None


class ApiResponse(BaseModel, Generic[T]):
    data: T | None
    meta: ResponseMeta
    error: ErrorDetail | None = None


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
