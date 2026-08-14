from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.models import Seat


class SeatBase(BaseDomain):
    model: ClassVar[Seat] = Seat

    id: Optional[UUID | str] = Field(default=None)
    name: str
