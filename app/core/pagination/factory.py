from functools import cached_property
from typing import ClassVar
from pydantic import field_validator
from sqlalchemy import ColumnElement, asc, desc
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.core.database import Base
from app.core.exceptions import BadRequestException
from app.core.pagination.base_parser import PaginationParser
from app.core.pagination.base_query import PaginationQuery
from app.core.pagination.exceptions import InvalidOperator
from app.core.pagination.operator import FieldOperation, LogicalOperator


class PaginationSortParser(PaginationParser):
    def _process_sort_fields(self, sort_by_str: str, model: Base) -> list[InstrumentedAttribute]:
        """
        Process and validate sort fields.

        :param model: SQLAlchemy model class
        :return: List of sort expressions
        """
        # print(f"sort_by is: {sort_by_str}")
        sort_fields = self.split_and_clean_fields(sort_by_str)
        sort_by = []

        for field in sort_fields:
            if not field:
                continue

            clean_field = field.lstrip("-")
            is_descending = field.startswith("-")

            try:
                column = getattr(model, clean_field)
                sort_expr = desc(column) if is_descending else asc(column)
                sort_by.append(sort_expr)
            except Exception as e:
                print(f"Invalid sort field {clean_field}: {e}")

        return sort_by


class PaginationFilterParser(PaginationParser):
    def _process_filter_fields(self, filter_by_str: str, model: Base) -> list[ColumnElement]:
        """
        Process and validate filter fields with type conversion.

        :param model: SQLAlchemy model class
        :return: List of filter expressions
        """
        filter_fields = self.split_and_clean_fields(filter_by_str)
        filter_by = []

        for pair in filter_fields:
            if not pair:
                continue

            operator: LogicalOperator = None
            try:
                operator = FieldOperation.determine_operator(pair)

                key, value = pair.split(operator.value, 1)

                column: InstrumentedAttribute = getattr(model, key)

                converted_value = self.convert_value(value=value, column_type=column.type, field_name=key)

                # print(f"Converted value: {bool(value)} - {converted_value}")

                sql_expr = FieldOperation.create_sql_expression(
                    column=column, operator=operator, column_value=converted_value
                )

                filter_by.extend(sql_expr)
            except InvalidOperator:
                print("Invalid oeprator passed")
            except ValueError as e:
                # print(f"Invalid filter: {pair} {operator}")
                raise BadRequestException(detail=str(e)) from e

        return filter_by


class PaginationFactory:
    @staticmethod
    def create(
        model: Base,
        /,
        *,
        exclude_sort_fields: list[str] = [],
        exclude_filter_fields: list[str] = [],
    ) -> PaginationQuery:
        filter_parser = PaginationFilterParser()
        sort_parser = PaginationSortParser()

        fields = model.columns()

        sort_fields = fields
        filter_fields = fields

        excluded_sort = set(exclude_sort_fields)
        excluded_filter = set(exclude_filter_fields)

        sortable_fields = list(sort_fields - excluded_sort)
        filterable_fields = list(filter_fields - excluded_filter)

        class CustomPaginationQuery(PaginationQuery):
            __model__: ClassVar[Base] = model

            @cached_property
            def sort_fields(self):
                fields = sort_parser._process_sort_fields(self.sort_by, self.__model__)

                if not fields:
                    return []

                return fields

            @cached_property
            def filter_fields(self):
                fields = filter_parser._process_filter_fields(self.filter_by, self.__model__)

                if not fields:
                    return []

                return fields

            @field_validator("sort_by")
            @classmethod
            def validate_sort_fields(cls, v):
                if not v:
                    return v

                sort_fields = sort_parser.split_and_clean_fields(v)

                for field in sort_fields:
                    clean_field = field.lstrip("-")

                    sort_parser.validate_field(field=clean_field, allowed_fields=sortable_fields)

                return v

            @field_validator("filter_by")
            @classmethod
            def validate_filter_fields(cls, v):
                if not v:
                    return v

                filter_pairs = filter_parser.split_and_clean_fields(v)

                error_message = "Filtering not allowed on field '{field}'. Allowed fields are {allowed_fields}"

                for pair in filter_pairs:
                    field = None

                    try:
                        operator: LogicalOperator = FieldOperation.determine_operator(pair)

                        field, _ = pair.split(operator.value, 1)

                    except Exception:
                        raise ValueError(
                            f"Invalid filter operator. Passed query is '{pair}'."
                            f" Use '<field><op><value>' format where op could be: {LogicalOperator.all_values()}"
                        )

                    filter_parser.validate_field(
                        field=field,
                        allowed_fields=filterable_fields,
                        error_message=error_message,
                    )
                return v

        return CustomPaginationQuery
