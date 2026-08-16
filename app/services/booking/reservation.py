import logging
from uuid import UUID

from fastapi import HTTPException

from app.domain.booking import BookingBase, BookingStatus
from app.dto.booking import CreateReservation
from app.repositories.booking_repository import BookingRepository
from app.repositories.seat_repository import SeatRepository
from app.services.base import BaseService
from app.services.booking.seat_guard import SeatHoldGuard

logger = logging.getLogger("uvicorn")

logger.setLevel(logging.INFO)


class ReservationHoldout(BaseService):
    _booking_hold_ttl = 60  # 1 minute for testing

    def __init__(self, session):
        super().__init__(session)
        self._booking_repo = BookingRepository(session)
        self._seat_repo = SeatRepository(session)
        self._seat_guard = SeatHoldGuard(self._booking_hold_ttl)

    async def reserve_booking(self, payload: CreateReservation, seat_id: UUID, user_id: UUID) -> BookingBase:
        # STEP 1: Acquire a lock
        acquired_reservation = await self._seat_guard.acquire_hold(seat_id, user_id)
        if not acquired_reservation:
            raise HTTPException(detail="Seat is currently held by another user or already booked.", status_code=409)

        try:
            # STEP 2: ensure the record is available
            is_held = await self._seat_repo.try_hold_seat(seat_id)

            if not is_held:
                raise HTTPException(detail="Seat is no longer available.", status_code=409)

            # STEP 3: lock the record for this user
            booking = await self._booking_repo.create_one(
                BookingBase(
                    ticket_price=payload.ticket_price,
                    status=BookingStatus.PENDING,
                    user_id=user_id,
                    seat_id=seat_id,
                )
            )

            await self.session.commit()
            return booking
        except Exception as e:
            await self._seat_guard.release_hold(seat_id)
            raise e
