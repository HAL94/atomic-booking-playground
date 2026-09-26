import asyncio
import logging
import uuid

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auth import UserBase
from app.domain.seat import SeatBase
from app.dto.seat import SeatStatus
from app.models import *  # noqa: F403
from app.repositories.seat_repository import SeatRepository
from app.repositories.user_repository import UserRepository

configure_logging()
logger = logging.getLogger(__name__)


def create_user(id_sequence: str, number_sequence: int):
    id_input = f"3cd57e13-93e1-4d54-ac68-a23a541b9{id_sequence}"
    return UserBase(
        id=id_input,
        full_name=f"Booker {number_sequence}",
        email=f"u{number_sequence}@example.com",
        hashed_password=hash_password("123456"),
    )


async def upsert_users(number_of_users: int = 3) -> list[UserBase]:
    async with session_manager.session() as session:
        user_repo = UserRepository(session)
        SUFFIX = 478
        payload = []
        for i in range(number_of_users):
            payload.append(create_user(str(SUFFIX), i + 1))
            SUFFIX += 1

        index_elements = ["id"]
        return await user_repo.upsert(payload, index_elements, commit=True)


async def upsert_seats() -> list[SeatBase]:
    async with session_manager.session() as session:
        seat_repo = SeatRepository(session)
        letters = ["A", "B", "C", "D", "E"]
        nums = ["1", "2", "3", "4", "5"]
        ids = [
            uuid.UUID("05b42ace-71c3-4172-b2d8-9d608cf93dab"),
            uuid.UUID("a825958c-4b13-40f2-a783-3c4ee932e74b"),
            uuid.UUID("4f9b0e7c-6d58-40be-922f-f472d472591c"),
            uuid.UUID("3d1222bb-2bbe-4569-b6fc-7028fe16b8b9"),
            uuid.UUID("7dcf4e26-cb98-4321-8cef-acd3e082821c"),
        ]

        seats = [
            SeatBase(id=str(seat_id), name=letter + num, status=SeatStatus.AVAILABLE)
            for letter, num, seat_id in zip(letters, nums, ids)
        ]

        return await seat_repo.upsert(seats, ["name"], commit=True)


async def main_pg():
    await upsert_users()
    await upsert_seats()
    logger.info("[Seeder]: finished..")


if __name__ == "__main__":
    asyncio.run(main_pg())
