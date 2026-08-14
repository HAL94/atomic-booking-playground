from typing import ClassVar, Generic, TypeVar

from sqlalchemy.orm.strategy_options import _AbstractLoad

from app.core.database.base import Base
from app.core.schema import BaseModel

T = TypeVar(name="T", bound=Base)

class BaseDomain(BaseModel, Generic[T]):
    model: ClassVar[T]

    @classmethod
    def relations(cls) -> list[_AbstractLoad]:
        return []
