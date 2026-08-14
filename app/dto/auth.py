from typing import Optional
from uuid import UUID

from pydantic import Field

from app.core.schema import BaseModel


class RegisterUserDto(BaseModel):
    full_name: str
    email: str
    password: str


class LoginUserDto(BaseModel):
    email: str
    password: str


class UserSession(BaseModel):
    session_id: Optional[UUID] = Field(default=None)
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
