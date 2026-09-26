from datetime import datetime
from typing import ClassVar
from uuid import UUID

from app.domain.base import BaseDomain
from app.models import SeatHold


class SeatHoldBase(BaseDomain[SeatHold]):
    model: ClassVar[SeatHold] = SeatHold

    id: str | UUID | None = None
    seat_id: str | UUID
    user_id: str | UUID
    expires_at: datetime
