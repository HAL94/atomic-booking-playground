from app.core.schema import BaseModel


class AuctionWinner(BaseModel):
    auction_id: str
    bid_id: str
