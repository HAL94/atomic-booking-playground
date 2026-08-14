from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.jwt import hash_token
from app.domain.session import SessionBase
from app.dto.session import CreateSessionDto
from app.repositories.session_repository import SessionRepository
from app.services.base import BaseService


class SessionService(BaseService):
    def __init__(self, session: AsyncSession):
        super().__init__(session=session)
        self._session_repo = SessionRepository(session)

    async def get_session_by_rt_hash(self, rt_hash: str):
        try:
            return await self._session_repo.get_one([SessionBase.model.refresh_token_hash == rt_hash])
        except Exception as e:
            raise e

    async def create_session(self, data: CreateSessionDto, *, commit: bool = True) -> SessionBase:
        try:
            data_base = SessionBase(
                refresh_token_hash=hash_token(data.refresh_token),
                access_token_hash=hash_token(data.access_token),
                expires_at=data.expires_at,
                user_id=data.user_id,
            )
            return await self._session_repo.create_one(data_base, commit=commit)
        except Exception as e:
            raise e

    async def logout_from_session(self, refresh_token: str) -> None:
        try:
            rt_hash = hash_token(refresh_token)
            session = await self.get_session_by_rt_hash(rt_hash)
            session.is_active = False

            session_by_rt_hash = SessionBase.model.refresh_token_hash == rt_hash
            await self._session_repo.update(session, [session_by_rt_hash], commit=True)
        except Exception:
            return None
