from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.domain.bid_status import BidStatus
from app.models import Auction


class AuctionBase(BaseDomain):
    model: ClassVar[Auction] = Auction

    id: Optional[str | UUID] = Field(default=None)
    name: str
    status: BidStatus = Field(default=BidStatus.SCHEDULED)
    ended_at: Optional[datetime] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    scheduled_at: datetime
    auction_owner_id: Optional[UUID | str] = Field(default=None)
