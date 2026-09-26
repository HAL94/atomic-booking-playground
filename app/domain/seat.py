from typing import ClassVar
from uuid import UUID

from app.domain.base import BaseDomain
from app.dto.seat import SeatStatus
from app.models import Seat


class SeatBase(BaseDomain[Seat]):
    model: ClassVar[Seat] = Seat

    id: str | UUID | None = None
    name: str
    status: SeatStatus
