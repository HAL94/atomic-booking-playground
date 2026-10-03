from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, WriteOnlyMapped, mapped_column, relationship

from app.constants.roles import UserRole
from app.core.database import Base
from app.domain.cart_status import CartReservationStatus, CartStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String, default=UserRole.USER.value, nullable=False)

    # Relations
    sessions: Mapped[List["Session"]] = relationship(back_populates="user", cascade="all, delete")
    reservations: WriteOnlyMapped["CartReservation"] = relationship(back_populates="reservation_owner")
    cart_items: WriteOnlyMapped["CartItem"] = relationship(back_populates="customer")
    cart: Mapped["Cart"] = relationship(back_populates="customer")

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    refresh_token_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)
    access_token_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    device_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relations
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="sessions")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column()
    sku: Mapped[str] = mapped_column(unique=True)
    price_cents: Mapped[int] = mapped_column()

    # relationships
    cart_items: WriteOnlyMapped["CartItem"] = relationship(back_populates="product")

    __table_args__ = (CheckConstraint("price_cents >= 0", name="is_price_pos"),)


class Inventory(Base):
    __tablename__ = "inventory"

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), primary_key=True)
    stock: Mapped[int] = mapped_column()
    reserved_stock: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        CheckConstraint("stock > 0", "is_stock_available"),
        CheckConstraint("reserved_stock >= 0", "is_stock_reserve_valid"),
    )


class CartReservation(Base):
    __tablename__ = "cart_reservations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    cart_id: Mapped[UUID] = mapped_column(ForeignKey("carts.id"))
    status: Mapped[str] = mapped_column(default=CartReservationStatus.PENDING)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # relationships
    cart: Mapped["Cart"] = relationship(back_populates="reservations")
    reservation_owner: Mapped[User] = relationship(back_populates="reservations")

    __table_args__ = (
        Index(
            "ix_cart_res_pending",
            "cart_id",
            "status",
            unique=True,
            postgresql_where=(status == CartReservationStatus.PENDING.value),
        ),
    )


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), default=uuid4
    )
    status: Mapped[str] = mapped_column(default=CartStatus.ACTIVE)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    total: Mapped[float] = mapped_column()

    # relations
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="cart", lazy="selectin")
    customer: Mapped["User"] = relationship(back_populates="cart", lazy="joined")
    reservations: WriteOnlyMapped["CartReservation"] = relationship(back_populates="cart")

    __table_args__ = (
        Index(
            "ix_customer_cart_status",
            "customer_id",
            "status",
            unique=True,
            postgresql_where=(status == CartStatus.ACTIVE.value),
        ),
    )

    @property
    def cart_total(self) -> float:
        total_cents = sum(item.quantity * item.unit_price_cents for item in self.cart_items)
        return round(total_cents / 100, 2)


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), default=uuid4
    )
    cart_id: Mapped[UUID] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"))
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    quantity: Mapped[int] = mapped_column()
    unit_price_cents: Mapped[int] = mapped_column()

    # relationships
    product: Mapped[Product] = relationship(back_populates="cart_items")
    customer: Mapped[User] = relationship(back_populates="cart_items")
    cart: Mapped[Cart] = relationship(back_populates="cart_items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="is_qty_pos"),
        UniqueConstraint("cart_id", "product_id", name="ux_cart_product_id"),
    )
