from datetime import datetime
from typing import Any, Dict, override

from sqlalchemy import (
    Column,
    DateTime,
    func,
    inspect,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    RelationshipProperty,
    mapped_column,
)


class Base(DeclarativeBase):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    def dict(self):
        return self.__dict__

    @override
    def __repr__(self) -> str:
        return str(self.dict())

    @classmethod
    def get_relationships(cls) -> Dict[str, RelationshipProperty[Any]]:
        """
        Returns:
            dictionary of a string mapped to relationships, where key is the relation name
        """
        mapper = inspect(cls)
        relations = {rel[0]: rel[1] for rel in mapper.relationships.items()}
        return relations

    @classmethod
    def get_foreign_columns(cls) -> Dict[str, Column]:
        """
        Determine the foreign columns of a table

        Returns:
            dictionary of a string mapped to column information, where key is column name
        """
        relations = cls.get_relationships()
        foreign_cols = {}
        for rel in relations:
            relationship_property: RelationshipProperty = relations[rel]
            for fk in relationship_property.remote_side:
                foreign_cols[rel] = fk.name

        return foreign_cols

    @classmethod
    def columns(cls):
        """
        Get a list of column with type information
        """
        return cls.__table__.columns
