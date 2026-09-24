import asyncio
import logging

from sqlalchemy import delete

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.models import AuctionWinner, Bid

configure_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def reset_db():
    """
    Remove bid records and reset redis
    """
    try:
        async with session_manager.session() as session:
            await session.execute(delete(AuctionWinner))
            await session.execute(delete(Bid))
            await session.commit()

        logger.info("[BidsSimulation]: successfully reset bids")

    except Exception as e:
        logger.exception(f"[BidsSimulation]: failed to reset bids and redis {str(e)}")
        raise e


if __name__ == "__main__":
    asyncio.run(reset_db())