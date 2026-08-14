from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.exceptions import NotFoundException
from app.core.schema import AppResponse
from app.core.security.jwt import JwtManager
from app.dependencies.auth import CurrentUser, RtCookie
from app.dependencies.db_session import DbSession
from app.domain.auth import UserWithoutPassword
from app.dto.auth import LoginUserDto, RegisterUserDto, UserSession
from app.services.auth import AuthService
from app.services.session import SessionService

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/login", response_model=AppResponse[UserSession])
async def login_user(
    response: Response,
    body: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DbSession,
) -> UserSession:
    """OAuth2 compatible token login.

    Returns access token and refresh token.
    """
    try:
        auth_service = AuthService(session=session)
        login_body = LoginUserDto(email=body.username, password=body.password)
        tokens = await auth_service.login(login_body)

        response.set_cookie(**JwtManager.rt_cookie_options(tokens.refresh_token))
        response.set_cookie(**JwtManager.at_cookie_options(tokens.access_token))

        return AppResponse(data=tokens)
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong") from e


@auth_router.post("/register")
async def register_user(
    body: RegisterUserDto, session: DbSession
) -> UserWithoutPassword:
    """Register a new user."""
    try:
        auth_service = AuthService(session=session)
        return await auth_service.register(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong") from e


@auth_router.get("/me")
async def get_user(user: CurrentUser) -> AppResponse[UserWithoutPassword]:
    return AppResponse(data=user)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(rt_encoding: RtCookie, session: DbSession):
    try:
        session_service = SessionService(session=session)
        await session_service.logout_from_session(JwtManager.validate_rt_cookie(rt_encoding))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong") from e


@auth_router.post("/refresh", response_model=AppResponse[UserSession])
async def refresh_token(rt_encoding: RtCookie, response: Response, session: DbSession) -> AppResponse[UserSession]:
    try:
        if not rt_encoding:
            raise HTTPException(status_code=401, detail="Not authorized for refresh")
        auth_service = AuthService(session=session)
        tokens = await auth_service.refresh_session(rt_encoding=rt_encoding)
        response.set_cookie(**JwtManager.rt_cookie_options(tokens.refresh_token))
        response.set_cookie(**JwtManager.at_cookie_options(tokens.access_token))
        return AppResponse(data=tokens)
    except Exception as e:
        raise e
