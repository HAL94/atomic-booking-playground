from enum import StrEnum


class BidStatus(StrEnum):
    SCHEDULED = "scheduled"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    ENDED = "ended"
