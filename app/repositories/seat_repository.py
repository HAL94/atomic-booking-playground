import logging
from datetime import datetime, timedelta, timezone
from typing import ClassVar

from sqlalchemy import select, update

from app.domain.booking_status import BookingStatus
from app.domain.seat import SeatBase
from app.models import Booking, Seat
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class SeatRepository(BaseRepository[SeatBase, Seat]):
    __model__: ClassVar[Seat] = Seat

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        SeatBase.model_validate(data, from_attributes=True)

    async def _validate_held_seat_booking(self, seat_id: str) -> bool:
        """
        Allows re-holding if previous booking is expired
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        stmt = (
            select(Booking, Seat)
            .join(Seat, Booking.seat_id == Seat.id)
            .where(Booking.status == BookingStatus.PENDING, Booking.seat_id == seat_id, Booking.reserved_at <= cutoff)
            .with_for_update(of=[Booking, Seat])
        )
        result = (await self.session.execute(stmt)).first()
        if not result:
            return False
        booking, seat = result
        booking.status = BookingStatus.CANCELED
        booking.canceled_at = datetime.now(tz=timezone.utc)

        logger.info(f"[ValidationStep]: seat {seat}")
        seat.is_held = False

        await self.session.flush()
        return True

    async def try_hold_seat(self, seat_id: str) -> bool:
        try:
            await self._validate_held_seat_booking(seat_id)
            stmt = (
                update(Seat)
                .where(Seat.is_held == False, Seat.is_booked == False, Seat.id == seat_id)  # noqa: E712
                .values(is_held=True)
            )
            result_set = await self.session.execute(stmt)
            return result_set.rowcount > 0
        except Exception as e:
            logger.exception(f"[SeatRepository]: failed to hold seat {str(e)}")
            raise e
