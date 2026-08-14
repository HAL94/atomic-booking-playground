from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.models import Session


class SessionBase(BaseDomain[Session]):
    model: ClassVar[type[Session]] = Session

    id: Optional[UUID] = Field(default=None)
    refresh_token_hash: str
    access_token_hash: str
    expires_at: datetime

    is_active: Optional[bool] = Field(default=True)
    last_used_at: Optional[datetime] = Field(default=datetime.now)

    device_name: Optional[str] = None
    device_type: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    user_id: UUID
