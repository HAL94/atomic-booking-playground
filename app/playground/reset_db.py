import asyncio
import logging

from sqlalchemy import delete

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.models import SeatHold

configure_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def reset_db():
    """
    Remove seat hold records
    """
    try:
        async with session_manager.session() as session:
            await session.execute(delete(SeatHold))
            await session.commit()

        logger.info("[SeatSimulation]: successfully reset seat holds")

    except Exception as e:
        logger.exception(f"[SeatSimulation]: failed to reset seat holds {str(e)}")
        raise e


if __name__ == "__main__":
    asyncio.run(reset_db())
