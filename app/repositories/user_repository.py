from typing import Any, Optional

from app.domain.auth import UserBase
from app.domain.base import BaseDomain
from app.models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[UserBase, User]):
    __model__ = User

    def domain_model(self, data: dict[str, Any], as_domain: Optional[BaseDomain] = None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return UserBase.model_validate(data, from_attributes=True)
