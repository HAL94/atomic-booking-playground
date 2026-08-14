import logging
import traceback

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistException, UnauthorizedException
from app.core.security.jwt import JwtManager, hash_password, hash_token, verify_password
from app.core.security.schema import JwtPayload, TokenType
from app.domain.auth import UserBase, UserWithoutPassword
from app.dto.auth import LoginUserDto, RegisterUserDto, UserSession
from app.dto.session import CreateSessionDto
from app.repositories.user_repository import UserRepository
from app.services.base import BaseService
from app.services.session import SessionService

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class AuthService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self._user_repo = UserRepository(session)
        self._session_service = SessionService(session)

    async def register(self, data: RegisterUserDto) -> UserWithoutPassword:
        try:
            # verify if exists, will throw if not by default
            found_user = await self._user_repo.get_one_or_none([UserBase.model.email == data.email])

            if found_user:
                raise AlreadyExistException

            hashed_password = hash_password(data.password)
            create_user = UserBase(
                full_name=data.full_name,
                email=data.email,
                hashed_password=hashed_password,
            )

            result = await self._user_repo.create_one(create_user, commit=True)

            return UserWithoutPassword.model_validate(result)
        except Exception as e:
            logger.info(f"[AuthService-register]: {e}")
            raise e

    async def login(self, data: LoginUserDto) -> UserSession:
        try:
            found_user: UserBase = await self._user_repo.get_one([UserBase.model.email == data.email])

            is_match = verify_password(data.password, found_user.hashed_password)

            if not is_match:
                raise UnauthorizedException()

            access_token = JwtManager.create_token(subject=found_user.email, token_type=TokenType.AccessToken)
            refresh_token = JwtManager.create_token(subject=found_user.email, token_type=TokenType.RefreshToken)

            user_session = await self._session_service.create_session(
                CreateSessionDto(
                    refresh_token=refresh_token,
                    access_token=access_token,
                    expires_at=JwtManager.get_expiry(TokenType.RefreshToken),
                    user_id=found_user.id,
                )
            )
            return UserSession(access_token=access_token, refresh_token=refresh_token, session_id=user_session.id)
        except Exception as e:
            logger.error(f"[AuthService-login]: {str(e)}")
            raise e

    async def refresh_session(self, rt_encoding: str) -> UserSession:
        try:
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            rt_token = JwtManager.validate_rt_cookie(rt_encoding)
            jwt_payload: JwtPayload = JwtManager.verify_token(rt_token)

            if jwt_payload.type != TokenType.RefreshToken:
                raise credentials_exception

            email = jwt_payload.sub
            found_user = await self._user_repo.get_one([email == UserBase.model.email])

            user_session = await self._session_service.get_session_by_rt_hash(hash_token(rt_token))
            if not user_session.is_active:
                raise credentials_exception

            new_access_token = JwtManager.create_token(subject=email, token_type=TokenType.AccessToken)
            new_refresh_token = JwtManager.create_token(subject=email, token_type=TokenType.RefreshToken)

            await self._session_service.logout_from_session(rt_token)

            new_session = await self._session_service.create_session(
                CreateSessionDto(
                    refresh_token=new_refresh_token,
                    access_token=new_access_token,
                    expires_at=JwtManager.get_expiry(TokenType.RefreshToken),
                    user_id=found_user.id,
                )
            )
            return UserSession(
                access_token=new_access_token, refresh_token=new_refresh_token, session_id=new_session.id
            )
        except Exception as e:
            logger.error(f"[AuthService-refresh]: {e}")
            traceback.print_exc()
            raise credentials_exception
