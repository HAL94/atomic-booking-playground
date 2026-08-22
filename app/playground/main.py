import asyncio
import logging
from datetime import datetime, timedelta

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auction import AuctionBase
from app.domain.auth import UserBase
from app.domain.bid_status import BidStatus
from app.models import *  # noqa: F403
from app.repositories.auction_repository import AuctionRepository
from app.repositories.user_repository import UserRepository

configure_logging()
logger = logging.getLogger(__name__)


async def main_pg():
    async with session_manager.session() as session:
        _auction_repo = AuctionRepository(session)
        _user_repo = UserRepository(session)
        u1 = UserBase(
            id="3cd57e13-93e1-4d54-ac68-a23a541b9476",
            full_name="James Brown",
            email="u1@example.com",
            hashed_password=hash_password("123456"),
        )
        u2 = UserBase(
            id="3cd57e13-93e1-4d54-ac68-a23a541b9477",
            full_name="Jason Limbu",
            email="u2@example.com",
            hashed_password=hash_password("123456"),
        )
        bidder_u1 = UserBase(
            id="3cd57e13-93e1-4d54-ac68-a23a541b9478",
            full_name="Bidder One",
            email="bu1@example.com",
            hashed_password=hash_password("123456"),
        )
        bidder_u2 = UserBase(
            id="3cd57e13-93e1-4d54-ac68-a23a541b9479",
            full_name="Bidder Two",
            email="bu2@example.com",
            hashed_password=hash_password("123456"),
        )
        await _user_repo.upsert([u1, u2, bidder_u1, bidder_u2])
        await _auction_repo.upsert(
            [
                AuctionBase(
                    id="6b91fa86-c200-4845-94f0-b221b2065e21",
                    name="PS1 Vinteage Auction",
                    scheduled_at=datetime.now() + timedelta(days=1),
                    auction_owner_id=u1.id,
                    status=BidStatus.SCHEDULED,
                ),
                AuctionBase(
                    id="6b91fa86-c200-4845-94f0-b221b2065e22",
                    name="PS2 Vinteage Auction",
                    scheduled_at=datetime.now() + timedelta(days=2),
                    auction_owner_id=u2.id,
                    status=BidStatus.SCHEDULED,
                ),
                AuctionBase(
                    id="6b91fa86-c200-4845-94f0-b221b2065e23",
                    name="Classic Chevrolet Caprice 1988",
                    scheduled_at=datetime.now() + timedelta(days=10),
                    auction_owner_id=u1.id,
                    status=BidStatus.SCHEDULED,
                ),
            ]
        )
        await session.commit()
        logger.info("[Seeder]: finished..")


if __name__ == "__main__":
    asyncio.run(main_pg())
