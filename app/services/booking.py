import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import UUID, and_, cast, delete, func, insert, literal, or_, select, text, update
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
            seat_cte = (
                select(Seat)
                .where(Seat.id == seat_id, Seat.status != SeatStatus.BOOKED)
                .with_for_update()
                .cte("seat_cte")
            )

            seat_update_cte = (
                update(Seat)
                .values(status=SeatStatus.HELD)
                .where(Seat.id.in_(select(seat_cte.c.id)))
                .returning(Seat.id)
                .cte("seat_update_cte")
            )

            hold_expiration = func.clock_timestamp() + text("INTERVAL '20 seconds'")
            payload_update_stmt = select(
                func.gen_random_uuid(), seat_update_cte.c.id, cast(literal(user_id), UUID), hold_expiration
            )

            hold_expiration = datetime.now(tz=timezone.utc) + timedelta(seconds=20)
            update_stmt = pg_insert(SeatHold).from_select(
                ["id", "seat_id", "user_id", "expires_at"], payload_update_stmt
            )
            update_stmt = update_stmt.on_conflict_do_update(
                index_elements=["seat_id"],
                set_={**update_stmt.excluded},
                where=(SeatHold.expires_at <= func.clock_timestamp()),
            )
            update_stmt = update_stmt.returning(SeatHold)
            seat_hold = (await self.session.execute(update_stmt)).scalar_one_or_none()

            if not seat_hold:
                await self.session.rollback()
                raise HTTPException(status_code=409, detail="Seat is already taken")

            await self.session.commit()

            return self._hold_repo.domain_model(seat_hold)

        except Exception:
            raise
