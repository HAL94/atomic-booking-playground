from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import field_validator

from app.domain.base import BaseDomain
from app.domain.bid_status import BidStatus
from app.models import BidInbox


class BidInboxBase(BaseDomain[BidInbox]):
    model: ClassVar[BidInbox] = BidInbox

    id: UUID | str | None = None
    auction_id: UUID | str
    user_id: UUID | str
    amount: float
    status: BidStatus | None = None
    created_at: datetime | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def transform_amount(cls, v: float) -> float | None:
        if not v:
            return v
        return round(v, 2)
