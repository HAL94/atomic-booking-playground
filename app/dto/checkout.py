from uuid import UUID

from app.core.schema import BaseModel

# {
#   "items": [
#     {"product_id": "prod_PHONE", "quantity": 1},
#     {"product_id": "prod_CASE", "quantity": 2}
#   ]
# }

class CartItemDto(BaseModel):
    product_id: UUID | str
    quantity: int


class CheckoutDto(BaseModel):
    items: list[CartItemDto]
