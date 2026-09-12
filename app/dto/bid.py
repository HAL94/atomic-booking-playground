from app.core.schema import BaseModel


class CreateBidAmount(BaseModel):
    bid_amount: int


class CreateAuctionBid(BaseModel):
    bid_amount: int
    user_id: str
    auction_id: str


class CreateBidResponse(BaseModel):
    message: str
