import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer

from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.security.jwt import JwtManager, hash_token
from app.core.security.schema import JwtPayload, TokenType
from app.dependencies.db_session import DbSession
from app.domain.auth import UserBase, UserWithoutPassword
from app.domain.session import SessionBase
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

logger = logging.getLogger("uvicorn.info")
logger.setLevel(logging.INFO)


RtCookie = Annotated[str, Depends(APIKeyCookie(name=JwtManager.RT_COOKIE_KEY))]
AtCookie = Annotated[str, Depends(APIKeyCookie(name=JwtManager.AT_COOKIE_KEY, auto_error=False))]


async def get_current_user(token_encoding: AtCookie, session: DbSession) -> UserWithoutPassword:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = JwtManager.validate_at_cookie(token_encoding)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        validated_payload = JwtPayload.model_validate(payload)

        if not validated_payload:
            logger.info(f"[GetCurrentUser]: payload not valid: {validated_payload}")
            raise credentials_exception
        if validated_payload.type != TokenType.AccessToken:
            logger.info(f"[GetCurrentUser]: token is not AccessToken: {validated_payload}")
            raise credentials_exception

        email = validated_payload.sub
        if not email:
            logger.info(f"[GetCurrentUser]: email is None {email}")
            raise credentials_exception

        session_repo = SessionRepository(session)
        session_by_at_hash = [hash_token(token) == SessionBase.model.access_token_hash]
        fetched_session = await session_repo.get_one_or_none(session_by_at_hash)

        if not fetched_session.is_active:
            logger.info(f"[GetCurrentUser]: session is not Active {fetched_session}")
            raise credentials_exception

        user_repo = UserRepository(session)
        user_by_email = [UserBase.model.email == email]
        user_data = await user_repo.get_one(user_by_email)
        if not user_data.is_active:
            logger.info(f"[GetCurrentUser]: user is not Active {user_data}")
            raise credentials_exception

        return UserWithoutPassword.model_validate(user_data)
    except jwt.InvalidTokenError as e:
        logger.info(f"[get_current_user] Error occured: {e.__str__()}")
        raise credentials_exception
    except NotFoundException as e:
        logger.info(f"[get_current_user] not found: {e.__str__()}")
        raise credentials_exception
    except Exception as e:
        logger.info(f"Exception at handler: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[UserBase, Depends(get_current_user)],
) -> UserWithoutPassword:
    return current_user


CurrentUser = Annotated[UserWithoutPassword, Depends(get_current_active_user)]
