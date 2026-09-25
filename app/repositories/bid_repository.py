import logging
import uuid
import zlib
from typing import Any, ClassVar

from sqlalchemy import UUID, cast, func, insert, literal, select, text, update

from app.core.exceptions import BadRequestException, NotFoundException
from app.domain.bid import BidBase
from app.dto.bid import CreateAuctionBid
from app.models import Auction, Bid
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class BidRepository(BaseRepository[BidBase, Bid]):
    __model__: ClassVar[Bid] = Bid

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return BidBase.model_validate(data, from_attributes=True)

    def uuid_to_lock_id(self, uuid_val: UUID) -> int:
        """Converts a UUID into a deterministic 64-bit integer lock key."""
        # Using CRC32 or hashing to convert UUID bytes into a 64-bit integer
        return zlib.crc32(uuid_val.bytes)

    async def insert_bid_with_advisory_lock(self, payload: CreateAuctionBid) -> Any:
        # 1. Generate deterministic 64-bit lock key for this specific auction
        lock_key = self.uuid_to_lock_id(uuid.UUID(payload.auction_id))

        # 2. Acquire transaction-level advisory lock
        # This blocks other concurrent transactions for the SAME auction until this transaction commits/rolls back.
        await self.session.execute(
            select(func.pg_advisory_xact_lock(lock_key))
        )

        # 3. Read the latest highest bid (No row lock needed now!)
        current_highest = (
            await self.session.execute(
                select(func.coalesce(Auction.highest_bid, 0.0)).where(Auction.id == payload.auction_id)
            )
        ).scalar_one()

        # 4. Guard check
        if payload.bid_amount < (current_highest + 1.0):
            await self.session.rollback()  # Releases lock immediately
            return None

        # 5. Insert Bid
        bid_stmt = (
            insert(Bid)
            .values(
                amount=payload.bid_amount,
                auction_id=payload.auction_id,
                user_id=payload.user_id,
                created_at=func.clock_timestamp(),
            )
            .returning(Bid)
        )
        bid_result = (await self.session.execute(bid_stmt)).scalar_one()

        # 6. Update Auction cached highest bid
        await self.session.execute(
            update(Auction)
            .values(highest_bid=payload.bid_amount)
            .where(Auction.id == payload.auction_id)
        )

        # 7. Commit transaction (Automatically releases pg_advisory_xact_lock)
        await self.session.commit()

        return self.domain_model(bid_result)

    async def insert_bid_by_sql_check(self, payload: CreateAuctionBid) -> Any:
        """
        Attempt to insert with one query
        """
        # 1. Lock parent auction row inside CTE
        lock_auction_cte = (
            select(Auction).where(Auction.id == payload.auction_id).with_for_update().cte("locked_auction")
        )

        # 3. Guard insertion against locked max
        payload_stmt = (
            select(
                literal(payload.bid_amount),
                cast(literal(payload.auction_id), UUID),
                cast(literal(payload.user_id), UUID),
                func.clock_timestamp(),
            )
            .select_from(lock_auction_cte)  # Forces lock execution first
            .where(
                literal(payload.bid_amount) >= (func.coalesce(lock_auction_cte.c.highest_bid, 0) + 1),
            )
        )

        insert_stmt = (
            insert(Bid).from_select(["amount", "auction_id", "user_id", "created_at"], payload_stmt).returning(Bid)
        )

        bid_result = (await self.session.execute(insert_stmt)).scalar_one_or_none()

        if not bid_result:
            await self.session.rollback()
            return None  # Price was out-of-date or invalid

        await self.session.execute(
            update(Auction).values(highest_bid=bid_result.amount).where(Auction.id == payload.auction_id)
        )

        await self.session.commit()

        return self.domain_model(bid_result)

    async def insert_bid(self, payload: CreateAuctionBid) -> BidBase:
        """
        Attempt to insert a bid with contention in mind for locking
        """
        await self.session.execute(text("SET LOCAL lock_timeout = '500ms';"))

        auction_top_query = select(Auction).where(Auction.id == payload.auction_id).with_for_update()

        auction_res = await self.session.execute(auction_top_query)
        auction = auction_res.scalar_one_or_none()

        if not auction:
            logger.info("[InsertBid] auction not found...")
            raise NotFoundException("Auction not found")

        bid = Bid(amount=payload.bid_amount, auction_id=payload.auction_id, user_id=payload.user_id)
        highest_bid = auction.highest_bid

        if highest_bid:
            min_required = highest_bid + 1.0
            max_allowed = highest_bid + 100.0

            if payload.bid_amount < min_required or payload.bid_amount > max_allowed:
                logger.info(f"[InsertBid] bid is not allowed...{min_required} - {max_allowed}")
                raise BadRequestException(f"Bid amount must be between {min_required} and {max_allowed}")

        logger.info(f"[InsertBid] inserting bid {payload.bid_amount}")
        auction.highest_bid = payload.bid_amount
        self.session.add(bid)
        await self.session.commit()
        return self.domain_model(bid)
