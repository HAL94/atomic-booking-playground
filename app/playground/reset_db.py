import asyncio
import logging

from sqlalchemy import delete

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.models import Cart, CartItem, CartReservation

configure_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def reset_db():
    """
    Remove cart items and reservation records
    """
    try:
        async with session_manager.session() as session:
            await session.execute(delete(CartItem))
            await session.execute(delete(CartReservation))
            await session.execute(delete(Cart))
            await session.commit()

        logger.info("[FlastItemSimulation]: successfully reset carts and reservations")

    except Exception as e:
        logger.exception(f"[FlastItemSimulation]: failed to reset carts and reservations {str(e)}")
        raise e


if __name__ == "__main__":
    asyncio.run(reset_db())
