from typing import Annotated

from fastapi import Depends

from app.core.database.session import session_manager


async def get_async_session():
    async with session_manager.session() as session:
        yield session

DbSession = Annotated[str, Depends(get_async_session)]
