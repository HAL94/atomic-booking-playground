from enum import StrEnum


class CartReservationStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELED = "canceled"


class CartStatus(StrEnum):
    ACTIVE = "active"
    PAYED = "PAYED"
    DROPPED = "dropped"
