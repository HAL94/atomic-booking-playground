from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.models import Bid


class BidBase(BaseDomain):
    model: ClassVar[Bid] = Bid

    id: Optional[UUID | str] = Field(default=None)
    amount: float
    bid_ts: Optional[int] = Field(default=None)
    bid_seq: Optional[int] = Field(default=None)
