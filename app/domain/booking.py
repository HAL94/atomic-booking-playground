from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field, field_validator
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from app.domain.auth import UserBase
from app.domain.base import BaseDomain
from app.domain.booking_status import BookingStatus
from app.models import Booking


class BookingBase(BaseDomain):
    model: ClassVar[Booking] = Booking

    id: Optional[UUID | str] = Field(default=None)
    reserved_at: Optional[datetime] = Field(default=datetime.now())
    ticket_price: float
    status: str = Field(default=BookingStatus.PENDING)
    user_id: Optional[UUID] = Field(default=None)
    seat_id: UUID | str

    @field_validator("ticket_price", mode="before")
    @classmethod
    def transform_ticket_price(cls, v: float) -> float:
        if not isinstance(v, float):
            return 0
        return round(v, 2)

    @field_validator("id", mode="before")
    @classmethod
    def transform_booking_id(cls, v: UUID | str) -> str:
        return str(v)

    @field_validator("seat_id", mode="before")
    @classmethod
    def transform_seat_id(cls, v: UUID) -> str:
        return str(v)


class BookingWithUser(BookingBase):
    user_id: Optional[UUID] = Field(exclude=True)
    user: UserBase

    @classmethod
    def relations(cls) -> list[_AbstractLoad]:
        return [selectinload(Booking.user)]
