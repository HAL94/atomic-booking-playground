from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, WriteOnlyMapped, mapped_column, relationship

from app.constants.roles import UserRole
from app.core.database import Base
from app.dto.seat import SeatStatus


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
    holds: WriteOnlyMapped["SeatHold"] = relationship(back_populates="seat_holder")

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


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column()
    # can add other foreign keys to link for events/avenues/showrooms etc.. keep it simple for now

    holds: WriteOnlyMapped["SeatHold"] = relationship(back_populates="seat")


class SeatHold(Base):
    __tablename__ = "seat_holds"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    seat_id: Mapped[UUID] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"), unique=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    seat: Mapped[Seat] = relationship(back_populates="holds")
    seat_holder: Mapped[User] = relationship(back_populates="holds")

