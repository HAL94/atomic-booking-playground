from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession


class BaseService(ABC):
    """
    Base service class providing common patterns for all services.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
