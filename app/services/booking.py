import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import UUID, and_, cast, delete, func, insert, literal, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domain.seat_hold import SeatHoldBase
from app.dto.seat import SeatStatus
from app.models import Seat, SeatHold
from app.repositories.seat_hold_repository import SeatHoldRepository
from app.services.base import BaseService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BookingService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._hold_repo = SeatHoldRepository(session)

    async def get_seat_hold(self, hold_id: str, user_id: str) -> SeatHoldBase | None:
        try:
            return await self._hold_repo.get_one_or_none([SeatHold.id == hold_id, SeatHold.user_id == user_id])
        except Exception as e:
            raise e

    async def try_hold_seat(self, seat_id: str, user_id: str) -> SeatHoldBase | None:
        try:
            # 1. determine if seat is available
            # 2. if not available, simply return
            # 3. if available, create hold record. Then set status to HELD
            stmt_seat_hold = select(Seat).where(Seat.id == seat_id, Seat.status != SeatStatus.BOOKED).with_for_update()

            seat = (await self.session.execute(stmt_seat_hold)).scalar_one_or_none()
            # logger.info(f"[InsertSeatHold] seat {seat}")

            if not seat:
                raise HTTPException(status_code=409, detail="Could not hold seat")

            stmt_seat_hold = select(SeatHold).where(SeatHold.seat_id == seat_id).with_for_update()
            seat_hold = (await self.session.execute(stmt_seat_hold)).scalar_one_or_none()

            if seat_hold and seat_hold.expires_at > datetime.now(tz=timezone.utc):
                raise HTTPException(status_code=409, detail="Seat is already taken")

            hold_expiration = datetime.now(tz=timezone.utc) + timedelta(seconds=20)
            update_stmt = pg_insert(SeatHold).values(seat_id=seat_id, user_id=user_id, expires_at=hold_expiration)
            update_stmt = update_stmt.on_conflict_do_update(index_elements=["seat_id"], set_={**update_stmt.excluded})
            update_stmt = update_stmt.returning(SeatHold)

            seat_hold = (await self.session.execute(update_stmt)).scalar_one_or_none()
            await self.session.commit()

            return self._hold_repo.domain_model(seat_hold)

        except Exception:
            raise
