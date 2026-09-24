import logging
from datetime import datetime, timezone
from typing import Any, ClassVar

from fastapi import HTTPException
from sqlalchemy import UUID, cast, func, insert, literal, select
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import BadRequestException, NotFoundException
from app.domain.bid import BidBase
from app.dto.bid import CreateAuctionBid
from app.models import Auction, AuctionWinner, Bid
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class BidRepository(BaseRepository[BidBase, Bid]):
    __model__: ClassVar[Bid] = Bid

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return BidBase.model_validate(data, from_attributes=True)

    async def insert_bid_by_sql_check(self, payload: CreateAuctionBid) -> Any:
        """
        Attempt to insert with one query
        """
        # 1. Lock parent auction row inside CTE
        lock_auction_cte = (
            select(Auction.id)
            .where(Auction.id == payload.auction_id)
            .with_for_update()
            .cte("locked_auction")
        )

        # 2. Compute current max bid AFTER lock is acquired
        max_stmt = (
            select(func.coalesce(func.max(Bid.amount), 0).label("max_val"))
            .where(Bid.auction_id == payload.auction_id)
            .scalar_subquery()
        )

        # 3. Guard insertion against locked max
        payload_stmt = (
            select(
                literal(payload.bid_amount),
                cast(literal(payload.auction_id), UUID),
                cast(literal(payload.user_id), UUID),
            )
            .select_from(lock_auction_cte)  # Forces lock execution first
            .where(literal(payload.bid_amount) >= max_stmt + 1)
        )

        insert_stmt = (
            insert(Bid)
            .from_select(["amount", "auction_id", "user_id"], payload_stmt)
            .returning(Bid)
        )

        bid_result = (await self.session.execute(insert_stmt)).scalar_one_or_none()
        await self.session.commit()

        if not bid_result:
            return None  # Price was out-of-date or invalid

        return self.domain_model(bid_result)

    async def insert_bid(self, payload: CreateAuctionBid) -> BidBase:
        """
        Attempt to insert a bid with contention in mind for locking
        """
        auction_top_query = (
            select(Auction, AuctionWinner, Bid)
            .join(AuctionWinner, AuctionWinner.auction_id == Auction.id, isouter=True)
            .join(Bid, AuctionWinner.bid_id == Bid.id, isouter=True)
            .where(Auction.id == payload.auction_id)
            .with_for_update(of=[Auction])
        )

        auction_res = await self.session.execute(auction_top_query)
        auction_res = auction_res.mappings().one_or_none()

        if not auction_res:
            raise NotFoundException("Auction not found")

        # logger.info(f"[InsertBid] auction result: {auction_res}")

        auction, auction_winner, highest_bid = (
            auction_res["Auction"],
            auction_res["AuctionWinner"],
            auction_res["Bid"],
        )

        if not auction:
            raise NotFoundException("Auction not found")

        auction_track = auction_winner
        bid = Bid(amount=payload.bid_amount, auction_id=payload.auction_id, user_id=payload.user_id)

        if highest_bid:
            min_required = highest_bid.amount + 1.0
            max_allowed = highest_bid.amount + 100.0

            if payload.bid_amount < min_required or payload.bid_amount > max_allowed:
                raise BadRequestException(f"Bid amount must be between {min_required} and {max_allowed}")

        self.session.add(bid)
        await self.session.flush()

        if auction_track:
            auction_track.winning_bid = bid
            auction_track.updated_at = datetime.now(tz=timezone.utc)
        else:
            auction_track = AuctionWinner(auction_id=payload.auction_id, winning_bid=bid)
            self.session.add(auction_track)

        await self.session.commit()
        return self.domain_model(bid)
