import asyncio
import logging
from uuid import UUID

from sqlalchemy import update

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.domain.booking import BookingBase
from app.domain.booking_status import BookingStatus
from app.models import Seat
from app.repositories.booking_repository import BookingRepository

configure_logging()

logger = logging.getLogger(__name__)


async def run_pg():
    async with session_manager.session() as session:
        booking_repo = BookingRepository(session)

        await booking_repo.upsert(
            [
                BookingBase(
                    id="649cabca-e315-44fe-bd03-c6f819a3c7f0",
                    status=BookingStatus.PENDING,
                    ticket_price=9.99,
                    user_id=UUID("ebb0e51e-372e-4d56-8e7c-eb7f085657cf"),
                    seat_id=UUID("5a3b417c-9e16-4f3e-b43d-b1024994b616"),
                ),
                BookingBase(
                    id="649cabca-e315-44fe-bd03-c6f819a3c7f1",
                    ticket_price=9.99,
                    status=BookingStatus.PENDING,
                    user_id=UUID("ebb0e51e-372e-4d56-8e7c-eb7f085657cf"),
                    seat_id=UUID("5a3b417c-9e16-4f3e-b43d-b1024994b617"),
                ),
                BookingBase(
                    id="649cabca-e315-44fe-bd03-c6f819a3c7f2",
                    ticket_price=9.99,
                    status=BookingStatus.PENDING,
                    user_id=UUID("ebb0e51e-372e-4d56-8e7c-eb7f085657cf"),
                    seat_id=UUID("5a3b417c-9e16-4f3e-b43d-b1024994b618"),
                ),
                BookingBase(
                    id="649cabca-e315-44fe-bd03-c6f819a3c7f3",
                    ticket_price=9.99,
                    status=BookingStatus.PENDING,
                    user_id=UUID("efd78619-f6b4-42d7-ad27-0cc948a8d795"),
                    seat_id=UUID("5a3b417c-9e16-4f3e-b43d-b1024994b619"),
                ),
                BookingBase(
                    id="649cabca-e315-44fe-bd03-c6f819a3c7f4",
                    ticket_price=9.99,
                    status=BookingStatus.PENDING,
                    user_id=UUID("efd78619-f6b4-42d7-ad27-0cc948a8d795"),
                    seat_id=UUID("5a3b417c-9e16-4f3e-b43d-b1024994b620"),
                ),
                BookingBase(
                    id="649cabca-e315-44fe-bd03-c6f819a3c7f5",
                    ticket_price=9.99,
                    status=BookingStatus.PENDING,
                    user_id=UUID("efd78619-f6b4-42d7-ad27-0cc948a8d795"),
                    seat_id=UUID("5a3b417c-9e16-4f3e-b43d-b1024994b621"),
                ),
            ],
        )

        stmt = update(Seat).values(is_held=True)
        await session.execute(stmt)

        await session.commit()

        logger.info("[Playground]: finished..")


if __name__ == "__main__":
    asyncio.run(run_pg())
