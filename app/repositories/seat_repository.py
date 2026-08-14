import logging
from typing import ClassVar

from sqlalchemy import update

from app.domain.seat import SeatBase
from app.models import Seat
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class SeatRepository(BaseRepository[SeatBase, Seat]):
    __model__: ClassVar[Seat] = Seat

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        SeatBase.model_validate(data, from_attributes=True)

    async def try_hold_seat(self, seat_id: str) -> bool:
        try:
            stmt = (
                update(Seat)
                .where(Seat.is_held == False, Seat.is_booked == False, Seat.id == seat_id)  # noqa: E712
                .values(is_held=False)
            )
            result_set = (await self.session.execute(stmt))
            return result_set.rowcount > 0
        except Exception as e:
            logger.exception(f"[SeatRepository]: failed to hold seat {str(e)}")
            raise e
