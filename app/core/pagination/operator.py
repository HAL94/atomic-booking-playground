import enum
from typing import Any

from app.core.pagination.exceptions import InvalidOperator
from sqlalchemy import ColumnElement
from sqlalchemy.orm import InstrumentedAttribute


class LogicalOperator(enum.StrEnum):
    EQ = "__eq__"
    LTE = "__lte__"
    LT = "__lt__"
    GTE = "__gte__"
    GT = "__gt__"
    NOT = "__ne__"
    ILIKE = "__il__"
    NOT_ILIKE = "__nil__"

    def __str__(self):
        return self.value

    @classmethod
    def all_values(cls):
        return str([operator.value for operator in cls])


class FieldOperation:
    @classmethod
    def determine_operator(cls, field_str: str) -> LogicalOperator:
        if LogicalOperator.GTE in field_str:
            return LogicalOperator.GTE

        if LogicalOperator.GT in field_str:
            return LogicalOperator.GT

        if LogicalOperator.LTE in field_str:
            return LogicalOperator.LTE

        if LogicalOperator.LT in field_str:
            return LogicalOperator.LT

        if LogicalOperator.NOT in field_str:
            return LogicalOperator.NOT

        if LogicalOperator.EQ in field_str:
            return LogicalOperator.EQ

        if LogicalOperator.NOT_ILIKE in field_str:
            return LogicalOperator.NOT_ILIKE

        if LogicalOperator.ILIKE in field_str:
            return LogicalOperator.ILIKE

        raise InvalidOperator

    @classmethod
    def create_sql_expression(
        cls, column: InstrumentedAttribute, operator: LogicalOperator, column_value: Any
    ) -> list[ColumnElement]:
        if operator is LogicalOperator.GTE:
            return [column >= column_value]
        if operator is LogicalOperator.GT:
            return [column > column_value]
        if operator is LogicalOperator.LTE:
            return [column <= column_value]
        if operator is LogicalOperator.LT:
            return [column < column_value]
        if operator is LogicalOperator.NOT:
            return [column != column_value]
        if operator is LogicalOperator.EQ:
            return [column == column_value]
        if operator is LogicalOperator.ILIKE:
            return [column.ilike(f"%{column_value}%")]
        if operator is LogicalOperator.NOT_ILIKE:
            return [column.not_ilike(f"%{column_value}")]

        raise ValueError("No suppoerted oeprations were determined")
