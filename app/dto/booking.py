from app.core.schema import BaseModel


class CreateReservation(BaseModel):
    # In reality, we may fallback to let's say something like a show id instead
    ticket_price: float
