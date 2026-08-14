import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Literal, Optional, Union

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security.schema import JwtPayload, TokenType
from app.core.security.signer import CookieSigner

password_hash = PasswordHash.recommended()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def hash_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode()).hexdigest()


class JwtCookieOptions(BaseModel):
    key: str
    value: str
    max_age: Optional[int] = Field(default=None)
    expires: Optional[datetime | str | int] = Field(default=None)
    samesite: Optional[Literal["lax", "strict", "none"]] = Field(defualt="lax")
    path: Optional[str] = Field(default="/")
    domain: Optional[str] = Field(default=None)
    secure: Optional[bool] = Field(default=False)
    httponly: Optional[bool] = Field(default=False)


class JwtManager:
    RT_COOKIE_KEY: str = "rtc"
    AT_COOKIE_KEY: str = "atc"

    signer: CookieSigner = CookieSigner()

    @classmethod
    def at_cookie_options(cls, value: str) -> Dict[str, Any]:
        return JwtCookieOptions(
            key=cls.AT_COOKIE_KEY,
            value=cls.signer.dumps(value),
            expires=cls.get_expiry(TokenType.AccessToken),
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "prod",
        ).model_dump()

    @classmethod
    def rt_cookie_options(cls, value: str) -> Dict[str, Any]:
        return JwtCookieOptions(
            key=cls.RT_COOKIE_KEY,
            value=cls.signer.dumps(value),
            expires=cls.get_expiry(TokenType.RefreshToken),
            httponly=True,
            samesite="lax",
            secure=settings.ENV == "prod",
        ).model_dump()

    @classmethod
    def validate_rt_cookie(cls, value: str) -> str:
        return cls.signer.loads(value, settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60)

    @classmethod
    def validate_at_cookie(cls, value: str) -> str:
        return cls.signer.loads(value, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    @classmethod
    def get_expiry(cls, token_type: TokenType, expire_delta: Union[timedelta | None] = None) -> datetime:
        if expire_delta is not None and isinstance(expire_delta, timedelta):
            return datetime.now(tz=UTC) + expire_delta

        duration_by_type = None

        if token_type == TokenType.AccessToken:
            duration_by_type = float(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        elif token_type == TokenType.RefreshToken:
            duration_by_type = float(settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        else:
            raise ValueError(f"Unknown type of {token_type}")

        return datetime.now(tz=UTC) + timedelta(minutes=duration_by_type)

    @classmethod
    def create_token(cls, *, subject: str, token_type: TokenType) -> str:
        try:
            logger.info(f"[JwtManager]: creating token with subject: {subject} and type: {token_type}")
            if subject is None:
                raise ValueError("'subject' cannot be None")
            if token_type is None:
                raise ValueError("'token_type' cannot be None")

            exp = cls.get_expiry(token_type=token_type)
            payload = JwtPayload(sub=subject, exp=exp, type=token_type, iat=datetime.now())

            return jwt.encode(payload.model_dump(by_alias=False), settings.JWT_SECRET, algorithm=settings.ALGORITHM)
        except Exception as e:
            raise e

    @classmethod
    def verify_token(cls, token: str) -> JwtPayload:
        try:
            result = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])

            return JwtPayload.model_validate(result, from_attributes=True)
        except Exception as e:
            raise e
