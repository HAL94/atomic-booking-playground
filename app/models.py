from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.roles import UserRole
from app.core.database import Base
from app.domain.booking_status import BookingStatus


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
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
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


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    ticket_price: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column()

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user: Mapped[User] = relationship(back_populates="bookings")

    seat_id: Mapped[UUID] = mapped_column(ForeignKey("seats.id", ondelete="SET NULL"), nullable=True)
    seat: Mapped["Seat"] = relationship(back_populates="booking")

    __table_args__ = (
        Index(
            "uc_seat_id_status",
            "status",
            "seat_id",
            unique=True,
            postgresql_where=((status == BookingStatus.PENDING.value) | (status == BookingStatus.CONFIRMED.value)),
        ),
    )


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column()

    is_booked: Mapped[bool] = mapped_column(server_default=text("false"))
    is_held: Mapped[bool] = mapped_column(server_default=text("false"))

    booking: Mapped[Booking] = relationship(back_populates="seat")
