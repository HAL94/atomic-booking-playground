import logging
import traceback
from datetime import datetime, timezone
from uuid import UUID

from app.core.database import session_manager
from app.models import JobLedger

from .utils import JobStatus

logger = logging.getLogger(__name__)


class LedgerManager:
    def __init__(self):
        self.session = session_manager._session_maker()

    async def start_job(self, job_name: str, worker_node: str) -> UUID:
        ledger_entry = JobLedger(
            job_name=job_name,
            status=JobStatus.RUNNING,
            worker_node=worker_node,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(ledger_entry)
        await self.session.commit()
        return ledger_entry.id

    async def mark_success(self, ledger_id: UUID, items_processed: int):
        entry = await self.session.get(JobLedger, ledger_id)
        if entry:
            entry.status = JobStatus.COMPLETED
            entry.finished_at = datetime.now(timezone.utc)
            entry.items_processed = items_processed
            await self.session.commit()

    async def mark_failed(self, ledger_id: UUID, error: Exception):
        entry = await self.session.get(JobLedger, ledger_id)
        if entry:
            entry.status = JobStatus.FAILED
            entry.finished_at = datetime.now(timezone.utc)
            entry.error_log = f"{str(error)}\n\n{traceback.format_exc()}"
            await self.session.commit()
