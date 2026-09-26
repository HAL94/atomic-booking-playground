from enum import StrEnum


class SeatStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    BOOKED = "BOOKED"
    CANCELED = "CANCELED"
