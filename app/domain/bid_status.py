from enum import StrEnum


class BidStatus(StrEnum):
    PROCESSING = "processing"
    PENDING = "pending"
    REJECTED = "rejected"
    PROCESSED = 'processed'
