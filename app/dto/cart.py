from enum import StrEnum
from uuid import UUID

from app.core.schema import BaseModel


class AddItemDto(BaseModel):
    product_id: UUID | str


class UpdateItemOp(StrEnum):
    INC = "inc"
    DEC = "dec"


class CartItemUpdateDto(BaseModel):
    update_op: UpdateItemOp
