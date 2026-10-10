import logging

from sqlalchemy import exists, select

from app.core.database import session_manager
from app.domain.bid_status import BidStatus
from app.models import Auction, Bid, BidInbox

logger = logging.getLogger(__name__)


async def bid_processor_loop(worker_id: str):
    try:
        logger.info(f"[BidInboxProcessor]: {worker_id} started..")

        async with session_manager.session() as session:
            has_pending = exists().where(BidInbox.auction_id == Auction.id, BidInbox.status == BidStatus.PENDING)
            auction_target_stmt = select(Auction).where(has_pending).limit(1).with_for_update(skip_locked=True)
            auction = await session.scalar(auction_target_stmt)

            if not auction:
                logger.debug(f"[BidProcessingWorker]: {worker_id} no auction found. Returning...")
                return

            batch_bids_stmt = (
                select(BidInbox)
                .where(BidInbox.status == BidStatus.PENDING, BidInbox.auction_id == auction.id)
                .order_by(BidInbox.created_at.asc())
                .limit(50)
                .with_for_update(skip_locked=True)
            )
            logger.info(f"[BidProcessingWorker]: auction id {auction.id}")

            batched_bids = (await session.scalars(batch_bids_stmt)).all()
            if not batched_bids:
                logger.debug(f"[BidProcessingWorker]: {worker_id} no bids to process. Returning...")
                return

            bids_inserted = 0
            for bid_inbox in batched_bids:
                if not auction.highest_bid or (
                    bid_inbox.amount >= auction.highest_bid + 1 and bid_inbox.amount <= auction.highest_bid + 100
                ):
                    auction.highest_bid = bid_inbox.amount
                    created_bid = Bid(
                        amount=bid_inbox.amount,
                        auction_id=bid_inbox.auction_id,
                        user_id=bid_inbox.user_id,
                        created_at=bid_inbox.created_at,
                        updated_at=bid_inbox.updated_at,
                    )
                    session.add(created_bid)
                    bids_inserted += 1
                    bid_inbox.status = BidStatus.PROCESSED
                else:
                    bid_inbox.status = BidStatus.REJECTED
            await session.commit()
            logger.info(f"[BidInboxProcessor]: worker {worker_id} inserted {bids_inserted} bids")
    except Exception as e:
        logger.exception(f"[BidInboxProcessor]: worker {worker_id} failed {str(e)}")
