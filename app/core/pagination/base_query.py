from abc import ABC, abstractmethod
from typing import Optional
from pydantic import Field
from app.core.schema import BaseModel

from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy import ColumnElement


class PaginationQuery(BaseModel, ABC):
    page: Optional[int] = Field(1, ge=1)
    size: Optional[int] = Field(20, ge=1)
    sort_by: Optional[str] = None
    filter_by: Optional[str] = None

    @abstractmethod
    def sort_fields() -> list[InstrumentedAttribute]:
        pass

    @abstractmethod
    def filter_fields() -> list[ColumnElement]:
        pass
