from typing import Generic, TypeVar

from app.core.schema import BaseModel

T = TypeVar(name="T")


class PaginatedResult(BaseModel, Generic[T]):
    result: list[T]
    total_records: int
    size: int
    page: int
