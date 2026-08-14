from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer

from app.core.exceptions import BadRequestException
from app.core.pagination.exceptions import InvalidDatetimeValue


class PaginationParser:
    @classmethod
    def split_and_clean_fields(cls, fields: Optional[str] = None) -> list[str]:
        if not fields:
            return []
        return [field.strip() for field in fields.split(",")]

    @classmethod
    def validate_field(
        cls,
        field: str,
        allowed_fields: list[str],
        error_message: str = "Operation not allowed on field '{field}'. Allowed fields are {allowed_fields}",
    ) -> None:
        """Validates if a field is in the allowed list."""
        # print(f"validatin if {field} exist in {allowed_fields}")
        if field not in allowed_fields:
            raise BadRequestException(error_message.format(field=field, allowed_fields=allowed_fields))

    @classmethod
    def convert_value(cls, *, value: Any, column_type: Any, field_name: str):
        """
        Convert value to appropriate type based on column type.

        :param value: String value to convert
        :param column_type: SQLAlchemy column type
        :return: Converted value
        """
        try:
            if isinstance(column_type, Integer):
                return int(value)
            if isinstance(column_type, Float):
                return float(value)
            if isinstance(column_type, Boolean):
                return value == "true" or value == "1"
            if isinstance(column_type, DateTime):
                from datetime import datetime

                try:
                    return datetime.fromisoformat(value)
                except Exception:
                    raise InvalidDatetimeValue(
                        message=f"Expected type of '{field_name}' is '{str(column_type).lower()}', could not parse the value '{value}'"
                    )
            return value
        except InvalidDatetimeValue as e:
            raise BadRequestException(detail=str(e))
        except Exception:
            raise ValueError(
                f"Type of field '{field_name}' is '{str(column_type).lower()}' but value passed is: '{type(value).__name__}'"
            )
