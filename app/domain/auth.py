from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.constants.roles import UserRole
from app.domain.base import BaseDomain
from app.models import User


class UserBase(BaseDomain[User]):
    model: ClassVar[User] = User

    id: Optional[UUID] = None
    full_name: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    role: UserRole = UserRole.USER


class UserWithoutPassword(UserBase):
    hashed_password: Optional[str] = Field(exclude=True, default=None)
