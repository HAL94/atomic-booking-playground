from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from app.core.database.session import session_manager


async def get_async_session():
    async with session_manager.session() as session:
        yield session


TdbSession = Annotated[AsyncSession, TaskiqDepends(get_async_session)]
