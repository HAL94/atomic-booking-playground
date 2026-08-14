from datetime import datetime
from enum import StrEnum

from app.core.schema import BaseModel


class TokenType(StrEnum):
    """
    Types for tokens
    """
    AccessToken = "access"
    RefreshToken = "refresh"


class JwtPayload(BaseModel):
    """
    JWT Payload
    """
    sub: str
    iat: datetime
    exp: datetime
    type: TokenType
