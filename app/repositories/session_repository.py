from app.domain.session import SessionBase
from app.models import Session
from app.repositories.base_repository import BaseRepository


class SessionRepository(BaseRepository[SessionBase, Session]):
    __model__ = Session

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return SessionBase.model_validate(data, from_attributes=True)
